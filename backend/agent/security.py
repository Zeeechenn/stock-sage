"""Local/remote guardrails for MingCang agent tools.

Local mode is intentionally trusted: Codex and Claude Code run on the owner's
machine during development and trial use. Remote mode is opt-in and read-only
by default. Legacy StockSage environment names remain accepted during the
MingCang transition.
"""
from __future__ import annotations

import hmac
import os
from collections.abc import Mapping


class AgentSecurityError(RuntimeError):
    """Raised when a remote agent call does not satisfy the configured policy."""


def _settings_env() -> dict[str, str]:
    """Return agent settings, with real environment variables taking priority."""
    try:
        from backend.config import settings

        fallback = {
            "MINGCANG_AGENT_MODE": settings.mingcang_agent_mode,
            "MINGCANG_AGENT_API_KEY": settings.mingcang_agent_api_key,
            "MINGCANG_AGENT_REMOTE_WRITE_ENABLED": (
                "true" if settings.mingcang_agent_remote_write_enabled else "false"
            ),
            "MINGCANG_AGENT_REMOTE_WRITE_ACTIONS": settings.mingcang_agent_remote_write_actions,
            "STOCKSAGE_AGENT_MODE": settings.stocksage_agent_mode,
            "STOCKSAGE_AGENT_API_KEY": settings.stocksage_agent_api_key,
            "STOCKSAGE_AGENT_REMOTE_WRITE_ENABLED": (
                "true" if settings.stocksage_agent_remote_write_enabled else "false"
            ),
            "STOCKSAGE_AGENT_REMOTE_WRITE_ACTIONS": settings.stocksage_agent_remote_write_actions,
        }
    except Exception:
        fallback = {}

    source = {**fallback, **os.environ}
    for new_key, legacy_key in (
        ("MINGCANG_AGENT_MODE", "STOCKSAGE_AGENT_MODE"),
        ("MINGCANG_AGENT_API_KEY", "STOCKSAGE_AGENT_API_KEY"),
        ("MINGCANG_AGENT_REMOTE_WRITE_ENABLED", "STOCKSAGE_AGENT_REMOTE_WRITE_ENABLED"),
        ("MINGCANG_AGENT_REMOTE_WRITE_ACTIONS", "STOCKSAGE_AGENT_REMOTE_WRITE_ACTIONS"),
    ):
        if new_key in os.environ:
            continue
        if legacy_key in os.environ:
            source[new_key] = os.environ[legacy_key]
            continue
        new_value = fallback.get(new_key, "")
        legacy_value = fallback.get(legacy_key, "")
        should_bridge = (
            (new_key == "MINGCANG_AGENT_MODE" and new_value in {"", "local"} and legacy_value != "")
            or (new_key == "MINGCANG_AGENT_REMOTE_WRITE_ENABLED" and legacy_value.lower() == "true")
            or (new_key not in {"MINGCANG_AGENT_MODE", "MINGCANG_AGENT_REMOTE_WRITE_ENABLED"}
                and new_value == "" and legacy_value != "")
        )
        if should_bridge:
            source[new_key] = legacy_value
    return source


def _first(source: Mapping[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = source.get(key, "")
        if value != "":
            return value
    return default


def agent_mode(env: Mapping[str, str] | None = None) -> str:
    """Return ``remote`` only when explicitly requested; otherwise ``local``."""
    source = env if env is not None else _settings_env()
    mode = _first(source, "MINGCANG_AGENT_MODE", "STOCKSAGE_AGENT_MODE", default="local")
    return "remote" if mode.strip().lower() == "remote" else "local"


def require_agent_access(
    operation: str = "read",
    *,
    env: Mapping[str, str] | None = None,
    api_key: str | None = None,
    action: str | None = None,
) -> None:
    """Validate access for an agent operation.

    ``operation`` is either ``read`` or a mutating operation such as ``write``.
    Local mode always passes. Remote mode requires a matching API key for every
    operation and keeps writes disabled unless explicitly opted in.
    """
    source = env if env is not None else _settings_env()
    if agent_mode(source) == "local":
        return

    expected = _first(source, "MINGCANG_AGENT_API_KEY", "STOCKSAGE_AGENT_API_KEY")
    if not expected:
        raise AgentSecurityError("remote agent mode requires MINGCANG_AGENT_API_KEY")
    if api_key is None or not hmac.compare_digest(str(api_key), expected):
        raise AgentSecurityError("invalid MingCang agent API key")

    if operation != "read":
        write_enabled = _first(
            source,
            "MINGCANG_AGENT_REMOTE_WRITE_ENABLED",
            "STOCKSAGE_AGENT_REMOTE_WRITE_ENABLED",
        )
        if write_enabled.lower() != "true":
            raise AgentSecurityError("remote agent mode is read-only by default")
        write_actions = _first(
            source,
            "MINGCANG_AGENT_REMOTE_WRITE_ACTIONS",
            "STOCKSAGE_AGENT_REMOTE_WRITE_ACTIONS",
        )
        allowed = {item.strip() for item in write_actions.split(",") if item.strip()}
        if action and allowed and action not in allowed:
            raise AgentSecurityError(f"remote agent write action not allowed: {action}")
