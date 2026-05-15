"""
StockSage 组合级回测
- 月度再平衡，等权 / 凯利 / 波动率加权三种仓位算法对比
- 逐日追踪 NAV，含交易成本（0.15% 单边）
- 板块集中度限制：单板块 ≤ 40%，单股 ≤ 30%
- 基准：沪深300买入持有
- 输出：NAV曲线、月度收益、完整绩效指标
"""
import sys
import warnings
import pandas as pd
import numpy as np
import akshare as ak
warnings.filterwarnings("ignore")

# 复用 stock_picker 的数据/选股函数
sys.path.insert(0, "/path/to/stock-sage")
from backend.backtest.stock_picker import (
    CANDIDATE_POOL, BT_EVAL_START, BT_EVAL_END, WARMUP, HS300_SYM,
    get_cn, get_index, precompute, precompute_index,
    pick_stocks,
)
from backend.portfolio.combo_weights import size_positions
from backend.config import settings

# ── 参数 ──────────────────────────────────────────────────────────────
INITIAL_CAPITAL = 1_000_000.0   # 初始资金（元）
COST_RATE       = 0.0015        # 单边交易成本（0.15%，含佣金+印花税）
MAX_POSITIONS   = 5             # 最多同时持仓股数
MAX_PER_STOCK   = settings.max_position_per_stock
MAX_PER_SECTOR  = settings.max_position_per_sector
MAX_TOTAL_EQUITY = settings.max_total_equity_pct

# 板块历史统计（来自 backtest_v3 2024-2026 实测）
# win_rate: 胜率, avg_win: 平均盈利%, avg_loss: 平均亏损%（绝对值）
SECTOR_STATS = {
    "有色金属": {"win_rate": 0.544, "avg_win": 9.2, "avg_loss": 4.1},
    "黄金矿业": {"win_rate": 0.353, "avg_win": 6.5, "avg_loss": 4.8},
    "AI算力":   {"win_rate": 0.500, "avg_win": 8.5, "avg_loss": 5.2},
    "半导体":   {"win_rate": 0.478, "avg_win": 7.8, "avg_loss": 4.9},
    "新能源":   {"win_rate": 0.418, "avg_win": 7.2, "avg_loss": 4.3},
    "电力":     {"win_rate": 0.413, "avg_win": 5.5, "avg_loss": 3.8},
    "能源矿业": {"win_rate": 0.381, "avg_win": 5.8, "avg_loss": 4.2},
    "消费":     {"win_rate": 0.333, "avg_win": 5.2, "avg_loss": 4.0},
    "医药":     {"win_rate": 0.333, "avg_win": 6.0, "avg_loss": 4.5},
    "银行":     {"win_rate": 0.422, "avg_win": 4.8, "avg_loss": 3.2},
    "化工":     {"win_rate": 0.500, "avg_win": 6.2, "avg_loss": 4.1},
    "军工":     {"win_rate": 0.425, "avg_win": 6.8, "avg_loss": 5.0},
    "基建":     {"win_rate": 0.294, "avg_win": 4.5, "avg_loss": 4.8},
}


