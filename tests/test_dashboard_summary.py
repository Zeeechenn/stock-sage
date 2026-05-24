from datetime import datetime


def test_dashboard_summary_returns_operational_snapshot(monkeypatch, tmp_path, test_db):
    from backend.api.routes import dashboard, dashboard_summary
    from backend.data.database import Price, Signal, Stock

    monkeypatch.setattr(dashboard, "TEST2_UNIVERSE_PATH", tmp_path / "missing-test2-universe.json")

    test_db.add(Stock(symbol="300308", name="中际旭创", market="CN", industry="通信设备", active=True))
    test_db.add(Stock(symbol="603986", name="兆易创新", market="CN", industry="半导体", active=True))
    test_db.add(Price(symbol="300308", date="2026-05-15", open=100, high=110, low=99, close=108, volume=1))
    test_db.add(Price(symbol="603986", date="2026-05-15", open=100, high=104, low=96, close=102, volume=1))
    test_db.add(
        Signal(
            symbol="300308",
            date="2026-05-15",
            quant_score=-7.7,
            technical_score=22.5,
            sentiment_score=0.75,
            composite_score=28.5,
            recommendation="买入",
            confidence="中",
            stop_loss=990.15,
            take_profit=1262.49,
            rule_version="test1_legacy_qlib",
            created_at=datetime(2026, 5, 15, 16, 0),
        )
    )
    test_db.commit()

    summary = dashboard_summary(as_of="2026-05-16", db=test_db)

    assert summary["paper_trading"]["active_test"] == "test1"
    assert summary["paper_trading"]["test1"]["positions"] == 4
    assert summary["paper_trading"]["test2"]["entry_threshold"] == 25
    assert summary["paper_trading"]["test2"]["forced_exit"] is False
    assert summary["paper_trading"]["test2"]["universe_available"] is False
    assert summary["coverage"]["summary"]["active_stocks"] == 2
    assert summary["signals"]["latest_date"] == "2026-05-15"
    assert summary["signals"]["entry_count"] == 1
    assert summary["signals"]["latest"][0]["symbol"] == "300308"
    assert summary["system"]["database_ok"] is True


def test_load_test2_universe_reports_availability(monkeypatch, tmp_path):
    from backend.api.routes import dashboard

    universe_path = tmp_path / "test2_universe.json"
    universe_path.write_text('{"stocks": [{"symbol": "600519", "name": "贵州茅台"}]}', encoding="utf-8")
    monkeypatch.setattr(dashboard, "TEST2_UNIVERSE_PATH", universe_path)

    stocks, available = dashboard._load_test2_universe()

    assert available is True
    assert stocks == [{"symbol": "600519", "name": "贵州茅台"}]


def test_load_test2_universe_missing_is_expected(monkeypatch, tmp_path):
    from backend.api.routes import dashboard

    monkeypatch.setattr(dashboard, "TEST2_UNIVERSE_PATH", tmp_path / "missing.json")

    stocks, available = dashboard._load_test2_universe()

    assert available is False
    assert stocks == []
