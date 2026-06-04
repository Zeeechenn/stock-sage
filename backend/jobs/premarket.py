"""Premarket scheduler job implementation."""
import logging

logger = logging.getLogger(__name__)


def run_premarket() -> None:
    """盘前任务：同步行情 + 个股新闻 + 沪深300指数"""
    from backend.data.database import SessionLocal, Stock
    from backend.data.market import backfill_if_needed, sync_index_to_db
    from backend.data.news import fetch_stock_news_cn, save_news_to_db

    db = SessionLocal()
    try:
        stocks = db.query(Stock).filter(Stock.active).all()
        price_rows, news_rows = 0, 0

        for stock in stocks:
            # 行情回填
            try:
                price_rows += backfill_if_needed(stock.symbol, stock.market, db, refresh_today=True)
            except Exception as e:
                logger.error("backfill failed %s: %s", stock.symbol, e)

            # 个股新闻（仅A股，美股 Phase 7）
            if stock.market == "CN":
                try:
                    news = fetch_stock_news_cn(stock.symbol)
                    news_rows += save_news_to_db(news, db)
                except Exception as e:
                    logger.error("news fetch failed %s: %s", stock.symbol, e)

        try:
            sync_index_to_db(db)
        except Exception as e:
            logger.error("index sync failed: %s", e)

        logger.info("pre-market done: %d stocks, %d price rows, %d news items",
                    len(stocks), price_rows, news_rows)
    finally:
        db.close()
