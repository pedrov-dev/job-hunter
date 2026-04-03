"""
tracking/tracker.py
-------------------
Persists all application state to a local SQLite database.
Generates the JSON feed consumed by the HTML dashboard.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from config import DATA_DIR
from core.discovery import JobPosting
from submissions.submitter import SubmissionResult

log = logging.getLogger("jobbot.tracking")

DB_PATH   = DATA_DIR / "applications.db"
FEED_PATH = DATA_DIR / "dashboard_feed.json"


# ── Database setup ─────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id              TEXT PRIMARY KEY,
    title           TEXT,
    company         TEXT,
    location        TEXT,
    remote          INTEGER,
    url             TEXT,
    source          TEXT,
    apply_method    TEXT,
    match_score     INTEGER,
    status          TEXT DEFAULT 'applied',
    applied_at      TEXT,
    last_updated    TEXT,
    cover_letter    TEXT,
    tailored_resume TEXT,
    resume_variant  TEXT,
    score_details   TEXT,
    followup_sent   INTEGER DEFAULT 0,
    followup_date   TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT,
    event_type  TEXT,
    detail      TEXT,
    created_at  TEXT
);
"""

@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str):
    existing = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "applications", "resume_variant", "TEXT DEFAULT ''")
    log.info(f"DB initialized at {DB_PATH}")


# ── Write operations ───────────────────────────────────────────────────────────

def record_application(
    job: JobPosting,
    result: SubmissionResult,
    tailored_resume: str = "",
    cover_letter: str = "",
    score_details: dict | None = None,
    resume_variant: str = "",
):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO applications
              (id, title, company, location, remote, url, source, apply_method,
               match_score, status, applied_at, last_updated,
               cover_letter, tailored_resume, resume_variant, score_details)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            job.id, job.title, job.company, job.location, int(job.remote),
            job.url, job.source, job.apply_method, job.match_score,
            "applied" if result.success else "error",
            now, now,
            cover_letter, tailored_resume, resume_variant,
            json.dumps(score_details or {}),
        ))

        conn.execute("""
            INSERT INTO events (job_id, event_type, detail, created_at) VALUES (?,?,?,?)
        """, (
            job.id,
            "applied" if result.success else "error",
            result.message or result.error,
            now,
        ))

    log.info(f"Recorded: {job.title} @ {job.company} [{result.method}] success={result.success}")
    _rebuild_feed()


def update_status(job_id: str, status: str, notes: str = ""):
    """Update application status (e.g. 'interviewing', 'rejected', 'offer')."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            UPDATE applications SET status=?, last_updated=?, notes=? WHERE id=?
        """, (status, now, notes, job_id))
        conn.execute("""
            INSERT INTO events (job_id, event_type, detail, created_at) VALUES (?,?,?,?)
        """, (job_id, f"status_change:{status}", notes, now))
    _rebuild_feed()


def mark_followup_sent(job_id: str):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute("""
            UPDATE applications SET followup_sent=1, followup_date=? WHERE id=?
        """, (now, job_id))


# ── Read operations ────────────────────────────────────────────────────────────

def get_all_applications() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_pending_followups(after_days: int = 7) -> list[dict]:
    """Return applications that haven't received a follow-up and are >N days old."""
    cutoff = (datetime.utcnow() - timedelta(days=after_days)).isoformat()
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT * FROM applications
            WHERE status = 'applied'
              AND followup_sent = 0
              AND applied_at < ?
        """, (cutoff,)).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        applied = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status='applied'"
        ).fetchone()[0]
        interview = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status='interviewing'"
        ).fetchone()[0]
        offers = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status='offer'"
        ).fetchone()[0]
        rejected = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status='rejected'"
        ).fetchone()[0]
        errors = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status='error'"
        ).fetchone()[0]
        avg_score = conn.execute(
            "SELECT AVG(match_score) FROM applications"
        ).fetchone()[0] or 0

        by_source = {}
        for row in conn.execute(
            "SELECT source, COUNT(*) as n FROM applications GROUP BY source"
        ).fetchall():
            by_source[row["source"]] = row["n"]

        recent = conn.execute("""
            SELECT title, company, status, applied_at, match_score
            FROM applications ORDER BY applied_at DESC LIMIT 10
        """).fetchall()

    return {
        "total": total,
        "applied": applied,
        "interviewing": interview,
        "offers": offers,
        "rejected": rejected,
        "errors": errors,
        "avg_score": round(avg_score, 1),
        "by_source": by_source,
        "recent": [dict(r) for r in recent],
    }


# ── Dashboard feed ─────────────────────────────────────────────────────────────

def _rebuild_feed():
    """Rebuild the JSON file that powers the HTML dashboard."""
    stats = get_stats()
    apps  = get_all_applications()
    feed  = {
        "generated_at": datetime.utcnow().isoformat(),
        "stats": stats,
        "applications": apps,
    }
    FEED_PATH.write_text(json.dumps(feed, indent=2))


# ── Follow-up email sender ─────────────────────────────────────────────────────

def send_followup_emails(dry_run: bool = False):
    """Send follow-up emails for stale applications."""
    import smtplib
    from email.mime.text import MIMEText

    from config import BEHAVIOR, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

    pending = get_pending_followups(after_days=BEHAVIOR.followup_after_days)
    log.info(f"Follow-ups pending: {len(pending)}")

    for app in pending:
        body = (
            f"Dear Hiring Team,\n\n"
            f"I wanted to follow up on my application for the {app['title']} "
            f"role at {app['company']}. I remain very interested and would "
            f"love to discuss how I can contribute.\n\n"
            f"Best regards,\nPedro Ventura"
        )
        if dry_run:
            log.info(f"  [DRY RUN] Would send follow-up for {app['title']} @ {app['company']}")
            continue

        try:
            msg = MIMEText(body)
            msg["From"]    = SMTP_USER
            msg["To"]      = SMTP_USER   # Real: look up recruiter email in app record
            msg["Subject"] = f"Following up — {app['title']} application"

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

            mark_followup_sent(app["id"])
            log.info(f"  Follow-up sent: {app['title']} @ {app['company']}")

        except Exception as e:
            log.error(f"  Follow-up failed for {app['id']}: {e}")
