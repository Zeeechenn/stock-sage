"""Local/remote guardrails for StockSage agent tools.

Local mode is intentionally trusted: Codex and Claude Code run on the owner's
machine during development and trial use. Remote mode is opt-in and read-only
by default.
"""
from __future__ import annotations

import hmac
import os
from collections.abc import Mapping


class AgentSecurityError(RuntimeError):
    """Raised when a remote agent call does not satisfy the configured policy."""


def agent_mode(env: Mapping[str, str] | None = None) -> str:
    """Return ``remote`` only when explicitly requested; otherwise ``local``."""
    source = env if env is not None else os.environ
    mode = source.get("STOCKSAGE_AGENT_MODE", "local").strip().lower()
    return "remote" if mode == "remote" else "local"


def require_agent_access(
    operation: str = "read",
    *,
    env: Mapping[str, str] | None = None,
    api_key: str | None = None,
) -> None:
    """Validate access for an agent operation.

    ``operation`` is either ``read`` or a mutating operation such as ``write``.
    Local mode always passes. Remote mode requires a matching API key for every
    operation and keeps writes disabled unless explicitly opted in.
    """
    source = env if env is not None else os.environ
    if agent_mode(source) == "local":
        return

    expected = source.get("STOCKSAGE_AGENT_API_KEY", "")
    if not expected:
        raise AgentSecurityError("remote agent mode requires STOCKSAGE_AGENT_API_KEY")
    if api_key is None or not hmac.compare_digest(str(api_key), expected):
        raise AgentSecurityError("invalid StockSage agent API key")

    if operation != "read" and source.get("STOCKSAGE_AGENT_REMOTE_WRITE_ENABLED", "").lower() != "true":
        raise AgentSecurityError("remote agent mode is read-only by default")
