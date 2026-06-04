"""行情数据拉取 facade：保留 market.py public imports，拆分实现到 market_* 模块。"""
import logging

import pandas as pd

from backend.config import settings
from backend.data.market_persistence import (
    BACKFILL_THRESHOLD_DAYS,
    BACKFILL_YEARS,
    REFRESH_WINDOW_DAYS,
    load_price_df,
)
from backend.data.market_persistence import backfill_if_needed as _backfill_if_needed
from backend.data.market_persistence import sync_index_to_db as _sync_index_to_db
from backend.data.market_sources import (
    ak,
    fetch_cn_daily,
    fetch_cn_daily_akshare_em,
    fetch_cn_daily_akshare_sina,
    fetch_cn_daily_akshare_tx,
    fetch_cn_daily_efinance,
    fetch_cn_daily_tickflow,
    fetch_cn_daily_tushare,
    fetch_cn_daily_tushare_qfq,
    fetch_cn_daily_yfinance,
    fetch_cn_index_akshare,
    fetch_cn_index_eastmoney,
    fetch_cn_index_efinance,
    fetch_cn_index_yfinance,
    fetch_hk_daily,
    fetch_us_daily,
    yf,
)
from backend.data.market_utils import (
    DAILY_PROVIDER_ADJUSTMENTS,
    INDEX_PROVIDER_ADJUSTMENTS,
    _attach_provenance_attrs,
    _cn_market_prefix,
    _efinance_available,
    _normalize_ohlcv,
    _retry,
    _to_sina_tx_symbol,
    _utcnow_naive,
    cn_tushare_ts_code,
    cn_yfinance_ticker,
    hk_yfinance_ticker,
)
from backend.data.providers import (
    fetch_daily_with_fallback,
    fetch_index_with_fallback,
    register_daily_provider,
    register_index_provider,
)

logger = logging.getLogger(__name__)


def register_default_market_providers() -> None:
    """Register default daily/index providers without fetching remote data."""
    if settings.tickflow_enabled and settings.tickflow_api_key:
        register_daily_provider("tickflow_cn", {"CN"}, fetch_cn_daily_tickflow, priority=-10, cooldown_seconds=30)
    register_daily_provider("akshare_sina_cn", {"CN"}, fetch_cn_daily_akshare_sina, priority=0, cooldown_seconds=30)
    if _efinance_available():
        register_daily_provider("efinance_cn", {"CN"}, fetch_cn_daily_efinance, priority=10, cooldown_seconds=60)
    register_daily_provider("eastmoney_cn", {"CN"}, fetch_cn_daily, priority=20, cooldown_seconds=60)
    register_daily_provider("akshare_em_cn", {"CN"}, fetch_cn_daily_akshare_em, priority=30, cooldown_seconds=60)
    if settings.tushare_qfq_enabled and settings.tushare_token:
        register_daily_provider("tushare_qfq_cn", {"CN"}, fetch_cn_daily_tushare_qfq, priority=50, cooldown_seconds=120)
    # M19.2: yfinance 对 A 股是后复权含分红再投，与其余源 qfq 口径冲突，不进入 CN fallback。
    # akshare_tx 当前返回结构缺 volume，暂不进入 CN 生产 fallback；保留函数供手动调试。
    register_daily_provider("yfinance_hk", {"HK"}, fetch_hk_daily, priority=90, cooldown_seconds=120)
    register_daily_provider("yfinance_us", {"US"}, fetch_us_daily, priority=90, cooldown_seconds=120)

    register_index_provider("akshare_index_cn", fetch_cn_index_akshare, priority=0, cooldown_seconds=60)
    register_index_provider("eastmoney_index_cn", fetch_cn_index_eastmoney, priority=10, cooldown_seconds=60)
    if _efinance_available():
        register_index_provider("efinance_index_cn", fetch_cn_index_efinance, priority=20, cooldown_seconds=60)
    register_index_provider("yfinance_index_cn", fetch_cn_index_yfinance, priority=90, cooldown_seconds=120)


def fetch_daily(symbol: str, market: str, days: int = 365) -> pd.DataFrame:
    """Dispatch to the appropriate market data fetcher based on market."""
    register_default_market_providers()
    df, provider = fetch_daily_with_fallback(symbol, market, days)
    _attach_provenance_attrs(
        df,
        provider=provider,
        adjustment=DAILY_PROVIDER_ADJUSTMENTS.get(provider),
    )
    logger.debug("fetch_daily provider=%s symbol=%s market=%s rows=%d",
                 provider, symbol, market, len(df))
    return df


def fetch_cn_index(index_symbol: str = "sh000300", days: int = 365) -> pd.DataFrame:
    """
    拉取A股指数日线数据，默认沪深300。
    index_symbol: "sh000300"（沪深300）/ "sh000001"（上证）/ "sh000016"（上证50）
    """
    register_default_market_providers()
    df, provider = fetch_index_with_fallback(index_symbol, days)
    _attach_provenance_attrs(
        df,
        provider=provider,
        adjustment=INDEX_PROVIDER_ADJUSTMENTS.get(provider),
    )
    logger.debug("fetch_cn_index provider=%s index=%s rows=%d", provider, index_symbol, len(df))
    return df


def sync_index_to_db(db, index_symbol: str = "sh000300", days: int = 365) -> int:
    return _sync_index_to_db(
        db,
        index_symbol=index_symbol,
        days=days,
        fetch_cn_index_fn=fetch_cn_index,
    )


def backfill_if_needed(symbol: str, market: str, db, years: int | None = None,
                       refresh_today: bool = False) -> int:
    return _backfill_if_needed(
        symbol,
        market,
        db,
        years=years,
        refresh_today=refresh_today,
        fetch_daily_fn=fetch_daily,
        backfill_years=BACKFILL_YEARS,
        backfill_threshold_days=BACKFILL_THRESHOLD_DAYS,
        refresh_window_days=REFRESH_WINDOW_DAYS,
    )


__all__ = [
    "BACKFILL_THRESHOLD_DAYS",
    "BACKFILL_YEARS",
    "DAILY_PROVIDER_ADJUSTMENTS",
    "INDEX_PROVIDER_ADJUSTMENTS",
    "REFRESH_WINDOW_DAYS",
    "_attach_provenance_attrs",
    "_cn_market_prefix",
    "_efinance_available",
    "_normalize_ohlcv",
    "_retry",
    "_to_sina_tx_symbol",
    "_utcnow_naive",
    "ak",
    "backfill_if_needed",
    "cn_tushare_ts_code",
    "cn_yfinance_ticker",
    "fetch_cn_daily",
    "fetch_cn_daily_akshare_em",
    "fetch_cn_daily_akshare_sina",
    "fetch_cn_daily_akshare_tx",
    "fetch_cn_daily_efinance",
    "fetch_cn_daily_tickflow",
    "fetch_cn_daily_tushare",
    "fetch_cn_daily_tushare_qfq",
    "fetch_cn_daily_yfinance",
    "fetch_cn_index",
    "fetch_cn_index_akshare",
    "fetch_cn_index_eastmoney",
    "fetch_cn_index_efinance",
    "fetch_cn_index_yfinance",
    "fetch_daily",
    "fetch_daily_with_fallback",
    "fetch_hk_daily",
    "fetch_index_with_fallback",
    "fetch_us_daily",
    "hk_yfinance_ticker",
    "load_price_df",
    "register_daily_provider",
    "register_default_market_providers",
    "register_index_provider",
    "settings",
    "sync_index_to_db",
    "yf",
]
