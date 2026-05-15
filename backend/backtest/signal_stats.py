"""
backend/backtest/signal_stats.py — 历史信号胜率/盈亏比统计（Phase 6.5 步骤一~三）

步骤一（默认）：  PYTHONPATH=. python3 backend/backtest/signal_stats.py
步骤二扫描：      PYTHONPATH=. python3 backend/backtest/signal_stats.py --scan
步骤三环境对比：  PYTHONPATH=. python3 backend/backtest/signal_stats.py --env
全部步骤：        PYTHONPATH=. python3 backend/backtest/signal_stats.py --all

信号代理说明：
  DB 不存储历史 Qlib/情感分，以技术信号作为综合分代理，
  计算公式与生产系统 technical.py 完全一致（趋势×0.4 + RSI×0.25 + MACD×0.25 + 量能×0.1）。
  生产系统入场阈值 >20 对应的是三路融合综合分，此处技术信号 >20 偏保守（技术占40%权重）。
"""
import sys
import argparse
import warnings
import numpy as np
import pandas as pd
warnings.filterwarnings("ignore")

from backend.data.database import SessionLocal, Stock, Price
from backend.analysis.factors import add_all_factors
from backend.analysis.technical import score_trend, score_rsi, score_macd, score_volume

HOLD_DAYS = 5     # 持有交易日数（固定）
WARMUP    = 80    # MA60 + 余量，不足此行数不生成信号
RR_RATIO  = 2.0   # 风险收益比（止盈 = 止损空间 × RR_RATIO）

# 步骤一/二的主研究区间（近 6 个月）
DEFAULT_START = "2025-11-01"
DEFAULT_END   = "2026-05-14"

# 步骤三：市场环境区间
ENV_PERIODS = {
    "近6个月":       (DEFAULT_START, DEFAULT_END),
    "牛市(24Q4)":    ("2024-09-01", "2024-10-31"),
    "调整期(24Q1)":  ("2024-02-01", "2024-04-30"),
}

# 步骤二：参数扫描网格
SCAN_THRESHOLDS = [15, 20, 25]
SCAN_ATR_MULTS  = [1.5, 2.0, 2.5]


# ── 数据加载 ──────────────────────────────────────────────────────────

def load_all_prices(db) -> dict:
    """返回 {symbol: (name, df_raw, df_factored)}，只加载 A 股活跃股票。"""
    stocks = db.query(Stock).filter(Stock.active == True, Stock.market == "CN").all()
    result = {}
    for s in stocks:
        rows = (db.query(Price)
                .filter(Price.symbol == s.symbol)
                .order_by(Price.date.asc())
                .all())
        if not rows:
            continue
        df_raw = pd.DataFrame([
            {"date": r.date, "open": r.open, "high": r.high,
             "low": r.low, "close": r.close, "volume": r.volume}
            for r in rows
        ]).set_index("date")
        df_factored = add_all_factors(df_raw)  # 预计算，避免 run_stats 重复计算
        result[s.symbol] = (s.name, df_raw, df_factored)
    return result


# ── 信号计算 ──────────────────────────────────────────────────────────

def tech_score_at(df_factored: pd.DataFrame, i: int) -> float:
    """返回第 i 行的技术综合分 (-100~+100)。"""
    if i < WARMUP:
        return 0.0
    s = df_factored.iloc[:i + 1]
    w = {"trend": 0.4, "rsi": 0.25, "macd": 0.25, "volume": 0.1}
    raw = (score_trend(s) * w["trend"]
           + score_rsi(s) * w["rsi"]
           + score_macd(s) * w["macd"]
           + score_volume(s) * w["volume"])
    return round(raw * 100, 1)


# ── 回测核心 ──────────────────────────────────────────────────────────

def run_stats(df_factored: pd.DataFrame, start: str, end: str,
              threshold: float, atr_mult: float) -> list:
    """
    统计 [start, end] 区间内信号触发后的交易结果。
    入场：信号日次日开盘；出场：止损/止盈触发或满 HOLD_DAYS 交易日后收盘。
    返回 trade 列表：{date, pnl, reason, score}。
    """
    if df_factored.empty or len(df_factored) < WARMUP + HOLD_DAYS + 2:
        return []

    dates = list(df_factored.index)
    trades = []

    for i, date in enumerate(dates):
        if date < start or date > end:
            continue

        score = tech_score_at(df_factored, i)
        if score <= threshold:
            continue

        # T+1 ~ T+HOLD_DAYS 共 HOLD_DAYS 行
        future = df_factored.iloc[i + 1: i + 1 + HOLD_DAYS]
        if len(future) < HOLD_DAYS:
            continue  # 回测末尾数据不足

        entry = float(future.iloc[0]["open"])
        atr   = float(df_factored.iloc[i]["atr14"])
        if pd.isna(atr) or atr <= 0 or entry <= 0:
            continue

        stop = entry - atr * atr_mult
        take = entry + atr * atr_mult * RR_RATIO

        exit_px, reason = None, "超时"
        for row in future.itertuples():
            if row.low <= stop:
                exit_px, reason = stop, "止损"
                break
            if row.high >= take:
                exit_px, reason = take, "止盈"
                break

        if exit_px is None:
            exit_px = float(future.iloc[-1]["close"])

        pnl = (exit_px - entry) / entry * 100
        trades.append({"date": date, "pnl": round(pnl, 2),
                       "reason": reason, "score": score})

    return trades


# ── 统计指标 ──────────────────────────────────────────────────────────

