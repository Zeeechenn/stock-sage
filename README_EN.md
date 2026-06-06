# MingCang · 明仓

**MingCang is a local-first personal A-share research and decision workbench.** It breaks "I like this stock" into an auditable loop — **import judgment → record evidence → falsify → track → review & attribute → update memory** — so every judgment can be replayed, challenged, and verified, and every outcome becomes evidence you can use next time.

The goal isn't a smarter "prediction AI." It's a **research operating system** for the individual investor:

- **You** own alpha, sector knowledge, and the final decision;
- **AI** handles breadth sweeps, falsification, and short-term risk discipline;
- **the system** turns judgments and outcomes into memory that grows over time.

[![CI](https://github.com/Zeeechenn/MingCang/actions/workflows/test.yml/badge.svg)](https://github.com/Zeeechenn/MingCang/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/Zeeechenn/MingCang?logo=github&color=success)](https://github.com/Zeeechenn/MingCang/releases)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-22c55e)
![Agent](https://img.shields.io/badge/agent--ready-Pi%20%7C%20Claude%20Code%20%7C%20Codex%20%7C%20Cursor-8957e5)
![License](https://img.shields.io/badge/license-MIT-blue)

**Language**: [简体中文](README.md) · [English](README_EN.md)

---

## What it helps you do

| You want to... | How MingCang plugs in |
|---|---|
| **Research one stock** | `mingcang stock 000001` pulls signals, news, labels, and the research-copilot shadow conclusion, and records your judgment as a `ResearchCase` |
| **Track a long-term theme/sector** | Import theses from external analysts, institutions, or prosperity frameworks as a `ForwardThesis` with invalidation conditions and a review cadence, tracked over time |
| **Stay on top of daily signals & risk** | Technical factors + LLM news sentiment generate the official signal; ATR trailing stops protect gains; exposure and data-quality alerts fire automatically |
| **Review and compound experience** | After outcomes land, attribute results; falsification hits/misses are scored; only human-confirmed lessons promote into trusted memory |
| **Let AI do all of the above** | A built-in `mingcang` Pi terminal, plus Claude Code / Codex / Cursor via CLI / MCP |

MingCang never decides for you: **LLMs don't predict prices, don't place orders, and don't silently change signals.** Stops are ATR-derived rules, and memory only promotes after outcomes and human confirmation.

---

## Architecture: the research-to-decision loop

0.3.0 rebuilds the whole research model into a **case-based loop**: four "cases" wire research, signal, position, and review into one loop across five layers (L0–L4). Each case answers exactly one question, and they link to each other and stay auditable.

![MingCang research-to-decision architecture](docs/assets/architecture.svg)

```
Import (data + news + your judgment + external theses)
        │
        ▼
  ResearchCase ──▶ SignalCase ──▶ PositionCase ──▶ ReviewCase
   why study it?    tradable now?   why hold / when exit?  what did it teach?
        ▲                                                     │
        └──────────── memory update (outcome-gated, human-confirmed) ◀───┘
```

| Layer | Name | Question | Boundary |
|---|---|---|---|
| **L0** | Memory / Knowledge Base | What have I learned before? | User rules, reviewed lessons, research memory; LLM output defaults to `pending` and cannot self-promote to trusted |
| **L1** | Evidence | What reliable evidence exists? | Source/time/PIT/quality-aware evidence cards; packaging only, no scoring |
| **L2** | Thesis | Is this worth studying? | `ResearchCase`, `ForwardThesis`, theme hypotheses; advisory, never overrides official action |
| **L3** | Signal / Position | Tradable now? How to enter/exit? | `SignalCase` / `PositionCase` proposals and shadow output; doesn't touch real positions directly |
| **L4** | Review / Promotion / Calibration | What did the outcome teach? | `ReviewCase` attribution → memory-promotion candidate; trusted promotion stays human-gated |

### How the pieces fuse together

- **Single-stock research** → the `ResearchCase → SignalCase → PositionCase` path: `mingcang stock <symbol>` gives you the official signal, news, labels, and the research copilot's shadow conclusion in one shot.
- **Long-term / theme research** → lives in **L2 (Thesis)**: external analyst, institutional, and prosperity/financial-framework judgments are imported as a `ForwardThesis` (with invalidation conditions, follow-up metrics, review cadence) and tracked as slow evidence — never a shortcut to a buy score.
- **Where data comes from** → **L1 (Evidence) + the data layer**: A-share prices/financials/QFII, news sentiment, A/HK/US read-only global data, all in local SQLite, never the cloud; a Provider Guard enforces freshness and adjustment-basis sanity.
- **What memory is for** → **L0 + L4**: rules, lessons, and research indexes are stored in layers; only ReviewCase-attributed, human-confirmed outcomes promote from `pending` to trusted, then feed back as context for the next judgment — that's why the loop grows.

> **Status**: this case-based loop has landed but is **dormant by default** — the skeleton comes first with zero production-signal change, activating layer by layer as the forward-evidence gate clears. Production signals remain technical 0.6 + sentiment 0.4 + ATR 2.5 trailing stop; quant stays off pending evidence.

---

## What's working now

| Layer | What it does |
|---|---|
| Data | Market, news, fundamentals, QFII, A/HK/US read-only global data — local SQLite, stays on your machine |
| Signals | Technical factors + LLM news sentiment, weighted 0.6 / 0.4 in production, ATR 2.5 trailing stop |
| Research | Stock dossier, deep research, thesis import, falsification scoreboard, external analyst / institutional ingest |
| Memory | Layered memory, outcome-gated promotion, full audit log |
| Agent | Built-in `mingcang` Pi terminal + MCP / CLI for Claude Code, Codex, Cursor |
| UI | React frontend + REST API, local-first |

---

## Quick start

MingCang ships with a **`mingcang` Pi terminal shell** — it packages the whole CLI, memory, research flow, and safety boundaries into a ready-to-use agent terminal, so you don't have to memorize commands.

```bash
curl -fsSL https://raw.githubusercontent.com/Zeeechenn/MingCang/main/scripts/install.sh | sh
mingcang
```

Once installed, just talk to it in plain language ("look at 300308", "scan my watchlist", "review last week's positions") — it reads project context, runs the CLI, and returns research and risk conclusions itself.

Manual / dev mode:

```bash
git clone https://github.com/Zeeechenn/MingCang.git
cd MingCang
make agent-setup   # prepare environment
make agent         # launch the Pi terminal
```

Default `AI_PROVIDER=local_cli` routes internal LLM work through your local Claude CLI — no cloud key needed. You can also call the raw CLI:

```bash
python3 -m backend.agent.cli health --pretty
python3 -m backend.agent.cli premarket --pretty
python3 -m backend.agent.cli stock-context 000001 --pretty
```

> Migration: the legacy `stocksage` command, `stock_sage_*` MCP tools, and `STOCKSAGE_AGENT_*` env vars remain available during transition. New installs should use `mingcang`.

---

## Agent integration

For Pi / Claude Code / Codex / Cursor, the minimal setup is:

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

## Docs

| File | Contents |
|---|---|
| [AGENTS.md](AGENTS.md) | Agent usage rules and safety boundaries |
| [PROJECT.md](PROJECT.md) | Codebase navigation and key file index |
| [STATUS.md](STATUS.md) | Current production state, signal weights, test entry points |
| [CHANGELOG.md](CHANGELOG.md) | Release history and completed work |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup and contribution flow |

---

## From StockSage to MingCang

The project was formerly **StockSage**; from 0.3.0 it's officially **MingCang / 明仓**. This is more than a rename:

- The whole research model was rebuilt into a case-based research-to-decision loop (research → signal → position → review → memory);
- Positioning shifted to "amplify human judgment, gated by forward evidence," adding thesis-import channels and a falsification scoreboard;
- A ready-to-use `mingcang` Pi terminal shell was added to lower the barrier to entry;
- A/HK/US read-only global data was expanded, with stronger data-quality and price-adjustment guards.

Legacy `stocksage`, `stock_sage_*`, and `STOCKSAGE_AGENT_*` paths remain available during the transition.

---

## Disclaimer

MingCang is a personal research tool, **not financial advice**. It doesn't place trades automatically. LLMs don't predict prices. Take-profit and stop-loss levels are generated from ATR formulas and risk constraints. All trading decisions and financial risk belong to the user.

---

## Where this is heading

MingCang is positioned as **amplifier-primary, source-gated** — not an oracle that predicts on its own, but a system that amplifies human judgment and gates on outcomes.

- **Offense (alpha) comes from humans, not a manufactured signal.** The primary source of offense is imported judgment from seasoned external researchers (paired with prosperity and financial-quality frameworks), with the user's own judgment as filter, veto, and position sizing. Manufacturing edge from price patterns has been ruled out — backtests showed no edge.
- **AI is an amplifier, not an oracle.** It does two things: breadth — aggregate public information and surface candidate theses a human would miss, always labeled "unproven hypotheses"; falsification & risk — build evidence dossiers, track theses, alarm on invalidation, plus a short-term risk-discipline lane.
- **AI may attempt to become an alpha source, but every attempt is gated.** Future models, new skills, and open-source components are all allowed to try, but they influence real decisions only after passing a forward, outcome-based falsification gate; default trust is always the human.
- **Learning is outcome-gated, not plausibility-gated.** A thesis is promoted from pending to trusted memory only after its outcome is realized and verified — never because it "sounds well-reasoned."
- **Judged on metrics that can fail.** Invalidation-catch rate (when a thesis breaks, did the alarm fire before the loss or only after?) and defensive value (drawdown and loss-rate with the system on vs. off); breadth hits are slow, secondary evidence.

Every future capability must clear this falsification gate before influencing decisions, preventing the accumulation of unfalsified complexity.
