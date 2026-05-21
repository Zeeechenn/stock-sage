"""QFII Outflow 反向规避分析师单元测试 — 不依赖网络"""
from datetime import date


def _history(*quarters):
    """quarters: ("20251231", [("高盛集团", 10000), ("摩根士丹利", 5000)]) ..."""
    out = {}
    for q, rows in quarters:
        out[q] = [{"holder": h, "shares": s, "change": None} for h, s in rows]
    return out


def test_no_qfii_in_top_holders_returns_neutral():
    from backend.agents.long_term import qfii_flow_analyst

    report = qfii_flow_analyst.analyze("600519", history={"20251231": []})
    assert report.role == "flow"
    assert report.confidence == 0.0
    assert report.label_vote == "观望"
    assert report.score == 0.0


def test_steady_qfii_holdings_returns_neutral():
    from backend.agents.long_term import qfii_flow_analyst

    history = _history(
        ("20241231", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250331", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250630", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250930", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
    )
    report = qfii_flow_analyst.analyze("000001", history=history)
    assert report.confidence == 0.0
    assert report.label_vote == "观望"


def test_single_holder_dropping_does_not_trigger():
    from backend.agents.long_term import qfii_flow_analyst

    history = _history(
        ("20241231", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250331", [("高盛集团", 8000), ("摩根士丹利", 8000)]),
        ("20250630", [("高盛集团", 6000), ("摩根士丹利", 8000)]),
        ("20250930", [("高盛集团", 4000), ("摩根士丹利", 8000)]),
    )
    report = qfii_flow_analyst.analyze("000002", history=history)
    assert report.label_vote == "观望"
    assert report.raw["stats"]["distinct_holders_dropping"] == 1


def test_single_quarter_drop_does_not_trigger():
    from backend.agents.long_term import qfii_flow_analyst

    history = _history(
        ("20241231", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250331", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250630", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250930", [("高盛集团", 8000), ("摩根士丹利", 7000)]),
    )
    report = qfii_flow_analyst.analyze("000003", history=history)
    assert report.label_vote == "观望"
    assert report.raw["stats"]["max_consecutive_drop"] == 1


def test_persistent_multi_holder_drop_triggers_avoid():
    from backend.agents.long_term import qfii_flow_analyst

    history = _history(
        ("20241231", [("高盛集团", 10000), ("摩根士丹利", 8000), ("瑞士联合银行集团", 6000)]),
        ("20250331", [("高盛集团", 8000), ("摩根士丹利", 6000), ("瑞士联合银行集团", 5000)]),
        ("20250630", [("高盛集团", 5000), ("摩根士丹利", 4000), ("瑞士联合银行集团", 3000)]),
        ("20250930", [("高盛集团", 2000), ("摩根士丹利", 2000)]),
    )
    report = qfii_flow_analyst.analyze("300308", history=history)
    assert report.label_vote == "规避"
    assert report.score == -70.0
    assert report.confidence > 0.5
    findings = " ".join(report.key_findings)
    assert "外资 QFII 持续减仓" in findings


def test_full_exit_counts_as_drop():
    from backend.agents.long_term import qfii_flow_analyst

    history = _history(
        ("20241231", [("高盛集团", 10000), ("摩根士丹利", 8000)]),
        ("20250331", [("高盛集团", 8000), ("摩根士丹利", 6000)]),
        ("20250630", [("高盛集团", 5000)]),  # 摩根士丹利完全退出
        ("20250930", []),                    # 高盛也完全退出
    )
    report = qfii_flow_analyst.analyze("002241", history=history)
    assert report.label_vote == "规避"
    stats = report.raw["stats"]
    assert stats["distinct_holders_dropping"] >= 2


def test_recent_quarter_dates_picks_completed_quarters():
    from backend.data.qfii_holdings import _recent_quarter_dates

    dates = _recent_quarter_dates(4, today=date(2026, 5, 15))
    assert dates[0] == "20260331"
    assert dates == ["20260331", "20251231", "20250930", "20250630"]


def test_is_qfii_holder_matches_keywords():
    from backend.data.qfii_holdings import is_qfii_holder

    assert is_qfii_holder("高盛集团")
    assert is_qfii_holder("高盛国际")
    assert is_qfii_holder("摩根士丹利国际股份有限公司")
    assert is_qfii_holder("瑞士联合银行集团")
    assert is_qfii_holder("阿布达比投资局")
    assert not is_qfii_holder("香港中央结算有限公司")
    assert not is_qfii_holder("中国证券金融股份有限公司")
    assert not is_qfii_holder("")


def test_team_includes_flow_analyst_in_votes(monkeypatch):
    """team.LongTermTeam.run 调用了 flow analyst，最终 votes 含 'flow' 键"""
    from backend.agents.long_term import (
        a_teacher_analyst,
        jingqi_analyst,
        piotroski_analyst,
        qfii_flow_analyst,
    )
    from backend.agents.long_term import team as team_mod
    from backend.agents.long_term.base import LongTermReport

    history = _history(
        ("20241231", [("高盛集团", 10000), ("摩根士丹利", 8000), ("瑞银集团", 6000)]),
        ("20250331", [("高盛集团", 7000), ("摩根士丹利", 5000), ("瑞银集团", 4000)]),
        ("20250630", [("高盛集团", 3000), ("摩根士丹利", 2000)]),
        ("20250930", []),
    )

    monkeypatch.setattr(qfii_flow_analyst, "get_qfii_history", lambda *a, **kw: history)

    monkeypatch.setattr(a_teacher_analyst, "analyze",
                        lambda s, n, db: LongTermReport(role="track", score=40, confidence=0.7,
                                                       label_vote="观望", key_findings=[]))
    monkeypatch.setattr(piotroski_analyst, "analyze",
                        lambda s, db: LongTermReport(role="quality", score=50, confidence=0.8,
                                                     label_vote="值得持有", key_findings=[]))
    monkeypatch.setattr(jingqi_analyst, "analyze",
                        lambda s, db: LongTermReport(role="boom", score=30, confidence=0.6,
                                                     label_vote="观望", key_findings=[]))

    label = team_mod.LongTermTeam().run("600000", "测试股", db=None)
    assert "flow" in label.votes
    assert label.votes["flow"] == "规避"
    assert label.label == "规避"  # 一票否决生效
