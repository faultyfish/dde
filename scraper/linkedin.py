"""
scraper/linkedin.py
Scrapes DevOps/Cloud jobs from LinkedIn using Playwright.
Uses cookie-based session to avoid login prompts where possible,
falls back to credential login.
"""
import os
import re
import time
import random
import logging
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from scraper.models import Job, make_external_id

logger = logging.getLogger(__name__)

SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS",
    "DevOps Engineer,Cloud Engineer,SRE,Platform Engineer,MLOps Engineer"
).split(",")
LOCATION       = os.getenv("SEARCH_LOCATION", "Dublin, Ireland")
MAX_PAGES      = int(os.getenv("MAX_PAGES_PER_SOURCE", "5"))
DELAY          = float(os.getenv("SCRAPE_DELAY", "3"))
LI_EMAIL       = os.getenv("LINKEDIN_EMAIL", "")
LI_PASSWORD    = os.getenv("LINKEDIN_PASSWORD", "")

LI_JOBS_URL = "https://www.linkedin.com/jobs/search/"


def _build_url(keyword: str, start: int = 0) -> str:
    params = {
        "keywords": keyword.strip(),
        "location": LOCATION,
        "f_TPR": "r604800",     # last 7 days
        "f_JT": "F,C",         # Full-time + Contract
        "start": str(start),
    }
    return f"{LI_JOBS_URL}?{urlencode(params)}"


def _random_delay():
    time.sleep(DELAY + random.uniform(1.0, 3.0))


def _extract_job_id(url: str) -> str:
    match = re.search(r"/jobs/view/(\d+)", url)
    if match:
        return match.group(1)
    return make_external_id("linkedin", url)


def _parse_remote(job_type_text: str, description: str) -> str:
    text = (job_type_text + " " + description).lower()
    if "remote" in text:
        return "Remote"
    if "hybrid" in text:
        return "Hybrid"
    return "On-site"


def _parse_job_type(job_type_text: str) -> str:
    text = job_type_text.lower()
    if "contract" in text:
        return "Contract"
    if "part" in text:
        return "Part-time"
    return "Full-time"


def _login(page) -> bool:
    """Log in to LinkedIn. Returns True on success."""
    try:
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
        page.fill("#username", LI_EMAIL)
        page.fill("#password", LI_PASSWORD)
        page.click('[data-litms-control-urn="login-submit"]')
        page.wait_for_url("https://www.linkedin.com/feed/", timeout=20000)
        logger.info("LinkedIn: logged in successfully")
        return True
    except Exception as e:
        logger.error(f"LinkedIn login failed: {e}")
        return False


def scrape_linkedin() -> list[Job]:
    if not LI_EMAIL or not LI_PASSWORD:
        logger.error("LinkedIn credentials not set — skipping.")
        return []

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
            viewport={"width": 1280, "height": 900},
            locale="en-IE",
        )
        page = context.new_page()

        # Login
        if not _login(page):
            browser.close()
            return []

        _random_delay()

        for keyword in SEARCH_KEYWORDS:
            logger.info(f"LinkedIn: searching '{keyword}'")

            for page_num in range(MAX_PAGES):
                url = _build_url(keyword, start=page_num * 25)
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    _random_delay()

                    # Scroll to trigger lazy load
                    for _ in range(3):
                        page.keyboard.press("End")
                        time.sleep(1)

                    # Job cards
                    cards = page.query_selector_all(".jobs-search__results-list li, .scaffold-layout__list-item")

                    if not cards:
                        logger.info(f"  No cards on page {page_num+1}")
                        break

                    logger.info(f"  Page {page_num+1}: {len(cards)} cards")

                    for card in cards:
                        try:
                            # Click card to load detail in right panel
                            card.click()
                            _random_delay()

                            title_el   = page.query_selector(".job-details-jobs-unified-top-card__job-title h1")
                            company_el = page.query_selector(".job-details-jobs-unified-top-card__company-name a")
                            location_el= page.query_selector(".job-details-jobs-unified-top-card__primary-description-without-tagline .tvm__text")
                            meta_el    = page.query_selector(".job-details-jobs-unified-top-card__job-insight span")
                            desc_el    = page.query_selector("#job-details")
                            url_el     = page.query_selector('a[href*="/jobs/view/"]')

                            title       = title_el.inner_text().strip()   if title_el   else ""
                            company     = company_el.inner_text().strip()  if company_el  else ""
                            location    = location_el.inner_text().strip() if location_el else LOCATION
                            meta_text   = meta_el.inner_text().strip()     if meta_el    else ""
                            description = desc_el.inner_text().strip()     if desc_el    else ""
                            job_url     = url_el.get_attribute("href")     if url_el     else page.url

                            # Normalise job URL
                            if job_url and not job_url.startswith("http"):
                                job_url = "https://www.linkedin.com" + job_url
                            job_id = _extract_job_id(job_url or "")

                            if not job_id or job_id in seen_ids:
                                continue
                            seen_ids.add(job_id)

                            if not title or not company:
                                continue

                            job = Job(
                                external_id=job_id,
                                source="linkedin",
                                title=title,
                                company=company,
                                location=location,
                                url=job_url,
                                description=description,
                                remote_type=_parse_remote(meta_text, description),
                                job_type=_parse_job_type(meta_text),
                            ).enrich()

                            jobs.append(job)
                            logger.info(f"  ✔ {title} @ {company}")

                        except Exception as e:
                            logger.warning(f"  Card error: {e}")
                            continue

                except PlaywrightTimeout:
                    logger.warning(f"  Timeout page {page_num+1} for '{keyword}'")
                    break
                except Exception as e:
                    logger.error(f"  Error page {page_num+1} for '{keyword}': {e}")
                    break

                _random_delay()

        browser.close()

    logger.info(f"LinkedIn total: {len(jobs)} jobs scraped")
    return jobs
