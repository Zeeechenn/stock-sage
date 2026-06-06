# MingCang — Position Lens

> Local-first clarity for positions, evidence, risk, and review.

MingCang turns market data, news, fundamentals, QFII flows, positions, reviews, and long-term memory into a local SQLite-backed research workspace. It connects technical signals, news sentiment, long-term research, portfolio constraints, and agent workflows so individual investors can see why a stock is being watched, what evidence supports it, what risks changed, and what still needs human judgment.

MingCang supports research, reviews, risk alerts, and dry-run orchestration only. **It does not place real orders, does not provide investment advice, and never makes the final decision for the user.**

[![CI](https://github.com/Zeeechenn/stock-sage/actions/workflows/test.yml/badge.svg)](https://github.com/Zeeechenn/stock-sage/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Zeeechenn/stock-sage?logo=github&color=success)](https://github.com/Zeeechenn/stock-sage/releases)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-22c55e)
![Agent](https://img.shields.io/badge/agent--ready-Codex%20%7C%20Claude%20Code%20%7C%20Cursor-8957e5)
![License](https://img.shields.io/badge/license-MIT-blue)

**Language**: [简体中文](README.md) · [English](README_EN.md)

## What MingCang Helps You See

| Lens | What it shows |
|---|---|
| Position | Watchlist, holdings, exposure, review state, and pending actions |
| Evidence | Technical signals, news sentiment, fundamentals/QFII, long-term labels, and data quality |
| Memory | Project rules, prior research, decision notes, audit logs, and chat summaries |
| Risk | ATR stops, portfolio caps, weak evidence, stale labels, and remote-write boundaries |
| Agent workflow | CLI / MCP context for Codex, Claude Code, Cursor, and other outer agents |

## How It Works

MingCang is a local-first research substrate, not an agent that decides for you. Data, memory, and personal portfolio context stay on your machine by default. Outer agents use CLI / MCP to read health, project context, single-stock dossiers, and memory snapshots. Mutating actions dry-run first and require explicit confirmation; remote exposure is read-only by default and gated by an API key, a write switch, and an action allowlist.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/Zeeechenn/stock-sage/main/scripts/install.sh | sh
mingcang
```

Developers can clone and run manually:

```bash
git clone https://github.com/Zeeechenn/stock-sage.git
cd stock-sage
make agent-setup
make agent
```

The default local setup uses `AI_PROVIDER=local_cli`, which routes internal LLM work through your logged-in Claude / Codex CLI. Cloud LLM keys are needed only when you switch to `anthropic` or `openai`.

```bash
python3 -m backend.agent.cli health --pretty
python3 -m backend.agent.cli premarket --pretty
python3 -m backend.agent.cli intraday --symbol 000001 --pretty
python3 -m backend.agent.cli postmarket --pretty
```

> Compatibility: the legacy `stocksage` command, `stock_sage_*` MCP tools, `STOCKSAGE_AGENT_*` env vars, and `~/.stock-sage` / `stock-sage.db` entry points remain available during migration. New installs should use `mingcang`, `mingcang_*`, `MINGCANG_AGENT_*`, `~/.mingcang`, and `mingcang.db`.
> Repository URL note: until the GitHub repository is formally renamed, public links intentionally keep pointing to the existing `Zeeechenn/stock-sage` repository so badges, install, and clone paths keep working.

## Agent Workflow

A fresh agent usually only needs to:

1. Read [AGENTS.md](AGENTS.md) first for local / remote boundaries.
2. Load `STATUS.md`, `PROJECT.md`, `docs/ROADMAP.md`, or `CHANGELOG.md` according to the task.
3. Use CLI / MCP to read project context, memory, and single-stock dossiers; mutating actions dry-run first and wait for confirmation.

Common MCP tools:

| Tool | Purpose |
|---|---|
| `mingcang_project_context` | Project runtime overview, config, positions, watchlist, and memory summary |
| `mingcang_memory_snapshot` | Project memory, layered memory, audit log, and chat-summary status |
| `mingcang_stock_context` | Single-stock signals, news, positions, long-term labels, and memory context |
| `mingcang_health` | Agent mode, database, dependency, and permission health |

Legacy `stock_sage_*` tool names remain compatibility aliases.

## Configuration

<details>
<summary><b>Local config, data sources, and remote agents</b></summary>

```env
AI_PROVIDER=local_cli
DATABASE_URL=sqlite:////absolute/path/to/mingcang.db
TUSHARE_QFQ_ENABLED=false
TICKFLOW_ENABLED=false
IFIND_MCP_ENABLED=false
MINGCANG_AGENT_MODE=local
```

Remote exposure is opt-in:

```env
MINGCANG_AGENT_MODE=remote
MINGCANG_AGENT_API_KEY=replace_with_a_long_random_secret
MINGCANG_AGENT_REMOTE_WRITE_ENABLED=false
MINGCANG_AGENT_REMOTE_WRITE_ACTIONS=
```

Legacy `STOCKSAGE_AGENT_*` names are still read, but new deployments should use `MINGCANG_AGENT_*`. Never commit `.env`, databases, model files, personal trading records, or real keys.

</details>

## Architecture

![MingCang System Architecture](docs/assets/architecture.svg)

## Status And Roadmap

MingCang remains research-first and conservative by default: A-share production signals rely on technical and news-sentiment layers, quant/Kronos evidence stays audit-only until it clears promotion gates, and HK/US remain read-only research contexts. See [CHANGELOG.md](CHANGELOG.md) for release history, [STATUS.md](STATUS.md) for the current runtime snapshot, and [docs/ROADMAP.md](docs/ROADMAP.md) for upcoming work.

## More Docs

| Document | Description |
|---|---|
| [AGENTS.md](AGENTS.md) | Codex / Claude Code / MCP local-agent instructions |
| [PROJECT.md](PROJECT.md) | Project index, capability map, and key file navigation |
| [STATUS.md](STATUS.md) | Current runtime snapshot, production boundaries, signal weights, tests, and startup commands |
| [CHANGELOG.md](CHANGELOG.md) | Completed releases, milestones, and major changes |
| [docs/ROADMAP.md](docs/ROADMAP.md) | M-numbered in-progress work, roadmap, and deferred items |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, test expectations, and contribution flow |

## Disclaimer

MingCang is a personal research and decision-support tool, **not investment advice**. It does not place trades automatically. LLMs do not predict prices. Take-profit and stop-loss levels are generated from ATR formulas and risk constraints. Users are responsible for all trading decisions and financial risks.
