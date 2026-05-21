from datetime import datetime, timedelta


def test_remember_recall_forget(test_db):
    from backend.memory.ai_memory import forget, recall, remember

    remember(test_db, "position:300308", "已买入 5%", category="position", scope="test1")

    assert recall(test_db, "position:300308", scope="test1") == "已买入 5%"
    assert forget(test_db, "position:300308", scope="test1") is True
    assert recall(test_db, "position:300308", scope="test1") is None


def test_ttl_expired_memory_is_hidden(test_db):
    from sqlalchemy import text

    from backend.memory.ai_memory import recall, remember

    remember(test_db, "risk", "过期风险", category="risk", ttl_days=1)
    old = (datetime.utcnow() - timedelta(days=2)).isoformat(timespec="seconds")
    test_db.execute(text("UPDATE ai_memory SET updated_at = :old"), {"old": old})
    test_db.commit()

    assert recall(test_db, "risk") is None


def test_scope_isolation_and_list_active(test_db):
    from backend.memory.ai_memory import list_active, recall, remember

    remember(test_db, "rule", "测试1规则", category="rule", scope="test1")
    remember(test_db, "rule", "测试2规则", category="rule", scope="test2")

    assert recall(test_db, "rule", scope="test1") == "测试1规则"
    assert recall(test_db, "rule", scope="test2") == "测试2规则"
    assert [m["scope"] for m in list_active(test_db, category="rule")] == ["test2", "test1"]


def test_should_remember_heuristic():
    from backend.memory.should_remember import should_remember

    positives = [
        "记住我已买入中际旭创",
        "风险预警：单股仓位过高",
        "测试规则切换到测试2",
        "remember my preference",
    ]
    negatives = [
        "今天查一下新闻",
        "临时看一下当前价格",
        "贵州茅台是什么",
        "帮我算一下收益",
    ]

    assert all(should_remember(t) for t in positives)
    assert not any(should_remember(t) for t in negatives)
