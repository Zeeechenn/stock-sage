"""
backend/backtest/signal_stats_universe.py — 50只股票宽基历史信号统计

用途：消除自选股选股偏差，用多元化股票池验证技术信号有效性。
数据来源：AkShare（直连东方财富，不依赖本地 DB）。

运行：
  PYTHONPATH=. python3 backend/backtest/signal_stats_universe.py           # 默认（步骤一）
  PYTHONPATH=. python3 backend/backtest/signal_stats_universe.py --scan    # 参数扫描
  PYTHONPATH=. python3 backend/backtest/signal_stats_universe.py --env     # 市场环境对比
  PYTHONPATH=. python3 backend/backtest/signal_stats_universe.py --all     # 全部
"""
import sys
import time
import argparse
import warnings
import requests
import numpy as np
import pandas as pd
import akshare as ak
warnings.filterwarnings("ignore")

from backend.analysis.factors import add_all_factors
from backend.analysis.technical import score_trend, score_rsi, score_macd, score_volume

HOLD_DAYS = 5
WARMUP    = 80
RR_RATIO  = 2.0

DEFAULT_START = "2025-11-01"
DEFAULT_END   = "2026-05-14"
FETCH_START   = "2025-05-01"   # 比研究区间多拉6个月用于预热

ENV_PERIODS = {
    "近6个月":      (DEFAULT_START, DEFAULT_END),
    "牛市(24Q4)":   ("2024-09-01", "2024-10-31"),
    "调整期(24Q1)": ("2024-02-01", "2024-04-30"),
}
FETCH_START_LONG = "2023-06-01"  # 步骤三历史区间需要更早的预热数据

SCAN_THRESHOLDS = [15, 20, 25]
SCAN_ATR_MULTS  = [1.5, 2.0, 2.5]

# ── 50 只股票池 ───────────────────────────────────────────────────────
# 原 backtest_v3.py 的 21 只（强势/成长偏向）+ 新增 29 只（多元化补充）
UNIVERSE = [
    # ── 原有 21 只（强势/成长/周期龙头）────────────────────────────
    ("601899", "紫金矿业",  "有色金属"),
    ("603799", "华友钴业",  "有色金属"),
    ("603993", "洛阳钼业",  "有色金属"),
    ("600547", "山东黄金",  "黄金矿业"),
    ("600900", "长江电力",  "电力"),
    ("600011", "华能国际",  "电力"),
    ("601088", "中国神华",  "能源矿业"),
    ("603986", "兆易创新",  "半导体"),
    ("688008", "澜起科技",  "半导体"),
    ("300308", "中际旭创",  "AI算力"),
    ("300750", "宁德时代",  "新能源"),
    ("002594", "比亚迪",    "新能源"),
    ("300274", "阳光电源",  "新能源"),
    ("600519", "贵州茅台",  "消费白酒"),
    ("600276", "恒瑞医药",  "创新药"),
    ("601398", "工商银行",  "国有银行"),
    ("600036", "招商银行",  "股份银行"),
    ("600309", "万华化学",  "化工"),
    ("600760", "中航沈飞",  "军工"),
    ("600150", "中国船舶",  "军工造船"),
    ("601390", "中国中铁",  "基建"),

    # ── 新增 29 只（防御/价值/弱势/多元化）──────────────────────
    # 消费/食品饮料（防御型，估值回落阶段）
    ("600887", "伊利股份",  "防御消费"),
    ("603288", "海天味业",  "防御消费"),
    ("000858", "五粮液",    "消费白酒"),
    ("002304", "洋河股份",  "消费白酒"),
    ("000568", "泸州老窖",  "消费白酒"),
    ("600600", "青岛啤酒",  "防御消费"),

    # 医药（传统/器械，不同于创新药）
    ("600085", "同仁堂",    "传统医药"),
    ("300760", "迈瑞医疗",  "医疗器械"),
    ("600436", "片仔癀",    "传统医药"),

    # 金融/保险/券商（价值型，受市场情绪压制）
    ("601318", "中国平安",  "保险"),
    ("601601", "中国太保",  "保险"),
    ("600030", "中信证券",  "券商"),

    # 传统制造/重工（出口+内需，周期中段）
    ("600031", "三一重工",  "工程机械"),
    ("000425", "徐工机械",  "工程机械"),

    # 钢铁/基础材料（强周期，估值低）
    ("600019", "宝钢股份",  "钢铁"),
    ("600585", "海螺水泥",  "建材"),

    # 交通运输（复苏型）
    ("601111", "中国国航",  "航空"),
    ("600018", "上港集团",  "港口"),
    ("600009", "上海机场",  "机场"),

    # 通信运营（防御高分红）
    ("600941", "中国移动",  "电信运营"),

    # 汽车（传统+新能源双轨）
    ("600104", "上汽集团",  "传统汽车"),
    ("601127", "赛力斯",    "新能源汽车"),

    # 石油化工（高分红周期）
    ("600028", "中国石化",  "石油化工"),

    # 特种化工/新材料
    ("002648", "卫星化学",  "特种化工"),

    # 安防科技（成熟期，估值压缩）
    ("002415", "海康威视",  "安防科技"),

    # 农业养殖（强周期底部）
    ("002714", "牧原股份",  "农业养殖"),

    # 家电（价值+出口）
    ("000651", "格力电器",  "家电"),

    # 零售/免税
    ("601888", "中国中免",  "零售免税"),

    # 金融科技
    ("600570", "恒生电子",  "金融科技"),
]

