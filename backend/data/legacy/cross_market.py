"""
跨市场数据获取（国际期货 + 美股ETF）
用于有色金属、黄金板块的跨市场信号。

数据来源：yfinance（美股收盘数据）
时差利用：美股收盘(北京时间次日4-5点) → A股开盘(9:30)
→ 前日美股走势可作为当日A股有色金属的领先指标。

相关性实测（2024年数据，1日滞后）：
  紫金矿业 ← 铜矿ETF COPX  r=0.41
  紫金矿业 ← 铜ETF  CPER   r=0.42
  紫金矿业 ← 黄金ETF GLD   r=0.26
  紫金矿业 ← 美元指数(反)  r=-0.16

注：DX-Y.NYB 已失效（Yahoo Finance 下架），改用 UUP（Invesco DB 美元多头ETF）。
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import pandas as pd

logger = logging.getLogger(__name__)

# 缓存路径（每日更新一次）
_CACHE_PATH = Path.home() / ".stock-sage" / "cache" / "cross_market.pkl"

# 各板块使用的国际指标
# UUP = Invesco DB 美元多头ETF，替代已下架的 DX-Y.NYB，负权重含义相同（弱美元利好大宗）
SECTOR_SIGNALS = {
    "有色金属": {
        "COPX":  ("铜矿ETF",   0.40),   # Global X Copper Miners ETF
        "GLD":   ("黄金ETF",   0.30),
        "CPER":  ("铜ETF",     0.20),
        "UUP":   ("美元ETF",  -0.10),
    },
    "黄金矿业": {
        "GLD":   ("黄金ETF",   0.50),
        "GOLD":  ("Barrick",   0.30),
        "UUP":   ("美元ETF",  -0.20),
    },
    "能源矿业": {
        "GLD":   ("黄金ETF",   0.20),
        "COPX":  ("铜矿ETF",   0.20),
        "XLE":   ("能源ETF",   0.40),
        "UUP":   ("美元ETF",  -0.20),
    },
}

# 各股票对应板块
STOCK_SECTOR = {
    "601899": "有色金属",   # 紫金矿业（金铜矿业）
    "603799": "有色金属",   # 华友钴业
    "600547": "黄金矿业",   # 山东黄金
    "601088": "能源矿业",   # 中国神华
    "000878": "有色金属",   # 云南铜业
}


def _fetch_latest(symbols: list[str], days: int = 10) -> pd.DataFrame:
    """批量获取最近 N 个交易日的收盘价。

    先批量下载，对批量中丢失的 symbol 逐个重试（yfinance 批量下载偶发丢失
    COPX 等 ETF，但单独用 period 下载时稳定）。
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.warning("yfinance 未安装，跨市场信号不可用")
        return pd.DataFrame()

    def _single(sym: str) -> pd.Series | None:
        try:
            df = yf.download(sym, period="3mo", progress=False, auto_adjust=True)
            if df.empty:
                return None
            s = df["Close"].squeeze()
            s.index = pd.to_datetime(s.index).tz_localize(None)
            return s.dropna()
        except Exception as e:
            logger.debug("yfinance %s 单独下载失败: %s", sym, e)
            return None

    collected: dict[str, pd.Series] = {}
    try:
        raw = yf.download(" ".join(symbols), period="3mo", progress=False, auto_adjust=True)
        if not raw.empty:
            close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            close.index = pd.to_datetime(close.index).tz_localize(None)
            for sym in symbols:
                if sym in close.columns and not close[sym].dropna().empty:
                    collected[sym] = close[sym].dropna()
    except Exception as e:
        logger.debug("批量下载失败: %s", e)

    # 对批量中未返回的 symbol 逐个重试
    for sym in symbols:
        if sym not in collected:
            logger.debug("批量缺失 %s，单独重试", sym)
            s = _single(sym)
            if s is not None and not s.empty:
                collected[sym] = s

    if not collected:
        return pd.DataFrame()

    df_out = pd.DataFrame(collected)
    return df_out.tail(days + 5)


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            with open(_CACHE_PATH, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return {}


def _save_cache(data: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_PATH, "wb") as f:
        pickle.dump(data, f)


def get_cross_market_score(symbol: str, date: str | None = None) -> dict:
    """
    根据前日（date-1个美国交易日）的国际市场数据计算跨市场信号。

    Args:
        symbol: 6位A股代码（如 "601899"）
        date:   目标日期 YYYY-MM-DD（默认今天）

    Returns:
        {
            "score":      float,   # -100 ~ +100
            "available":  bool,
            "components": {sym: (name, ret, weight, contrib), ...},
        }
    """
    sector = STOCK_SECTOR.get(symbol)
    if sector is None:
        return {"score": 0.0, "available": False, "components": {}}

    weights = SECTOR_SIGNALS[sector]
    all_syms = list(weights.keys())

    # 检查缓存（当天只取一次）
    today = (datetime.today()).strftime("%Y-%m-%d")
    cache = _load_cache()
    if cache.get("date") == today and all(sym in cache.get("data", {}) for sym in all_syms):
        prices_df = pd.DataFrame(cache["data"])
    else:
        prices_df = _fetch_latest(all_syms, days=10)
        if not prices_df.empty:
            _save_cache({"date": today, "data": {col: prices_df[col] for col in prices_df.columns}})

    if prices_df.empty or len(prices_df) < 2:
        return {"score": 0.0, "available": False, "components": {}}

    # 前一日收益率（相对于前前日）
    ret = prices_df.pct_change().iloc[-1]

    components = {}
    composite = 0.0
    for sym, (name, weight) in weights.items():
        if sym not in ret or pd.isna(ret[sym]):
            continue
        r = float(ret[sym])
        contrib = r * weight * 2000   # ±2.5% → ±50分
        composite += contrib
        components[sym] = {"name": name, "return_pct": round(r * 100, 3),
                            "weight": weight, "contrib": round(contrib, 2)}

    score = round(max(-100, min(100, composite)), 1)
    return {"score": score, "available": True, "components": components}


def fetch_historical(symbols: list[str], start: str, end: str) -> pd.DataFrame:
    """回测用：批量获取历史数据"""
    try:
        import yfinance as yf
        dfs = {}
        for sym in symbols:
            try:
                df = yf.download(sym, start=start, end=end,
                                 progress=False, auto_adjust=True)
                if len(df) > 0:
                    s = df["Close"].squeeze()
                    s.index = pd.to_datetime(s.index).tz_localize(None)
                    dfs[sym] = s
            except Exception as e:
                logger.debug("yfinance %s failed: %s", sym, e)
        return pd.DataFrame(dfs)
    except ImportError:
        return pd.DataFrame()
