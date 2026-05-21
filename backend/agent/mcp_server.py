"""MCP server exposing StockSage as local-first agent tools.

Run locally with:
    PYTHONPATH=. python -m backend.agent.mcp_server

Remote transports should set STOCKSAGE_AGENT_MODE=remote and require
STOCKSAGE_AGENT_API_KEY at the hosting layer. The tools themselves keep remote
writes disabled unless STOCKSAGE_AGENT_REMOTE_WRITE_ENABLED=true is set.
"""
from __future__ import annotations

from backend.agent.context import (
    stock_sage_context as build_stock_sage_context,
)
from backend.agent.context import (
    stock_sage_memory_snapshot as build_stock_sage_memory_snapshot,
)
from backend.agent.context import (
    stock_sage_stock_context as build_stock_sage_stock_context,
)
from backend.agent.security import require_agent_access
from backend.data.database import SessionLocal

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without optional extra
    raise SystemExit(
        "MCP SDK is not installed. Run `pip install -e '.[agent]'` first."
    ) from exc


mcp = FastMCP("stock-sage")


def _with_db(fn):
    db = SessionLocal()
    try:
        return fn(db)
    finally:
        db.close()


@mcp.tool()
def stock_sage_project_context(symbol: str | None = None) -> dict:
    """Read StockSage startup context, memory counts, watchlist, and positions."""
    require_agent_access("read")
    return _with_db(lambda db: build_stock_sage_context(db, symbol=symbol))


@mcp.tool()
def stock_sage_memory_snapshot() -> dict:
    """Read StockSage project-owned memory summary and recent entries."""
    require_agent_access("read")
    return _with_db(build_stock_sage_memory_snapshot)


@mcp.tool()
def stock_sage_stock_context(symbol: str) -> dict:
    """Read signal, position, long-term label, and memory context for one stock."""
    require_agent_access("read")
    return _with_db(lambda db: build_stock_sage_stock_context(db, symbol))


@mcp.tool()
def stock_sage_health() -> dict:
    """Read basic database-backed agent health."""
    require_agent_access("read")

    def _health(db):
        context = build_stock_sage_context(db)
        return {
            "ok": True,
            "agent_mode": context["agent_mode"],
            "project_root": context["project_root"],
            "memory": context["memory"],
            "positions": context["positions"],
            "watchlist": context["watchlist"],
        }

    return _with_db(_health)


if __name__ == "__main__":
    mcp.run()
