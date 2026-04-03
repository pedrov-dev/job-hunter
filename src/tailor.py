"""
src/tailor.py
-------------
Two responsibilities:
  1. Score job postings against your profile (match_score 0-100).
  2. Select the best pre-written resume variant for the role and optionally
     write a cover letter.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import unicodedata
from pathlib import Path

from openai import OpenAI

from config import (
    AI,
    BASE_DIR,
    OPENAI_API_KEY,
    RESUME_DIR,
    RESUMES,
    SEARCH,
    ResumeVariant,
    SearchCriteria,
)
from src.discovery import JobPosting

log = logging.getLogger("jobbot.tailor")
RESUME_LIBRARY = RESUMES.variants
LEGACY_RESUME_PATH = RESUME_DIR / "master_resume.pdf"


def _ascii_lower(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii").lower()


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _ascii_lower(text)).strip()


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9+#.-]{3,}", text.lower())}


def _default_resume_variant() -> ResumeVariant:
    for variant in RESUME_LIBRARY:
        if variant.is_default:
            return variant
    if RESUME_LIBRARY:
        return RESUME_LIBRARY[0]
    return ResumeVariant(
        key="master_resume",
        filename="master_resume.pdf",
        is_default=True,
    )


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as err:
        raise ImportError("Install with: pip install pypdf") from err

    reader = PdfReader(str(path))
    extracted_pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(filter(None, extracted_pages)).strip()
    if text:
        return text

    log.warning(
        "Resume PDF at %s has no extractable text; using filename as fallback context.",
        path,
    )
    return path.stem.replace("_", " ")


def resolve_resume_path(variant: ResumeVariant) -> Path:
    candidate_path = RESUME_DIR / variant.filename
    if candidate_path.exists():
        return candidate_path

    default_variant = _default_resume_variant()
    default_path = RESUME_DIR / default_variant.filename
    if variant.filename != default_variant.filename and default_path.exists():
        log.warning(
            "Resume variant '%s' not found at %s; falling back to default.",
            variant.key,
            candidate_path,
        )
        return default_path

    if LEGACY_RESUME_PATH.exists():
        log.warning(
            "Resume variant '%s' not found; using fallback %s.",
            variant.key,
            LEGACY_RESUME_PATH.name,
        )
        return LEGACY_RESUME_PATH

    raise FileNotFoundError(
        "No resume PDF files found. Add the files listed in config.RESUMES.variants "
        f"under {RESUME_DIR} or create {LEGACY_RESUME_PATH.name}."
    )


def load_resume_text(variant: ResumeVariant) -> str:
    return _extract_pdf_text(resolve_resume_path(variant))


def score_resume_variant(job: JobPosting, variant: ResumeVariant) -> int:
    title_text = _normalize(job.title)
    context = _normalize(" ".join(filter(None, [job.title, job.company, job.description])))
    score = 0

    for keyword in variant.title_keywords:
        normalized = _normalize(keyword)
        if not normalized:
            continue
        if normalized in title_text:
            score += 5
        elif normalized in context:
            score += 2

    for industry in variant.industries:
        normalized = _normalize(industry)
        if normalized and normalized in context:
            score += 3

    if variant.is_default:
        score += 1
    return score


def select_resume_variant(job: JobPosting) -> tuple[ResumeVariant, str]:
    if not RESUME_LIBRARY:
        variant = _default_resume_variant()
        return variant, load_resume_text(variant)

    best_variant = max(RESUME_LIBRARY, key=lambda variant: score_resume_variant(job, variant))
    default_score = 1 if best_variant.is_default else 0
    if score_resume_variant(job, best_variant) <= default_score:
        best_variant = _default_resume_variant()

    return best_variant, load_resume_text(best_variant)


MEXICO_LOCATION_MARKERS = (
    "mexico",
    "mexico city",
    "ciudad de mexico",
    "cdmx",
    "guadalajara",
    "monterrey",
)

SALARY_HINT_PATTERN = re.compile(
    r"\$|usd|mxn|salary|compensation|pay|a(?:n|ñ)o|year|month|mes|hour|hora",
    re.IGNORECASE,
)
SALARY_NUMBER_PATTERN = re.compile(r"\d[\d,.]*(?:\.\d+)?\s*[kKmM]?")


def _salary_period_multiplier(text: str) -> int:
    normalized = _ascii_lower(text)
    if any(token in normalized for token in ("per hour", "/hour", "hourly", "por hora")):
        return 2080
    if any(token in normalized for token in ("per day", "/day", "daily", "por dia")):
        return 260
    if any(token in normalized for token in ("per week", "/week", "weekly", "por semana")):
        return 52
    if any(
        token in normalized
        for token in ("per month", "/month", "monthly", "al mes", "por mes", "mensual")
    ):
        return 12
    return 1


def _parse_salary_number(raw: str) -> int | None:
    cleaned = raw.strip().lower().replace(" ", "")
    multiplier = 1
    if cleaned.endswith("k"):
        multiplier = 1_000
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000
        cleaned = cleaned[:-1]

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") >= 1 and all(part.isdigit() for part in cleaned.split(".")):
        if any(len(part) == 3 for part in cleaned.split(".")[1:]):
            cleaned = cleaned.replace(".", "")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
        return None


def _infer_salary_currency(job: JobPosting, text: str, criteria: SearchCriteria) -> str:
    normalized_text = _ascii_lower(text)
    normalized_location = _ascii_lower(job.location)

    if re.search(r"\bmxn\b|mx\$|pesos?\b", normalized_text):
        return "MXN"
    if re.search(r"\busd\b|us\$|dollars?\b", normalized_text):
        return "USD"
    if "$" in text and any(marker in normalized_location for marker in MEXICO_LOCATION_MARKERS):
        return "MXN"
    return criteria.currency.upper()


def extract_annual_salary(
    job: JobPosting,
    criteria: SearchCriteria = SEARCH,
) -> tuple[str, int] | None:
    salary_blob = " ".join(part for part in (job.salary_text, job.description) if part).strip()
    if not salary_blob or not SALARY_HINT_PATTERN.search(salary_blob):
        return None

    amounts = [
        parsed
        for match in SALARY_NUMBER_PATTERN.finditer(salary_blob)
        if (parsed := _parse_salary_number(match.group())) is not None and parsed >= 100
    ]
    if not amounts:
        return None

    annual_amount = max(amounts) * _salary_period_multiplier(salary_blob)
    currency = _infer_salary_currency(job, salary_blob, criteria)
    return currency, annual_amount


def job_meets_salary_threshold(
    job: JobPosting,
    criteria: SearchCriteria = SEARCH,
) -> bool:
    salary_info = extract_annual_salary(job, criteria)
    if salary_info is None:
        return True

    currency, annual_amount = salary_info
    threshold = criteria.min_salary_mxn if currency == "MXN" else criteria.min_salary_usd
    return annual_amount >= threshold


# ── OpenAI client ──────────────────────────────────────────────────────────────

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ── Scoring ────────────────────────────────────────────────────────────────────

SCORE_SYSTEM = """You are a job-fit scoring assistant.
Given a candidate's resume and a job description, return a JSON object with:
  - score (int 0-100): overall fit
  - reasons (list[str]): top 3 reasons for the score
  - missing (list[str]): top skills/experience the candidate lacks
  - highlights (list[str]): strongest matching points

