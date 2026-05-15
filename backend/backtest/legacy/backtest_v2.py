"""
StockSage Phase 6 改进回测 v2
改进点：
  1. 大盘趋势过滤 — 沪深300 60日均线判断牛熊，熊市入场阈值 20→50
  2. ATR 自适应   — 20日已实现波动率动态调整止损空间
  3. RSI 过滤     — 入场时 RSI > 68 视为超买，跳过
  4. 止损冷静期   — 触发止损后 3 日内不再入场
回测期：2023-01-01 ~ 2024-12-31
"""
import sys
import pandas as pd
import numpy as np
import akshare as ak

TEST_STOCKS = [
    # 原始4只（对比 v1）
    ("sh603986", "兆易创新",  "半导体"),
    ("sh688008", "澜起科技",  "半导体"),
    ("sz002028", "思源电气",  "制造业"),
    ("sz300274", "阳光电源",  "PCS/新能源"),
    # 矿业/有色
    ("sh601088", "中国神华",  "煤炭矿业"),
    ("sh601899", "紫金矿业",  "有色金属"),
    ("sh603799", "华友钴业",  "有色金属"),
    # 电力
    ("sh600900", "长江电力",  "电力"),
    ("sh600011", "华能国际",  "电力"),
    # AI / 算力
    ("sz002230", "科大讯飞",  "AI"),
    ("sz300308", "中际旭创",  "AI算力"),
    # 制造业
    ("sz002594", "比亚迪",    "制造业"),
    ("sz300750", "宁德时代",  "制造业"),
    # PCS储能
    ("sz300827", "上能电气",  "PCS储能"),
]

WARMUP_START   = "20220101"
BACKTEST_START = "2023-01-01"
BACKTEST_END   = "2024-12-31"

# ── 策略参数 ───────────────────────────────────────────────────────────
ENTRY_BULL     = 20    # 牛市入场阈值
ENTRY_BEAR     = 50    # 熊市入场阈值（大盘弱势时更严格）
EXIT_THRESHOLD = -20   # 信号反转出场
BASE_ATR_MULT  = 2.0   # 基础止损ATR倍数
RR_RATIO       = 2.0   # 风险收益比 1:2
MAX_HOLD_DAYS  = 20    # 最长持仓天数
RSI_OB_LIMIT   = 68    # RSI超买阈值（超过此值不入场）
SL_COOLDOWN    = 3     # 止损后冷静天数


# ── 数据获取 ───────────────────────────────────────────────────────────

def fetch_prices(symbol: str) -> pd.DataFrame:
    df = ak.stock_zh_a_daily(
        symbol=symbol,
        start_date=WARMUP_START,
        end_date=BACKTEST_END.replace("-", ""),
        adjust="qfq",
    )
    df.index = pd.to_datetime(df.index)
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    return df[["open", "high", "low", "close", "volume"]].sort_index()


def fetch_index() -> pd.DataFrame | None:
    """沪深300日线 + 60日均线，用于牛熊判断"""
    try:
        df = ak.stock_zh_index_daily(symbol="sh000300")
        df.index = pd.to_datetime(df.index)
        df["ma60"] = df["close"].rolling(60).mean()
        return df[["close", "ma60"]]
    except Exception as e:
        print(f"  ⚠ 沪深300数据获取失败，关闭大盘过滤: {e}")
        return None


# ── 因子预计算（一次性，无前视偏差） ──────────────────────────────────

