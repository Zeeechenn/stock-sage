"""M9.0 死代码接电：should_remember 把关 + audit_write 全链路埋点。"""
from __future__ import annotations

from sqlalchemy import text


def _count_audit(db, event_type: str, *, like: str | None = None) -> int:
    """Count audit_log_fts rows matching event_type and optional content substring."""
    from backend.memory.audit_log import _ensure_schema
    _ensure_schema(db)
    sql = "SELECT count(*) FROM audit_log_fts WHERE event_type = :et"
    params: dict = {"et": event_type}
    if like is not None:
        sql += " AND content LIKE :like"
        params["like"] = f"%{like}%"
    return db.execute(text(sql), params).scalar() or 0


def test_remember_audits_on_success(test_db):
    from backend.memory.ai_memory import remember

    result = remember(test_db, "position:300308", "已买入 5%", category="position", scope="test1")

    assert result is True
    assert _count_audit(test_db, "memory.write", like="position:300308") == 1


def test_remember_skipped_when_should_remember_rejects(test_db):
    from backend.memory.ai_memory import recall, remember

    result = remember(test_db, "noise", "今天查一下新闻")

    assert result is False
    assert recall(test_db, "noise") is None
    assert _count_audit(test_db, "memory.skipped", like="noise") == 1


def test_remember_force_bypasses_should_remember(test_db):
    from backend.memory.ai_memory import recall, remember

    result = remember(test_db, "raw", "今天查一下新闻", force=True)

    assert result is True
    assert recall(test_db, "raw") == "今天查一下新闻"
    assert _count_audit(test_db, "memory.write", like="raw") == 1


def test_recall_audits_on_hit_only(test_db):
    from backend.memory.ai_memory import recall, remember

    remember(test_db, "rule", "测试1规则", category="rule", scope="test1")

    assert recall(test_db, "rule", scope="test1") == "测试1规则"
    assert recall(test_db, "missing", scope="test1") is None

    assert _count_audit(test_db, "memory.recall", like="rule") == 1
    assert _count_audit(test_db, "memory.recall", like="missing") == 0


def test_forget_audits_always(test_db):
    from backend.memory.ai_memory import forget, remember

    remember(test_db, "rule", "测试1规则", category="rule", scope="test1")

    assert forget(test_db, "rule", scope="test1") is True
    assert forget(test_db, "rule", scope="test1") is False

    assert _count_audit(test_db, "memory.forget", like="rule") == 2


def test_remember_deep_research_persists_via_extended_whitelist(test_db):
    from backend.memory.ai_memory import recall
    from backend.memory.research_memory import remember_deep_research

    remember_deep_research(
        test_db,
        topic="AI算力产业链",
        summary="算力链条龙头表现",
        symbols=["300308"],
        report_path="docs/research/2026-05-19-ai.md",
    )

    stored = recall(test_db, "deep_research:AI算力产业链", scope="research")
    assert stored is not None
    assert "AI算力产业链" in stored
    assert _count_audit(test_db, "memory.write", like="deep_research:AI算力产业链") == 1


def test_save_decision_layered_audits_when_db_provided(test_db, tmp_path, monkeypatch):
    from backend.decision import memory_layered

    monkeypatch.setattr(memory_layered, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_layered, "LONG_TERM_PATH", tmp_path / "long_term_reflection.md")

    signal = {
        "recommendation": "买入",
        "composite_score": 12,
        "position_pct": 0.05,
        "stop_loss": 9.5,
        "take_profit": 11.0,
        "risk_notes": [],
    }
    memory_layered.save_decision_layered("300308", "2026-05-19", signal, db=test_db)

    assert _count_audit(test_db, "decision_memory.save", like="300308") == 1


def test_save_decision_layered_no_audit_when_db_omitted(test_db, tmp_path, monkeypatch):
    from backend.decision import memory_layered

    monkeypatch.setattr(memory_layered, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_layered, "LONG_TERM_PATH", tmp_path / "long_term_reflection.md")

    signal = {
        "recommendation": "买入",
        "composite_score": 12,
        "position_pct": 0.05,
        "stop_loss": 9.5,
        "take_profit": 11.0,
        "risk_notes": [],
    }
    memory_layered.save_decision_layered("300308", "2026-05-19", signal)

    assert _count_audit(test_db, "decision_memory.save") == 0


def test_get_layered_context_audits_when_nonempty(test_db, tmp_path, monkeypatch):
    from backend.decision import memory_layered

    monkeypatch.setattr(memory_layered, "MEMORY_DIR", tmp_path)
    monkeypatch.setattr(memory_layered, "LONG_TERM_PATH", tmp_path / "long_term_reflection.md")
    memory_layered._SHORT_TERM.clear()

    signal = {
        "recommendation": "买入",
        "composite_score": 12,
        "position_pct": 0.05,
        "stop_loss": 9.5,
        "take_profit": 11.0,
        "risk_notes": [],
    }
    memory_layered.save_decision_layered("300308", "2026-05-19", signal, db=test_db)

    ctx = memory_layered.get_layered_context("300308", test_db)
    assert ctx  # 至少有短期或中期文本
    assert _count_audit(test_db, "decision_memory.recall", like="300308") >= 1
