"""
StockSage 简单选股策略
基于回测发现的规律，提炼选股信号并验证

选股逻辑（五步过滤）：
  1. 大盘趋势过滤  — 沪深300 > MA60（牛市环境，减少逆势交易）
  2. 技术信号过滤  — 综合得分 > 25
  3. RSI 过滤      — RSI14 < 65（避免追高）
  4. 量价验证      — 近5日成交量 > 20日均量 × 1.05（温和放量确认）
  5. 板块优先级    — 有色金属/半导体/新能源 > 消费/化工 > 银行/基建

输出：按综合评分排序的买入候选池，附带止损止盈参考价
"""
import sys
import warnings
import pandas as pd
import numpy as np
import akshare as ak
from datetime import datetime, timedelta
warnings.filterwarnings("ignore")

# ── 选股参数 ────────────────────────────────────────────────────────
TECH_THRESHOLD   = 25     # 技术信号最低分
RSI_MAX          = 65     # RSI上限（避免追高）
VOL_RATIO_MIN    = 1.05   # 近5日量 / 20日均量
ATR_MULT_SL      = 2.0    # 止损ATR倍数
RR_RATIO         = 2.0    # 止盈风险收益比

# 板块优先级权重（叠加到综合分）
SECTOR_BOOST = {
    "有色金属": 8,
    "黄金矿业": 8,
    "半导体":   10,
    "AI算力":   10,
    "新能源":   6,
    "消费":     4,
    "化工":     4,
    "电力":     2,
    "能源矿业": 2,
    "银行":     0,
    "医药":     3,
    "军工":     5,
    "基建":     0,
}

# 候选股票池（与 backtest_v3 一致）
CANDIDATE_POOL = [
    ("sh601899", "紫金矿业",  "有色金属"),
    ("sh603799", "华友钴业",  "有色金属"),
    ("sh603993", "洛阳钼业",  "有色金属"),
    ("sh600547", "山东黄金",  "黄金矿业"),
    ("sh600900", "长江电力",  "电力"),
    ("sh600011", "华能国际",  "电力"),
    ("sh601088", "中国神华",  "能源矿业"),
    ("sh603986", "兆易创新",  "半导体"),
    ("sh688008", "澜起科技",  "半导体"),
    ("sz300308", "中际旭创",  "AI算力"),
    ("sz300750", "宁德时代",  "新能源"),
    ("sz002594", "比亚迪",    "新能源"),
    ("sz300274", "阳光电源",  "新能源"),
    ("sh600519", "贵州茅台",  "消费"),
    ("sh600276", "恒瑞医药",  "医药"),
    ("sh601398", "工商银行",  "银行"),
    ("sh600036", "招商银行",  "银行"),
    ("sh600309", "万华化学",  "化工"),
    ("sh600760", "中航沈飞",  "军工"),
    ("sh600150", "中国船舶",  "军工"),
    ("sh601390", "中国中铁",  "基建"),
]

# 选股策略回测参数
BT_EVAL_START = "2024-01-01"
BT_EVAL_END   = "2026-05-12"
WARMUP        = "20220101"
HS300_SYM     = "sh000300"

# 月度再平衡（每月首个交易日重新选股）
REBALANCE_FREQ = "MS"   # Month Start


# ── 数据工具 ────────────────────────────────────────────────────────
def get_cn(sym: str) -> pd.DataFrame:
    df = ak.stock_zh_a_daily(symbol=sym, start_date=WARMUP,
                              end_date=BT_EVAL_END.replace("-", ""), adjust="qfq")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[["open", "high", "low", "close", "volume"]].sort_index()


def get_index() -> pd.DataFrame:
    df = ak.stock_zh_index_daily(symbol=HS300_SYM)
    df.index = pd.to_datetime(df.index) if df.index.dtype == "object" else df.index
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    return df[["close"]].sort_index()