assert len(UNIVERSE) == 50, f"股票数量应为50，当前{len(UNIVERSE)}"


# ── 数据获取 ──────────────────────────────────────────────────────────

def _ak_symbol(symbol: str) -> str:
    """转换为 AkShare stock_zh_a_daily 所需格式：sh/sz + code"""
    return ("sh" if symbol[:2] in ("60", "68", "11") else "sz") + symbol


def fetch_price(symbol: str, start: str) -> pd.DataFrame:
    """
    拉取前复权日线数据，优先 AkShare（稳定），失败则尝试东方财富直连。
    返回 OHLCV DataFrame（index=date str，升序）。
    """
    start_fmt = start.replace("-", "")
    end_fmt   = "20500101"

    # ── 方法一：AkShare ─────────────────────────────────────────────
    for attempt in range(3):
        try:
            df = ak.stock_zh_a_daily(
                symbol=_ak_symbol(symbol),
                start_date=start_fmt,
                end_date=end_fmt,
                adjust="qfq",
            )
            if df.empty:
                break
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df = df.set_index("date")[["open", "high", "low", "close", "volume"]].sort_index()
            return df
        except Exception:
            if attempt < 2:
                time.sleep(2.0 * (attempt + 1))

    # ── 方法二：东方财富直连（备用）────────────────────────────────
    prefix = "1" if symbol[:2] in ("60", "68", "11") else "0"
    for attempt in range(3):
        try:
            resp = requests.get(
                "https://push2his.eastmoney.com/api/qt/stock/kline/get",
                params={
                    "secid": f"{prefix}.{symbol}",
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56",
                    "klt": "101", "fqt": "1",
                    "beg": start_fmt, "end": end_fmt,
                    "ut": "7eea3edcaed734bea9cbfc24409ed989",
                },
                proxies={"http": None, "https": None},
                timeout=10,
            )
            resp.raise_for_status()
            klines = (resp.json().get("data") or {}).get("klines") or []
            if not klines:
                break
            rows = []
            for line in klines:
                p = line.split(",")
                rows.append({"date": p[0], "open": float(p[1]), "close": float(p[2]),
                             "high": float(p[3]), "low": float(p[4]), "volume": float(p[5])})
            return pd.DataFrame(rows).set_index("date")
        except Exception:
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))

    return pd.DataFrame()


# ── 大盘过滤器 ────────────────────────────────────────────────────────

def fetch_index_df(start: str) -> pd.DataFrame:
    """拉取沪深300日线，计算 MA60，用于大盘机制过滤。"""
    for attempt in range(3):
        try:
            df = ak.stock_zh_index_daily(symbol="sh000300")
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df = df[df["date"] >= start].set_index("date")[["close"]].sort_index()
            df["ma60"] = df["close"].rolling(60).mean()
            return df
        except Exception:
            if attempt < 2:
                time.sleep(2.0)
    return pd.DataFrame()


