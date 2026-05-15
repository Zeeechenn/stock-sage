"""
StockSage Phase 6 历史回测
策略：技术信号（ATR止盈止损）— 不含LLM/LightGBM，零前视偏差
回测期：2023-01-01 ~ 2024-12-31（2年）
"""
import sys
import pandas as pd
import numpy as np
import akshare as ak

TEST_STOCKS = [
    ("sh603986", "兆易创新"),
    ("sh688008", "澜起科技"),
    ("sz002028", "思源电气"),
    ("sz300274", "阳光电源"),
]

WARMUP_START  = "20220101"
BACKTEST_START = "2023-01-01"
BACKTEST_END   = "2024-12-31"
ENTRY_THRESHOLD = 20    # 复合得分 > 20 → 买入
EXIT_THRESHOLD  = -20   # 复合得分 < -20 → 平仓
MAX_HOLD_DAYS   = 20    # 最长持仓天数
ATR_MULT        = 2.0   # 止损：收盘 - ATR × 2
RR_RATIO        = 2.0   # 止盈：风险 × 2（1:2 风险收益）


# ── 数据获取 ───────────────────────────────────────────────────────────

def fetch_prices(symbol: str) -> pd.DataFrame:
    # stock_zh_a_daily 支持 sh/sz 前缀，不走东方财富被墙的接口
    df = ak.stock_zh_a_daily(
        symbol=symbol,
        start_date=WARMUP_START,
        end_date=BACKTEST_END.replace("-", ""),
        adjust="qfq",
    )
    # 该接口已有英文列名: date/open/high/low/close/volume
    df.index = pd.to_datetime(df.index) if df.index.dtype == "object" else df.index
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index)
    return df[["open", "high", "low", "close", "volume"]].sort_index()


# ── 因子预计算（一次性，无前视偏差） ──────────────────────────────────