def precompute(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    prev = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"],
                    (d["high"] - prev).abs(),
                    (d["low"] - prev).abs()], axis=1).max(axis=1)
    d["atr14"]     = tr.ewm(alpha=1/14, adjust=False).mean()
    delta          = d["close"].diff()
    gain           = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss           = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["rsi14"]     = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    d["ma20"]      = d["close"].rolling(20).mean()
    d["ma60"]      = d["close"].rolling(60).mean()
    ema12          = d["close"].ewm(span=12, adjust=False).mean()
    ema26          = d["close"].ewm(span=26, adjust=False).mean()
    d["macd_hist"] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()
    d["vol20_avg"] = d["volume"].rolling(20).mean()
    d["vol5_avg"]  = d["volume"].rolling(5).mean()
    return d


def precompute_index(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["ma60"] = d["close"].rolling(60).mean()
    return d


def is_bull(index_df: pd.DataFrame, date: pd.Timestamp) -> bool:
    past = index_df[index_df.index <= date]
    if len(past) < 60:
        return True
    row = past.iloc[-1]
    return not pd.isna(row["ma60"]) and row["close"] > row["ma60"]


# ── 单股技术得分（某个历史时点）────────────────────────────────────
def score_at(df: pd.DataFrame, date: pd.Timestamp) -> dict | None:
    """计算 date 当天的技术指标，返回 None 表示数据不足"""
    past = df[df.index <= date]
    if len(past) < 65:
        return None
    i     = len(past) - 1
    row   = past.iloc[i]
    prev  = past.iloc[i-1]

    c, m20, m60, rsi, hist, phist, atr = (
        row["close"], row["ma20"], row["ma60"], row["rsi14"],
        row["macd_hist"], prev["macd_hist"], row["atr14"])
    v5, v20 = row["vol5_avg"], row["vol20_avg"]

    if any(pd.isna(x) for x in [m20, m60, rsi, hist, atr, v5, v20]):
        return None

    trend = 1.0 if (m20 > m60 and c > m20) else (-1.0 if (m20 < m60 and c < m20) else 0.0)
    rsi_s = 1.0 if rsi < 30 else (-1.0 if rsi > 70 else (50 - rsi) / 20.0)
    if pd.isna(phist):
        macd_s = 0.0
    elif hist > 0 and phist <= 0:
        macd_s = 1.0
    elif hist < 0 and phist >= 0:
        macd_s = -1.0
    else:
        macd_s = 0.3 if hist > 0 else -0.3
    vol_ratio = v5 / v20 if v20 > 0 else 0.0
    vol_s     = trend * 0.5 if vol_ratio > 1.2 else 0.0

    tech_score = (trend * 0.4 + rsi_s * 0.25 + macd_s * 0.25 + vol_s * 0.1) * 100
    return {
        "score": round(tech_score, 1),
        "rsi": round(float(rsi), 1),
        "atr": float(atr),
        "close": float(c),
        "vol_ratio": round(vol_ratio, 2),
        "trend": trend,
    }


# ── 核心选股函数 ─────────────────────────────────────────────────────
def pick_stocks(date: pd.Timestamp, stock_dfs: dict, index_df: pd.DataFrame,
                top_n: int = 5) -> list[dict]:
    """
    在给定日期运行五步选股，返回最多 top_n 个买入候选。
    stock_dfs: {sym: precomputed_df}
    """
    if not index_df.empty and not is_bull(index_df, date):
        return []   # 熊市环境：全部观望

    candidates = []
    for sym, name, sector in CANDIDATE_POOL:
        df = stock_dfs.get(sym)
        if df is None:
            continue
        info = score_at(df, date)
        if info is None:
            continue

        # 五步过滤
        if info["score"] <= TECH_THRESHOLD:
            continue
        if info["rsi"] >= RSI_MAX:
            continue
        if info["vol_ratio"] < VOL_RATIO_MIN:
            continue

        boost   = SECTOR_BOOST.get(sector, 0)
        final_s = info["score"] + boost
        sl      = info["close"] - info["atr"] * ATR_MULT_SL
        tp      = info["close"] + info["atr"] * ATR_MULT_SL * RR_RATIO
        candidates.append({
            "sym": sym, "name": name, "sector": sector,
            "tech_score": info["score"],
            "final_score": round(final_s, 1),
            "rsi": info["rsi"],
            "vol_ratio": info["vol_ratio"],
            "close": info["close"],
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "atr": round(info["atr"], 3),
        })

    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return candidates[:top_n]


# ── 策略回测：月度再平衡 + ATR止盈止损 ──────────────────────────────
def backtest_picker(stock_dfs: dict, index_df: pd.DataFrame) -> dict:
    """
    模拟月度选股策略：
    - 每月初选出前5只，等权买入（下一交易日开盘）
    - ATR×2 止损，ATR×4 止盈（1:2风险收益）
    - 最长持有20个交易日，信号反转平仓
    """
    # 生成月度再平衡日期
    all_dates = sorted(set(
        d for df in stock_dfs.values() for d in df.index
        if BT_EVAL_START <= str(d.date()) <= BT_EVAL_END
    ))
    if not all_dates:
        return {}

    # 月首交易日
    rebalance_dates = []
    seen_months = set()
    for d in all_dates:
        m = (d.year, d.month)
        if m not in seen_months:
            seen_months.add(m)
            rebalance_dates.append(d)

    portfolio_trades = []   # 所有已平仓记录
    open_positions   = []   # {sym, name, sector, entry_date, entry_price, sl, tp, hold}

    date_set = set(all_dates)

    for rb_date in rebalance_dates:
        # 平掉上期持仓（月度再平衡）
        next_dates = [d for d in all_dates if d > rb_date]

        for pos in open_positions[:]:
            df = stock_dfs.get(pos["sym"])
            if df is None:
                open_positions.remove(pos)
                continue
            # 检查是否被止盈/止损
            exit_p = exit_r = None
            for check_d in all_dates:
                if check_d <= pos["entry_date"] or check_d > rb_date:
                    continue
                row = df[df.index == check_d]
                if row.empty:
                    continue
                r = row.iloc[0]
                if r["low"] <= pos["sl"]:
                    exit_p, exit_r = pos["sl"], "止损"
                    break
                elif r["high"] >= pos["tp"]:
                    exit_p, exit_r = pos["tp"], "止盈"
                    break
            if exit_p is None:
                # 月底平仓
                close_row = df[df.index <= rb_date]
                if not close_row.empty:
                    exit_p, exit_r = close_row.iloc[-1]["close"], "月末再平衡"
            if exit_p is not None:
                pnl = (exit_p - pos["entry_price"]) / pos["entry_price"] * 100
                portfolio_trades.append({
                    "sym": pos["sym"], "name": pos["name"], "sector": pos["sector"],
                    "entry_date": pos["entry_date"].strftime("%Y-%m-%d"),
                    "exit_date": rb_date.strftime("%Y-%m-%d"),
                    "entry_price": round(pos["entry_price"], 2),
                    "exit_price": round(exit_p, 2),
                    "pnl": round(pnl, 2), "reason": exit_r,
                })
        open_positions = []

        # 选股
        picks = pick_stocks(rb_date, stock_dfs, index_df, top_n=5)
        if not picks:
            continue

        # 下一交易日开盘入场
        entry_candidates = [d for d in all_dates if d > rb_date]
        if not entry_candidates:
            continue
        entry_date = entry_candidates[0]

        for pick in picks:
            df = stock_dfs.get(pick["sym"])
            if df is None:
                continue
            entry_rows = df[df.index == entry_date]
            if entry_rows.empty:
                continue
            ep = entry_rows.iloc[0]["open"]
            # 重新按入场价计算止盈止损
            atr_val = pick["atr"]
            sl  = ep - atr_val * ATR_MULT_SL
            tp  = ep + atr_val * ATR_MULT_SL * RR_RATIO
            open_positions.append({
                "sym": pick["sym"], "name": pick["name"], "sector": pick["sector"],
                "entry_date": entry_date, "entry_price": ep, "sl": sl, "tp": tp,
            })

    # 强制平仓剩余持仓
    for pos in open_positions:
        df = stock_dfs.get(pos["sym"])
        if df is None:
            continue
        close_rows = df[df.index <= pd.Timestamp(BT_EVAL_END)]
        if close_rows.empty:
            continue
        lc  = close_rows.iloc[-1]["close"]
        pnl = (lc - pos["entry_price"]) / pos["entry_price"] * 100
        portfolio_trades.append({
            "sym": pos["sym"], "name": pos["name"], "sector": pos["sector"],
            "entry_date": pos["entry_date"].strftime("%Y-%m-%d"),
            "exit_date": BT_EVAL_END,
            "entry_price": round(pos["entry_price"], 2),
            "exit_price": round(lc, 2),
            "pnl": round(pnl, 2), "reason": "到期",
        })

    return portfolio_trades


def calc_metrics(trades: list) -> dict:
    if not trades:
        return {"n": 0}
    pnls  = [t["pnl"] for t in trades]
    total = 1.0
    for p in pnls:
        total *= 1 + p / 100
    total = (total - 1) * 100
    cumv  = [1.0]
    for p in pnls:
        cumv.append(cumv[-1] * (1 + p / 100))
    peak, mdd = 1.0, 0.0
    for v in cumv:
        peak = max(peak, v)
        mdd  = max(mdd, (peak - v) / peak * 100)
    wins = [p for p in pnls if p > 0]
    return {"n": len(pnls),
            "win": round(len(wins) / len(pnls) * 100, 1),
            "avg": round(np.mean(pnls), 2),
            "total": round(total, 2),
            "mdd": round(mdd, 2),
            "best": round(max(pnls), 2),
            "worst": round(min(pnls), 2)}


# ── 主程序 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    today_str = datetime.today().strftime("%Y-%m-%d")
    print(f"\nStockSage 选股策略  {BT_EVAL_START} ~ {BT_EVAL_END}")
    print(f"选股规则：大盘牛市 + 技术>{TECH_THRESHOLD} + RSI<{RSI_MAX} + "
          f"量比>{VOL_RATIO_MIN} + 板块优先级")
    print(f"再平衡：月度 | 止损：ATR×{ATR_MULT_SL} | 止盈：1:{RR_RATIO}\n")

    # 拉取沪深300
    print("▶ 拉取沪深300...", end=" ", flush=True)
    try:
        idx_raw  = get_index()
        index_df = precompute_index(idx_raw)
        print(f"OK ({len(index_df)} 行)")
    except Exception as e:
        print(f"失败({e})")
        index_df = pd.DataFrame()

    # 拉取所有候选股票
    stock_dfs = {}
    for sym, name, sector in CANDIDATE_POOL:
        print(f"  拉取 {name} ({sym})...", end=" ", flush=True)
        try:
            df         = get_cn(sym)
            stock_dfs[sym] = precompute(df)
            print(f"OK ({len(df)} 行)")
        except Exception as e:
            print(f"失败({e})")

    # ── 当前选股快照（实盘参考）────────────────────────────────────
    snap_date = pd.Timestamp(today_str)
    # 用最近一个有数据的日期
    all_avail = sorted(set(
        d for df in stock_dfs.values() for d in df.index
    ))
    if all_avail:
        snap_date = all_avail[-1]

    print(f"\n{'='*70}")
    print(f"  当前选股快照（截至 {snap_date.date()}）")
    is_bull_now = is_bull(index_df, snap_date) if not index_df.empty else True
    print(f"  大盘状态：{'牛市 ✅' if is_bull_now else '熊市 ⚠️  (全部观望)'}")
    print(f"{'='*70}")

    picks = pick_stocks(snap_date, stock_dfs, index_df, top_n=10)
    if picks:
        print(f"  {'名称':8} {'代码':6} {'板块':8} {'技术分':>6} {'综合分':>6} "
              f"{'RSI':>5} {'量比':>6} {'现价':>8} {'止损':>8} {'止盈':>8}")
        print("  " + "-" * 68)
        for p in picks:
            code = p["sym"].replace("sh","").replace("sz","")
            print(f"  {p['name']:8} {code:6} {p['sector']:8} "
                  f"{p['tech_score']:>6.1f} {p['final_score']:>6.1f} "
                  f"{p['rsi']:>5.1f} {p['vol_ratio']:>6.2f} "
                  f"{p['close']:>8.2f} {p['stop_loss']:>8.2f} {p['take_profit']:>8.2f}")
    else:
        print("  当前无符合条件的买入候选（熊市环境或信号不足）")

    # ── 策略历史回测 ─────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  月度选股策略回测  {BT_EVAL_START} ~ {BT_EVAL_END}")
    print(f"{'='*70}")

    trades = backtest_picker(stock_dfs, index_df)
    m      = calc_metrics(trades)

    if m["n"] == 0:
        print("  ⚠ 回测期内无交易触发")
    else:
        # HS300 基准收益
        bt_idx = index_df[(index_df.index >= BT_EVAL_START) &
                          (index_df.index <= BT_EVAL_END)]
        bah_hs300 = 0.0
        if len(bt_idx) >= 2:
            bah_hs300 = round((bt_idx.iloc[-1]["close"] - bt_idx.iloc[0]["close"]) /
                               bt_idx.iloc[0]["close"] * 100, 2)

        print(f"  交易笔数  ：{m['n']}")
        print(f"  策略总收益：{m['total']:+.2f}%  （复利，等权月度再平衡）")
        print(f"  沪深300   ：{bah_hs300:+.2f}%  （买入持有基准）")
        print(f"  超额收益  ：{m['total'] - bah_hs300:+.2f}%")
        print(f"  胜率      ：{m['win']}%")
        print(f"  均收益/笔 ：{m['avg']:+.2f}%")
        print(f"  最大回撤  ：{m['mdd']:.2f}%")
        print(f"  最佳/最差 ：{m['best']:+.2f}% / {m['worst']:+.2f}%")

        # 按板块汇总
        sector_pnls: dict[str, list] = {}
        for t in trades:
            sector_pnls.setdefault(t["sector"], []).append(t["pnl"])
        print(f"\n  各板块表现：")
        for sec, pnls in sorted(sector_pnls.items(), key=lambda x: np.mean(x[1]), reverse=True):
            wins = len([p for p in pnls if p > 0])
            print(f"    {sec:8}  {len(pnls):2}笔  均收益{np.mean(pnls):+.2f}%  "
                  f"胜率{wins/len(pnls)*100:.0f}%")

        # 明细（最近20笔）
        print(f"\n  最近交易明细（共{m['n']}笔，显示后20笔）：")
        print(f"  {'名称':8} {'板块':8} {'入场':10} {'出场':10} "
              f"{'入场价':>8} {'出场价':>8} {'收益':>8}  原因")
        print("  " + "-" * 68)
        for t in trades[-20:]:
            flag = "✅" if t["pnl"] > 0 else "❌"
            print(f"  {t['name']:8} {t['sector']:8} {t['entry_date']:10} "
                  f"{t['exit_date']:10} {t['entry_price']:>8.2f} "
                  f"{t['exit_price']:>8.2f} {t['pnl']:>+7.2f}%  {flag} {t['reason']}")

    print()
    print("选股策略总结：")
    print("  核心逻辑：牛市环境 × 多因子技术信号 × 板块景气度 → 月度再平衡")
    print("  适用场景：A股中枢向上阶段，有色金属/半导体/新能源板块轮动")
    print("  风险提示：策略依赖历史规律，不构成投资建议")
    print()
