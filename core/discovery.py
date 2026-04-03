"""
core/discovery.py
-----------------
Discovers job postings from multiple sources.
Returns a unified list of JobPosting objects.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import random
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page

from config import SEARCH, BEHAVIOR, LINKEDIN_EMAIL, LINKEDIN_PASSWORD, DATA_DIR

log = logging.getLogger("jobbot.discovery")


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class JobPosting:
    id: str = ""                   # Stable hash of (source + url)
    title: str = ""
    company: str = ""
    location: str = ""
    remote: bool = False
    url: str = ""
    source: str = ""               # "linkedin" | "indeed" | "career_page" | "email"
    description: str = ""
    salary_text: str = ""
    posted_date: str = ""
    apply_method: str = ""         # "easy_apply" | "external" | "email"
    match_score: int = 0
    discovered_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def compute_id(self):
        self.id = hashlib.md5(f"{self.source}::{self.url}".encode()).hexdigest()[:12]
        return self


# ── Seen-jobs deduplication ────────────────────────────────────────────────────

SEEN_FILE = DATA_DIR / "seen_jobs.json"

def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text()))
    return set()

def save_seen(seen: set[str]):
    SEEN_FILE.write_text(json.dumps(list(seen), indent=2))


# ── LinkedIn discovery ─────────────────────────────────────────────────────────

class LinkedInDiscovery:
    """
    Scrapes LinkedIn job search using Playwright.
    Handles login + Easy Apply detection.
    """
    LOGIN_URL  = "https://www.linkedin.com/login"
    SEARCH_URL = "https://www.linkedin.com/jobs/search/"

    def __init__(self):
        self._logged_in = False

    async def _login(self, page: Page):
        log.info("LinkedIn: logging in...")
        await page.goto(self.LOGIN_URL)
        await page.fill("#username", LINKEDIN_EMAIL)
        await page.fill("#password", LINKEDIN_PASSWORD)
        await page.click('[type="submit"]')
        await page.wait_for_timeout(3000)
        self._logged_in = True
        log.info("LinkedIn: logged in")

    async def discover(self, limit: int = 50) -> list[JobPosting]:
        postings: list[JobPosting] = []
        seen = load_seen()

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=BEHAVIOR.headless_browser)
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                )
            )
            page = await ctx.new_page()

            if LINKEDIN_EMAIL:
                await self._login(page)

            for title in SEARCH.job_titles:
                for location in SEARCH.locations:
                    url = (
                        f"{self.SEARCH_URL}?keywords={title.replace(' ', '%20')}"
                        f"&location={location.replace(' ', '%20')}"
                        f"&f_TPR=r{SEARCH.max_days_old * 86400}"   # days → seconds
                        f"&f_WT=2" if SEARCH.remote_ok else ""     # remote filter
                    )
                    await page.goto(url)
                    await page.wait_for_timeout(random.uniform(2000, 4000))

                    # Scroll to load more results
                    for _ in range(3):
                        await page.keyboard.press("End")
                        await page.wait_for_timeout(1500)

                    cards = await page.query_selector_all(".job-card-container")
                    log.info(f"LinkedIn: found {len(cards)} cards for '{title}' in '{location}'")

                    for card in cards[:limit]:
                        try:
                            job = await self._parse_card(page, card, seen)
                            if job:
                                postings.append(job)
                                seen.add(job.id)
                                if len(postings) >= limit:
                                    break
                        except Exception as e:
                            log.warning(f"LinkedIn card parse error: {e}")

                    await asyncio.sleep(random.uniform(
                        BEHAVIOR.min_delay_seconds, BEHAVIOR.max_delay_seconds
                    ))

            await browser.close()

        save_seen(seen)
        return postings

    async def _parse_card(self, page: Page, card, seen: set) -> Optional[JobPosting]:
        title_el = await card.query_selector(".job-card-list__title")
        company_el = await card.query_selector(".job-card-container__company-name")
        location_el = await card.query_selector(".job-card-container__metadata-item")
        link_el = await card.query_selector("a.job-card-list__title")

        title   = (await title_el.inner_text()).strip()   if title_el   else ""
        company = (await company_el.inner_text()).strip() if company_el else ""
        loc     = (await location_el.inner_text()).strip() if location_el else ""
        href    = await link_el.get_attribute("href")     if link_el    else ""

        if not href:
            return None
        url = f"https://www.linkedin.com{href.split('?')[0]}"

        job = JobPosting(
            title=title,
            company=company,
            location=loc,
            remote="remote" in loc.lower(),
            url=url,
            source="linkedin",
        ).compute_id()

        if job.id in seen:
            return None

        # Fetch full description
        await page.goto(url)
        await page.wait_for_timeout(random.uniform(1500, 2500))
        desc_el = await page.query_selector(".jobs-description__content")
        if desc_el:
            job.description = (await desc_el.inner_text()).strip()

        # Detect Easy Apply vs external
        easy_btn = await page.query_selector(".jobs-apply-button--top-card")
        if easy_btn:
            btn_text = (await easy_btn.inner_text()).lower()
            job.apply_method = "easy_apply" if "easy apply" in btn_text else "external"
        else:
            job.apply_method = "external"

        return job


# ── Indeed discovery ───────────────────────────────────────────────────────────

class IndeedDiscovery:
    """
    Uses Indeed's RSS feed (no auth needed) + httpx for job details.
    """
    RSS_URL = "https://www.indeed.com/rss?q={query}&l={location}&fromage={days}&sort=date"

    async def discover(self, limit: int = 50) -> list[JobPosting]:
        postings: list[JobPosting] = []
        seen = load_seen()

        async with httpx.AsyncClient(
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; JobBot/1.0; "
                    "+https://github.com/your-user/jobbot)"
                )
            },
            follow_redirects=True,
            timeout=15,
        ) as client:
            for title in SEARCH.job_titles:
                for location in SEARCH.locations:
                    url = self.RSS_URL.format(
                        query=title.replace(" ", "+"),
                        location=location.replace(" ", "+"),
                        days=SEARCH.max_days_old,
                    )
                    try:
                        resp = await client.get(url)
                        resp.raise_for_status()
                        items = self._parse_rss(resp.text, seen)
                        postings.extend(items[:limit])
                        for j in items:
                            seen.add(j.id)
                    except Exception as e:
                        log.warning(f"Indeed RSS error for '{title}': {e}")

                    await asyncio.sleep(random.uniform(1.5, 3.0))

        save_seen(seen)
        return postings

    def _parse_rss(self, xml: str, seen: set) -> list[JobPosting]:
        soup = BeautifulSoup(xml, "xml")
        jobs = []
        for item in soup.find_all("item"):
            url   = item.find("link").text if item.find("link") else ""
            title = item.find("title").text if item.find("title") else ""
            desc  = item.find("description").text if item.find("description") else ""
            date  = item.find("pubDate").text if item.find("pubDate") else ""
            # Company usually in the title: "Job Title - Company (Location)"
            company, loc = self._extract_company_location(title)

            job = JobPosting(
                title=title.split(" - ")[0].strip(),
                company=company,
                location=loc,
                url=url,
                source="indeed",
                description=BeautifulSoup(desc, "html.parser").get_text(),
                posted_date=date,
                apply_method="external",
            ).compute_id()

            if job.id not in seen:
                jobs.append(job)

        return jobs

    def _extract_company_location(self, raw: str) -> tuple[str, str]:
        # Format: "Title - Company Name (City, ST)"
        parts = raw.split(" - ")
        if len(parts) >= 2:
            rest = parts[-1]
            if "(" in rest:
                company = rest[:rest.index("(")].strip()
                loc = rest[rest.index("(")+1:rest.index(")")].strip()
                return company, loc
            return rest.strip(), ""
        return "", ""


# ── Career page discovery ──────────────────────────────────────────────────────

class CareerPageDiscovery:
    """
    Scrapes Lever / Greenhouse / Ashby ATS public APIs.
    Add target companies to the COMPANIES list.
    """

    # Format: (company_slug, ats_type)
    COMPANIES: list[tuple[str, str]] = [
        # Add your target companies here, e.g.:
        # ("stripe", "greenhouse"),
        # ("linear", "lever"),
        # ("ashby-hq", "ashby"),
    ]

    GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    LEVER_URL      = "https://api.lever.co/v0/postings/{slug}?mode=json"
    ASHBY_URL      = "https://jobs.ashbyhq.com/api/non-user-graphql"

    async def discover(self) -> list[JobPosting]:
        postings: list[JobPosting] = []
        seen = load_seen()

        async with httpx.AsyncClient(timeout=10) as client:
            for slug, ats in self.COMPANIES:
                try:
                    if ats == "greenhouse":
                        jobs = await self._greenhouse(client, slug, seen)
                    elif ats == "lever":
                        jobs = await self._lever(client, slug, seen)
                    elif ats == "ashby":
                        jobs = await self._ashby(client, slug, seen)
                    else:
                        continue
                    postings.extend(jobs)
                    for j in jobs:
                        seen.add(j.id)
                except Exception as e:
                    log.warning(f"Career page error ({slug}, {ats}): {e}")

        save_seen(seen)
        return postings

    async def _greenhouse(self, client, slug: str, seen: set) -> list[JobPosting]:
        resp = await client.get(self.GREENHOUSE_URL.format(slug=slug))
        data = resp.json()
        jobs = []
        for item in data.get("jobs", []):
            loc = item.get("location", {}).get("name", "")
            job = JobPosting(
                title=item.get("title", ""),
                company=slug.replace("-", " ").title(),
                location=loc,
                remote="remote" in loc.lower(),
                url=item.get("absolute_url", ""),
                source="career_page",
                apply_method="external",
            ).compute_id()
            if job.id not in seen:
                jobs.append(job)
        return jobs

    async def _lever(self, client, slug: str, seen: set) -> list[JobPosting]:
        resp = await client.get(self.LEVER_URL.format(slug=slug))
        data = resp.json()
        jobs = []
        for item in data:
            loc = item.get("categories", {}).get("location", "")
            job = JobPosting(
                title=item.get("text", ""),
                company=slug.replace("-", " ").title(),
                location=loc,
                remote="remote" in loc.lower(),
                url=item.get("hostedUrl", ""),
                source="career_page",
                description=BeautifulSoup(
                    item.get("descriptionPlain", ""), "html.parser"
                ).get_text(),
                apply_method="external",
            ).compute_id()
            if job.id not in seen:
                jobs.append(job)
        return jobs

    async def _ashby(self, client, slug: str, seen: set) -> list[JobPosting]:
        # Ashby uses GraphQL
        query = """
        query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
          jobBoard: publishedJobBoard(organizationHostedJobsPageName: $organizationHostedJobsPageName) {
            jobPostings { id title locationName isRemote externalLink }
          }
        }"""
        resp = await client.post(
            self.ASHBY_URL,
            json={"query": query, "variables": {"organizationHostedJobsPageName": slug}},
        )
        data = resp.json()
        jobs = []
        for item in data.get("data", {}).get("jobBoard", {}).get("jobPostings", []):
            job = JobPosting(
                title=item.get("title", ""),
                company=slug.replace("-", " ").title(),
                location=item.get("locationName", ""),
                remote=item.get("isRemote", False),
                url=item.get("externalLink", ""),
                source="career_page",
                apply_method="external",
            ).compute_id()
            if job.id not in seen:
                jobs.append(job)
        return jobs


# ── Unified runner ─────────────────────────────────────────────────────────────

async def discover_all(limit_per_source: int = 30) -> list[JobPosting]:
    """Run all enabled discovery sources concurrently."""
    tasks = []

    if BEHAVIOR.use_linkedin and LINKEDIN_EMAIL:
        tasks.append(LinkedInDiscovery().discover(limit=limit_per_source))
    if BEHAVIOR.use_indeed:
        tasks.append(IndeedDiscovery().discover(limit=limit_per_source))
    if BEHAVIOR.use_career_pages:
        tasks.append(CareerPageDiscovery().discover())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_jobs: list[JobPosting] = []
    for r in results:
        if isinstance(r, Exception):
            log.error(f"Discovery error: {r}")
        else:
            all_jobs.extend(r)

    log.info(f"Discovery complete. {len(all_jobs)} raw postings found.")
    return all_jobs