# ── 核心：组合模拟引擎 ────────────────────────────────────────────────
def run_portfolio(stock_dfs: dict, index_df: pd.DataFrame,
                  method: str = "equal") -> dict:
    """
    月度再平衡组合模拟。

    Returns:
        {
          "nav":     pd.Series (逐日净值, 初始=1.0),
          "trades":  list[dict],
          "monthly": pd.DataFrame (月度收益率),
          "metrics": dict,
        }
    """
    # 收集所有交易日
    all_dates = sorted(set(
        d for df in stock_dfs.values()
        for d in df.index
        if BT_EVAL_START <= str(d.date()) <= BT_EVAL_END
    ))
    if not all_dates:
        return {}

    # 月首再平衡日
    rebalance_dates = []
    seen = set()
    for d in all_dates:
        m = (d.year, d.month)
        if m not in seen:
            seen.add(m)
            rebalance_dates.append(d)

    # 状态
    cash      = INITIAL_CAPITAL
    holdings  = {}   # {sym: {"shares": float, "cost": float}}
    nav_series = {}
    trade_log  = []

    def portfolio_value(date: pd.Timestamp) -> float:
        """按当日收盘价计算总市值"""
        val = cash
        for sym, pos in holdings.items():
            df = stock_dfs.get(sym)
            if df is None:
                continue
            rows = df[df.index <= date]
            if rows.empty:
                continue
            val += pos["shares"] * rows.iloc[-1]["close"]
        return val

    def liquidate_all(date: pd.Timestamp) -> None:
        """全部平仓，资金回收"""
        nonlocal cash
        for sym, pos in list(holdings.items()):
            df = stock_dfs.get(sym)
            if df is None:
                continue
            rows = df[df.index <= date]
            if rows.empty:
                continue
            price  = rows.iloc[-1]["close"]
            proceeds = pos["shares"] * price * (1 - COST_RATE)
            pnl_pct  = (price - pos["cost"]) / pos["cost"] * 100
            trade_log.append({
                "date": date.strftime("%Y-%m-%d"),
                "sym": sym,
                "action": "卖出",
                "price": round(price, 2),
                "pnl_pct": round(pnl_pct, 2),
            })
            cash += proceeds
        holdings.clear()

    def buy_positions(date: pd.Timestamp, picks_sized: list[dict],
                      total_val: float) -> None:
        """按权重买入"""
        nonlocal cash
        # 下一交易日开盘价买入
        next_dates = [d for d in all_dates if d > date]
        if not next_dates:
            return
        entry_date = next_dates[0]

        for p in picks_sized:
            sym = p["sym"]
            df  = stock_dfs.get(sym)
            if df is None:
                continue
            entry_rows = df[df.index == entry_date]
            if entry_rows.empty:
                continue
            price    = entry_rows.iloc[0]["open"]
            alloc    = total_val * p["weight"]
            cost_fee = alloc * COST_RATE
            net_alloc = alloc - cost_fee
            shares   = net_alloc / price
            cash    -= alloc
            holdings[sym] = {"shares": shares, "cost": price, "name": p["name"]}
            trade_log.append({
                "date": entry_date.strftime("%Y-%m-%d"),
                "sym": sym,
                "action": "买入",
                "price": round(price, 2),
                "weight": p["weight"],
                "pnl_pct": 0.0,
            })

    # 再平衡集合
    rb_set = set(rebalance_dates)

    prev_rb_val = INITIAL_CAPITAL
    for date in all_dates:
        # 月初再平衡
        if date in rb_set:
            total_val = portfolio_value(date)
            liquidate_all(date)
            picks = pick_stocks(date, stock_dfs, index_df, top_n=MAX_POSITIONS)
            if picks:
                # 补充 vol20（年化波动率）和 Kelly 统计字段
                for p in picks:
                    df = stock_dfs.get(p["sym"])
                    if df is not None:
                        past = df[df.index <= date]
                        if len(past) >= 22:
                            # 20日年化波动率（用收益率标准差计算，非成交量）
                            p["vol20"] = float(
                                past["close"].pct_change().rolling(20).std().iloc[-1]
                                * np.sqrt(252) * 100
                            )
                        else:
                            p["vol20"] = 30.0
                    # Kelly 用板块历史统计（来自 backtest_v3 实测）
                    p["win_rate"] = SECTOR_STATS.get(p["sector"], {}).get("win_rate", 0.50)
                    p["avg_win"]  = SECTOR_STATS.get(p["sector"], {}).get("avg_win",  5.0)
                    p["avg_loss"] = SECTOR_STATS.get(p["sector"], {}).get("avg_loss", 3.5)
                picks_sized = size_positions(picks, method=method,
                                             max_per=MAX_PER_STOCK,
                                             sector_max=MAX_PER_SECTOR)
                capped_val = min(total_val, INITIAL_CAPITAL * MAX_TOTAL_EQUITY)
                buy_positions(date, picks_sized, capped_val)
            prev_rb_val = total_val

        # 记录当日NAV
        nav_series[date] = portfolio_value(date) / INITIAL_CAPITAL

    # 强制平仓
    last_date = all_dates[-1]
    liquidate_all(last_date)
    nav_series[last_date] = cash / INITIAL_CAPITAL

    nav = pd.Series(nav_series).sort_index()
    metrics = _calc_metrics(nav, index_df, trade_log)
    monthly = _monthly_returns(nav)

    return {
        "nav":     nav,
        "trades":  trade_log,
        "monthly": monthly,
        "metrics": metrics,
    }