Return only valid JSON, no preamble."""


def heuristic_score_job(job_description: str, resume: str) -> dict:
    """Lightweight offline scorer used when the AI provider is unavailable."""
    job_tokens = _tokenize(job_description)
    resume_tokens = _tokenize(resume)

    overlap = sorted(job_tokens & resume_tokens)
    missing = sorted(job_tokens - resume_tokens)
    score = 35 if not overlap else min(95, 45 + len(overlap[:12]) * 4)

    reasons = [
        (
            "Strong keyword overlap with the selected resume."
            if overlap
            else "Limited keyword overlap."
        ),
        (
            f"Top matches: {', '.join(overlap[:3])}"
            if overlap
            else "Using default scoring fallback."
        ),
    ]
    highlights = overlap[:5]

    return {
        "score": score,
        "reasons": reasons,
        "missing": missing[:5],
        "highlights": highlights,
    }


def score_job(job_description: str, resume: str) -> dict:
    """Returns {score, reasons, missing, highlights}."""
    try:
        resp = get_client().chat.completions.create(
            model=AI.model,
            messages=[
                {"role": "system", "content": SCORE_SYSTEM},
                {
                    "role": "user",
                    "content": f"## RESUME\n{resume}\n\n## JOB DESCRIPTION\n{job_description}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        log.warning("AI scoring unavailable (%s); using heuristic score.", exc)
        return heuristic_score_job(job_description, resume)


# ── Cover letter generation ────────────────────────────────────────────────────

COVER_LETTER_SYSTEM = f"""You are an expert cover letter writer.
Write a compelling, specific cover letter for the role.

