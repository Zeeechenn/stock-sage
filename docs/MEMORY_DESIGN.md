# 记忆系统设计

## Layer 1：项目事实源
`PROJECT.md`、`PAPER_TRADING.md`、`stock-sage.db` 和 `backend/config.py` 是每次决策前的基础事实源。

## Layer 2：AI Memory
`ai_memory` 表保存可主动召回的长期规则、持仓、风险、偏好和决策上下文。接口位于 `backend/memory/ai_memory.py`。

## Layer 3：Audit Log
`audit_log_fts` 使用 SQLite FTS5 保存可检索审计事件。接口位于 `backend/memory/audit_log.py`。

## Layer 4：Remember Decision
`backend/memory/should_remember.py` 用轻量启发式判断一段信息是否值得写入长期记忆。