def precompute(df: pd.DataFrame) -> pd.DataFrame:
    """计算技术因子，使用 ewm/rolling（仅依赖过去数据）"""
    d = df.copy()
    # ATR
    prev = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"],
                    (d["high"] - prev).abs(),
                    (d["low"] - prev).abs()], axis=1).max(axis=1)
    d["atr14"] = tr.ewm(alpha=1/14, adjust=False).mean()
    # RSI
    delta = d["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    d["rsi14"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    # MA
    d["ma20"] = d["close"].rolling(20).mean()
    d["ma60"] = d["close"].rolling(60).mean()
    # MACD
    ema12 = d["close"].ewm(span=12, adjust=False).mean()
    ema26 = d["close"].ewm(span=26, adjust=False).mean()
    macd  = ema12 - ema26
    d["macd_hist"] = macd - macd.ewm(span=9, adjust=False).mean()
    return d


def signal_at(df: pd.DataFrame, i: int) -> tuple[float, float]:
    """
    在第 i 行计算技术信号分和 ATR。
    返回 (score, atr14)。score: -100 ~ +100
    """
    if i < 1:
        return 0.0, 0.0
    row  = df.iloc[i]
    prev = df.iloc[i - 1]

    close = row["close"]
    ma20  = row["ma20"]
    ma60  = row["ma60"]
    rsi14 = row["rsi14"]
    hist  = row["macd_hist"]
    phist = prev["macd_hist"]
    atr14 = row["atr14"]

    if any(pd.isna(v) for v in [ma20, ma60, rsi14, hist, atr14]):
        return 0.0, float(atr14) if not pd.isna(atr14) else 0.0

    # 趋势
    if ma20 > ma60 and close > ma20:
        trend = 1.0
    elif ma20 < ma60 and close < ma20:
        trend = -1.0
    else:
        trend = 0.0

    # RSI
    if rsi14 < 30:
        rsi_s = 1.0
    elif rsi14 > 70:
        rsi_s = -1.0
    else:
        rsi_s = (50 - rsi14) / 20.0

    # MACD
    if not pd.isna(phist):
        if hist > 0 and phist <= 0:
            macd_s = 1.0
        elif hist < 0 and phist >= 0:
            macd_s = -1.0
        else:
            macd_s = 0.3 if hist > 0 else -0.3
    else:
        macd_s = 0.0

    # 成交量
    vol5  = df.iloc[max(0, i-4):i+1]["volume"].mean()
    vol20 = df.iloc[max(0, i-19):i+1]["volume"].mean()
    vol_s = trend * 0.5 if vol20 > 0 and vol5 / vol20 > 1.2 else 0.0

    score = (trend * 0.4 + rsi_s * 0.25 + macd_s * 0.25 + vol_s * 0.1) * 100
    return round(score, 1), float(atr14)


# ── 回测引擎 ───────────────────────────────────────────────────────────

def run_backtest(symbol: str, name: str) -> dict:
    print(f"\n▶ {name} ({symbol}) 数据拉取中…", flush=True)
    df_raw = fetch_prices(symbol)
    df = precompute(df_raw)

    bt = df[df.index >= BACKTEST_START].copy()
    all_idx = list(df.index)

    trades = []
    position = None  # {entry_i, entry_price, stop_loss, take_profit, hold_days}

    for bt_i, date in enumerate(bt.index):
        i = all_idx.index(date)    # 在完整 df 中的位置（确保用历史数据）
        row = df.iloc[i]

        # ── 持仓检查 ──────────────────────────────────────────────────
        if position is not None:
            sl  = position["stop_loss"]
            tp  = position["take_profit"]
            ep  = position["entry_price"]
            hd  = position["hold_days"]
            sig, _ = signal_at(df, i)

            exit_price  = None
            exit_reason = None

            if row["low"] <= sl:
                exit_price  = sl
                exit_reason = "止损"
            elif row["high"] >= tp:
                exit_price  = tp
                exit_reason = "止盈"
            elif hd >= MAX_HOLD_DAYS:
                # 下一日开盘平仓
                next_bt = bt[bt.index > date]
                if len(next_bt):
                    exit_price  = next_bt.iloc[0]["open"]
                    exit_reason = "超时"
                else:
                    exit_price  = row["close"]
                    exit_reason = "到期"
            elif sig < EXIT_THRESHOLD:
                next_bt = bt[bt.index > date]
                if len(next_bt):
                    exit_price  = next_bt.iloc[0]["open"]
                    exit_reason = "信号反转"
                else:
                    exit_price  = row["close"]
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
                })
                position = None
            else:
                position["hold_days"] += 1

        # ── 开仓检查（当日已无持仓时）────────────────────────────────
        if position is None:
            sig, atr = signal_at(df, i)
            if sig > ENTRY_THRESHOLD:
                next_bt = bt[bt.index > date]
                if len(next_bt) == 0:
                    break
                next_open = next_bt.iloc[0]["open"]
                next_date = next_bt.index[0]
                risk      = atr * ATR_MULT
                sl        = next_open - risk
                tp        = next_open + risk * RR_RATIO
                position  = {
                    "entry_date":  next_date,
                    "entry_price": next_open,
                    "stop_loss":   sl,
                    "take_profit": tp,
                    "hold_days":   1,
                }

    # 强制平仓（回测结束时还持仓）
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
        })

    # ── 基准（买入持有）收益 ──────────────────────────────────────────
    bt_open  = bt.iloc[0]["open"]
    bt_close = bt.iloc[-1]["close"]
    bah = round((bt_close - bt_open) / bt_open * 100, 2)

    return {
        "symbol": symbol,
        "name":   name,
        "trades": trades,
        "bah":    bah,            # buy-and-hold %
        "bt_open":  bt_open,
        "bt_close": bt_close,
    }


# ── 绩效指标 ───────────────────────────────────────────────────────────

def metrics(result: dict) -> dict:
    trades = result["trades"]
    if not trades:
        return {"n_trades": 0}

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    n    = len(pnls)

    # 复利总收益
    total_return = 1.0
    for p in pnls:
        total_return *= (1 + p / 100)
    total_return = (total_return - 1) * 100

    # 最大回撤（基于逐笔累计净值）
    cumulative = [1.0]
    for p in pnls:
        cumulative.append(cumulative[-1] * (1 + p / 100))
    peak = cumulative[0]
    max_dd = 0.0
    for v in cumulative:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # 夏普（简化：无风险利率取3%年化）
    rf_per_trade = 3.0 / 252 * np.mean([t["hold_days"] for t in trades])
    excess = [p - rf_per_trade for p in pnls]
    sharpe = (np.mean(excess) / np.std(excess) * np.sqrt(252 / np.mean([t["hold_days"] for t in trades]))
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
        "avg_hold":     round(np.mean([t["hold_days"] for t in trades]), 1),
    }


