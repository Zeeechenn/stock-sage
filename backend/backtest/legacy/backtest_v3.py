"""
StockSage 扩展回测 v3
- 回测期：2024-01-01 ~ 2026-05-12
- 股票池：21只，覆盖9个板块
- 改进：v2全部改进 + 跨市场信号（有色金属/黄金矿业）
"""
import sys
import warnings
import pandas as pd
import numpy as np
import akshare as ak
warnings.filterwarnings("ignore")

# ── 参数 ──────────────────────────────────────────────────────────────
BT_START   = "2024-01-01"
BT_END     = "2026-05-12"
WARMUP     = "20220101"

ENTRY_BULL = 20     # 牛市入场阈值
ENTRY_BEAR = 50     # 熊市入场阈值（提高，减少逆势交易）
EXIT_THR   = -20
ATR_MULT   = 2.0
RR_RATIO   = 2.0
MAX_HOLD   = 20
RSI_OB     = 68
SL_COOL    = 3
CROSS_W    = 0.20   # 跨市场信号权重（有色/黄金）

# ── 股票池（21只，9板块）─────────────────────────────────────────────
TEST_STOCKS = [
    # 有色金属 — 跨市场信号（COPX/GLD/CPER/DXY）
    ("sh601899", "紫金矿业",  "有色金属"),
    ("sh603799", "华友钴业",  "有色金属"),
    ("sh603993", "洛阳钼业",  "有色金属"),
    # 黄金矿业 — 跨市场信号（GLD/GOLD/DXY）
    ("sh600547", "山东黄金",  "黄金矿业"),
    # 能源/电力
    ("sh600900", "长江电力",  "电力"),
    ("sh600011", "华能国际",  "电力"),
    ("sh601088", "中国神华",  "能源矿业"),
    # 半导体/AI算力
    ("sh603986", "兆易创新",  "半导体"),
    ("sh688008", "澜起科技",  "半导体"),
    ("sz300308", "中际旭创",  "AI算力"),
    # 新能源车/储能
    ("sz300750", "宁德时代",  "新能源"),
    ("sz002594", "比亚迪",    "新能源"),
    ("sz300274", "阳光电源",  "新能源"),
    # 消费
    ("sh600519", "贵州茅台",  "消费"),
    # 医药
    ("sh600276", "恒瑞医药",  "医药"),
    # 银行
    ("sh601398", "工商银行",  "银行"),
    ("sh600036", "招商银行",  "银行"),
    # 化工
    ("sh600309", "万华化学",  "化工"),
    # 军工
    ("sh600760", "中航沈飞",  "军工"),
    ("sh600150", "中国船舶",  "军工"),
    # 基建
    ("sh601390", "中国中铁",  "基建"),
]

# 跨市场信号适用板块
CROSS_SECTORS = {"有色金属", "黄金矿业"}

# 跨市场权重配置
SECTOR_WEIGHTS = {
    "有色金属": {"COPX": 0.40, "GLD": 0.30, "CPER": 0.20, "UUP": -0.10},
    "黄金矿业": {"GLD": 0.50, "GOLD": 0.30, "UUP": -0.20},
}

# 沪深300指数代码
HS300_SYM = "sh000300"


# ── 数据获取 ────────────────────────────────────────────────────────
def get_cn(sym: str) -> pd.DataFrame:
    df = ak.stock_zh_a_daily(symbol=sym, start_date=WARMUP,
                              end_date=BT_END.replace("-", ""), adjust="qfq")
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")[["open", "high", "low", "close", "volume"]].sort_index()


def get_index() -> pd.DataFrame:
    df = ak.stock_zh_index_daily(symbol=HS300_SYM)
    df.index = pd.to_datetime(df.index) if df.index.dtype == "object" else df.index
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    return df[["close"]].sort_index()


def get_intl(sector: str) -> pd.DataFrame:
    """获取跨市场数据（尝试2年历史）"""
    if sector not in SECTOR_WEIGHTS:
        return pd.DataFrame()
    try:
        import yfinance as yf
        syms = list(SECTOR_WEIGHTS[sector].keys())
        dfs = {}
        for sym in syms:
            try:
                df = yf.download(sym, period="3y", progress=False, auto_adjust=True)
                if len(df) == 0:
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


# ── 因子预计算 ────────────────────────────────────────────────────────
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


def cross_signal(intl_df: pd.DataFrame, date: pd.Timestamp, weights: dict) -> float:
    if intl_df.empty:
        return 0.0
    past = intl_df[intl_df.index < date]
    if len(past) < 2:
        return 0.0
    ret = past.pct_change().iloc[-1]
    score = 0.0
    for sym, w in weights.items():
        if sym in ret and not pd.isna(ret[sym]):
            score += float(ret[sym]) * w * 2000
    return round(max(-100, min(100, score)), 1)


# ── 回测引擎 ─────────────────────────────────────────────────────────
def run_bt(df: pd.DataFrame, index_df: pd.DataFrame,
           intl_df: pd.DataFrame, sector: str) -> list:
    bt_all = list(df.index)
    bt     = df[df.index >= BT_START]
    use_cross = sector in CROSS_SECTORS and not intl_df.empty
    weights = SECTOR_WEIGHTS.get(sector, {})

    trades   = []
    position = None
    cooldown = pd.Timestamp("1970-01-01")

    for date in bt.index:
        i   = bt_all.index(date)
        row = df.iloc[i]
        t_sig, atr, rsi = tech_signal(df, i)

        # 跨市场信号融合
        if use_cross:
            c_sig = cross_signal(intl_df, date, weights)
            sig   = t_sig * (1 - CROSS_W) + c_sig * CROSS_W
        else:
            sig = t_sig

        # 持仓检查
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

        # 开仓检查
        if position is None and date > cooldown:
            bull = is_bull(index_df, date)
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
    wins   = [p for p in pnls if p > 0]
    hold_avg = np.mean([t["hold"] for t in trades])
    rf     = 3.0 / 252 * hold_avg
    excess = [p - rf for p in pnls]
    sharpe = (np.mean(excess) / np.std(excess) * np.sqrt(252 / hold_avg)
              if np.std(excess) > 0 else 0.0)
    return {"n": len(pnls), "win": round(len(wins) / len(pnls) * 100, 1),
            "avg": round(np.mean(pnls), 2), "total": round(total, 2),
            "mdd": round(mdd, 2), "sharpe": round(sharpe, 2),
            "best": round(max(pnls), 2), "worst": round(min(pnls), 2),
            "hold_avg": round(hold_avg, 1)}