# ── 绩效计算 ─────────────────────────────────────────────────────────
def _calc_metrics(nav: pd.Series, index_df: pd.DataFrame,
                  trades: list) -> dict:
    total_return = (nav.iloc[-1] - 1) * 100
    daily_ret    = nav.pct_change().dropna()

    # 最大回撤
    peak = nav.cummax()
    dd   = (peak - nav) / peak * 100
    mdd  = dd.max()

    # 年化收益（从 BT_EVAL_START 到 BT_EVAL_END）
    days = (nav.index[-1] - nav.index[0]).days
    years = days / 365
    annualized = ((nav.iloc[-1]) ** (1 / max(years, 0.01)) - 1) * 100

    # 夏普（年化）
    rf_daily = 0.03 / 252
    excess   = daily_ret - rf_daily
    sharpe   = (excess.mean() / excess.std() * np.sqrt(252)
                if excess.std() > 0 else 0.0)

    # Calmar
    calmar = annualized / mdd if mdd > 0 else 0.0

    # 沪深300基准
    bt_idx = index_df[(index_df.index >= nav.index[0]) &
                      (index_df.index <= nav.index[-1])]
    hs300_ret = 0.0
    if len(bt_idx) >= 2:
        hs300_ret = (bt_idx.iloc[-1]["close"] - bt_idx.iloc[0]["close"]) / \
                     bt_idx.iloc[0]["close"] * 100

    # 胜率（卖出记录）
    sells  = [t for t in trades if t["action"] == "卖出"]
    wins   = [t for t in sells if t.get("pnl_pct", 0) > 0]
    win_rt = len(wins) / len(sells) * 100 if sells else 0.0

    # 月度胜率
    monthly_r = _monthly_returns(nav)
    mon_wins  = (monthly_r > 0).sum()
    mon_total = len(monthly_r)

    return {
        "total_return":  round(total_return, 2),
        "annualized":    round(annualized, 2),
        "hs300_return":  round(hs300_ret, 2),
        "alpha":         round(total_return - hs300_ret, 2),
        "mdd":           round(mdd, 2),
        "sharpe":        round(sharpe, 2),
        "calmar":        round(calmar, 2),
        "win_rate":      round(win_rt, 1),
        "n_trades":      len(sells),
        "monthly_win":   f"{mon_wins}/{mon_total}",
    }


def _monthly_returns(nav: pd.Series) -> pd.Series:
    """月度收益率（按月末NAV计算）"""
    monthly_nav = nav.resample("ME").last()
    return monthly_nav.pct_change().dropna() * 100


# ── 打印报告 ─────────────────────────────────────────────────────────
def print_report(result: dict, method: str) -> None:
    m   = result["metrics"]
    nav = result["nav"]

    labels = {"equal": "等权分配", "kelly": "凯利准则", "vol": "逆波动率"}
    print(f"\n{'─'*60}")
    print(f"  仓位方法：{labels.get(method, method)}")
    print(f"{'─'*60}")
    print(f"  总收益率  ：{m['total_return']:>+8.2f}%")
    print(f"  年化收益  ：{m['annualized']:>+8.2f}%")
    print(f"  沪深300   ：{m['hs300_return']:>+8.2f}%  (买入持有基准)")
    print(f"  超额收益α ：{m['alpha']:>+8.2f}%")
    print(f"  最大回撤  ：{m['mdd']:>8.2f}%")
    print(f"  夏普比率  ：{m['sharpe']:>8.2f}")
    print(f"  卡玛比率  ：{m['calmar']:>8.2f}")
    print(f"  交易胜率  ：{m['win_rate']:>7.1f}%  ({m['n_trades']} 笔卖出)")
    print(f"  月度胜率  ：{m['monthly_win']}")

    # 月度收益详情
    monthly = result["monthly"]
    if not monthly.empty:
        print(f"\n  月度收益（%）：")
        for dt, r in monthly.items():
            bar = "█" * int(abs(r) / 2) if abs(r) < 40 else "█" * 20
            sign = "+" if r >= 0 else ""
            color = "▲" if r >= 0 else "▼"
            print(f"    {dt.strftime('%Y-%m')}  {color}{sign}{r:>6.2f}%  {bar}")


def print_comparison(results: dict) -> None:
    """三种方法横向对比"""
    print(f"\n{'='*70}")
    print(f"  三种仓位算法对比  （{BT_EVAL_START} ~ {BT_EVAL_END}）")
    print(f"{'='*70}")
    print(f"  {'方法':8} {'总收益':>9} {'年化':>7} {'vs HS300':>9} "
          f"{'最大回撤':>8} {'夏普':>6} {'卡玛':>6} {'胜率':>7}")
    print(f"  {'-'*66}")
    for method, res in results.items():
        if not res:
            continue
        m  = res["metrics"]
        labels = {"equal": "等权", "kelly": "凯利", "vol": "逆波动率"}
        print(f"  {labels.get(method,method):8} "
              f"{m['total_return']:>+8.2f}% "
              f"{m['annualized']:>+6.2f}% "
              f"{m['alpha']:>+8.2f}% "
              f"{m['mdd']:>7.2f}% "
              f"{m['sharpe']:>5.2f} "
              f"{m['calmar']:>5.2f} "
              f"{m['win_rate']:>6.1f}%")
    hs = list(results.values())[0]["metrics"]["hs300_return"]
    print(f"  {'沪深300':8} {hs:>+8.2f}%    (买入持有基准)")


