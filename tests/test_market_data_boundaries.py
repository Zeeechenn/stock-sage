from datetime import date, timedelta

import pandas as pd


def test_market_facade_keeps_public_entrypoints():
    from backend.data import market

    public_names = [
        "register_default_market_providers",
        "fetch_daily",
        "fetch_cn_index",
        "load_price_df",
        "sync_index_to_db",
        "backfill_if_needed",
        "fetch_cn_daily",
        "fetch_cn_daily_akshare_em",
        "fetch_cn_daily_akshare_sina",
        "fetch_cn_daily_tushare",
        "fetch_cn_daily_tickflow",
        "fetch_cn_daily_tushare_qfq",
        "fetch_cn_daily_yfinance",
        "fetch_hk_daily",
        "fetch_us_daily",
        "fetch_cn_index_akshare",
        "fetch_cn_index_eastmoney",
        "fetch_cn_index_efinance",
        "fetch_cn_index_yfinance",
        "_normalize_ohlcv",
        "_utcnow_naive",
    ]

    for name in public_names:
        assert callable(getattr(market, name))

    assert market.DAILY_PROVIDER_ADJUSTMENTS["eastmoney_cn"] == "qfq"
    assert market.DAILY_PROVIDER_ADJUSTMENTS["yfinance_hk"] == "auto_adjust"
    assert "yfinance_cn" not in market.DAILY_PROVIDER_ADJUSTMENTS
    assert market.INDEX_PROVIDER_ADJUSTMENTS["eastmoney_index_cn"] == "index_unadjusted"


def test_backfill_write_guard_rejects_hfq_scaled_rows(test_db, monkeypatch):
    from backend.analysis import factors
    from backend.data import market
    from backend.data.database import Price

    latest = date.today() - timedelta(days=2)
    seed_start = latest - timedelta(days=9)
    for offset in range(10):
        day = seed_start + timedelta(days=offset)
        test_db.add(
            Price(
                symbol="600519",
                date=day.isoformat(),
                open=10.0,
                high=11.0,
                low=9.5,
                close=10.0,
                volume=1_000_000,
                source="seed",
                adjustment="qfq",
            )
        )
    test_db.commit()

    contaminated_day = date.today() - timedelta(days=1)
    df = pd.DataFrame(
        [
            {
                "open": 980.0,
                "high": 1020.0,
                "low": 970.0,
                "close": 1000.0,
                "volume": 500_000,
            }
        ],
        index=[contaminated_day.isoformat()],
    )
    df.attrs["source"] = "unit_provider"
    df.attrs["fetched_at"] = market._utcnow_naive()
    df.attrs["adjustment"] = "qfq"

    monkeypatch.setattr(market, "fetch_daily", lambda *args, **kwargs: df)
    monkeypatch.setattr(factors, "add_all_factors", lambda frame: frame.assign(atr14=0.1))

    inserted = market.backfill_if_needed("600519", "CN", test_db, years=1)

    assert inserted == 0
    assert (
        test_db.query(Price)
        .filter(Price.symbol == "600519", Price.date == contaminated_day.isoformat())
        .count()
        == 0
    )
    assert test_db.query(Price).filter(Price.symbol == "600519").count() == 10
