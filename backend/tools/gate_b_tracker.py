"""Gate-B prospective tracker CLI — record / realize / report.

record  : for each signal date<=as_of, evaluate M33 gate AS-OF that date,
          write a GateBObservation row with forward_return_net=NULL.
realize : fill forward_return_net for observations whose 5-day window has closed.
report  : compute pre-registered metrics and emit PROMOTE/REJECT/INCONCLUSIVE/ABORT.

DATABASE_URL / SOURCE_DATABASE_URL:
  --database-url       atlas worktree DB (writes GateBObservation).  Default: settings.database_url.
  --source-database-url  read-only source DB for Signal/LongTermLabel/Price.  Default: settings.database_url.

When running in tests both URLs point to the same in-memory DB.
"""
from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.research.gate_b_recorder import (
    list_observations,
    realize_returns,
    record_observations,
    report,
)


# ---------------------------------------------------------------------------
# Session context managers
# ---------------------------------------------------------------------------

def _sqlite_readonly_url(raw_url: str) -> str:
    """Convert a SQLite file URL to a read-only URI mode URL."""
    if not raw_url.startswith("sqlite:///"):
        return raw_url
    db_path = raw_url[len("sqlite:///"):]
    abs_path = Path(db_path).resolve()
    encoded = quote(str(abs_path), safe="/:")
    return f"sqlite:///file:{encoded}?mode=ro&uri=true"


@contextmanager
def readonly_session(database_url: str | None = None):
    """Open a read-only SQLAlchemy session on the given SQLite database."""
    url = database_url or settings.database_url
    # Try read-only first; fall back to read-write for in-memory / test DBs
    try:
        ro_url = _sqlite_readonly_url(url)
        engine = create_engine(ro_url, connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            yield db
        finally:
            db.close()
            engine.dispose()
    except Exception:
        # Fallback for :memory: or non-file DBs
        engine = create_engine(url, connect_args={"check_same_thread": False})
        Session = sessionmaker(bind=engine)
        db = Session()
        try:
            yield db
        finally:
            db.close()
            engine.dispose()


@contextmanager
def write_session(database_url: str | None = None):
    """Open a writable SQLAlchemy session."""
    url = database_url or settings.database_url
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--database-url",
        default=None,
        metavar="URL",
        help="Atlas worktree DB URL (writes GateBObservation). Default: settings.database_url",
    )
    parser.add_argument(
        "--source-database-url",
        default=None,
        metavar="URL",
        help="Read-only source DB for Signal/Label/Price. Default: settings.database_url",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # record subcommand
    rec = sub.add_parser(
        "record",
        help="Walk signals, build PIT dossiers, write GateBObservation rows.",
    )
    rec.add_argument(
        "--as-of",
        default=None,
        metavar="YYYY-MM-DD",
        help="Only process signals with date <= as_of. Default: today.",
    )
    rec.add_argument(
        "--horizon-days",
        type=int,
        default=5,
        metavar="N",
        help="Forward-return horizon in trading days (default 5).",
    )
    rec.add_argument(
        "--symbols",
        default=None,
        metavar="SYM1,SYM2,...",
        help="Restrict to comma-separated symbols. Default: all.",
    )

    # realize subcommand
    rea = sub.add_parser(
        "realize",
        help="Fill forward_return_net for matured observations.",
    )
    rea.add_argument(
        "--as-of",
        default=None,
        metavar="YYYY-MM-DD",
        help="Reference date for staleness check. Default: today.",
    )

    # report subcommand
    rep = sub.add_parser(
        "report",
        help="Compute pre-registered metrics and emit PROMOTE/REJECT/INCONCLUSIVE/ABORT.",
    )
    rep.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format (default: markdown).",
    )

    return parser.parse_args()


def _format_markdown(result: dict) -> str:
    lines = [
        "## Gate-B Experiment Report",
        "",
        f"**Verdict**: {result['verdict']}",
    ]
    if result.get("reason"):
        lines.append(f"**Reason**: {result['reason']}")
    lines += [
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| n_total | {result['n_total']} |",
        f"| n_pass | {result['n_pass']} |",
        f"| n_fail | {result['n_fail']} |",
        f"| gate_pass_rate | {result['gate_pass_rate']!r} |",
        f"| avg_net_return_pass | {result['avg_net_return_pass']!r} |",
        f"| avg_net_return_fail | {result['avg_net_return_fail']!r} |",
        f"| avg_net_return_delta | {result['avg_net_return_delta']!r} |",
        f"| hit_rate_pass | {result['hit_rate_pass']!r} |",
        f"| icir | {result['icir']!r} |",
        f"| ic_days | {result['ic_days']} |",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    if args.cmd == "record":
        sym_list: list[str] | None = None
        if args.symbols:
            sym_list = [s.strip() for s in args.symbols.split(",") if s.strip()]

        with write_session(args.database_url) as db:
            rows = record_observations(
                db,
                as_of=args.as_of,
                horizon_days=args.horizon_days,
                symbols=sym_list,
            )
        print(f"Recorded {len(rows)} new observation(s).")
        return 0

    elif args.cmd == "realize":
        with write_session(args.database_url) as db:
            rows = realize_returns(db, as_of=args.as_of)
        print(f"Realized {len(rows)} observation(s).")
        return 0

    elif args.cmd == "report":
        with readonly_session(args.database_url) as db:
            result = report(db)
        if args.format == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(_format_markdown(result))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
