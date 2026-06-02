"""
M35 Thesis Ledger — idempotent schema migration.

Execute:
  PYTHONPATH=. python -m backend.data.migrations.add_thesis_ledger

Changes:
  1. Creates thesis_records and thesis_confidence_entries tables (create_all
     skips tables that already exist, so re-running is safe).
  No existing tables are altered.
"""
import logging

from backend.data.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    """Apply M35 Thesis Ledger schema (idempotent)."""
    init_db()  # runs Base.metadata.create_all — stamps thesis_records + thesis_confidence_entries
    logger.info("thesis_records and thesis_confidence_entries tables ready")


if __name__ == "__main__":
    run()
