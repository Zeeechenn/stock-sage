import pytest

from backend.data import database
from backend.data.database import Price


def test_get_latest_price_date_returns_latest_symbol_date(test_db):
    test_db.add_all([
        Price(symbol="600519", date="2026-05-20", open=1, high=1, low=1, close=1, volume=1),
        Price(symbol="600519", date="2026-05-22", open=1, high=1, low=1, close=1, volume=1),
        Price(symbol="000001", date="2026-06-01", open=1, high=1, low=1, close=1, volume=1),
    ])
    test_db.commit()

    assert database.get_latest_price_date("600519", test_db) == "2026-05-22"
    assert database.get_latest_price_date("300308", test_db) is None


def test_get_db_dependency_closes_yielded_session(monkeypatch):
    class FakeSession:
        closed = False

        def close(self):
            self.closed = True

    session = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    dependency = database.get_db()

    assert next(dependency) is session
    with pytest.raises(StopIteration):
        next(dependency)
    assert session.closed is True
