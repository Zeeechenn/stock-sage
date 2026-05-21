# StockSage

Personal A-share decision-support system: local data foundation, quant/technical indicators, LLM news sentiment, multi-agent risk control and memory governance, producing auditable stock-selection and position suggestions. StockSage is advisory only. It does not predict prices, does not place orders and does not make the final investment decision for the user.

![Tests](https://img.shields.io/badge/tests-300%20pytest%20%2B%209%20node-brightgreen)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-22c55e)
![License](https://img.shields.io/badge/license-MIT-blue)
![Status](https://img.shields.io/badge/status-M2%20paper%20trading-yellow)

[Product Preview](#product-preview) · [Features](#feature-highlights) · [Quick Start](#quick-start) · [API Key Limits](#api-key-limits) · [Architecture](#architecture) · [Docs](#documentation) · [Roadmap](#roadmap)

[简体中文](README.md) | [English](README_EN.md)

---

## Overview

StockSage is a personal A-share research and decision-support workstation. It stores market data, news, fundamentals, QFII holdings, index data and manual positions in local SQLite, then combines technical signals, LLM news sentiment, long-term analyst labels, risk management and portfolio constraints into auditable trading suggestions.

The current default production profile is `new_framework`: 60% technical signal, 40% LLM sentiment and 0% Qlib quant weight. The Qlib/LightGBM engineering pipeline is available, but recent expanded validation did not pass the alpha gate, so quant remains disabled in production.

## Product Preview

![StockSage System Architecture](docs/assets/architecture.svg)

## Architecture

1. Data sources: AkShare, fundamentals/QFII, market-cap and flow snapshots, news feeds, manual positions and runtime config.
2. Storage: SQLite keeps prices, news, signals, positions, reviews, chat history and memory. Point-in-time access reduces look-ahead bias.
3. Analysis: technical indicators, news source audit, LLM sentiment, offline Qlib validation, long-term analyst team and manual deep research.
4. Decision: `backend/decision/aggregator.py` merges signals; the multi-agent pipeline adds research, trading, risk and portfolio constraints.
5. Delivery: FastAPI and React expose the dashboard; Bark sends buy-signal and 14:30 stop-loss alerts.
6. Governance: ai_memory, layered decision memory, audit_log_fts, chat summaries, TTL cleanup and daily backups.

## Current Status

| Milestone | Name | Status |
|---|---|---|
| M0 | System skeleton | Done |
| M1 | Serious validation gates | Done, Sharpe 1.36 / max drawdown 8.6% / profit-loss ratio 2.78 |
| M2 | Paper trading validation | In progress |
| M3 | Credibility audit layer | Done, DSR / PBO / walk-forward / PIT / kill switch |
| M4 | Multi-agent decision layer | Mostly done; LangGraph and full FinMem replacement are deferred |
| M5 | Automated execution | Deferred until paper trading and holdout validation pass |
| M6 | Iteration and expansion | Current scope done, including quant infrastructure and frontend workspace |
| M7 | Engineering and open-source readiness | Done, with CI, Docker, Makefile, pyproject and documentation |
| M8 | Deep research and source audit | Done, manual-only and outside daily signals |
| M9 | Memory integration and governance | Mostly done, including memory admin, audit, summaries and backups |
| M10 | Reliability and product polish | M10.0-M10.4 done; M10.5 deferred |

## Feature Highlights

**Data and Coverage**

- A-share market data, stock news and index synchronization.
- Fundamentals, QFII holdings, market cap, float market cap and fund-flow features.
- Provider registry with fallback and health tracking.
- Data coverage snapshot for active stocks, price coverage, two-year price coverage, fundamentals coverage, 24h news coverage and signal date range.
- Point-in-time reads for training and inference to reduce look-ahead risk.

**Signals and Analysis**

- Technical factors: ATR, RSI, MA, RSRS and regime filters.
- LLM news sentiment scoring with rationale.
- News source audit by source, URL traceability, freshness and duplicate titles.
- Qlib/LightGBM pipeline with technical, PIT fundamental and market-flow features.
- Backtrader, walk-forward, holdout, DSR, PBO, IC significance, threshold sweep and exit experiments.

**Multi-Agent Decision Making**

- Long-term analyst team: sector thesis, Piotroski quality, prosperity indicators and QFII outflow veto.
- Researcher: bull/bear multi-round debate with graceful fallback.
- Research Director: quality review and debate-topic selection.
- Trader: converts evidence into trading suggestions.
- Risk Manager: risk veto, ATR take-profit/stop-loss and kill-switch constraints.
- Portfolio Manager: allocation under single-stock, sector and total exposure limits.

**Frontend Workspace**

- Pulse dashboard with watchlist, latest signals, market snapshot, real positions and activity feed.
- Stock detail page with chart, latest signal, news, evidence, reviews and long-term labels.
- Review center for daily and long-term reviews with Markdown report rendering.
- Position manager with stock search, open/closed positions and realized PnL.
- AI chat with session isolation, confirmation workflow, Markdown replies and SSE streaming.
- Admin page for weights, exposure limits, data backfill parameters, review schedules and memory management.

**Memory and Audit**

- `ai_memory` for long-term rules, risk preferences, research indexes and user preferences.
- Layered decision memory for symbol-level medium-term notes and global long-term reflections.
- `audit_log_fts` for searchable memory, research, recall, backup and action events.
- `should_remember()` heuristic before long-term memory writes.
- User confirmation before chat-triggered memory writes.
- TTL cleanup, daily backup and chat-window summarization.

**Manual Deep Research**

- CLI/API deep research flow with industry researcher, company researcher, risk reviewer, source auditor and report writer.
- Default report path: `docs/research/YYYY-MM-DD-topic.md`.
- Deep research writes an indexed memory pointer but does not create a `Signal` or participate in daily postmarket signals.

## Quick Start

```bash
# 1. Clone and install dependencies
git clone <repo-url> && cd stock-sage
pip install ".[dev]"

# 2. Configure environment variables
cp .env.example .env
# Fill ANTHROPIC_API_KEY and optionally BARK_KEY

# 3. Initialize database
python3 backend/data/database.py

# 4. Start backend
PYTHONPATH=. uvicorn backend.main:app --reload

# 5. Start frontend in another terminal
cd frontend && npm install && npm run dev
```

Open http://localhost:5173 for the dashboard. API docs are available at http://localhost:8000/docs.

## API Key Limits

This is a 2026-05-21 snapshot from official docs. Free, trial and promotional quotas can change; always treat each provider dashboard as the source of truth.

| Variable | Purpose | Free/trial limit | StockSage guidance |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Default LLM provider | Anthropic API has no stable daily free-call allowance. Limits depend on account tier, credit balance and rate limits shown in Claude Console. | Set a monthly spend limit and avoid unbounded LLM calls in batch jobs. |
| `OPENAI_API_KEY` | OpenAI or compatible provider | OpenAI API limits vary by organization, project and model. There is no project-safe daily free-call number to hardcode. | Required only when `AI_PROVIDER=openai`; set a project hard cap. |
| `TUSHARE_TOKEN` | Optional A-share data source | 120-point tier: 50 RPM and 8000 calls/day, only non-adjusted stock daily prices. 2000-point tier: 200 RPM and 100000 calls/day/API. 5000-point tier: 500 RPM and no regular-data daily cap. | Low/free tiers are suitable only for daily price supplementation. Fundamentals, flow data, HK/US, minute data and news usually need higher points or separate permissions. |
| `TAVILY_API_KEY` | Optional realtime news supplement | Free Researcher plan: 1000 API credits/month. Basic search costs 1 credit/request; advanced search costs 2. Development keys default to 100 RPM. | Basic search averages about 33 requests/day across a month. StockSage calls Tavily only when local 24h news is sparse. |
| `ANSPIRE_API_KEY` | Optional strict news backfill | Official pages currently show both 2500 signup points and a 500-call promotion. Standard search is listed at RMB 30/1000 calls. | Do not assume a daily reset. Plan around the console usage page and one-time trial balance. |
| `BARK_KEY` | Optional iOS push | Not a market-data or LLM API key. StockSage uses it only for buy-signal and stop-loss alerts. | Push failures are logged/audited and do not block signal persistence. |
| `STOCKSAGE_AGENT_API_KEY` | Remote agent auth | Self-generated project access key, with no third-party quota. | Required only for remote agent mode; local Codex/Claude sessions do not need it. |

Sources: Anthropic [rate limits](https://docs.anthropic.com/en/api/rate-limits), OpenAI [rate limits](https://help.openai.com/en/articles/5955598) / [usage tiers](https://platform.openai.com/docs/guides/rate-limits), Tushare [points and rate table](https://tushare.pro/document/1?doc_id=290), Tavily [credits](https://docs.tavily.com/documentation/api-credits) / [rate limits](https://docs.tavily.com/documentation/rate-limits), Anspire [product page](https://open.anspire.cn/document/docs/searchProduce/) / [best practice](https://open.anspire.cn/document/docs/bestPractice/).

## Common Commands

| Command | Purpose |
|---|---|
| `make install` | Install Python dev dependencies and frontend packages |
| `make dev` | Start backend dev server |
| `make build` | Build frontend |
| `make test` | Run backend pytest suite |
| `make frontend-test` | Run frontend node:test suite |
| `make verify` | Run lint, typecheck, backend tests, frontend tests and frontend build |
| `make coverage-snapshot` | Print current data coverage snapshot |
| `make paper-stats` | Compute paper trading statistics |
| `make docker-up` | Start services with docker compose |

## Documentation

| Document | Description |
|---|---|
| [PROJECT.md](PROJECT.md) | Project index, milestones and key file map |
| [STATUS.md](STATUS.md) | Current snapshot, signal weights, schedules, tests and startup commands |
| [CHANGELOG.md](CHANGELOG.md) | Completed milestones and major changes |
| [docs/ROADMAP.md](docs/ROADMAP.md) | In-progress work, roadmap and deferred items |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, test expectations and contribution flow |
| [AGENTS.md](AGENTS.md) | Codex / Claude Code / MCP local agent instructions |

## Roadmap

**Near term**

- Finish the M2 test-1 closing summary and start the two-month test-2 validation.
- Compare real paper-trading results against system suggestions, manual actions, stop rules and holding periods.
- Keep calibrating entry threshold, exit logic, trailing stop and exposure limits.

**Mid term**

- Consider a small Qlib weight such as 0.1 only after M2/M3 independent validation passes.
- Keep Qlib restoration offline-first: factor versioning, train/validation windows, IC/ICIR, monotonic buckets and cost-adjusted returns.
- Add an Alembic baseline to gradually replace `create_all + runtime patch`.
- Generate TypeScript types/client from OpenAPI for high-traffic frontend pages.
- Move scheduling out of the FastAPI process via `backend.scheduler_worker` and launchd/systemd/supervisor.

**Deferred**

- LangGraph pipeline rewrite only if test-2 provides enough samples and path B clearly beats path A.
- Full FinMem replacement only if memory depth shows verified improvement in return or drawdown.
- US market expansion stays deferred until the A-share path is stable and explicitly needed.
- QMT/miniQMT execution stays deferred until paper trading and holdout validation pass.

## Disclaimer

StockSage is a personal research and decision-support tool, not investment advice. It does not place trades automatically. LLMs do not predict prices. Take-profit and stop-loss levels are generated from ATR formulas and risk constraints. Users are responsible for all trading decisions and financial risks.