def calc_metrics(trades: list) -> dict:
    if not trades:
        return {"n": 0}
    pnls   = [t["pnl"] for t in trades]
    wins   = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    if wins and losses:
        pf = float(np.mean(wins)) / abs(float(np.mean(losses)))
    elif wins:
        pf = float("inf")
    else:
        pf = 0.0
    return {
        "n":             len(pnls),
        "win_rate":      round(len(wins) / len(pnls) * 100, 1),
        "avg_return":    round(float(np.mean(pnls)), 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else float("inf"),
        "avg_win":       round(float(np.mean(wins)), 2) if wins else 0.0,
        "avg_loss":      round(abs(float(np.mean(losses))), 2) if losses else 0.0,
        "reasons":       {r: sum(1 for t in trades if t["reason"] == r) for r in ("止损", "止盈", "超时")},
    }


def fmt_metrics(m: dict) -> str:
    if m["n"] == 0:
        return "无触发"
    pf = f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "∞"
    r  = m["reasons"]
    return (f"{m['n']}笔  胜率{m['win_rate']}%  均{m['avg_return']:+.2f}%  "
            f"盈亏比{pf}  [止损{r['止损']} 止盈{r['止盈']} 超时{r['超时']}]")


def print_acceptance(m: dict) -> None:
    """打印三项验收标准的达标情况。"""
    if m["n"] == 0:
        return
    pf = m["profit_factor"] if m["profit_factor"] != float("inf") else 999.0
    checks = [
        (m["n"] >= 30,       f"样本≥30（当前 {m['n']}）"),
        (m["win_rate"] > 50, f"胜率>50%（当前 {m['win_rate']}%）"),
        (pf >= 1.5,          f"盈亏比≥1.5（当前 {pf:.2f}）"),
    ]
    all_pass = all(ok for ok, _ in checks)
    for ok, desc in checks:
        print(f"    {'✅' if ok else '❌'} {desc}")
    if all_pass:
        print("    → 全部达标，可启动小仓位实盘")
    else:
        print("    → 尚未全部达标，建议继续观察")


# ── 步骤实现 ──────────────────────────────────────────────────────────

def step1(price_data: dict, threshold: float = 20, atr_mult: float = 2.0) -> None:
    start, end = DEFAULT_START, DEFAULT_END
    print(f"\n{'='*65}")
    print(f"步骤一：历史信号统计  阈值>{threshold}  ATR×{atr_mult}  {start}~{end}")
    print(f"{'='*65}")

    all_trades = []
    for sym, (name, _, df_f) in price_data.items():
        trades = run_stats(df_f, start, end, threshold, atr_mult)
        all_trades.extend(trades)
        m = calc_metrics(trades)
        print(f"  {name}({sym}):  {fmt_metrics(m)}")

    print(f"{'─'*65}")
    m_all = calc_metrics(all_trades)
    print(f"  汇总:  {fmt_metrics(m_all)}")
    print("\n  验收标准：")
    print_acceptance(m_all)


def step2(price_data: dict) -> None:
    start, end = DEFAULT_START, DEFAULT_END
    print(f"\n{'='*65}")
    print(f"步骤二：参数鲁棒性扫描  {start}~{end}")
    print(f"{'='*65}")
    print(f"  {'阈值':>4} {'ATR':>4}  {'样本':>4} {'胜率':>7} {'均收益':>8} {'盈亏比':>7}")
    print("  " + "─" * 46)

    for thr in SCAN_THRESHOLDS:
        for atr_m in SCAN_ATR_MULTS:
            all_trades = []
            for sym, (_, _, df_f) in price_data.items():
                all_trades.extend(run_stats(df_f, start, end, thr, atr_m))
            m = calc_metrics(all_trades)
            if m["n"] == 0:
                print(f"  {thr:>4} {atr_m:>4.1f}  无触发")
                continue
            pf = f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "   ∞"
            print(f"  {thr:>4} {atr_m:>4.1f} {m['n']:>5} {m['win_rate']:>6.1f}% "
                  f"{m['avg_return']:>+7.2f}% {pf:>7}")

    print("\n  说明：参数改变后结果若变化幅度不超过±10pp，视为鲁棒；否则可能存在过拟合。")


def step3(price_data: dict, threshold: float = 20, atr_mult: float = 2.0) -> None:
    print(f"\n{'='*65}")
    print(f"步骤三：市场环境对比  阈值>{threshold}  ATR×{atr_mult}")
    print(f"{'='*65}")

    for label, (start, end) in ENV_PERIODS.items():
        all_trades = []
        for sym, (_, _, df_f) in price_data.items():
            all_trades.extend(run_stats(df_f, start, end, threshold, atr_mult))
        m = calc_metrics(all_trades)
        print(f"\n  [{label}] {start} ~ {end}")
        print(f"    {fmt_metrics(m)}")

    print("\n  说明：若牛市胜率>60% 而调整期<40%，则信号顺势有效但逆势不可信。")


# ── 入口 ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="StockSage 信号统计 (Phase 6.5)")
    ap.add_argument("--scan", action="store_true", help="步骤二：参数鲁棒性扫描")
    ap.add_argument("--env",  action="store_true", help="步骤三：市场环境对比")
    ap.add_argument("--all",  action="store_true", help="运行全部三个步骤")
    args = ap.parse_args()

    db = SessionLocal()
    print("加载价格数据...", end=" ", flush=True)
    price_data = load_all_prices(db)
    db.close()

    if not price_data:
        print("\nDB 中无 A 股数据，请先通过 API 添加自选股并回填行情")
        sys.exit(1)

    names = [name for name, _, _ in price_data.values()]
    print(f"完成")
    print(f"股票池：{len(price_data)} 只 — {', '.join(names)}")

    run1 = args.all or not (args.scan or args.env)
    run2 = args.all or args.scan
    run3 = args.all or args.env

    if run1:
        step1(price_data)
    if run2:
        step2(price_data)
    if run3:
        step3(price_data)

    print()
