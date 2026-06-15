"""
scraper/run.py
Entry point for the scraper. Called by GitHub Actions.

Usage:
  python -m scraper.run --source indeed
  python -m scraper.run --source linkedin
  python -m scraper.run --source all
"""
import argparse
import logging
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from scraper.indeed   import scrape_indeed
from scraper.linkedin import scrape_linkedin
from db.queries       import get_conn, upsert_job, start_scrape_run, finish_scrape_run, mark_stale_jobs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run")


def run_source(source: str):
    logger.info(f"{'='*50}")
    logger.info(f"Starting scrape: {source.upper()}")
    logger.info(f"{'='*50}")

    conn = get_conn()
    run_id = start_scrape_run(conn, source)

    try:
        if source == "indeed":
            jobs = scrape_indeed()
        elif source == "linkedin":
            jobs = scrape_linkedin()
        else:
            raise ValueError(f"Unknown source: {source}")

        new_count = updated_count = 0
        for job in jobs:
            is_new, is_updated = upsert_job(conn, job.to_db_dict())
            if is_new:
                new_count += 1
            elif is_updated:
                updated_count += 1

        mark_stale_jobs(conn, source)

        finish_scrape_run(conn, run_id,
            jobs_found=len(jobs),
            jobs_new=new_count,
            jobs_updated=updated_count,
            status="success"
        )

        logger.info(f"✅ {source}: {len(jobs)} found | {new_count} new | {updated_count} updated")

    except Exception as e:
        logger.error(f"❌ Scrape failed for {source}: {e}")
        finish_scrape_run(conn, run_id, 0, 0, 0, status="failed", error=str(e))
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Run job scraper")
    parser.add_argument("--source", choices=["indeed", "linkedin", "all"],
                        default="all", help="Which source to scrape")
    args = parser.parse_args()

    sources = ["indeed", "linkedin"] if args.source == "all" else [args.source]
    for source in sources:
        run_source(source)


if __name__ == "__main__":
    main()
