"""M9.4 ChatPage 接入：用户说"记住 X" → memory.write 候选 → 二次确认。"""
from __future__ import annotations

from sqlalchemy import text


def test_detect_action_extracts_memory_write_from_phrase(test_db):
    """`记住 X` is detected as a memory.write candidate, not silently saved."""
    from backend.api.routes.ai import _detect_action

    action = _detect_action("记住 我不碰高负债公司", db=test_db)
    assert action is not None
    name, payload = action
    assert name == "memory.write"
    assert "高负债" in payload["value"]
    assert payload["scope"] == "global"
    assert payload["category"] in {"preference", "rule", "risk"}
    assert payload["key"].startswith("chat:")


def test_detect_action_routes_rule_keyword(test_db):
    from backend.api.routes.ai import _detect_action

    action = _detect_action("记住 测试2 的规则切换条件", db=test_db)
    assert action is not None
    _, payload = action
    assert payload["category"] == "rule"


def test_detect_action_routes_risk_keyword(test_db):
    from backend.api.routes.ai import _detect_action

    action = _detect_action("记住 这是一个重要的风险预警", db=test_db)
    assert action is not None
    _, payload = action
    assert payload["category"] == "risk"


def test_detect_action_returns_none_for_unrelated_message(test_db):
    """Plain queries do not produce a memory.write candidate."""
    from backend.api.routes.ai import _detect_action

    assert _detect_action("贵州茅台现在怎么样", db=test_db) is None
    assert _detect_action("帮我看一下 300308", db=test_db) is None


def test_memory_write_does_not_persist_until_confirmation(test_db):
    """The detect step must not write directly — only the confirm path writes."""
    from backend.api.routes.ai import _detect_action, _pending
    from backend.memory.ai_memory import recall

    action = _detect_action("记住 用户偏好稳健仓位", db=test_db)
    assert action is not None
    name, payload = action
    pending = _pending(name, payload, "记住 用户偏好稳健仓位", test_db)

    # 仅候选写入了 pending_ai_actions，未落 ai_memory
    assert pending["status"] == "pending"
    assert recall(test_db, payload["key"], scope="global") is None


def test_confirm_action_persists_memory_write(test_db):
    """Calling confirm_action on a memory.write pending writes to ai_memory."""
    from backend.api.routes.ai import _detect_action, _pending, confirm_action
    from backend.memory.ai_memory import recall

    action = _detect_action("记住 用户偏好稳健仓位", db=test_db)
    name, payload = action
    pending = _pending(name, payload, "记住 用户偏好稳健仓位", test_db)

    resp = confirm_action(pending["id"], db=test_db)
    assert resp["status"] == "executed"
    assert resp["result"]["persisted"] is True

    stored = recall(test_db, payload["key"], scope="global")
    assert stored == payload["value"]


def test_confirm_action_uses_force_so_should_remember_does_not_reject(test_db):
    """The user already opted-in via confirmation; should_remember must not block."""
    from backend.api.routes.ai import _execute_action
    from backend.memory.ai_memory import recall

    # 普通文本（没有 hint 关键词，不在白名单 category）默认会被 should_remember 拒。
    # 但 memory.write 用 force=True，所以应该写成功。
    payload = {
        "key": "chat:test:0001",
        "value": "今天查一下新闻",  # 这是 NEGATIVE_HINT
        "category": None,
        "scope": "global",
    }
    res = _execute_action("memory.write", payload, db=test_db)
    assert res["persisted"] is True
    assert recall(test_db, payload["key"], scope="global") == payload["value"]


def test_memory_write_audit_recorded(test_db):
    """Confirmed memory writes show up in audit_log_fts under memory.write."""
    from backend.api.routes.ai import _execute_action

    payload = {
        "key": "chat:preference:abc",
        "value": "稳健仓位",
        "category": "preference",
        "scope": "global",
    }
    _execute_action("memory.write", payload, db=test_db)

    count = test_db.execute(text(
        "SELECT count(*) FROM audit_log_fts "
        "WHERE event_type = 'memory.write' AND content LIKE :pat"
    ), {"pat": "%chat:preference:abc%"}).scalar()
    assert count == 1
