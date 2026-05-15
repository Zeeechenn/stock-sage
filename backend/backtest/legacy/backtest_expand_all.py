"""
跨市场信号扩展测试：全板块 A/B 对比
A: 纯技术信号
B: 技术 + 板块对应美股ETF信号（20%权重）

目标：判断哪些板块的跨市场信号有增益，有增益则扩展到 cross_market.py
回测期：2024-01-01 ~ 2026-05-12（与 v3 一致）
"""
import sys
import warnings
import pandas as pd
import numpy as np
import akshare as ak
warnings.filterwarnings("ignore")

BT_START  = "2024-01-01"
BT_END    = "2026-05-12"
WARMUP    = "20220101"
CROSS_W   = 0.20

ENTRY_BULL = 20
ENTRY_BEAR = 50
EXIT_THR   = -20
ATR_MULT   = 2.0
RR_RATIO   = 2.0
MAX_HOLD   = 20
RSI_OB     = 68
SL_COOL    = 3

# 每个板块对应的美股信号（加权后换算成 -100~+100 分）
SECTOR_SIGNALS = {
    "有色金属": {
        "COPX":     ("铜矿ETF",     0.40),
        "GLD":      ("黄金ETF",     0.30),
        "CPER":     ("铜ETF",       0.20),
        "UUP": ("美元指数",   -0.10),
    },
    "黄金矿业": {
        "GLD":      ("黄金ETF",     0.50),
        "GOLD":     ("Barrick",     0.30),
        "UUP": ("美元指数",   -0.20),
    },
    "能源矿业": {
        "XLE":      ("能源ETF",     0.40),
        "GLD":      ("黄金ETF",     0.20),
        "COPX":     ("铜矿ETF",     0.20),
        "UUP": ("美元指数",   -0.20),
    },
    "电力": {
        "XLU":      ("公用事业ETF", 0.70),
        "SPY":      ("标普500",     0.30),
    },
    "半导体": {
        "SOXX":     ("半导体ETF",   0.45),
        "QQQ":      ("纳指ETF",     0.35),
        "UUP": ("美元指数",   -0.20),
    },
    "AI算力": {
        "QQQ":      ("纳指ETF",     0.50),
        "SOXX":     ("半导体ETF",   0.30),
        "SMH":      ("芯片ETF",     0.20),
    },
    "新能源": {
        "LIT":      ("锂矿ETF",     0.35),
        "ICLN":     ("清洁能源ETF", 0.35),
        "QQQ":      ("纳指ETF",     0.30),
    },
    "消费": {
        "XLP":      ("必需消费ETF", 0.50),
        "XLY":      ("可选消费ETF", 0.50),
    },
    "医药": {
        "XLV":      ("医疗ETF",     0.55),
        "IBB":      ("生物科技ETF", 0.45),
    },
    "银行": {
        "XLF":      ("金融ETF",     0.70),
        "SPY":      ("标普500",     0.30),
    },
    "化工": {
        "XLB":      ("基础材料ETF", 0.60),
        "UUP": ("美元指数",   -0.20),
        "SPY":      ("标普500",     0.20),
    },
    "军工": {
        "ITA":      ("航空防务ETF", 0.70),
        "SPY":      ("标普500",     0.30),
    },
    "基建": {
        "XLI":      ("工业ETF",     0.60),
        "SPY":      ("标普500",     0.40),
    },
}

TEST_STOCKS = [
    ("sh601899", "紫金矿业", "有色金属"),
    ("sh603799", "华友钴业", "有色金属"),
    ("sh603993", "洛阳钼业", "有色金属"),
    ("sh600547", "山东黄金", "黄金矿业"),
    ("sh601088", "中国神华", "能源矿业"),
    ("sh600900", "长江电力", "电力"),
    ("sh600011", "华能国际", "电力"),
    ("sh603986", "兆易创新", "半导体"),
    ("sh688008", "澜起科技", "半导体"),
    ("sz300308", "中际旭创", "AI算力"),
    ("sz300750", "宁德时代", "新能源"),
    ("sz002594", "比亚迪",   "新能源"),
    ("sz300274", "阳光电源", "新能源"),
    ("sh600519", "贵州茅台", "消费"),
    ("sh600276", "恒瑞医药", "医药"),
    ("sh601398", "工商银行", "银行"),
    ("sh600036", "招商银行", "银行"),
    ("sh600309", "万华化学", "化工"),
    ("sh600760", "中航沈飞", "军工"),
    ("sh600150", "中国船舶", "军工"),
    ("sh601390", "中国中铁", "基建"),
]

HS300_SYM = "sh000300"