def is_bull_at(index_df: pd.DataFrame, date: str) -> bool:
    """沪深300收盘价在 MA60 之上视为多头市场；无指数数据时默认返回 True。"""
    if index_df.empty:
        return True
    past = index_df[index_df.index <= date]
    if len(past) < 60:
        return True
    row = past.iloc[-1]
    return (not pd.isna(row["ma60"])) and (row["close"] > row["ma60"])


# ── 信号与回测核心（与 signal_stats.py 相同逻辑）────────────────────

def tech_score_at(df_factored: pd.DataFrame, i: int) -> float:
    if i < WARMUP:
        return 0.0
    s = df_factored.iloc[:i + 1]
    w = {"trend": 0.4, "rsi": 0.25, "macd": 0.25, "volume": 0.1}
    raw = (score_trend(s) * w["trend"] + score_rsi(s) * w["rsi"]
           + score_macd(s) * w["macd"] + score_volume(s) * w["volume"])
    return round(raw * 100, 1)


def run_stats(df_factored: pd.DataFrame, start: str, end: str,
              threshold: float, atr_mult: float,
              index_df: pd.DataFrame = None,
              early_exit: bool = False, early_exit_thr: float = -10) -> list:
    if df_factored.empty or len(df_factored) < WARMUP + HOLD_DAYS + 2:
        return []
    dates = list(df_factored.index)
    trades = []
    for i, date in enumerate(dates):
        if date < start or date > end:
            continue
        if index_df is not None and not is_bull_at(index_df, date):
            continue
        score = tech_score_at(df_factored, i)
        if score <= threshold:
            continue
        future = df_factored.iloc[i + 1: i + 1 + HOLD_DAYS]
        if len(future) < HOLD_DAYS:
            continue
        entry = float(future.iloc[0]["open"])
        atr   = float(df_factored.iloc[i]["atr14"])
        if pd.isna(atr) or atr <= 0 or entry <= 0:
            continue
        stop = entry - atr * atr_mult
        take = entry + atr * atr_mult * RR_RATIO
        exit_px, reason = None, "超时"
        for j, row in enumerate(future.itertuples()):
            if row.low <= stop:
                exit_px, reason = stop, "止损"
                break
            if row.high >= take:
                exit_px, reason = take, "止盈"
                break
            if early_exit and tech_score_at(df_factored, i + 1 + j) < early_exit_thr:
                # 信号反转：次日开盘离场（无次日则用当日收盘）
                if j + 1 < len(future):
                    exit_px, reason = float(future.iloc[j + 1]["open"]), "信号反转"
                else:
                    exit_px, reason = float(row.close), "信号反转"
                break
        if exit_px is None:
            exit_px = float(future.iloc[-1]["close"])
        pnl = (exit_px - entry) / entry * 100
        trades.append({"date": date, "pnl": round(pnl, 2),
                       "reason": reason, "score": score})
    return trades


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
    reasons = {r: sum(1 for t in trades if t["reason"] == r)
               for r in ("止损", "止盈", "超时", "信号反转")}
    return {
        "n":             len(pnls),
        "win_rate":      round(len(wins) / len(pnls) * 100, 1),
        "avg_return":    round(float(np.mean(pnls)), 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else float("inf"),
        "avg_win":       round(float(np.mean(wins)), 2) if wins else 0.0,
        "avg_loss":      round(abs(float(np.mean(losses))), 2) if losses else 0.0,
        "reasons":       reasons,
    }


def fmt_metrics(m: dict) -> str:
    if m["n"] == 0:
        return "无触发"
    pf  = f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "∞"
    r   = m["reasons"]
    rev = f" 反转{r['信号反转']}" if r.get("信号反转", 0) > 0 else ""
    return (f"{m['n']}笔  胜率{m['win_rate']}%  均{m['avg_return']:+.2f}%  "
            f"盈亏比{pf}  [止损{r['止损']} 止盈{r['止盈']} 超时{r['超时']}{rev}]")


def print_acceptance(m: dict) -> None:
    if m["n"] == 0:
        return
    pf = m["profit_factor"] if m["profit_factor"] != float("inf") else 999.0
    checks = [
        (m["n"] >= 100,      f"样本≥100（当前 {m['n']}）"),
        (m["win_rate"] > 50, f"胜率>50%（当前 {m['win_rate']}%）"),
        (pf >= 1.5,          f"盈亏比≥1.5（当前 {pf:.2f}）"),
    ]
    for ok, desc in checks:
        print(f"    {'✅' if ok else '❌'} {desc}")
    ci = 1.96 * ((m["win_rate"] / 100 * (1 - m["win_rate"] / 100) / m["n"]) ** 0.5) * 100
    print(f"    📊 胜率95%置信区间：{m['win_rate'] - ci:.1f}% ~ {m['win_rate'] + ci:.1f}%")
    if all(ok for ok, _ in checks) and (m["win_rate"] - ci) > 50:
        print("    → 全部达标且置信区间下界>50%，信号显著有效")
    elif all(ok for ok, _ in checks):
        print("    → 点估计全部达标，但置信区间下界未超50%，建议继续积累")
    else:
        print("    → 尚未全部达标")


# ── 步骤实现 ──────────────────────────────────────────────────────────

def load_universe(fetch_start: str) -> list:
    """拉取50只股票数据，返回 [(symbol, name, sector, df_factored), ...]。"""
    results = []
    for i, (sym, name, sector) in enumerate(UNIVERSE):
        print(f"  [{i+1:2d}/50] {name}({sym})...", end=" ", flush=True)
        if i > 0:
            time.sleep(0.4)   # 避免东方财富 API 频率限制
        df_raw = fetch_price(sym, fetch_start)
        if df_raw.empty or len(df_raw) < WARMUP + 10:
            print("数据不足，跳过")
            continue
        df_f = add_all_factors(df_raw)
        results.append((sym, name, sector, df_f))
        print(f"OK ({len(df_raw)}行)")
    return results


def step1(data: list, threshold: float = 20, atr_mult: float = 2.0,
          index_df: pd.DataFrame = None, early_exit: bool = False) -> None:
    start, end = DEFAULT_START, DEFAULT_END
    tag = "（含大盘过滤）" if index_df is not None else ""
    exit_tag = "  [路一:信号反转提前离场]" if early_exit else ""
    print(f"\n{'='*70}")
    print(f"步骤一：50只股票历史信号统计{tag}{exit_tag}  阈值>{threshold}  ATR×{atr_mult}  {start}~{end}")
    print(f"{'='*70}")

    sector_trades: dict[str, list] = {}
    all_trades = []
    for sym, name, sector, df_f in data:
        trades = run_stats(df_f, start, end, threshold, atr_mult, index_df, early_exit)
        all_trades.extend(trades)
        sector_trades.setdefault(sector, []).extend(trades)
        m = calc_metrics(trades)
        print(f"  {name:8}({sym})  {fmt_metrics(m)}")

    print(f"\n{'─'*70}")
    print("  板块汇总：")
    for sec, trades in sorted(sector_trades.items()):
        m = calc_metrics(trades)
        print(f"    {sec:8}  {fmt_metrics(m)}")

    print(f"\n{'─'*70}")
    m_all = calc_metrics(all_trades)
    print(f"  全股票池汇总:  {fmt_metrics(m_all)}")
    print("\n  验收标准（宽基50只，样本门槛提升至100笔）：")
    print_acceptance(m_all)


def step2(data: list, index_df: pd.DataFrame = None, early_exit: bool = False) -> None:
    start, end = DEFAULT_START, DEFAULT_END
    tag = "（含大盘过滤）" if index_df is not None else ""
    exit_tag = "  [路一]" if early_exit else ""
    print(f"\n{'='*70}")
    print(f"步骤二：参数鲁棒性扫描{tag}{exit_tag}  {start}~{end}  50只股票")
    print(f"{'='*70}")
    print(f"  {'阈值':>4} {'ATR':>4}  {'样本':>5} {'胜率':>7} {'均收益':>8} {'盈亏比':>7}  CI下界")
    print("  " + "─" * 60)
    for thr in SCAN_THRESHOLDS:
        for atr_m in SCAN_ATR_MULTS:
            all_trades = []
            for _, _, _, df_f in data:
                all_trades.extend(run_stats(df_f, start, end, thr, atr_m, index_df, early_exit))
            m = calc_metrics(all_trades)
            if m["n"] == 0:
                print(f"  {thr:>4} {atr_m:>4.1f}  无触发")
                continue
            pf    = f"{m['profit_factor']:.2f}" if m["profit_factor"] != float("inf") else "   ∞"
            ci_lo = m["win_rate"] - 1.96 * ((m["win_rate"]/100*(1-m["win_rate"]/100)/m["n"])**0.5)*100
            print(f"  {thr:>4} {atr_m:>4.1f} {m['n']:>6} {m['win_rate']:>6.1f}% "
                  f"{m['avg_return']:>+7.2f}% {pf:>7}  {ci_lo:.1f}%")
    print("\n  注：置信区间下界>50% 才可认为胜率显著为正。")


def step3(data: list, threshold: float = 20, atr_mult: float = 2.0,
          index_df: pd.DataFrame = None, early_exit: bool = False) -> None:
    tag = "（含大盘过滤）" if index_df is not None else ""
    exit_tag = "  [路一]" if early_exit else ""
    print(f"\n{'='*70}")
    print(f"步骤三：市场环境对比{tag}{exit_tag}  阈值>{threshold}  ATR×{atr_mult}  50只股票")
    print(f"{'='*70}")
    for label, (start, end) in ENV_PERIODS.items():
        all_trades = []
        for _, _, _, df_f in data:
            all_trades.extend(run_stats(df_f, start, end, threshold, atr_mult, index_df, early_exit))
        m = calc_metrics(all_trades)
        print(f"\n  [{label}] {start} ~ {end}")
        print(f"    {fmt_metrics(m)}")


# ── 入口 ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="50只股票宽基信号统计")
    ap.add_argument("--scan",         action="store_true", help="步骤二：参数扫描")
    ap.add_argument("--env",          action="store_true", help="步骤三：市场环境对比")
    ap.add_argument("--all",          action="store_true", help="全部步骤")
    ap.add_argument("--bull-filter",  action="store_true", help="加沪深300 MA60 大盘过滤器")
    ap.add_argument("--compare",      action="store_true", help="同时输出过滤前后对比")
    ap.add_argument("--early-exit",   action="store_true", help="路一：信号反转提前离场（分<-10次日开盘离场）")
    ap.add_argument("--compare-exit", action="store_true", help="路一对比：原策略 vs 信号反转提前离场")
    args = ap.parse_args()

    run1 = args.all or not (args.scan or args.env)
    run2 = args.all or args.scan
    run3 = args.all or args.env

    fetch_start = FETCH_START_LONG if (run3 or args.all) else FETCH_START

    print(f"拉取50只股票数据（起始：{fetch_start}）...")
    data = load_universe(fetch_start)
    print(f"\n成功加载 {len(data)}/50 只股票")

    index_df = None
    if args.bull_filter or args.compare:
        print("拉取沪深300指数...", end=" ", flush=True)
        index_df = fetch_index_df(fetch_start)
        print(f"OK ({len(index_df)}行)" if not index_df.empty else "失败，过滤器禁用")

    print()
    idx = index_df if args.bull_filter else None

    if args.compare:
        # 并排对比：不过滤 vs 大盘过滤
        print(">>> 无大盘过滤")
        if run1: step1(data)
        if run2: step2(data)
        if run3: step3(data)
        print("\n>>> 加沪深300 MA60 大盘过滤")
        if run1: step1(data, index_df=index_df)
        if run2: step2(data, index_df=index_df)
        if run3: step3(data, index_df=index_df)
    elif args.compare_exit:
        # 路一对比：原策略 vs 信号反转提前离场
        print(">>> 原策略（持满5日或止盈/止损）")
        if run1: step1(data, index_df=idx)
        if run2: step2(data, index_df=idx)
        if run3: step3(data, index_df=idx)
        print("\n>>> 路一：信号反转提前离场（持仓中分<-10则次日开盘离场）")
        if run1: step1(data, index_df=idx, early_exit=True)
        if run2: step2(data, index_df=idx, early_exit=True)
        if run3: step3(data, index_df=idx, early_exit=True)
    else:
        early = args.early_exit
        if run1: step1(data, index_df=idx, early_exit=early)
        if run2: step2(data, index_df=idx, early_exit=early)
        if run3: step3(data, index_df=idx, early_exit=early)

    print()
