# MingCang

Individual investors rarely lose because they aren't smart enough. They lose because their judgments lack discipline and their mistakes don't build memory.

MingCang is the research environment I built for myself. The idea isn't to make a smarter AI — it's to build a loop: record what you think about a stock, let AI find holes and track risks, wait for outcomes, attribute results, and let that memory feed the next judgment.

**Import → Record → Falsify → Review → Promote** — this loop is the system's core. Not a feature. The design goal.

[![CI](https://github.com/Zeeechenn/MingCang/actions/workflows/test.yml/badge.svg)](https://github.com/Zeeechenn/MingCang/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Zeeechenn/MingCang?logo=github&color=success)](https://github.com/Zeeechenn/MingCang/releases)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-22c55e)
![Agent](https://img.shields.io/badge/agent--ready-Codex%20%7C%20Claude%20Code%20%7C%20Cursor-8957e5)
![License](https://img.shields.io/badge/license-MIT-blue)

**Language**: [简体中文](README.md) · [English](README_EN.md)

---

## What AI Does. What You Do.

AI isn't the main character here. Alpha comes from human judgment — your research, your sector knowledge, your filter and veto. AI plays three supporting roles:

| Role | Owner | What it means |
|---|---|---|
| Alpha / direction | **You** | Your research, intuition, sector knowledge |
| Breadth sweep | AI | News, signals, and angles you can't track manually |
| Falsification | AI | Challenge your thesis, check whether stop conditions still hold |
| Short-term risk discipline | AI + rules | ATR stops, portfolio exposure, data quality alerts |
| Final decision | **You** | Always |

AI doesn't predict prices. It doesn't manufacture alpha. It doesn't trade automatically.

---

## The Research Loop

```
     Your thesis / external analyst / institutional research
                    ↓
    ResearchCase ← ForwardThesis (draft)
                    ↓
         Falsification checks / stop tracking
                    ↓
       SignalCase → PositionCase
                    ↓
     ReviewCase → Attribution → MemoryPromotion
                    ↓
            Better calibration next time
```

Every step is logged and auditable. Memory isn't promoted by AI automatically — it waits for outcomes and explicit human confirmation before entering the trusted layer.

---

## What's Working Now

| Layer | What it does |
|---|---|
| Data | Market, news, fundamentals, QFII — local SQLite, stays on your machine |
| Signals | Technical factors + LLM news sentiment, weighted 0.6 / 0.4 in production |
| Research | Thesis import, falsification scoreboard, external analyst / institutional research ingest |
| Memory | Layered memory, outcome-gated promotion, full audit log |
| Agent | MCP / CLI for Claude Code, Codex, Cursor |
| UI | React frontend + REST API, local-first |

Quant/Kronos is currently `WEIGHT_QUANT=0.0`, waiting for forward evidence to clear the promotion gate. The Atlas L0-L4 architecture is merged into local main with `ATLAS_ENABLED=false` — dormant until M29 gate clearance.

---

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/Zeeechenn/MingCang/main/scripts/install.sh | sh
mingcang
```

Or manually:

```bash
git clone https://github.com/Zeeechenn/MingCang.git
cd MingCang
make agent-setup
make agent
```

Default setup uses `AI_PROVIDER=local_cli` and routes internal LLM work through your local Claude CLI — no cloud key needed.

```bash
python3 -m backend.agent.cli health --pretty
python3 -m backend.agent.cli premarket --pretty
python3 -m backend.agent.cli stock-context 000001 --pretty
```

> Migration: the legacy `stocksage` command, `stock_sage_*` MCP tools, and `STOCKSAGE_AGENT_*` env vars remain available during transition. New installs should use `mingcang`.

---

## Agent Integration

For Codex / Claude Code / Cursor, the minimal setup is:

1. Read [AGENTS.md](AGENTS.md) — local/remote boundaries
2. Load `STATUS.md` / `PROJECT.md` / `docs/ROADMAP.md` as the task requires
3. Mutating actions dry-run first and wait for confirmation

Core MCP tools:

| Tool | Purpose |
|---|---|
| `mingcang_project_context` | Positions, watchlist, memory summary, config overview |
| `mingcang_stock_context` | Single-stock signals, news, labels, copilot shadow |
| `mingcang_memory_snapshot` | Layered memory, audit log, promotion pipeline state |
| `mingcang_health` | Database, dependency, permission health check |

Legacy `stock_sage_*` tool names remain compatibility aliases.

---

## Configuration

<details>
<summary><b>Local and remote configuration</b></summary>

```env
AI_PROVIDER=local_cli
DATABASE_URL=sqlite:////absolute/path/to/mingcang.db
MINGCANG_AGENT_MODE=local
```

Remote exposure is opt-in and read-only by default:

```env
MINGCANG_AGENT_MODE=remote
MINGCANG_AGENT_API_KEY=your_secret_key
MINGCANG_AGENT_REMOTE_WRITE_ENABLED=false
MINGCANG_AGENT_REMOTE_WRITE_ACTIONS=
```

Legacy `STOCKSAGE_AGENT_*` names are still read, but new deployments should use `MINGCANG_AGENT_*`. Keep `.env`, databases, personal trading records, and real keys out of Git.

</details>

---

## Architecture

![MingCang System Architecture](docs/assets/architecture.svg)

---

## Current Status and Roadmap

Production signals: technical 0.6 + sentiment 0.4, ATR 2.5 trailing stop. Quant disabled, awaiting forward evidence. M45 thesis import pipeline live (external analyst theses in draft state).

- [STATUS.md](STATUS.md) — current runtime snapshot
- [docs/ROADMAP.md](docs/ROADMAP.md) — in-progress work
- [CHANGELOG.md](CHANGELOG.md) — release history

---

## Docs

| File | Contents |
|---|---|
| [AGENTS.md](AGENTS.md) | Agent usage rules and safety boundaries |
| [PROJECT.md](PROJECT.md) | Codebase navigation and key file index |
| [STATUS.md](STATUS.md) | Current production state, signal weights, test entry points |
| [CHANGELOG.md](CHANGELOG.md) | Release history and completed milestones |
| [docs/ROADMAP.md](docs/ROADMAP.md) | In-progress and deferred work |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and contribution flow |

---

## Disclaimer

MingCang is a personal research tool, **not financial advice**. It doesn't place trades automatically. LLMs don't predict prices. Take-profit and stop-loss levels are generated from ATR formulas and risk constraints. All trading decisions and financial risk belong to the user.