def get_cn(sym: str) -> pd.DataFrame:
    df = ak.stock_zh_a_daily(symbol=sym, start_date=WARMUP,
                              end_date=BT_END.replace("-", ""), adjust="qfq")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[["open", "high", "low", "close", "volume"]].sort_index()


def get_index() -> pd.DataFrame:
    df = ak.stock_zh_index_daily(symbol=HS300_SYM)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    else:
        df.index = pd.to_datetime(df.index)
    return df[["close"]].sort_index()


def get_intl(sector: str) -> pd.DataFrame:
    if sector not in SECTOR_SIGNALS:
        return pd.DataFrame()
    try:
        import yfinance as yf
        syms = list(SECTOR_SIGNALS[sector].keys())
        dfs = {}
        for sym in syms:
            try:
                df = yf.download(sym, start="2023-01-01", end=BT_END,
                                 progress=False, auto_adjust=True)
                if len(df) > 0:
                    s = df["Close"].squeeze()
                    s.index = pd.to_datetime(s.index).tz_localize(None)
                    dfs[sym] = s
            except Exception as e:
                print(f"    yfinance {sym}: {e}", file=sys.stderr)
        return pd.DataFrame(dfs)
    except ImportError:
        return pd.DataFrame()


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
    d["vol20"]     = d["close"].pct_change().rolling(20).std() * np.sqrt(252) * 100
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


def adaptive_atr_mult(df: pd.DataFrame, i: int) -> float:
    v = df.iloc[i]["vol20"]
    if pd.isna(v):
        return ATR_MULT
    if v > 60:
        return ATR_MULT * 1.5
    if v < 25:
        return ATR_MULT * 0.8
    return ATR_MULT


def tech_signal(df: pd.DataFrame, i: int) -> tuple[float, float, float]:
    if i < 1:
        return 0.0, 0.0, 50.0
    row, prev = df.iloc[i], df.iloc[i-1]
    c, m20, m60, rsi, hist, phist, atr = (
        row["close"], row["ma20"], row["ma60"], row["rsi14"],
        row["macd_hist"], prev["macd_hist"], row["atr14"])
    if any(pd.isna(v) for v in [m20, m60, rsi, hist, atr]):
        return 0.0, float(atr) if not pd.isna(atr) else 0.0, 50.0
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
    vol5  = df.iloc[max(0, i-4):i+1]["volume"].mean()
    vol20 = df.iloc[max(0, i-19):i+1]["volume"].mean()
    vol_s = trend * 0.5 if vol20 > 0 and vol5 / vol20 > 1.2 else 0.0
    score = (trend * 0.4 + rsi_s * 0.25 + macd_s * 0.25 + vol_s * 0.1) * 100
    return round(score, 1), float(atr), float(rsi)


def cross_signal(intl_df: pd.DataFrame, date: pd.Timestamp, sector: str) -> float:
    if intl_df.empty or sector not in SECTOR_SIGNALS:
        return 0.0
    past = intl_df[intl_df.index < date]
    if len(past) < 2:
        return 0.0
    ret = past.pct_change().iloc[-1]
    weights = SECTOR_SIGNALS[sector]
    score = 0.0
    for sym, (_, w) in weights.items():
        if sym in ret and not pd.isna(ret[sym]):
            score += float(ret[sym]) * w * 2000
    return round(max(-100, min(100, score)), 1)


