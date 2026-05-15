# StockSage 架构

## 数据流
AkShare/补充新闻源写入 SQLite，盘后任务读取价格、新闻、长期标签，生成技术、情感和量化输入。

## 决策流
`backend/decision/aggregator.py` 负责旧版聚合与新版多 Agent 入口。默认新版路径调用 `backend/agents/pipeline.py`，依次经过分析师、研究员、交易员和风险经理。

## 风控与记忆
风险经理在 `backend/agents/risk_manager.py` 做最终降级/否决。长期记忆由 `backend/memory/` 提供，审计记录写入 `audit_log_fts`。

## 前端
React/Vite 前端通过 `/api` 读取 watchlist、signal、price、news 和 long-term。`/system/*` 已由后端提供，前端管理入口尚未接入。