# ── 报告输出 ───────────────────────────────────────────────────────────

def print_report(result: dict, m: dict) -> None:
    sym  = result["symbol"].replace("sh", "").replace("sz", "")
    name = result["name"]
    bah  = result["bah"]

    print(f"\n{'='*62}")
    print(f"  {name} ({sym})  回测期：{BACKTEST_START} ~ {BACKTEST_END}")
    print(f"{'='*62}")

    if m.get("n_trades", 0) == 0:
        print("  ⚠ 回测期内无触发交易")
        print(f"  买入持有收益：{bah:+.2f}%")
        return

    print(f"  买入持有基准：{bah:+.2f}%")
    print(f"  策略总收益　：{m['total_return']:+.2f}%   {'↑超额' if m['total_return'] > bah else '↓跑输'} {abs(m['total_return']-bah):.2f}%")
    print(f"  胜率　　　　：{m['win_rate']}%  ({m['n_trades']} 笔交易)")
    print(f"  单笔均值　　：{m['avg_pnl']:+.2f}%  (最佳 {m['best_trade']:+.2f}% / 最差 {m['worst_trade']:+.2f}%)")
    print(f"  最大回撤　　：{m['max_dd']:.2f}%")
    print(f"  夏普比率　　：{m['sharpe']:.2f}")
    print(f"  平均持仓天数：{m['avg_hold']} 天")
    print()
    print(f"  {'入场日期':<12} {'出场日期':<12} {'入场价':>8} {'出场价':>8} {'收益':>8}  原因")
    print(f"  {'-'*60}")
    for t in result["trades"]:
        flag = "✅" if t["pnl_pct"] > 0 else "❌"
        print(f"  {t['entry_date']:<12} {t['exit_date']:<12} "
              f"{t['entry_price']:>8.2f} {t['exit_price']:>8.2f} "
              f"{t['pnl_pct']:>+7.2f}%  {flag} {t['exit_reason']}")


# ── 汇总 ───────────────────────────────────────────────────────────────

def print_summary(all_results: list) -> None:
    print(f"\n{'='*62}")
    print(f"  汇总对比  {'股票':<10} {'策略':>9} {'买持':>9} {'超额':>9} {'胜率':>7} {'最大回撤':>9}")
    print(f"  {'-'*58}")
    for r, m in all_results:
        code = r["symbol"].replace("sh","").replace("sz","")
        label = f"{r['name']}({code})"
        if m.get("n_trades", 0) == 0:
            print(f"  {label:<14} {'—':>9} {r['bah']:>+8.2f}%  {'无交易':>9}")
            continue
        alpha = m["total_return"] - r["bah"]
        print(f"  {label:<14} {m['total_return']:>+8.2f}% {r['bah']:>+8.2f}% "
              f"{alpha:>+8.2f}% {m['win_rate']:>6.1f}% {m['max_dd']:>8.2f}%")
    print()


# ── 入口 ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\nStockSage 历史回测  {BACKTEST_START} ~ {BACKTEST_END}")
    print(f"策略：技术信号（ATR×{ATR_MULT}止损，1:{RR_RATIO}风险收益）")
    print(f"入场阈值：≥{ENTRY_THRESHOLD}  出场阈值：≤{EXIT_THRESHOLD}  最长持仓：{MAX_HOLD_DAYS}天")

    all_results = []
    for symbol, name in TEST_STOCKS:
        try:
            result = run_backtest(symbol, name)
            m = metrics(result)
            print_report(result, m)
            all_results.append((result, m))
        except Exception as e:
            print(f"\n{name} ({symbol}) 失败：{e}")

    if all_results:
        print_summary(all_results)
