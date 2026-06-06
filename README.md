# 明仓

散户亏钱，很少亏在不够聪明，常常亏在判断没有纪律、失误没有记忆。

明仓是我给自己搭的研究环境。解法不是做个更聪明的 AI，而是建立一个循环：把对一只票的判断记下来，让 AI 帮你找漏洞、盯风险；等结果出来，归因，让下次的判断更有证据可依。

**进口 → 记录 → 证伪 → 归因 → 记忆更新** — 这个循环是系统的核心，不是某个功能，是整体设计目标。

[![CI](https://github.com/Zeeechenn/MingCang/actions/workflows/test.yml/badge.svg)](https://github.com/Zeeechenn/MingCang/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Zeeechenn/MingCang?logo=github&color=success)](https://github.com/Zeeechenn/MingCang/releases)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-22c55e)
![Agent](https://img.shields.io/badge/agent--ready-Codex%20%7C%20Claude%20Code%20%7C%20Cursor-8957e5)
![License](https://img.shields.io/badge/license-MIT-blue)

**语言**：[简体中文](README.md) · [English](README_EN.md)

---

## AI 做什么，人做什么

AI 不是主角。Alpha 来自人的判断——你的研究、行业认知、过滤和否决权。AI 的角色是三件事：

| 角色 | 负责方 | 具体是什么 |
|---|---|---|
| Alpha / 方向 | **你** | 你的研究、直觉、行业认知 |
| 广度扫描 | AI | 你盯不过来的新闻、信号、关联线索 |
| 证伪 | AI | 反驳假设、检查止损条件是否还成立 |
| 短期风险纪律 | AI + 规则 | ATR 止损、组合暴露、数据质量预警 |
| 最终决策 | **你** | 始终是你 |

---

## 研究循环

```
     你的判断 / 外部研究员 / 行业研究输入
                ↓
    ResearchCase ← ForwardThesis（draft）
                ↓
       证伪核查 / 止损条件跟踪
                ↓
     SignalCase → PositionCase
                ↓
   ReviewCase → 归因 → MemoryPromotion
                ↓
          下次判断更有证据
```

每一步都有记录、可审计。记忆不由 AI 自动促进——要等结果出来，人工确认，才能进入可信层。

---

## 当前能力

| 层 | 做什么 |
|---|---|
| 数据 | 行情、新闻、财务、QFII，本地 SQLite，不上云 |
| 信号 | 技术因子 + LLM 新闻情感，生产权重 0.6 / 0.4 |
| 研究 | 假设进口、证伪记分牌、外部研究员 / 机构研究导入 |
| 记忆 | 分层记忆，outcome-gated 促进，审计日志 |
| Agent | MCP / CLI，供 Claude Code / Codex / Cursor 调用 |
| 界面 | React 前端 + REST API，本地优先 |

量化 / Kronos 当前 `WEIGHT_QUANT=0.0`，等待前向证据通过门控。Atlas L0-L4 架构已合入本地 main，`ATLAS_ENABLED=false` 休眠，等 M29 量化门控通过后逐步激活。

---

## 快速开始

```bash
curl -fsSL https://raw.githubusercontent.com/Zeeechenn/MingCang/main/scripts/install.sh | sh
mingcang
```

手动安装：

```bash
git clone https://github.com/Zeeechenn/MingCang.git
cd MingCang
make agent-setup
make agent
```

默认 `AI_PROVIDER=local_cli`，走本机已登录的 Claude CLI，不需要云端 key。

```bash
python3 -m backend.agent.cli health --pretty
python3 -m backend.agent.cli premarket --pretty
python3 -m backend.agent.cli stock-context 000001 --pretty
```

> 迁移说明：旧 `stocksage` 命令、`stock_sage_*` MCP 工具、`STOCKSAGE_AGENT_*` 环境变量在过渡期仍可用；新安装建议使用 `mingcang`。

---

## Agent 接入

外层 agent（Codex / Claude Code / Cursor）接入时，默认只需要：

1. 读 [AGENTS.md](AGENTS.md)——了解本地 / 远程边界
2. 按需加载 `STATUS.md` / `PROJECT.md` / `docs/ROADMAP.md`
3. 写操作先 dry-run，等用户确认

核心 MCP 工具：

| 工具 | 用途 |
|---|---|
| `mingcang_project_context` | 持仓、自选、记忆摘要、配置概况 |
| `mingcang_stock_context` | 单只股票：信号、新闻、标签、copilot shadow |
| `mingcang_memory_snapshot` | 分层记忆、审计日志、记忆促进状态 |
| `mingcang_health` | 数据库、依赖、权限健康检查 |

旧 `stock_sage_*` 工具名保留为兼容别名。

---

## 配置

<details>
<summary><b>本地与远程配置</b></summary>

```env
AI_PROVIDER=local_cli
DATABASE_URL=sqlite:////absolute/path/to/mingcang.db
MINGCANG_AGENT_MODE=local
```

远程暴露是 opt-in，默认只读：

```env
MINGCANG_AGENT_MODE=remote
MINGCANG_AGENT_API_KEY=your_secret_key
MINGCANG_AGENT_REMOTE_WRITE_ENABLED=false
MINGCANG_AGENT_REMOTE_WRITE_ACTIONS=
```

旧 `STOCKSAGE_AGENT_*` 变量名仍可读取，新部署推荐用 `MINGCANG_AGENT_*`。`.env`、数据库、个人交易记录、真实 key 不进 Git。

</details>

---

## 架构

![明仓系统架构](docs/assets/architecture.svg)

---

## 当前状态与路线图

生产信号：技术 0.6 + 情感 0.4，ATR 2.5 移动止损保护浮盈。量化关闭，等待前向证据。M45 研究假设进口通道已就绪（外部研究员论题 draft 状态）。

- [STATUS.md](STATUS.md) — 当前运行快照
- [docs/ROADMAP.md](docs/ROADMAP.md) — 进行中任务
- [CHANGELOG.md](CHANGELOG.md) — 版本历史

---

## 文档索引

| 文件 | 内容 |
|---|---|
| [AGENTS.md](AGENTS.md) | Agent 使用规则和安全边界 |
| [PROJECT.md](PROJECT.md) | 代码库导航和关键文件索引 |
| [STATUS.md](STATUS.md) | 当前生产状态、信号权重、测试入口 |
| [CHANGELOG.md](CHANGELOG.md) | 版本历史和已完成里程碑 |
| [docs/ROADMAP.md](docs/ROADMAP.md) | 进行中和待做任务 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 开发环境和贡献流程 |

---

## 声明

明仓是个人研究工具，**不构成投资建议**。系统不自动下单，LLM 不做价格预测，止盈止损由 ATR 公式和风险约束生成。所有交易决策和资金风险由使用者自行承担。