# ── 主程序 ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\nStockSage 扩展回测 v3  {BT_START} ~ {BT_END}")
    print(f"股票池：{len(TEST_STOCKS)} 只 / 9 个板块")
    print(f"改进：大盘过滤 + 自适应ATR + RSI超买过滤 + 止损冷却 + 跨市场信号\n")

    # 预拉取沪深300指数
    print("▶ 拉取沪深300指数...", end=" ", flush=True)
    try:
        idx_raw    = get_index()
        index_df   = precompute_index(idx_raw)
        print(f"OK ({len(index_df)} 行)")
    except Exception as e:
        print(f"失败({e})，大盘过滤禁用")
        index_df   = pd.DataFrame()

    # 预拉取跨市场数据（按板块）
    intl_cache = {}
    for sec in CROSS_SECTORS:
        print(f"▶ 拉取跨市场数据 [{sec}]...", end=" ", flush=True)
        try:
            intl_cache[sec] = get_intl(sec)
            syms_ok = list(intl_cache[sec].columns)
            print(f"OK: {syms_ok}")
        except Exception as e:
            print(f"失败({e})")
            intl_cache[sec] = pd.DataFrame()

    all_rows = []
    sector_stats: dict[str, list] = {}

    for sym, name, sector in TEST_STOCKS:
        print(f"\n▶ {name} ({sym}) [{sector}]", flush=True)
        try:
            df_raw   = get_cn(sym)
            df       = precompute(df_raw)
            intl_df  = intl_cache.get(sector, pd.DataFrame())

            bt_slice = df[df.index >= BT_START]
            if len(bt_slice) < 2:
                print("  ⚠ 回测期数据不足，跳过")
                continue
            bah = round((bt_slice.iloc[-1]["close"] - bt_slice.iloc[0]["open"]) /
                        bt_slice.iloc[0]["open"] * 100, 2)

            trades = run_bt(df, index_df, intl_df, sector)
            m      = calc_metrics(trades)

            if m["n"]:
                cross_tag = "（含跨市场）" if sector in CROSS_SECTORS else ""
                print(f"  买入持有：{bah:+.2f}%")
                print(f"  策略总收益：{m['total']:+.2f}%{cross_tag}  胜率{m['win']}%  "
                      f"{m['n']}笔  回撤{m['mdd']:.1f}%  夏普{m['sharpe']:.2f}")
                alpha = m["total"] - bah
                print(f"  超额收益：{alpha:+.2f}%  均持{m['hold_avg']}天")
            else:
                print(f"  买入持有：{bah:+.2f}%  |  策略：无触发")

            row_data = {"name": name, "sym": sym.replace("sh","").replace("sz",""),
                        "sector": sector, "bah": bah,
                        "total": m.get("total", None), "n": m.get("n", 0),
                        "win": m.get("win", 0), "mdd": m.get("mdd", 0),
                        "sharpe": m.get("sharpe", 0),
                        "has_cross": sector in CROSS_SECTORS}
            all_rows.append(row_data)
            sector_stats.setdefault(sector, []).append(row_data)

        except Exception as e:
            print(f"  ❌ 失败：{e}")

    # ── 汇总表格 ────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print(f"  {'板块':8} {'名称':8} {'代码':6} {'买持':>8} {'策略':>8} "
          f"{'超额':>8} {'胜率':>6} {'回撤':>6} {'夏普':>6}")
    print("  " + "-" * 76)
    for r in all_rows:
        if r["n"] == 0:
            print(f"  {r['sector']:8} {r['name']:8} {r['sym']:6} "
                  f"{r['bah']:>+7.2f}%  {'—':>8}  {'—':>8}  {'—':>6}  {'—':>6}  {'—':>6}")
            continue
        alpha = r["total"] - r["bah"]
        cross_tag = "★" if r["has_cross"] else " "
        print(f"  {r['sector']:8} {r['name']:8} {r['sym']:6} "
              f"{r['bah']:>+7.2f}% {r['total']:>+7.2f}% {alpha:>+7.2f}%"
              f"  {r['win']:>5.1f}%  {r['mdd']:>5.1f}%  {r['sharpe']:>5.2f}{cross_tag}")

    # ── 板块平均 ─────────────────────────────────────────────────────
    print("\n  板块均值：")
    for sec, rows in sorted(sector_stats.items()):
        valid = [r for r in rows if r["n"] > 0]
        if not valid:
            continue
        avg_total = np.mean([r["total"] for r in valid])
        avg_alpha = np.mean([r["total"] - r["bah"] for r in valid])
        avg_win   = np.mean([r["win"] for r in valid])
        print(f"    {sec:8}  策略均值 {avg_total:+6.2f}%  超额 {avg_alpha:+6.2f}%  胜率 {avg_win:.1f}%")

    print("\n  注：★ = 含跨市场信号（有色金属/黄金矿业）")
    print()
