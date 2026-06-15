"""
db/queries.py
Reusable DB helpers used by both scraper and API.
"""
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return psycopg2.connect(
        os.environ["NEON_DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )


def upsert_job(conn, job: dict) -> tuple[bool, bool]:
    """
    Insert or update a job. Returns (is_new, is_updated).
    Deduplication key: (source, external_id).
    """
    sql = """
        INSERT INTO jobs (
            external_id, source, title, company, location, remote_type,
            job_type, salary_raw, salary_min, salary_max, description,
            url, category, level, stack, visa_sponsor, last_seen_at, scraped_at
        ) VALUES (
            %(external_id)s, %(source)s, %(title)s, %(company)s, %(location)s,
            %(remote_type)s, %(job_type)s, %(salary_raw)s, %(salary_min)s,
            %(salary_max)s, %(description)s, %(url)s, %(category)s, %(level)s,
            %(stack)s, %(visa_sponsor)s, NOW(), NOW()
        )
        ON CONFLICT (source, external_id) DO UPDATE SET
            title        = EXCLUDED.title,
            company      = EXCLUDED.company,
            location     = EXCLUDED.location,
            remote_type  = EXCLUDED.remote_type,
            job_type     = EXCLUDED.job_type,
            salary_raw   = EXCLUDED.salary_raw,
            salary_min   = EXCLUDED.salary_min,
            salary_max   = EXCLUDED.salary_max,
            description  = EXCLUDED.description,
            url          = EXCLUDED.url,
            category     = EXCLUDED.category,
            level        = EXCLUDED.level,
            stack        = EXCLUDED.stack,
            visa_sponsor = EXCLUDED.visa_sponsor,
            is_active    = TRUE,
            last_seen_at = NOW(),
            scraped_at   = NOW()
        RETURNING (xmax = 0) AS is_insert
    """
    cur = conn.cursor()
    cur.execute(sql, job)
    row = cur.fetchone()
    is_new = row["is_insert"]
    conn.commit()
    return is_new, not is_new


def start_scrape_run(conn, source: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scrape_runs (source) VALUES (%s) RETURNING id",
        (source,)
    )
    run_id = cur.fetchone()["id"]
    conn.commit()
    return run_id


def finish_scrape_run(conn, run_id: int, jobs_found: int, jobs_new: int,
                       jobs_updated: int, status: str = "success", error: str = None):
    cur = conn.cursor()
    cur.execute("""
        UPDATE scrape_runs SET
            finished_at   = NOW(),
            jobs_found    = %s,
            jobs_new      = %s,
            jobs_updated  = %s,
            status        = %s,
            error_message = %s
        WHERE id = %s
    """, (jobs_found, jobs_new, jobs_updated, status, error, run_id))
    conn.commit()


def mark_stale_jobs(conn, source: str, cutoff_hours: int = 48):
    """Mark jobs not seen in the last N hours as inactive."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE jobs SET is_active = FALSE
        WHERE source = %s
          AND last_seen_at < NOW() - INTERVAL '%s hours'
          AND is_active = TRUE
    """, (source, cutoff_hours))
    conn.commit()