Tone: {AI.cover_letter_tone}
Style: concise and direct — max 3 short paragraphs
Rules:
- Reference 2-3 specific, concrete things from the JD
- Connect candidate's past wins to the company's current needs
- No generic opener ("I am writing to apply for...") — start with a hook
- No sign-off block — just the body paragraphs
- Return only the letter body, in plain text"""


def _fallback_cover_letter(company: str, title: str) -> str:
    return (
        f"The {title} role at {company} stands out because it blends strategy with execution.\n\n"
        "My background is strongest in applying AI and automation to real operating workflows, "
        "and I enjoy turning ambiguous opportunities into practical systems teams actually use.\n\n"
        "I would welcome the chance to discuss how that experience could help your team deliver "
        "meaningful results quickly."
    )


def write_cover_letter(job_description: str, resume: str, company: str, title: str) -> str:
    """Returns a cover letter body as plain text."""
    try:
        resp = get_client().chat.completions.create(
            model=AI.model,
            messages=[
                {"role": "system", "content": COVER_LETTER_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"## ROLE\n{title} at {company}\n\n"
                        f"## JOB DESCRIPTION\n{job_description}\n\n"
                        f"## MY RESUME\n{resume}"
                    ),
                },
            ],
            temperature=0.7,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        log.warning("Cover letter generation unavailable (%s); using fallback template.", exc)
        return _fallback_cover_letter(company, title)


# ── Unified resume-selection pipeline ──────────────────────────────────────────


def process_job(job: JobPosting) -> dict | None:
    """
    Select resume → score → filter → prepare submission assets.
    Returns a dict ready for submission, or None if below threshold.
    """
    salary_info = extract_annual_salary(job)
    if salary_info is not None:
        currency, annual_amount = salary_info
        threshold = SEARCH.min_salary_mxn if currency == "MXN" else SEARCH.min_salary_usd
        if annual_amount < threshold:
            log.info("  → Skipped (salary %s %s < %s)", annual_amount, currency, threshold)
            return None

    variant, selected_resume = select_resume_variant(job)
    selected_resume_pdf = resolve_resume_path(variant)

    log.info("Scoring: %s @ %s [resume=%s]", job.title, job.company, variant.key)
    score_result = score_job(job.description, selected_resume)
    job.match_score = score_result.get("score", 0)

    if job.match_score < AI.min_match_score:
        log.info("  → Skipped (score %s < %s)", job.match_score, AI.min_match_score)
        return None

    log.info("  → Score %s. Using resume '%s'.", job.match_score, variant.key)

    cover_letter = ""
    if AI.include_cover_letter:
        cover_letter = write_cover_letter(
            job.description,
            selected_resume,
            job.company,
            job.title,
        )

    out_dir = BASE_DIR / "output" / job.id
    out_dir.mkdir(parents=True, exist_ok=True)
    output_resume_pdf = out_dir / "resume.pdf"
    shutil.copy2(selected_resume_pdf, output_resume_pdf)
    (out_dir / "resume.txt").write_text(selected_resume, encoding="utf-8")
    (out_dir / "cover_letter.txt").write_text(cover_letter, encoding="utf-8")
    (out_dir / "job.json").write_text(
        json.dumps(
            {
                **job.__dict__,
                "score_details": score_result,
                "resume_variant": variant.key,
                "resume_file": selected_resume_pdf.name,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "job": job,
        "tailored_resume": selected_resume,
        "selected_resume": selected_resume,
        "resume_variant": variant.key,
        "resume_pdf": output_resume_pdf,
        "cover_letter": cover_letter,
        "score": job.match_score,
        "score_details": score_result,
        "output_dir": str(out_dir),
    }
