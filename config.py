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

# Gmail/SMTP (for email-based applications)
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Use an App Password for Gmail


# ── Job Search Criteria ────────────────────────────────────────────────────────
@dataclass
class SearchCriteria:
    job_titles: list[str] = field(default_factory=lambda: [
        "AI Engineer",
        "AI Solutions Architect",
        "LLM Engineer",
        "GenAI Product Engineer",
        "Conversational AI Engineer",
        "Machine Learning Consultant",
        "Automation Consultant",
        "AI Product Manager",
    ])
    keywords_required: list[str] = field(default_factory=lambda: [
        "AI",
        "automation",
        "LLM",
        "GenAI",
        "RAG",
        "agents",
        "Python",
        "OpenAI",
    ])
    keywords_excluded: list[str] = field(default_factory=lambda: [
        "internship",
        "unpaid",
        "research scientist",
        "entry level",
    ])

    locations: list[str] = field(default_factory=lambda: [
        "Mexico City",
        "CDMX",
        "Ciudad de México",
        "Remote",
        "Hybrid",
        "Latin America",
    ])
    remote_ok: bool = True

    # Annual compensation floors. Mexico-based roles can be filtered in MXN.
    min_salary_usd: int = 80000
    min_salary_mxn: int = 600000
    currency: str = "USD"

    company_sizes: list[str] = field(default_factory=lambda: [
        "11-50",
        "51-200",
        "201-500",
        "501-1000",
        "1001-5000",
        "5001-10000",
    ])
    industries_preferred: list[str] = field(default_factory=lambda: [
        "Technology",
        "SaaS",
        "Fintech",
        "Financial Services",
        "Healthcare",
        "Consulting",
        "EdTech",
        "E-commerce",
        "Insurtech",
    ])
    companies_blacklisted: list[str] = field(default_factory=list)

    max_days_old: int = 7


@dataclass
class SweepConfig:
    active_tier: str = "daily"
    tier_descriptions: dict[str, str] = field(default_factory=lambda: {
        "daily": "CDMX-presence + LATAM-remote companies (~30)",
        "weekly": "AI-native startups + global remote-friendly companies (~50)",
        "monthly": "Relocation/visa sponsors + enterprise platforms (~40)",
        "all": "Full sweep across every priority bucket",
    })
    tier_groups: dict[str, list[str]] = field(default_factory=lambda: {
        "daily": ["cdmx_presence", "latam_remote"],
        "weekly": ["ai_native_startups", "global_remote_friendly"],
        "monthly": ["relocation_visa", "enterprise_platforms"],
        "all": [
            "cdmx_presence",
            "latam_remote",
            "ai_native_startups",
            "global_remote_friendly",
            "relocation_visa",
            "enterprise_platforms",
        ],
    })
    cadence_days: dict[str, int] = field(default_factory=lambda: {
        "daily": 1,
        "weekly": 7,
        "monthly": 30,
    })
    company_limits: dict[str, int] = field(default_factory=lambda: {
        "daily": 30,
        "weekly": 50,
        "monthly": 40,
        "all": 999,
    })

    def resolve_tier(self, tier: str | None = None) -> str:
        candidate = (tier or self.active_tier).strip().lower()
        return candidate if candidate in self.tier_groups else self.active_tier

    def resolve_groups(self, tier: str | None = None) -> list[str]:
        return self.tier_groups[self.resolve_tier(tier)]

    def describe_tier(self, tier: str | None = None) -> str:
        return self.tier_descriptions[self.resolve_tier(tier)]

    def get_company_limit(self, tier: str | None = None) -> int:
        return self.company_limits[self.resolve_tier(tier)]


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
    provider: str = "openai"
    model: str = "gpt-5.4-nano"

    # Optional cover letter behavior
    cover_letter_tone: str = "direct"    # "direct" | "warm" | "formal"
    include_cover_letter: bool = False

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
SWEEPS   = SweepConfig()
RESUMES  = ResumeConfig()
AI       = AIConfig()
BEHAVIOR = BehaviorConfig()
