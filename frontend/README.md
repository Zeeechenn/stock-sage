# StockSage Frontend

React 18 + Vite + TailwindCSS + TradingView Lightweight Charts

---

## 开发

```bash
npm install
npm run dev          # 开发服务器 http://localhost:5173
npm run build        # 生产构建
npm run preview      # 预览生产构建
```

后端需同时运行（默认 `http://localhost:8000`）：

```bash
cd ..
PYTHONPATH=. uvicorn backend.main:app --reload
```

---

## 页面结构

| 页面 | 路由 | 说明 |
|------|------|------|
| Pulse / Watchlist | `/` | 决策引擎收盘快照、自选股、持仓、大盘和最新信号 |
| StockDetail | `/stock/:symbol` | 单股详情：K 线、信号、新闻、dossier、copilot 与长期标签 |
| Reviews | `/reviews` | 每日复盘与长期复盘中心 |
| Positions | `/positions` | 本地持仓设置与平仓记录 |
| Chat | `/chat` | 项目内 AI 对话助手 |
| Admin | `/admin` | 后端参数、LLM/agent、成本与专题研究控制台 |

---

## 关键组件

| 组件 | 说明 |
|------|------|
| `Chart.jsx` | TradingView Lightweight Charts K 线图 |
| `EvidenceCard.jsx` | 信号证据链、仓位和风控裁剪展示 |
| `ResearchCopilotCard.jsx` | copilot / shadow research 结论展示 |
| `SignalEvalCard.jsx` | 信号复盘卡片：胜率 / 平均次日收益 / 30~180 天窗口切换 |

---

## 环境变量

前端通过相对路径 `/api` 调用后端，无需额外配置。
如需修改后端地址，编辑 `src/api.js` 中的 `BASE_URL`。
