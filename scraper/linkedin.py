"""
scraper/linkedin.py
Scrapes LinkedIn via JobSpy (no login / no Playwright needed).
JobSpy hits LinkedIn's public job search API — no credentials required.
"""
import os
import logging
from jobspy import scrape_jobs
from scraper.models import Job, make_external_id

logger = logging.getLogger(__name__)

SEARCH_KEYWORDS = os.getenv(
    "SEARCH_KEYWORDS",
    "DevOps Engineer,Cloud Engineer,SRE,Platform Engineer,MLOps Engineer"
).split(",")
LOCATION  = os.getenv("SEARCH_LOCATION", "Dublin, Ireland")
MAX_PAGES = int(os.getenv("MAX_PAGES_PER_SOURCE", "5"))


def scrape_linkedin() -> list[Job]:
    jobs: list[Job] = []
    seen_ids: set[str] = set()

    for keyword in SEARCH_KEYWORDS:
        keyword = keyword.strip()
        logger.info(f"LinkedIn: searching '{keyword}'")
        try:
            df = scrape_jobs(
                site_name=["linkedin"],
                search_term=keyword,
                location=LOCATION,
                results_wanted=MAX_PAGES * 10,
                hours_old=168,          # last 7 days
                linkedin_fetch_description=True,
            )
            logger.info(f"  {len(df)} rows returned")

            for _, row in df.iterrows():
                job_id = str(row.get("id") or make_external_id("linkedin", str(row.get("job_url", ""))))
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                description = str(row.get("description") or "")
                title       = str(row.get("title") or "")
                company     = str(row.get("company") or "")
                location    = str(row.get("location") or LOCATION)
                url         = str(row.get("job_url") or "")
                salary_raw  = ""
                if row.get("min_amount") and row.get("max_amount"):
                    salary_raw = f"€{int(row['min_amount'])}–€{int(row['max_amount'])}"
                elif row.get("min_amount"):
                    salary_raw = f"€{int(row['min_amount'])}+"

                remote_raw  = str(row.get("is_remote") or "")
                remote_type = "Remote" if remote_raw == "True" else _infer_remote(title, location, description)
                job_type    = _parse_job_type(str(row.get("job_type") or ""), description)

                if not title or not company or not url:
                    continue

                job = Job(
                    external_id=job_id,
                    source="linkedin",
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    description=description,
                    salary_raw=salary_raw,
                    remote_type=remote_type,
                    job_type=job_type,
                ).enrich()

                jobs.append(job)
                logger.info(f"  ✔ {title} @ {company}")

        except Exception as e:
            logger.error(f"LinkedIn error for '{keyword}': {e}")
            continue

    logger.info(f"LinkedIn total: {len(jobs)} jobs")
    return jobs


def _infer_remote(title: str, location: str, desc: str) -> str:
    text = (title + location + desc).lower()
    if "remote" in text: return "Remote"
    if "hybrid" in text: return "Hybrid"
    return "On-site"

def _parse_job_type(raw: str, desc: str) -> str:
    text = (raw + desc).lower()
    if "contract" in text: return "Contract"
    if "part" in text:     return "Part-time"
    return "Full-time"
