"""
core/tailor.py
--------------
Two responsibilities:
  1. Score job postings against your profile (match_score 0-100).
  2. Select the best pre-written resume variant for the role and optionally
     write a cover letter.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from openai import OpenAI

from config import AI, BASE_DIR, OPENAI_API_KEY, RESUME_DIR, RESUMES, ResumeVariant
from core.discovery import JobPosting

log = logging.getLogger("jobbot.tailor")
RESUME_LIBRARY = RESUMES.variants
LEGACY_RESUME_PATH = RESUME_DIR / "master_resume.md"


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


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
        filename="master_resume.md",
        is_default=True,
    )


def _read_resume_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_resume_text(variant: ResumeVariant) -> str:
    candidate_path = RESUME_DIR / variant.filename
    if candidate_path.exists():
        return _read_resume_text(candidate_path)

    default_variant = _default_resume_variant()
    default_path = RESUME_DIR / default_variant.filename
    if variant.filename != default_variant.filename and default_path.exists():
        log.warning(
            "Resume variant '%s' not found at %s; falling back to default.",
            variant.key,
            candidate_path,
        )
        return _read_resume_text(default_path)

    if LEGACY_RESUME_PATH.exists():
        log.warning(
            "Resume variant '%s' not found; using legacy master_resume.md.",
            variant.key,
        )
        return _read_resume_text(LEGACY_RESUME_PATH)

    raise FileNotFoundError(
        "No resume files found. Add the files listed in config.RESUMES.variants "
        f"under {RESUME_DIR} or create {LEGACY_RESUME_PATH.name}."
    )


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
    variant, selected_resume = select_resume_variant(job)

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
    (out_dir / "resume.md").write_text(selected_resume, encoding="utf-8")
    (out_dir / "cover_letter.txt").write_text(cover_letter, encoding="utf-8")
    (out_dir / "job.json").write_text(
        json.dumps(
            {
                **job.__dict__,
                "score_details": score_result,
                "resume_variant": variant.key,
                "resume_file": variant.filename,
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
        "cover_letter": cover_letter,
        "score": job.match_score,
        "score_details": score_result,
        "output_dir": str(out_dir),
    }
