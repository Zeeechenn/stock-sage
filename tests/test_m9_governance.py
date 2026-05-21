"""M9.3 治理：窗口摘要器 + 过期清理 + 深度研究召回压缩。"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import text

# ── 1) Window summarizer ─────────────────────────────────────────────────

class _StubProvider:
    """LLM provider stub: returns the summary text it was constructed with."""
    def __init__(self, summary: str):
        self.summary = summary
        self.calls = 0

    def complete_structured(self, prompt: str, tool: dict, **kwargs) -> dict:
        self.calls += 1
        self.last_prompt = prompt
        return {"summary": self.summary}


def _make_session(test_db, sid: str = "sess1") -> None:
    test_db.execute(text(
        "INSERT INTO chat_sessions(id, mode, created_at, updated_at) "
        "VALUES(:id, 'general', :now, :now)"
    ), {"id": sid, "now": datetime.utcnow().isoformat(timespec="seconds")})
    test_db.commit()


def _add_messages(test_db, sid: str, n: int, *, prefix: str = "msg") -> None:
    rows = [
        {"sid": sid, "role": "user" if i % 2 == 0 else "assistant",
         "content": f"{prefix} {i}", "now": datetime.utcnow().isoformat(timespec="seconds")}
        for i in range(n)
    ]
    test_db.execute(text(
        "INSERT INTO chat_messages(session_id, role, content, created_at) "
        "VALUES(:sid, :role, :content, :now)"
    ), rows)
    test_db.commit()


def test_summarizer_below_threshold_is_noop(test_db):
    from backend.memory.summarizer import summarize_if_needed

    _make_session(test_db)
    _add_messages(test_db, "sess1", 10)
    stub = _StubProvider("should not be used")
    assert summarize_if_needed(test_db, "sess1", threshold=50, provider=stub) is False
    assert stub.calls == 0


def test_summarizer_compresses_at_threshold(test_db):
    from backend.memory.summarizer import summarize_if_needed

    _make_session(test_db)
    _add_messages(test_db, "sess1", 60)
    stub = _StubProvider("用户偏好稳健仓位；规则：不碰高负债公司。")
    assert summarize_if_needed(test_db, "sess1", threshold=50, keep_recent=10, provider=stub) is True
    assert stub.calls == 1

    row = test_db.execute(text(
        "SELECT summary, summary_until_id FROM chat_sessions WHERE id='sess1'"
    )).first()
    assert "稳健仓位" in row.summary
    # 50 / 60 messages compressed (id 1..50); tail 10 kept
    assert row.summary_until_id == 50


def test_summarizer_writes_audit(test_db):
    from backend.memory.summarizer import summarize_if_needed

    _make_session(test_db)
    _add_messages(test_db, "sess1", 60)
    stub = _StubProvider("摘要 v1")
    summarize_if_needed(test_db, "sess1", threshold=50, provider=stub)

    count = test_db.execute(text(
        "SELECT count(*) FROM audit_log_fts WHERE event_type = 'chat.summary'"
    )).scalar()
    assert count == 1


def test_summarizer_resumes_after_prior(test_db):
    """Re-running after more messages compresses only new ones beyond prior_until."""
    from backend.memory.summarizer import summarize_if_needed

    _make_session(test_db)
    _add_messages(test_db, "sess1", 60, prefix="first")
    summarize_if_needed(test_db, "sess1", threshold=50, keep_recent=10,
                        provider=_StubProvider("first pass"))

    _add_messages(test_db, "sess1", 40, prefix="second")  # total 100
    stub = _StubProvider("second pass")
    summarize_if_needed(test_db, "sess1", threshold=50, keep_recent=10, provider=stub)

    # Prompt should include prior_summary preamble
    assert "first pass" in stub.last_prompt
    # Should NOT contain any "first" prefix messages (already compressed)
    assert "first 0" not in stub.last_prompt


def test_summarizer_skips_when_provider_returns_empty(test_db):
    from backend.memory.summarizer import summarize_if_needed

    _make_session(test_db)
    _add_messages(test_db, "sess1", 60)
    stub = _StubProvider("")  # empty summary
    assert summarize_if_needed(test_db, "sess1", threshold=50, provider=stub) is False
    row = test_db.execute(text(
        "SELECT summary FROM chat_sessions WHERE id='sess1'"
    )).first()
    assert row.summary is None


# ── 2) Expire stale memories ─────────────────────────────────────────────

def test_expire_removes_stale_and_audits(test_db):
    from backend.memory.ai_memory import expire_stale_memories, remember

    remember(test_db, "fresh:1", "新风险", category="risk", ttl_days=7)
    remember(test_db, "stale:1", "过期风险", category="risk", ttl_days=1)
    old = (datetime.utcnow() - timedelta(days=2)).isoformat(timespec="seconds")
    test_db.execute(text(
        "UPDATE ai_memory SET updated_at = :old WHERE key='stale:1'"
    ), {"old": old})
    test_db.commit()

    removed = expire_stale_memories(test_db)
    assert removed == 1

    remaining = test_db.execute(text(
        "SELECT key FROM ai_memory ORDER BY key"
    )).all()
    assert [r.key for r in remaining] == ["fresh:1"]

    audit_count = test_db.execute(text(
        "SELECT count(*) FROM audit_log_fts WHERE event_type = 'memory.expire'"
    )).scalar()
    assert audit_count == 1


def test_expire_skips_pinned_and_fresh(test_db):
    """Rows with ttl_days=NULL (pinned) and rows still within TTL are kept."""
    from backend.memory.ai_memory import expire_stale_memories, remember

    remember(test_db, "pin:1", "永久规则", category="rule")  # ttl_days=None
    remember(test_db, "fresh:1", "新风险", category="risk", ttl_days=7)

    removed = expire_stale_memories(test_db)
    assert removed == 0


def test_expire_preserves_value_in_audit_for_recovery(test_db):
    """The deleted value is captured in audit content for forensic recovery."""
    from backend.memory.ai_memory import expire_stale_memories, remember

    remember(test_db, "stale:1", "重要的风险记忆 X23 文本", category="risk", ttl_days=1)
    old = (datetime.utcnow() - timedelta(days=2)).isoformat(timespec="seconds")
    test_db.execute(text(
        "UPDATE ai_memory SET updated_at = :old WHERE key='stale:1'"
    ), {"old": old})
    test_db.commit()

    expire_stale_memories(test_db)
    content = test_db.execute(text(
        "SELECT content FROM audit_log_fts WHERE event_type='memory.expire' LIMIT 1"
    )).scalar()
    assert "重要的风险记忆 X23 文本" in content


# ── 3) Deep research recall is already compressed (pointer-only) ──────────

def test_deep_research_recall_returns_pointer_not_full_report(test_db, tmp_path):
    """research_memory only stores indexed JSON {topic, summary, symbols, report_path}.
    Recall must NOT include any raw report markdown body."""
    import json

    from backend.memory.ai_memory import recall
    from backend.memory.research_memory import remember_deep_research

    report = tmp_path / "deep.md"
    report.write_text(
        "# 深度研究报告\n\n这里是非常长的原始内容 " + ("x" * 5000),
        encoding="utf-8",
    )
    remember_deep_research(
        test_db,
        topic="AI算力产业链",
        summary="≤200字摘要",
        symbols=["300308"],
        report_path=str(report),
    )

    stored = recall(test_db, "deep_research:AI算力产业链", scope="research")
    assert stored is not None
    payload = json.loads(stored)
    assert payload["report_path"] == str(report)
    assert payload["summary"] == "≤200字摘要"
    assert "x" * 100 not in stored  # raw body must not be in the recall payload