def run_bt(df: pd.DataFrame, index_df: pd.DataFrame,
           intl_df: pd.DataFrame, sector: str, use_cross: bool) -> list:
    bt_all = list(df.index)
    bt     = df[df.index >= BT_START]
    trades   = []
    position = None
    cooldown = pd.Timestamp("1970-01-01")

    for date in bt.index:
        i   = bt_all.index(date)
        row = df.iloc[i]
        t_sig, atr, rsi = tech_signal(df, i)

        if use_cross and not intl_df.empty:
            c_sig = cross_signal(intl_df, date, sector)
            sig   = t_sig * (1 - CROSS_W) + c_sig * CROSS_W
        else:
            sig = t_sig

        if position is not None:
            sl, tp, ep, hd = (position["stop_loss"], position["take_profit"],
                               position["entry_price"], position["hold_days"])
            xp = xr = None
            if row["low"] <= sl:
                xp, xr = sl, "止损"
                cooldown = date + pd.Timedelta(days=SL_COOL)
            elif row["high"] >= tp:
                xp, xr = tp, "止盈"
            elif hd >= MAX_HOLD:
                nxt = bt[bt.index > date]
                xp  = nxt.iloc[0]["open"] if len(nxt) else row["close"]
                xr  = "超时"
            elif sig < EXIT_THR:
                nxt = bt[bt.index > date]
                xp  = nxt.iloc[0]["open"] if len(nxt) else row["close"]
                xr  = "信号反转"
            if xp is not None:
                trades.append({"entry": position["entry_date"].strftime("%Y-%m-%d"),
                               "exit": date.strftime("%Y-%m-%d"),
                               "ep": ep, "xp": xp,
                               "pnl": (xp - ep) / ep * 100,
                               "reason": xr, "hold": hd})
                position = None
            else:
                position["hold_days"] += 1

        if position is None and date > cooldown:
            bull = is_bull(index_df, date) if not index_df.empty else True
            entry_thr = ENTRY_BULL if bull else ENTRY_BEAR
            if sig > entry_thr and rsi < RSI_OB and not pd.isna(atr) and atr > 0:
                nxt = bt[bt.index > date]
                if not len(nxt):
                    break
                no, nd = nxt.iloc[0]["open"], nxt.index[0]
                am = adaptive_atr_mult(df, i)
                position = {"entry_date": nd, "entry_price": no,
                            "stop_loss":  no - atr * am,
                            "take_profit": no + atr * am * RR_RATIO,
                            "hold_days": 1}

    if position:
        lc = bt.iloc[-1]["close"]
        trades.append({"entry": position["entry_date"].strftime("%Y-%m-%d"),
                       "exit": bt.index[-1].strftime("%Y-%m-%d"),
                       "ep": position["entry_price"], "xp": lc,
                       "pnl": (lc - position["entry_price"]) / position["entry_price"] * 100,
                       "reason": "到期", "hold": position["hold_days"]})
    return trades


def calc_metrics(trades: list) -> dict:
    if not trades:
        return {"n": 0, "total": 0.0, "win": 0.0, "mdd": 0.0, "sharpe": 0.0}
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
    wins     = [p for p in pnls if p > 0]
    hold_avg = np.mean([t["hold"] for t in trades])
    rf       = 3.0 / 252 * hold_avg
    excess   = [p - rf for p in pnls]
    sharpe   = (np.mean(excess) / np.std(excess) * np.sqrt(252 / hold_avg)
                if np.std(excess) > 0 else 0.0)
    return {"n": len(pnls), "win": round(len(wins) / len(pnls) * 100, 1),
            "total": round(total, 2), "mdd": round(mdd, 2),
            "sharpe": round(sharpe, 2)}


