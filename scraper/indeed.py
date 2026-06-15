"""
scraper/indeed.py
Scrapes DevOps/Cloud jobs from Indeed Ireland using Playwright.
Handles pagination, anti-bot delays, and structured extraction.
"""
import os
import re
import time
import random
import logging
from urllib.parse import urlencode, quote_plus

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from scraper.models import Job, make_external_id

logger = logging.getLogger(__name__)

BASE_URL = "https://ie.indeed.com/jobs"
SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS",
    "DevOps Engineer,Cloud Engineer,SRE,Platform Engineer,MLOps Engineer"
).split(",")
LOCATION = os.getenv("SEARCH_LOCATION", "Dublin, Ireland")
MAX_PAGES = int(os.getenv("MAX_PAGES_PER_SOURCE", "5"))
DELAY = float(os.getenv("SCRAPE_DELAY", "3"))


def _build_url(query: str, start: int = 0) -> str:
    params = {
        "q": query.strip(),
        "l": LOCATION,
        "radius": "50",
        "fromage": "14",    # last 14 days
        "start": str(start),
    }
    return f"{BASE_URL}?{urlencode(params)}"


def _random_delay():
    time.sleep(DELAY + random.uniform(0.5, 2.0))


def _extract_job_id(url: str) -> str:
    match = re.search(r"jk=([a-f0-9]+)", url)
    if match:
        return match.group(1)
    return make_external_id("indeed", url)


def _parse_remote(title: str, location: str, description: str) -> str:
    text = (title + " " + location + " " + description).lower()
    if "remote" in text:
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    return "On-site"


def _parse_job_type(description: str) -> str:
    text = description.lower()
    if "contract" in text or "contractor" in text:
        return "Contract"
    if "part-time" in text or "part time" in text:
        return "Part-time"
    return "Full-time"


def scrape_indeed() -> list[Job]:
    jobs: list[Job] = []
    seen_ids: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-IE",
        )
        page = context.new_page()

        for keyword in SEARCH_KEYWORDS:
            logger.info(f"Indeed: searching '{keyword}'")
            for page_num in range(MAX_PAGES):
                url = _build_url(keyword, start=page_num * 10)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    _random_delay()

                    # Dismiss cookie banner if present
                    try:
                        page.click("#onetrust-accept-btn-handler", timeout=3000)
                    except Exception:
                        pass

                    # Wait for job cards
                    page.wait_for_selector("[data-jk]", timeout=15000)
                    cards = page.query_selector_all("[data-jk]")

                    if not cards:
                        logger.info(f"  No cards on page {page_num+1}, stopping.")
                        break

                    logger.info(f"  Page {page_num+1}: {len(cards)} cards found")

                    for card in cards:
                        try:
                            job_id = card.get_attribute("data-jk") or ""
                            if not job_id or job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)

                            title_el   = card.query_selector("[data-testid='jobTitle'] span")
                            company_el = card.query_selector("[data-testid='company-name']")
                            location_el= card.query_selector("[data-testid='text-location']")
                            salary_el  = card.query_selector("[data-testid='attribute_snippet_testid']")

                            title   = title_el.inner_text().strip()   if title_el   else ""
                            company = company_el.inner_text().strip()  if company_el  else ""
                            location= location_el.inner_text().strip() if location_el else LOCATION
                            salary  = salary_el.inner_text().strip()   if salary_el   else ""

                            job_url = f"https://ie.indeed.com/viewjob?jk={job_id}"

                            # --- Fetch detail page for description ---
                            detail_page = context.new_page()
                            description = ""
                            try:
                                detail_page.goto(job_url, wait_until="domcontentloaded", timeout=25000)
                                _random_delay()
                                desc_el = detail_page.query_selector("#jobDescriptionText")
                                if desc_el:
                                    description = desc_el.inner_text().strip()
                            except Exception as e:
                                logger.warning(f"  Detail page failed for {job_id}: {e}")
                            finally:
                                detail_page.close()

                            if not title or not company:
                                continue

                            job = Job(
                                external_id=job_id,
                                source="indeed",
                                title=title,
                                company=company,
                                location=location,
                                url=job_url,
                                description=description,
                                salary_raw=salary,
                                remote_type=_parse_remote(title, location, description),
                                job_type=_parse_job_type(description),
                            ).enrich()

                            jobs.append(job)
                            logger.info(f"  ✔ {title} @ {company}")

                        except Exception as e:
                            logger.warning(f"  Card parse error: {e}")
                            continue

                except PlaywrightTimeout:
                    logger.warning(f"  Timeout on page {page_num+1} for '{keyword}'")
                    break
                except Exception as e:
                    logger.error(f"  Error on page {page_num+1} for '{keyword}': {e}")
                    break

                _random_delay()

        browser.close()

    logger.info(f"Indeed total: {len(jobs)} jobs scraped")
    return jobs
