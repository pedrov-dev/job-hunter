"""
JobBot — Autonomous Job Application System
==========================================
Edit this file to configure your job search.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DATA_DIR   = BASE_DIR / "data"
RESUME_DIR = BASE_DIR / "resumes"
LOG_DIR    = BASE_DIR / "logs"

for d in [DATA_DIR, RESUME_DIR, LOG_DIR]:
    d.mkdir(exist_ok=True)

# ── API Keys (set via environment variables or .env file) ─────────────────────

load_dotenv()

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Gmail/SMTP (for email-based applications)
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Use an App Password for Gmail


# ── Job Search Criteria ────────────────────────────────────────────────────────
@dataclass
class SearchCriteria:
    # What you're looking for
    job_titles: list[str] = field(default_factory=lambda: [
        "AI Consultant",
        "AI Strategy Lead",
        "Head of AI",
        "Machine Learning Consultant",
        "Automation Consultant",
    ])
    keywords_required: list[str] = field(default_factory=lambda: [
        "AI", "automation", "LLM"
    ])
    keywords_excluded: list[str] = field(default_factory=lambda: [
        "internship", "junior", "entry level"
    ])

    # Location
    locations: list[str] = field(default_factory=lambda: [
        "Mexico City", "Remote", "CDMX"
    ])
    remote_ok: bool = True

    # Compensation
    min_salary_usd: int = 60_000
    currency: str = "USD"

    # Company filters
    company_sizes: list[str] = field(default_factory=lambda: [
        "51-200", "201-500", "501-1000", "1001-5000"
    ])
    industries_preferred: list[str] = field(default_factory=lambda: [
        "Technology", "Financial Services", "Healthcare", "Consulting"
    ])
    companies_blacklisted: list[str] = field(default_factory=list)

    # Job post freshness
    max_days_old: int = 7


@dataclass(frozen=True)
class ResumeVariant:
    key: str
    filename: str
    title_keywords: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    is_default: bool = False


@dataclass
class ResumeConfig:
    variants: list[ResumeVariant] = field(default_factory=lambda: [
        ResumeVariant(
            key="general_ai",
            filename="general_ai.pdf",
            title_keywords=[
                "ai consultant",
                "machine learning consultant",
                "llm engineer",
            ],
            industries=["technology", "saas", "consulting"],
            is_default=True,
        ),
        ResumeVariant(
            key="ai_leadership",
            filename="ai_leadership.pdf",
            title_keywords=[
                "head of ai",
                "ai strategy lead",
                "director of ai",
                "ai lead",
            ],
            industries=["financial services", "fintech", "healthcare"],
        ),
    ])


# ── AI Model Config ────────────────────────────────────────────────────────────
@dataclass
class AIConfig:
    # Provider: "openai" or "anthropic"
    provider: str = "openai"
    model: str = "gpt-4o"

    # Optional cover letter behavior
    cover_letter_tone: str = "direct"    # "direct" | "warm" | "formal"
    include_cover_letter: bool = True

    # Scoring threshold (0–100). Jobs below this are skipped.
    min_match_score: int = 65


# ── Application Behavior ───────────────────────────────────────────────────────
@dataclass
class BehaviorConfig:
    # How many applications to submit per run
    max_applications_per_run: int = 10

    # Channels to use (set False to disable one)
    use_indeed:       bool = True
    use_career_pages: bool = True
    use_email:        bool = True

    # Browser behavior (mimics human pacing)
    min_delay_seconds: float = 3.0
    max_delay_seconds: float = 9.0
    headless_browser: bool = True   # Set False to watch the browser

    # Follow-up emails
    send_followups: bool = True
    followup_after_days: int = 7


# ── Instantiate defaults ───────────────────────────────────────────────────────
SEARCH   = SearchCriteria()
RESUMES  = ResumeConfig()
AI       = AIConfig()
BEHAVIOR = BehaviorConfig()
