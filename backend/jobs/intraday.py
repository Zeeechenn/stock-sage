"""Intraday scheduler job implementations."""
import logging

logger = logging.getLogger(__name__)


def run_stoploss_check() -> None:
    """
    盘中止损预警（每天 14:30 运行）：
    取最近一次正向信号，比对当日最新价是否触及止损线，
    触及则发送 Bark 推送。
    """
    from backend.data.database import Price, SessionLocal, Signal, Stock
    from backend.decision.market_policy import is_production_signal_eligible_stock
    from backend.decision.signal_policy import entry_recommendations
    from backend.notification.bark import send_stoploss_alert

    db = SessionLocal()
    try:
        stocks = [
            stock
            for stock in db.query(Stock).filter(Stock.active).all()
            if is_production_signal_eligible_stock(stock)
        ]
        for stock in stocks:
            try:
                sig = (
                    db.query(Signal)
                    .filter(
                        Signal.symbol == stock.symbol,
                        Signal.recommendation.in_(entry_recommendations(include_legacy=True)),
                        Signal.stop_loss.isnot(None),
                    )
                    .order_by(Signal.date.desc())
                    .first()
                )
                if not sig:
                    continue

                latest_price = (
                    db.query(Price.close)
                    .filter(Price.symbol == stock.symbol)
                    .order_by(Price.date.desc())
                    .first()
                )
                if not latest_price:
                    continue

                current = float(latest_price[0])
                if sig.stop_loss is not None and current <= sig.stop_loss:
                    logger.warning("止损触发: %s 当前%.2f ≤ 止损%.2f (信号%s)",
                                   stock.symbol, current, sig.stop_loss, sig.date)
                    send_stoploss_alert(
                        symbol=stock.symbol,
                        name=stock.name,
                        current_price=current,
                        stop_loss=sig.stop_loss,
                        signal_date=sig.date,
                    )
            except Exception as e:
                logger.error("stoploss check failed %s: %s", stock.symbol, e)
    finally:
        db.close()
