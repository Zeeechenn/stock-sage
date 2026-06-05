"""
M36 Theme Hypothesis Engine — idempotent schema migration.

Execute:
  PYTHONPATH=. python -m backend.data.migrations.add_theme_hypothesis_engine

Changes:
  1. Creates theme_records table.
  2. Creates theme_hypotheses table.
  (create_all skips tables that already exist, so re-running is safe.)
  No existing tables are altered.
"""
import logging

from backend.data.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run() -> None:
    """Apply M36 Theme Hypothesis Engine schema (idempotent)."""
    init_db()  # runs Base.metadata.create_all — stamps theme_records + theme_hypotheses
    logger.info("theme_records and theme_hypotheses tables ready")


if __name__ == "__main__":
    run()
