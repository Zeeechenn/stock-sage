"""Analyst-level bias-override caveats that flow into decision prompts.

Stored in `ai_memory` with `scope='bias_override'` and `category='bias_override'`.

Key convention:
  - `<analyst>:<label_vote>` — applied whenever the named analyst emits that
    label vote. Example: `piotroski:规避` adds a caveat to every 规避 vote from
    the Piotroski analyst.

v1 only consults the global form. Industry-scoped overrides (e.g.
`piotroski:规避:industry:电力`) are deferred until needed.

The caveat is a free-text string that the analyst surfaces in its
`key_findings` (slot 0) and `raw["bias_caveat"]`. It does **not** override the
`label_vote` — the LLM decision chain still sees the original vote alongside
the caveat and decides for itself.
"""
from __future__ import annotations

from backend.memory.ai_memory import recall, remember

BIAS_SCOPE = "bias_override"


def lookup_caveat(db, analyst: str, label_vote: str) -> str | None:
    """Look up a bias-override caveat for an analyst's vote, or None if absent."""
    return recall(db, f"{analyst}:{label_vote}", scope=BIAS_SCOPE)


def set_caveat(db, analyst: str, label_vote: str, caveat: str) -> bool:
    """Upsert a bias-override caveat. Returns True if persisted."""
    return remember(
        db,
        f"{analyst}:{label_vote}",
        caveat,
        category="bias_override",
        scope=BIAS_SCOPE,
    )


# Default Piotroski 规避 caveat. Sourced from the standing observation that the
# F-Score is systematically harsh on capex-heavy / expansion-phase names
# (utilities, growth-stage industrials) where CFO < NI is structural, not a
# quality warning.
PIOTROSKI_WEAK_DEFAULT = (
    "Piotroski F-Score 对电力/扩张期成长股系统性偏严，"
    "'规避'标签建议人工复核：先看是否资本开支重 / 在产能扩张期，"
    "再决定是否采纳。"
)


def seed_default_overrides(db) -> None:
    """Idempotently seed the default Piotroski 规避 bias override."""
    set_caveat(db, "piotroski", "规避", PIOTROSKI_WEAK_DEFAULT)
