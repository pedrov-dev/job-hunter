"""
core/tailor.py
--------------
Two responsibilities:
  1. Score job postings against your profile (match_score 0-100).
  2. Generate tailored resume bullets + cover letter for approved jobs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from openai import OpenAI

from config import AI, SEARCH, BASE_DIR, RESUME_DIR

log = logging.getLogger("jobbot.tailor")

# ── Load master resume ─────────────────────────────────────────────────────────
# Save your resume as resumes/master_resume.md (plain text / Markdown)
MASTER_RESUME_PATH = RESUME_DIR / "master_resume.md"

def get_master_resume() -> str:
    if MASTER_RESUME_PATH.exists():
        return MASTER_RESUME_PATH.read_text()
    raise FileNotFoundError(
        f"Master resume not found at {MASTER_RESUME_PATH}. "
        "Create resumes/master_resume.md with your full resume in plain text."
    )

# ── OpenAI client ──────────────────────────────────────────────────────────────
from config import OPENAI_API_KEY
_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
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

def score_job(job_description: str, resume: str) -> dict:
    """Returns {score, reasons, missing, highlights}."""
    resp = get_client().chat.completions.create(
        model=AI.model,
        messages=[
            {"role": "system", "content": SCORE_SYSTEM},
            {"role": "user", "content": (
                f"## RESUME\n{resume}\n\n"
                f"## JOB DESCRIPTION\n{job_description}"
            )},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Score parse failed, returning default.")
        return {"score": 0, "reasons": [], "missing": [], "highlights": []}


# ── Resume tailoring ───────────────────────────────────────────────────────────

TAILOR_SYSTEM = f"""You are an expert resume writer.
Given a master resume and a job description, produce a tailored version of the resume 
optimized for this specific role. 

Rules:
- Keep everything truthful — do not invent experience
- Reorder bullet points to surface the most relevant experience first
- Swap in keywords from the JD where semantically equivalent
- Keep to {AI.max_resume_pages} page(s) max
- Return only the resume in Markdown format, no commentary"""

def tailor_resume(job_description: str, resume: str, company: str, title: str) -> str:
    """Returns a tailored resume as Markdown."""
    resp = get_client().chat.completions.create(
        model=AI.model,
        messages=[
            {"role": "system", "content": TAILOR_SYSTEM},
            {"role": "user", "content": (
                f"## TARGET ROLE\n{title} at {company}\n\n"
                f"## JOB DESCRIPTION\n{job_description}\n\n"
                f"## MY MASTER RESUME\n{resume}"
            )},
        ],
        temperature=0.4,
    )
    return resp.choices[0].message.content.strip()


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

def write_cover_letter(job_description: str, resume: str, company: str, title: str) -> str:
    """Returns a cover letter body as plain text."""
    resp = get_client().chat.completions.create(
        model=AI.model,
        messages=[
            {"role": "system", "content": COVER_LETTER_SYSTEM},
            {"role": "user", "content": (
                f"## ROLE\n{title} at {company}\n\n"
                f"## JOB DESCRIPTION\n{job_description}\n\n"
                f"## MY RESUME\n{resume}"
            )},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


# ── Unified tailor pipeline ────────────────────────────────────────────────────

from core.discovery import JobPosting

def process_job(job: JobPosting) -> dict | None:
    """
    Score → filter → tailor.
    Returns a dict ready for submission, or None if below threshold.
    """
    resume = get_master_resume()

    # 1. Score
    log.info(f"Scoring: {job.title} @ {job.company}")
    score_result = score_job(job.description, resume)
    job.match_score = score_result.get("score", 0)

    if job.match_score < AI.min_match_score:
        log.info(f"  → Skipped (score {job.match_score} < {AI.min_match_score})")
        return None

    log.info(f"  → Score {job.match_score}. Tailoring...")

    # 2. Tailor resume
    tailored_resume = tailor_resume(job.description, resume, job.company, job.title)

    # 3. Cover letter
    cover_letter = ""
    if AI.include_cover_letter:
        cover_letter = write_cover_letter(job.description, tailored_resume, job.company, job.title)

    # 4. Save to disk
    out_dir = BASE_DIR / "output" / job.id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resume.md").write_text(tailored_resume)
    (out_dir / "cover_letter.txt").write_text(cover_letter)
    (out_dir / "job.json").write_text(json.dumps({
        **job.__dict__,
        "score_details": score_result,
    }, indent=2))

    return {
        "job": job,
        "tailored_resume": tailored_resume,
        "cover_letter": cover_letter,
        "score": job.match_score,
        "score_details": score_result,
        "output_dir": str(out_dir),
    }
