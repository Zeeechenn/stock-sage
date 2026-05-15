# StockSage — 股票辅助决策系统 架构设计与实施计划

> ⚠ **本文档为历史架构参考保留**。原"Phase 0–7"任务体系已于 2026-05-15 迁移到 `PROJECT.md` 的 **M0–M6 里程碑**体系。当前项目状态请以 `PROJECT.md` 为准。
>
> 迁移映射：
> - Phase 0–6（系统骨架）→ **M0**
> - Phase 7（调度完善 + 通知 + 边界打磨）→ 已被 M0 收尾段 + M3.4 kill switch 替代
> - 美股扩展（原文档未含但 PROJECT.md 早期表格中的 Phase 7）→ **M6.2**

## Context
用户需要一个个人股票辅助决策工具，核心诉求：
- 有量化依据的止盈/止损建议（不靠 LLM 猜，用 ATR/回测数据计算）
- LLM 处理新闻情感，量化引擎处理价格信号，两者融合输出综合建议
- 用户自行最终操作，软件只提供辅助意见
- 市场范围：A股（AkShare）+ 美股（YFinance）
- LLM：Claude API（复用现有账号）

---

## 系统架构（4层）

```
[Layer 1] Data Collection
    AkShare (A股行情/新闻) + YFinance (美股) + RSS新闻源
    → SQLite 本地存储

[Layer 2] Analysis Engine
    ├── Qlib 量化模块
    │     因子工程 → LightGBM Alpha模型 → 回测验证
    │     止损 = Close - ATR(14)×2 | 止盈 = Risk×2 (1:2 RR)
    ├── 技术分析模块
    │     MA趋势 / RSI超买超卖 / 支撑阻力 / 量价配合
    └── LLM 新闻情感模块
          新闻抓取 → Claude摘要 → 情感评分(-1~+1) → 影响评估

[Layer 3] Decision Aggregation
    量化信号(40%) + 技术信号(35%) + 新闻情感(25%)
    → 综合评分(-100~+100) + 建议(强买/买/观望/卖/强卖)
    → 止损价 / 止盈价 / 置信度

[Layer 4] Web Dashboard
    FastAPI 后端 + React 前端
    页面：自选股看板 / 单股详情(K线+信号+新闻) / 历史信号准确率
    调度：APScheduler (盘前08:30数据更新, 盘后16:00复盘)
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 API | Python 3.11 + FastAPI + Uvicorn |
| 前端 | React 18 + Vite + TailwindCSS + TradingView Lightweight Charts |
| 量化引擎 | Microsoft Qlib |
| A股数据 | AkShare |
| 美股数据 | yfinance |
| LLM | anthropic SDK (Claude API) |
| 数据库 | SQLite + SQLAlchemy |
| 调度 | APScheduler |
| 新闻抓取 | feedparser + requests |

---

## 项目目录结构

```
stock-sage/
├── PROJECT.md              ← 进度追踪文件（每次开始先读这里）
├── backend/
│   ├── main.py             ← FastAPI 入口
│   ├── config.py           ← 环境变量/配置
│   ├── scheduler.py        ← 定时任务
│   ├── data/
│   │   ├── market.py       ← AkShare + YFinance 数据拉取
│   │   ├── news.py         ← 新闻抓取（RSS + 爬虫）
│   │   └── database.py     ← SQLAlchemy ORM + 建表
│   ├── analysis/
│   │   ├── factors.py      ← 技术因子计算（ATR/RSI/MA等）
│   │   ├── qlib_engine.py  ← Qlib 集成（因子→模型→回测）
│   │   ├── technical.py    ← 技术信号生成
│   │   └── sentiment.py    ← LLM新闻分析（Claude API）
│   ├── decision/
│   │   └── aggregator.py   ← 多信号融合，输出最终建议
│   └── api/
│       └── routes.py       ← REST API 路由
└── frontend/
    ├── src/
    │   ├── pages/
    │   │   ├── Watchlist.tsx    ← 自选股总览
    │   │   ├── StockDetail.tsx  ← 单股详情
    │   │   └── SignalHistory.tsx← 历史信号
    │   └── components/
    │       ├── StockCard.tsx
    │       ├── Chart.tsx        ← TradingView K线
    │       └── SignalBadge.tsx
    └── package.json
```

---

## 开发阶段计划

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 0 | 架构设计 + 项目初始化（scaffold） | 🔲 当前 |
| Phase 1 | 数据管道：AkShare/YFinance拉取 + SQLite建模 + 调度 | 🔲 |
| Phase 2 | 技术分析模块：ATR/RSI/MA因子 + 止盈止损计算 | 🔲 |
| Phase 3 | Qlib量化引擎：因子→LightGBM→回测→信号 | 🔲 |
| Phase 4 | LLM新闻分析：RSS抓取→Claude摘要→情感评分 | 🔲 |
| Phase 5 | 信号聚合层：多信号融合→综合评分→建议输出 | 🔲 |
| Phase 6 | Web看板：FastAPI接口 + React前端 + K线图 | 🔲 |
| Phase 7 | 调度完善 + 通知推送 + 边界打磨 | 🔲 |

---

## 实施步骤（Phase 0，当前任务）

1. 在 `/path/to/stock-sage/` 创建完整目录结构
2. 写 `PROJECT.md`（进度追踪，每次开始先读）
3. 写 `backend/config.py`（ANTHROPIC_API_KEY / 数据库路径 / 调度时间）
4. 写 `backend/data/database.py`（建表：stocks / prices / news / signals）
5. 写 `backend/main.py`（FastAPI骨架）
6. 前端 `npm create vite frontend` 初始化
7. 写根目录 `.env.example`

## 关键设计约束
- 止盈止损由 ATR 公式计算，严禁由 LLM 直接输出价格
- LLM 调用仅在新闻模块（sentiment.py），不参与价格预测
- 所有信号附带置信度字段，前端必须显示
- 数据库先用 SQLite，接口设计兼容 PostgreSQL（未来迁移无需改代码）
