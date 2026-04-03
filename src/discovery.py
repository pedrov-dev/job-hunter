"""
src/discovery.py
----------------
Discovers job postings from multiple sources.
Returns a unified list of JobPosting objects.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

from config import BEHAVIOR, DATA_DIR, SEARCH, SWEEPS

from .companies import COMPANIES, build_company_list

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
    source: str = ""               # "indeed" | "career_page" | "email"
    description: str = ""
    salary_text: str = ""
    posted_date: str = ""
    apply_method: str = ""         # "external" | "email"
    match_score: int = 0
    discovered_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

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

    def _parse_rss(self, xml: str, seen: set[str]) -> list[JobPosting]:
        soup = BeautifulSoup(xml, "xml")
        jobs: list[JobPosting] = []
        for item in soup.find_all("item"):
            link_tag = item.find("link")
            title_tag = item.find("title")
            description_tag = item.find("description")
            pub_date_tag = item.find("pubDate")

            url = link_tag.text if link_tag else ""
            title = title_tag.text if title_tag else ""
            desc = description_tag.text if description_tag else ""
            date = pub_date_tag.text if pub_date_tag else ""
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


def get_company_targets_for_tier(sweep_tier: str | None = None) -> list[tuple[str, str]]:
    group_names = SWEEPS.resolve_groups(sweep_tier)
    company_limit = SWEEPS.get_company_limit(sweep_tier)
    return build_company_list(group_names, limit=company_limit)


class CareerPageDiscovery:
    """
    Scrapes Lever / Greenhouse / Ashby ATS public APIs.
    Company targets are configured in `src/companies.py`.
    """

    # Format: (company_slug, ats_type)
    COMPANIES: list[tuple[str, str]] = COMPANIES

    GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    LEVER_URL      = "https://api.lever.co/v0/postings/{slug}?mode=json"
    ASHBY_URL      = "https://jobs.ashbyhq.com/api/non-user-graphql"

    def __init__(
        self,
        company_targets: list[tuple[str, str]] | None = None,
        sweep_tier: str | None = None,
    ) -> None:
        self.sweep_tier = SWEEPS.resolve_tier(sweep_tier)
        self.company_targets = company_targets or get_company_targets_for_tier(
            self.sweep_tier,
        )

    async def discover(self) -> list[JobPosting]:
        postings: list[JobPosting] = []
        seen = load_seen()

        log.info(
            "Career sweep '%s': checking %s company pages",
            self.sweep_tier,
            len(self.company_targets),
        )

        async with httpx.AsyncClient(timeout=10) as client:
            for slug, ats in self.company_targets:
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
        query ApiJobBoardWithTeams(
          $organizationHostedJobsPageName: String!
        ) {
          jobBoard: publishedJobBoard(
            organizationHostedJobsPageName: $organizationHostedJobsPageName
          ) {
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

async def discover_all(
    limit_per_source: int = 30,
    sweep_tier: str | None = None,
) -> list[JobPosting]:
    """Run all enabled discovery sources concurrently."""
    tasks = []
    resolved_tier = SWEEPS.resolve_tier(sweep_tier)

    if BEHAVIOR.use_indeed:
        tasks.append(IndeedDiscovery().discover(limit=limit_per_source))
    if BEHAVIOR.use_career_pages:
        tasks.append(CareerPageDiscovery(sweep_tier=resolved_tier).discover())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_jobs: list[JobPosting] = []
    for r in results:
        if isinstance(r, BaseException):
            log.error(f"Discovery error: {r}")
        else:
            all_jobs.extend(r)

    log.info(f"Discovery complete. {len(all_jobs)} raw postings found.")
    return all_jobs