if __name__ == "__main__":
    print(f"\n跨市场信号扩展测试  {BT_START} ~ {BT_END}")
    print(f"方法：每只股票跑 A（纯技术）vs B（技术+板块美股信号 20%）\n")

    print("▶ 拉取沪深300...", end=" ", flush=True)
    try:
        index_df = precompute_index(get_index())
        print(f"OK ({len(index_df)} 行)")
    except Exception as e:
        print(f"失败({e})")
        index_df = pd.DataFrame()

    # 按板块预拉取美股数据，避免重复下载
    intl_cache: dict[str, pd.DataFrame] = {}
    sectors_needed = set(s for _, _, s in TEST_STOCKS)
    for sec in sorted(sectors_needed):
        if sec not in SECTOR_SIGNALS:
            intl_cache[sec] = pd.DataFrame()
            continue
        print(f"▶ 拉取美股 [{sec}]...", end=" ", flush=True)
        df_intl = get_intl(sec)
        intl_cache[sec] = df_intl
        got = list(df_intl.columns) if not df_intl.empty else []
        print(f"OK: {got}" if got else "无数据")

    results = []

    for sym, name, sector in TEST_STOCKS:
        print(f"\n▶ {name} ({sym}) [{sector}]", flush=True)
        try:
            df_raw  = get_cn(sym)
            df      = precompute(df_raw)
            intl_df = intl_cache.get(sector, pd.DataFrame())

            bt_slice = df[df.index >= BT_START]
            if len(bt_slice) < 2:
                print("  ⚠ 数据不足，跳过")
                continue
            bah = round((bt_slice.iloc[-1]["close"] - bt_slice.iloc[0]["open"]) /
                        bt_slice.iloc[0]["open"] * 100, 2)

            mA = calc_metrics(run_bt(df, index_df, intl_df, sector, use_cross=False))
            mB = calc_metrics(run_bt(df, index_df, intl_df, sector, use_cross=True))

            delta_total  = mB["total"] - mA["total"]
            delta_win    = mB["win"]   - mA["win"]
            delta_sharpe = mB["sharpe"] - mA["sharpe"]
            improved     = delta_total > 0

            tag = "▲" if improved else "▼"
            print(f"  买持 {bah:+.2f}%  |  "
                  f"A纯技术 {mA['total']:+.2f}%(W{mA['win']:.0f}%) → "
                  f"B+跨市场 {mB['total']:+.2f}%(W{mB['win']:.0f}%)  "
                  f"{tag}{abs(delta_total):.2f}%")

            results.append({
                "name": name, "sym": sym, "sector": sector, "bah": bah,
                "A_total": mA["total"], "A_win": mA["win"], "A_mdd": mA["mdd"],
                "A_sharpe": mA["sharpe"], "A_n": mA["n"],
                "B_total": mB["total"], "B_win": mB["win"], "B_mdd": mB["mdd"],
                "B_sharpe": mB["sharpe"], "B_n": mB["n"],
                "delta": delta_total, "delta_win": delta_win,
                "delta_sharpe": delta_sharpe, "improved": improved,
                "has_intl": not intl_df.empty,
            })
        except Exception as e:
            print(f"  ❌ 失败：{e}")

    # ── 板块汇总 ────────────────────────────────────────────────────────
    print("\n" + "=" * 90)
    print("  板块级汇总（板块内所有股票平均）")
    print("  " + "-" * 86)
    print(f"  {'板块':8}  {'股数':>4}  {'A策略均值':>10}  {'B策略均值':>10}  "
          f"{'Δ总收益':>9}  {'Δ胜率':>7}  {'Δ夏普':>7}  {'有美股数据':>9}")
    print("  " + "-" * 86)

    sector_results: dict[str, list] = {}
    for r in results:
        sector_results.setdefault(r["sector"], []).append(r)

    sector_decisions = {}
    for sec, rows in sorted(sector_results.items()):
        valid = [r for r in rows if r["A_n"] > 0 and r["B_n"] > 0]
        if not valid:
            continue
        avg_A    = np.mean([r["A_total"] for r in valid])
        avg_B    = np.mean([r["B_total"] for r in valid])
        avg_d    = np.mean([r["delta"] for r in valid])
        avg_dw   = np.mean([r["delta_win"] for r in valid])
        avg_ds   = np.mean([r["delta_sharpe"] for r in valid])
        has_data = any(r["has_intl"] for r in valid)
        improved = avg_d > 0.5 and has_data   # 阈值：总收益提升>0.5%才算有效
        sector_decisions[sec] = improved
        tag = "✅ 扩展" if improved else ("⚪ 无效" if has_data else "❌ 无数据")
        print(f"  {sec:8}  {len(valid):>4}  {avg_A:>+9.2f}%  {avg_B:>+9.2f}%  "
              f"{avg_d:>+8.2f}%  {avg_dw:>+6.1f}%  {avg_ds:>+6.2f}  {tag:>9}")

    # ── 明细表格 ────────────────────────────────────────────────────────
    print("\n" + "=" * 100)
    print("  个股明细")
    print("  " + "-" * 96)
    print(f"  {'板块':8} {'名称':8} {'买持':>8} "
          f"{'A总收益':>9} {'A胜率':>7} {'A回撤':>7} "
          f"{'B总收益':>9} {'B胜率':>7} {'B回撤':>7} {'Δ':>8}  决策")
    print("  " + "-" * 96)
    for r in results:
        if r["A_n"] == 0 and r["B_n"] == 0:
            continue
        decided = sector_decisions.get(r["sector"], False)
        tag = "✅" if (r["improved"] and decided) else ("⚪" if decided else "")
        print(f"  {r['sector']:8} {r['name']:8} {r['bah']:>+7.2f}%"
              f"  {r['A_total']:>+8.2f}% {r['A_win']:>6.1f}% {r['A_mdd']:>6.1f}%"
              f"  {r['B_total']:>+8.2f}% {r['B_win']:>6.1f}% {r['B_mdd']:>6.1f}%"
              f"  {r['delta']:>+7.2f}%  {tag}")

    # ── 结论 ────────────────────────────────────────────────────────────
    expand_sectors = [s for s, v in sector_decisions.items() if v]
    no_effect      = [s for s, v in sector_decisions.items() if not v]
    print(f"\n{'='*60}")
    print(f"结论：")
    if expand_sectors:
        print(f"  ✅ 建议扩展跨市场信号的板块（总收益改善 >0.5%）：")
        for s in expand_sectors:
            rows = [r for r in results if r["sector"] == s]
            avg_d = np.mean([r["delta"] for r in rows if r["A_n"] > 0])
            print(f"     {s}  平均改善 {avg_d:+.2f}%")
    else:
        print("  ⚠ 没有板块显示出显著的跨市场信号改善（>0.5%）")
    if no_effect:
        print(f"  ⚪ 无效/无数据板块：{', '.join(no_effect)}")
    print()