# ── 当前仓位快照（实盘参考） ──────────────────────────────────────────
def current_portfolio_snapshot(stock_dfs: dict, index_df: pd.DataFrame,
                                method: str = "equal") -> None:
    all_avail = sorted(set(d for df in stock_dfs.values() for d in df.index))
    if not all_avail:
        print("  暂无数据")
        return
    snap_date = all_avail[-1]

    from backend.backtest.stock_picker import is_bull
    is_bull_now = is_bull(index_df, snap_date) if not index_df.empty else True

    print(f"\n{'='*70}")
    print(f"  当前仓位建议  （截至 {snap_date.date()}，{method.upper()} 方法）")
    print(f"  大盘状态：{'牛市 ✅' if is_bull_now else '熊市 ⚠️  (建议空仓)'}")
    print(f"{'='*70}")

    if not is_bull_now:
        print("  熊市环境，本策略全部空仓")
        return

    picks = pick_stocks(snap_date, stock_dfs, index_df, top_n=MAX_POSITIONS)
    if not picks:
        print("  当前无符合条件的股票（信号不足）")
        return

    for p in picks:
        df = stock_dfs.get(p["sym"])
        if df is not None:
            past = df[df.index <= snap_date]
            if len(past) >= 22:
                p["vol20"] = float(
                    past["close"].pct_change().rolling(20).std().iloc[-1]
                    * np.sqrt(252) * 100
                )
            else:
                p["vol20"] = 30.0
        p["win_rate"] = SECTOR_STATS.get(p["sector"], {}).get("win_rate", 0.50)
        p["avg_win"]  = SECTOR_STATS.get(p["sector"], {}).get("avg_win",  5.0)
        p["avg_loss"] = SECTOR_STATS.get(p["sector"], {}).get("avg_loss", 3.5)

    sized = size_positions(picks, method=method,
                           max_per=MAX_PER_STOCK,
                           sector_max=MAX_PER_SECTOR)

    capital = INITIAL_CAPITAL
    print(f"\n  初始资金：{capital/10000:.0f} 万元  |  最多 {MAX_POSITIONS} 只  |"
          f"  单股≤{MAX_PER_STOCK*100:.0f}%  |  单板块≤{MAX_PER_SECTOR*100:.0f}%\n")
    print(f"  {'名称':8} {'代码':6} {'板块':8} {'权重':>6} {'建议金额':>10} "
          f"{'现价':>8} {'止损':>8} {'止盈':>8}")
    print(f"  {'-'*64}")
    for s in sized:
        code  = s["sym"].replace("sh","").replace("sz","")
        alloc = capital * s["weight"]
        print(f"  {s['name']:8} {code:6} {s['sector']:8} "
              f"{s['weight']*100:>5.1f}% {alloc/10000:>8.2f}万 "
              f"{s['close']:>8.2f} {s['stop_loss']:>8.2f} {s['take_profit']:>8.2f}")

    total_allocated = sum(s["weight"] for s in sized) * 100
    print(f"\n  总投入：{total_allocated:.1f}%  |  留存现金：{100-total_allocated:.1f}%")

    # 板块分布
    sectors: dict[str, float] = {}
    for s in sized:
        sectors[s["sector"]] = sectors.get(s["sector"], 0) + s["weight"] * 100
    print(f"\n  板块分布：" + "  ".join(f"{k} {v:.1f}%" for k, v in sectors.items()))


# ── 主程序 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\nStockSage 组合回测  {BT_EVAL_START} ~ {BT_EVAL_END}")
    print(f"初始资金：{INITIAL_CAPITAL/10000:.0f}万元  |  交易成本：{COST_RATE*100:.2f}%单边  "
          f"|  月度再平衡  |  最多{MAX_POSITIONS}只\n")

    # 数据加载
    print("▶ 加载基础数据...")
    print("  沪深300...", end=" ", flush=True)
    try:
        idx_raw  = get_index()
        index_df = precompute_index(idx_raw)
        print(f"OK ({len(index_df)}行)")
    except Exception as e:
        print(f"失败({e})")
        index_df = pd.DataFrame()

    stock_dfs = {}
    for sym, name, sector in CANDIDATE_POOL:
        print(f"  {name} ({sym})...", end=" ", flush=True)
        try:
            df = get_cn(sym)
            stock_dfs[sym] = precompute(df)
            print("OK")
        except Exception as e:
            print(f"失败({e})")

    # 三种方法回测
    methods  = ["equal", "kelly", "vol"]
    results  = {}
    for method in methods:
        labels = {"equal": "等权", "kelly": "凯利准则", "vol": "逆波动率"}
        print(f"\n▶ 运行 {labels[method]} 回测...", flush=True)
        results[method] = run_portfolio(stock_dfs, index_df, method)
        print_report(results[method], method)

    # 横向对比
    print_comparison(results)

    # 当前仓位建议（以等权为默认）
    current_portfolio_snapshot(stock_dfs, index_df, method="equal")
    print()
