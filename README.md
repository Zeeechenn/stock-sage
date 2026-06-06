# MingCang — Position Lens

> 本地优先的个人 A 股持仓研究镜头：看清仓位、证据、风险和复盘。

MingCang（明仓）把行情、新闻、财务、QFII、持仓、复盘和长期记忆组织在本地 SQLite 中，再把技术信号、新闻情绪、长期研究、组合约束和 agent 工作流连接成一套可审计的研究工作台。它关注的不是“预测下一个价格”，而是帮个人投资者看清：为什么关注一只股票、证据是否足够、风险哪里变化、下一步是否需要人工判断。

MingCang 只做研究、复盘、风险提示和 dry-run 编排，**不自动下真实订单，不构成投资建议，最终决策始终由用户负责**。

[![CI](https://github.com/Zeeechenn/stock-sage/actions/workflows/test.yml/badge.svg)](https://github.com/Zeeechenn/stock-sage/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Zeeechenn/stock-sage?logo=github&color=success)](https://github.com/Zeeechenn/stock-sage/releases)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-22c55e)
![Agent](https://img.shields.io/badge/agent--ready-Codex%20%7C%20Claude%20Code%20%7C%20Cursor-8957e5)
![License](https://img.shields.io/badge/license-MIT-blue)

**语言**：[简体中文](README.md) · [English](README_EN.md)

## 明仓能帮你看清什么

| 镜头 | 看到什么 |
|---|---|
| 持仓 | 自选、持仓、暴露、复盘状态和待处理动作 |
| 证据 | 技术信号、新闻情绪、财务/QFII、长期标签和数据质量 |
| 记忆 | 项目规则、历史研究、决策笔记、审计日志和聊天摘要 |
| 风险 | ATR 止损、组合上限、弱证据、过期标签和远程写入边界 |
| Agent 工作流 | CLI / MCP 上下文，供 Codex、Claude Code、Cursor 等外层 agent 调用 |

## 工作方式

MingCang 是本地优先的研究底座，而不是替你决策的 agent。数据、记忆和个人持仓默认保留在本机；外层 agent 通过 CLI / MCP 读取健康状态、项目上下文、单股 dossier 和记忆摘要。写操作先 dry-run，只有在用户确认后才执行；远程暴露默认只读，并受 API key、写开关和 action allowlist 保护。

## 快速开始

```bash
curl -fsSL https://raw.githubusercontent.com/Zeeechenn/stock-sage/main/scripts/install.sh | sh
mingcang
```

开发者也可以手动 clone 后启动：

```bash
git clone https://github.com/Zeeechenn/stock-sage.git
cd stock-sage
make agent-setup
make agent
```

默认本地配置是 `AI_PROVIDER=local_cli`，会使用本机已登录的 Claude / Codex CLI；只有切换到 `anthropic` 或 `openai` 时才需要云端 LLM key。

```bash
python3 -m backend.agent.cli health --pretty
python3 -m backend.agent.cli premarket --pretty
python3 -m backend.agent.cli intraday --symbol 000001 --pretty
python3 -m backend.agent.cli postmarket --pretty
```

> 兼容说明：旧 `stocksage` 命令、`stock_sage_*` MCP tool、`STOCKSAGE_AGENT_*` 环境变量和 `~/.stock-sage` / `stock-sage.db` 入口在迁移期仍保留；新安装建议使用 `mingcang`、`mingcang_*`、`MINGCANG_AGENT_*`、`~/.mingcang` 和 `mingcang.db`。
> 仓库 URL 说明：GitHub 仓库正式重命名前，公开链接暂时继续指向现有 `Zeeechenn/stock-sage` 仓库，避免首页徽章、安装脚本和 clone 入口失效。

## Agent 使用

新 agent 默认只需要：

1. 先读 [AGENTS.md](AGENTS.md)，确认本地/远程边界。
2. 按任务加载 `STATUS.md`、`PROJECT.md`、`docs/ROADMAP.md` 或 `CHANGELOG.md`。
3. 通过 CLI / MCP 读取项目上下文、记忆和单股 dossier；写操作先 dry-run，再等用户确认。

常用 MCP 工具：

| 工具 | 用途 |
|---|---|
| `mingcang_project_context` | 项目运行概况、配置、持仓、自选和记忆摘要 |
| `mingcang_memory_snapshot` | 项目记忆、分层记忆、审计日志和聊天摘要状态 |
| `mingcang_stock_context` | 单只股票的信号、新闻、持仓、长期标签和记忆上下文 |
| `mingcang_health` | agent 模式、数据库、依赖和权限健康检查 |

旧 `stock_sage_*` 工具名仍作为兼容别名。

## 配置

<details>
<summary><b>本地配置、数据源和远程 agent</b></summary>

```env
AI_PROVIDER=local_cli
DATABASE_URL=sqlite:////absolute/path/to/mingcang.db
TUSHARE_QFQ_ENABLED=false
TICKFLOW_ENABLED=false
IFIND_MCP_ENABLED=false
MINGCANG_AGENT_MODE=local
```

远程暴露是 opt-in：

```env
MINGCANG_AGENT_MODE=remote
MINGCANG_AGENT_API_KEY=replace_with_a_long_random_secret
MINGCANG_AGENT_REMOTE_WRITE_ENABLED=false
MINGCANG_AGENT_REMOTE_WRITE_ACTIONS=
```

旧 `STOCKSAGE_AGENT_*` 名称仍可读取，但新部署应使用 `MINGCANG_AGENT_*`。`.env`、数据库、模型文件、个人交易记录和真实 key 不应进入 Git。

</details>

## 架构

![MingCang 系统架构](docs/assets/architecture.svg)

## 当前状态与路线图

MingCang 当前主线仍坚持“研究先行、交易保守”：A 股生产信号以技术面和新闻情绪为主，量化/Kronos 证据继续作为可审计研究线索沉淀；HK/US 保持只读研究边界。版本历史见 [CHANGELOG.md](CHANGELOG.md)，当前运行快照见 [STATUS.md](STATUS.md)，后续计划见 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 更多文档

| 文档 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | Codex / Claude Code / MCP 本地 agent 使用说明 |
| [PROJECT.md](PROJECT.md) | 项目索引、能力地图和关键文件导航 |
| [STATUS.md](STATUS.md) | 当前运行快照、生产边界、信号权重、测试和启动命令 |
| [CHANGELOG.md](CHANGELOG.md) | 已完成版本、里程碑和重要变更 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | M 编号进行中任务、未来规划和后置事项 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 开发环境、测试要求和贡献流程 |

## 风险声明

MingCang 是个人研究和辅助决策工具，**不构成投资建议**。系统不会自动下单，LLM 不做价格预测，止盈止损由 ATR 公式和风险约束生成。任何交易决策和资金风险均由使用者自行承担。
