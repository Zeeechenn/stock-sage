"""
回填历史 FinancialMetric.disclosure_date

用法：
    PYTHONPATH=. python3 -m backend.data.backfill_disclosure_dates
    PYTHONPATH=. python3 -m backend.data.backfill_disclosure_dates --years 5
"""
import argparse
import logging

from backend.data.database import SessionLocal
from backend.data.fundamentals import sync_disclosure_dates

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", type=int, default=3,
                        help="回填最近几年的期次（默认 3 年）")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        n = sync_disclosure_dates(db, years=args.years)
        print(f"完成：更新 {n} 条 disclosure_date")
    finally:
        db.close()


if __name__ == "__main__":
    main()