def precompute(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    # ATR14
    prev = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"],
                    (d["high"] - prev).abs(),
                    (d["low"]  - prev).abs()], axis=1).max(axis=1)
    d["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean()
    # RSI14
    delta = d["close"].diff()
    gain  = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["rsi14"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    # MA
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma60"] = d["close"].rolling(60).mean()
    # MACD
    ema12 = d["close"].ewm(span=12, adjust=False).mean()
    ema26 = d["close"].ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    d["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    # 20日已实现波动率（年化）
    d["vol20"] = d["close"].pct_change().rolling(20).std() * np.sqrt(252) * 100
    return d


def signal_at(df: pd.DataFrame, i: int) -> tuple[float, float, float]:
    """返回 (tech_score, atr14, rsi14)"""
    if i < 1:
        return 0.0, 0.0, 50.0
    row  = df.iloc[i]
    prev = df.iloc[i - 1]
    close = row["close"]
    ma20, ma60 = row["ma20"], row["ma60"]
    rsi14 = row["rsi14"]
    hist, phist = row["macd_hist"], prev["macd_hist"]
    atr14 = row["atr14"]

    if any(pd.isna(v) for v in [ma20, ma60, rsi14, hist, atr14]):
        return 0.0, float(atr14) if not pd.isna(atr14) else 0.0, 50.0

    # 趋势
    if ma20 > ma60 and close > ma20:
        trend = 1.0
    elif ma20 < ma60 and close < ma20:
        trend = -1.0
    else:
        trend = 0.0

    # RSI
    rsi_s = 1.0 if rsi14 < 30 else (-1.0 if rsi14 > 70 else (50 - rsi14) / 20.0)

    # MACD
    if pd.isna(phist):
        macd_s = 0.0
    elif hist > 0 and phist <= 0:
        macd_s = 1.0
    elif hist < 0 and phist >= 0:
        macd_s = -1.0
    else:
        macd_s = 0.3 if hist > 0 else -0.3

    # 成交量确认
    vol5  = df.iloc[max(0, i-4):i+1]["volume"].mean()
    vol20 = df.iloc[max(0, i-19):i+1]["volume"].mean()
    vol_s = trend * 0.5 if vol20 > 0 and vol5 / vol20 > 1.2 else 0.0

    score = (trend * 0.4 + rsi_s * 0.25 + macd_s * 0.25 + vol_s * 0.1) * 100
    return round(score, 1), float(atr14), float(rsi14)


def adaptive_atr_mult(df: pd.DataFrame, i: int) -> float:
    """根据近20日年化波动率动态调整止损倍数"""
    vol = df.iloc[i]["vol20"]
    if pd.isna(vol):
        return BASE_ATR_MULT
    if vol > 60:
        return BASE_ATR_MULT * 1.5   # 高波动：放宽止损
    elif vol < 25:
        return BASE_ATR_MULT * 0.8   # 低波动：收紧止损
    return BASE_ATR_MULT


def is_bull(index_df: pd.DataFrame | None, date) -> bool:
    """大盘是否处于牛市（沪深300 > 60日均线）"""
    if index_df is None:
        return True
    try:
        row = index_df.asof(date)
        return bool(row["close"] > row["ma60"]) if not pd.isna(row["ma60"]) else True
    except Exception:
        return True


# ── 回测引擎 ───────────────────────────────────────────────────────────

def run_backtest(symbol: str, name: str, sector: str,
                 index_df: pd.DataFrame | None) -> dict:
    df_raw = fetch_prices(symbol)
    df = precompute(df_raw)
    bt = df[df.index >= BACKTEST_START].copy()
    all_idx = list(df.index)

    trades = []
    position = None
    cooldown_until = pd.Timestamp("1970-01-01")   # 止损冷静期截止日

    for date in bt.index:
        i = all_idx.index(date)
        row = df.iloc[i]
        sig, atr, rsi = signal_at(df, i)
        bull = is_bull(index_df, date)
        entry_thr = ENTRY_BULL if bull else ENTRY_BEAR

        # ── 持仓检查 ──────────────────────────────────────────────────
        if position is not None:
            sl, tp = position["stop_loss"], position["take_profit"]
            ep, hd = position["entry_price"], position["hold_days"]

            exit_price, exit_reason = None, None

            if row["low"] <= sl:
                exit_price, exit_reason = sl, "止损"
                cooldown_until = date + pd.Timedelta(days=SL_COOLDOWN)
            elif row["high"] >= tp:
                exit_price, exit_reason = tp, "止盈"
            elif hd >= MAX_HOLD_DAYS:
                next_rows = bt[bt.index > date]
                exit_price = next_rows.iloc[0]["open"] if len(next_rows) else row["close"]
                exit_reason = "超时"
            elif sig < EXIT_THRESHOLD:
                next_rows = bt[bt.index > date]
                exit_price = next_rows.iloc[0]["open"] if len(next_rows) else row["close"]
                exit_reason = "信号反转"

            if exit_price is not None:
                pnl = (exit_price - ep) / ep * 100
                trades.append({
                    "entry_date":  position["entry_date"].strftime("%Y-%m-%d"),
                    "exit_date":   date.strftime("%Y-%m-%d"),
                    "entry_price": round(ep, 3),
                    "exit_price":  round(exit_price, 3),
                    "exit_reason": exit_reason,
                    "pnl_pct":     round(pnl, 2),
                    "hold_days":   hd,
                    "bull_entry":  position["bull_entry"],
                })
                position = None
            else:
                position["hold_days"] += 1

        # ── 开仓检查 ──────────────────────────────────────────────────
        if position is None and date > cooldown_until:
            if (sig > entry_thr                        # 信号强度
                    and rsi < RSI_OB_LIMIT             # 未超买
                    and not pd.isna(atr) and atr > 0): # ATR有效
                next_rows = bt[bt.index > date]
                if len(next_rows) == 0:
                    break
                next_open = next_rows.iloc[0]["open"]
                next_date = next_rows.index[0]
                mult = adaptive_atr_mult(df, i)
                risk = atr * mult
                position = {
                    "entry_date":  next_date,
                    "entry_price": next_open,
                    "stop_loss":   next_open - risk,
                    "take_profit": next_open + risk * RR_RATIO,
                    "hold_days":   1,
                    "bull_entry":  bull,
                }

    # 强制平仓（回测结束仍持仓）
    if position:
        last_close = bt.iloc[-1]["close"]
        pnl = (last_close - position["entry_price"]) / position["entry_price"] * 100
        trades.append({
            "entry_date":  position["entry_date"].strftime("%Y-%m-%d"),
            "exit_date":   bt.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(position["entry_price"], 3),
            "exit_price":  round(last_close, 3),
            "exit_reason": "到期",
            "pnl_pct":     round(pnl, 2),
            "hold_days":   position["hold_days"],
            "bull_entry":  position["bull_entry"],
        })

    bah = round((bt.iloc[-1]["close"] - bt.iloc[0]["open"]) / bt.iloc[0]["open"] * 100, 2)
    return {
        "symbol": symbol.replace("sh", "").replace("sz", ""),
        "name": name, "sector": sector,
        "trades": trades, "bah": bah,
    }


# ── 绩效指标 ───────────────────────────────────────────────────────────

def metrics(result: dict) -> dict:
    trades = result["trades"]
    if not trades:
        return {"n_trades": 0}
    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    n    = len(pnls)

    total_return = 1.0
    for p in pnls:
        total_return *= (1 + p / 100)
    total_return = (total_return - 1) * 100

    cumulative, peak, max_dd = [1.0], 1.0, 0.0
    for p in pnls:
        cumulative.append(cumulative[-1] * (1 + p / 100))
    for v in cumulative:
        peak = max(peak, v)
        max_dd = max(max_dd, (peak - v) / peak * 100)

    avg_hold = np.mean([t["hold_days"] for t in trades])
    rf = 3.0 / 252 * avg_hold
    excess = [p - rf for p in pnls]
    sharpe = (np.mean(excess) / np.std(excess) * np.sqrt(252 / avg_hold)
              if np.std(excess) > 0 else 0.0)

    return {
        "n_trades":     n,
        "win_rate":     round(len(wins) / n * 100, 1),
        "avg_pnl":      round(np.mean(pnls), 2),
        "total_return": round(total_return, 2),
        "max_dd":       round(max_dd, 2),
        "sharpe":       round(sharpe, 2),
        "best_trade":   round(max(pnls), 2),
        "worst_trade":  round(min(pnls), 2),
        "avg_hold":     round(avg_hold, 1),
    }


# ── 报告输出 ───────────────────────────────────────────────────────────

def print_report(result: dict, m: dict) -> None:
    sym, name, sector = result["symbol"], result["name"], result["sector"]
    bah = result["bah"]
    print(f"\n{'='*66}")
    print(f"  {name} ({sym})  [{sector}]  {BACKTEST_START} ~ {BACKTEST_END}")
    print(f"{'='*66}")
    if m.get("n_trades", 0) == 0:
        print(f"  ⚠ 回测期内无触发交易  |  买入持有基准：{bah:+.2f}%")
        return

    alpha = m["total_return"] - bah
    flag  = "↑超额" if alpha > 0 else "↓跑输"
    print(f"  买入持有基准：{bah:+.2f}%")
    print(f"  策略总收益　：{m['total_return']:+.2f}%  {flag} {abs(alpha):.2f}%  "
          f"夏普={m['sharpe']:.2f}  回撤={m['max_dd']:.1f}%")
    print(f"  胜率：{m['win_rate']}%  共{m['n_trades']}笔  "
          f"均盈亏：{m['avg_pnl']:+.2f}%  "
          f"最佳：{m['best_trade']:+.2f}%  最差：{m['worst_trade']:+.2f}%  "
          f"均持{m['avg_hold']}天")
    print()
    print(f"  {'入场日':12} {'出场日':12} {'入场价':>8} {'出场价':>8} {'收益':>8}  原因")
    print(f"  {'-'*62}")
    for t in result["trades"]:
        flag2 = "✅" if t["pnl_pct"] > 0 else "❌"
        mkt   = "牛" if t.get("bull_entry", True) else "熊"
        print(f"  {t['entry_date']:12} {t['exit_date']:12} "
              f"{t['entry_price']:>8.2f} {t['exit_price']:>8.2f} "
              f"{t['pnl_pct']:>+7.2f}%  {flag2}[{mkt}] {t['exit_reason']}")


def print_summary(all_results: list) -> None:
    # 按超额收益排序
    ranked = sorted(
        [(r, m) for r, m in all_results if m.get("n_trades", 0) > 0],
        key=lambda x: x[1]["total_return"] - x[0]["bah"],
        reverse=True,
    )
    no_trades = [(r, m) for r, m in all_results if m.get("n_trades", 0) == 0]

    print(f"\n{'='*80}")
    print(f"  汇总对比（按超额收益排序）  回测期：{BACKTEST_START} ~ {BACKTEST_END}")
    print(f"  改进：大盘趋势过滤 + ATR自适应 + RSI超买过滤 + 止损冷静期")
    print(f"{'='*80}")
    print(f"  {'股票':<8} {'代码':6} {'板块':8} {'策略':>9} {'买持':>9} {'超额':>9} "
          f"{'胜率':>7} {'笔数':>5} {'回撤':>8} {'夏普':>6}")
    print(f"  {'-'*76}")
    for r, m in ranked:
        alpha = m["total_return"] - r["bah"]
        flag  = "▲" if alpha > 0 else "▼"
        print(f"  {r['name']:<8} {r['symbol']:6} {r['sector']:8} "
              f"{m['total_return']:>+8.2f}% {r['bah']:>+8.2f}% "
              f"{flag}{abs(alpha):>7.2f}% {m['win_rate']:>6.1f}% "
              f"{m['n_trades']:>5} {m['max_dd']:>7.1f}% {m['sharpe']:>6.2f}")
    for r, m in no_trades:
        print(f"  {r['name']:<8} {r['symbol']:6} {r['sector']:8} "
              f"{'—':>9} {r['bah']:>+8.2f}%  无交易触发")
    print()

    # 行业分析
    from collections import defaultdict
    sector_stats = defaultdict(list)
    for r, m in ranked:
        sector_stats[r["sector"]].append(m["total_return"] - r["bah"])
    print("  行业超额均值：")
    for sec, alphas in sorted(sector_stats.items(), key=lambda x: -np.mean(x[1])):
        print(f"    {sec:10}: {np.mean(alphas):>+.2f}%  (共{len(alphas)}只)")
    print()


# ── 入口 ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nStockSage 改进回测 v2  {BACKTEST_START} ~ {BACKTEST_END}")
    print(f"策略改进：大盘过滤（牛{ENTRY_BULL}/熊{ENTRY_BEAR}）"
          f"+ ATR自适应 + RSI<{RSI_OB_LIMIT} + 止损冷静{SL_COOLDOWN}天")

    print("\n获取沪深300指数…", end=" ", flush=True)
    index_df = fetch_index()
    print("OK" if index_df is not None else "失败，关闭过滤")

    all_results = []
    for symbol, name, sector in TEST_STOCKS:
        print(f"\n▶ {name} ({symbol}) [{sector}]", flush=True)
        try:
            result = run_backtest(symbol, name, sector, index_df)
            m = metrics(result)
            print_report(result, m)
            all_results.append((result, m))
        except Exception as e:
            print(f"  ❌ 失败：{e}")

    if all_results:
        print_summary(all_results)
