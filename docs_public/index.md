# 明仓文档

明仓是一个本地优先的股票研究工作台。它把自选、行情、新闻、官方信号、AI 研究、长期论题、复盘和记忆放在同一个可审计流程里。

明仓不自动下单，不接券商，不让 LLM 替你买卖。它的目标是帮助你研究、记录、证伪、复盘和沉淀经验。

## 快速开始

| 你要做什么 | 入口 |
|---|---|
| 体验 demo | `make demo` |
| 打开前端 | `http://127.0.0.1:5173` |
| 研究一只股票 | `mingcang stock 300308` |
| 检查运行状态 | `mingcang doctor` |
| 查看全部功能 | [Feature Map](FEATURE_MAP.md) |

```bash
make demo
mingcang doctor
mingcang stock 300308
```

## 推荐阅读顺序

1. [User Guide](USER_GUIDE.md)：按任务学习怎么用明仓。
2. [Feature Map](FEATURE_MAP.md)：查看所有功能、入口、状态、写入边界和 key 要求。
3. [Why Not AI Stock Picker](WHY_NOT_AI_STOCK_PICKER.md)：理解明仓为什么不是 AI 荐股器。
4. [Reference](REFERENCE.md)：查前端页面、后端 API、CLI、action 和配置。
5. [Developer Guide](DEVELOPER_GUIDE.md)：后续开发和扩展功能时再读。

## 常见任务

| 任务 | 看哪里 | 你会得到什么 |
|---|---|---|
| 研究一只股票 | [User Guide](USER_GUIDE.md#31) | 官方信号、新闻、copilot、长期标签和记忆上下文。 |
| 每日扫描 | [User Guide](USER_GUIDE.md#33) | 盘前、盘中、盘后、周末的使用节奏。 |
| 专题研究 | [User Guide](USER_GUIDE.md#34) | Deep research、长期论题和来源审计。 |
| 了解所有模块 | [Feature Map](FEATURE_MAP.md) | 启动、前端、信号、研究、记忆、数据、量化、风控、agent。 |
| 查系统接口 | [Reference](REFERENCE.md) | API、CLI、action registry、配置项和前端页面。 |

## 核心边界

| 边界 | 说明 |
|---|---|
| 官方信号 | 规则系统输出，当前主要由技术、情绪和风控组成。 |
| LLM 研究 | 负责整理、反问、辩论和风险提示；默认不覆盖官方信号。 |
| 量化系统 | 当前是验证和影子证据路径，不进正式信号。 |
| 写入动作 | 自选、持仓、配置、记忆等高风险动作必须显式确认。 |
| 交易执行 | 不接券商，不自动下单。 |

## 文档结构

| 页面 | 用途 |
|---|---|
| [User Guide](USER_GUIDE.md) | 任务型使用手册。 |
| [Feature Map](FEATURE_MAP.md) | 全功能地图。 |
| [Architecture](ARCHITECTURE.md) | 研究闭环、证据对象和记忆促进模型。 |
| [Reference](REFERENCE.md) | 前端、后台、CLI、action 和配置参考。 |
| [Developer Guide](DEVELOPER_GUIDE.md) | 开发者扩展指南。 |
