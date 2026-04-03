"""
main.py
-------
JobBot entry point. Run this to start a full application cycle:

  python main.py                 # full run
  python main.py --dry-run       # score & select resumes but don't submit
  python main.py --followups     # only send follow-up emails
  python main.py --stats         # print stats and exit
  python main.py --limit 5       # apply to max 5 jobs
  python main.py --dashboard     # launch the live dashboard
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/jobbot.log"),
    ],
)
log = logging.getLogger("jobbot.main")

# ── Imports (after logging is set up) ─────────────────────────────────────────
from config import BEHAVIOR, SWEEPS
from src.discovery import discover_all
from src.submitter import submit
from src.tailor import process_job
from tracking.tracker import (
    _rebuild_feed,
    get_stats,
    init_db,
    record_application,
    send_followup_emails,
)

# ── Main pipeline ──────────────────────────────────────────────────────────────

async def run(
    dry_run: bool = False,
    limit: int | None = None,
    sweep_tier: str | None = None,
):
    resolved_sweep_tier = SWEEPS.resolve_tier(sweep_tier)

    log.info("=" * 60)
    log.info("JobBot starting")
    log.info(
        "  dry_run=%s  limit=%s  sweep_tier=%s",
        dry_run,
        limit or BEHAVIOR.max_applications_per_run,
        resolved_sweep_tier,
    )
    log.info("  sweep_focus=%s", SWEEPS.describe_tier(resolved_sweep_tier))
    log.info("=" * 60)

    init_db()
    _rebuild_feed()
    max_apps = limit or BEHAVIOR.max_applications_per_run

    # ── 1. Discover ────────────────────────────────────────────────────────────
    log.info("Phase 1: Discovery")
    jobs = await discover_all(
        limit_per_source=max_apps * 3,
        sweep_tier=resolved_sweep_tier,
    )
    log.info(f"  {len(jobs)} new jobs found across all sources")

    if not jobs:
        log.info("Nothing new to apply to. Exiting.")
        return

    # ── 2. Score & select resume ───────────────────────────────────────────────
    log.info("Phase 2: scoring and resume selection")
    applications = []
    for job in jobs:
        if len(applications) >= max_apps:
            break
        if not job.description:
            log.debug(f"  Skipping {job.id}: no description")
            continue

        result = process_job(job)
        if result:
            applications.append(result)
            log.info(
                f"  ✓ Queued: {job.title} @ {job.company} "
                f"[score={job.match_score}]"
            )

    log.info(f"  {len(applications)} jobs passed the scoring threshold")

    if not applications:
        log.info("No jobs met the match threshold. Done.")
        return

    # ── 3. Validate selected PDFs ─────────────────────────────────────────────
    log.info("Phase 3: Validating selected PDF resumes")
    ready_applications = []
    for app in applications:
        resume_pdf = app.get("resume_pdf")
        if resume_pdf and resume_pdf.exists():
            ready_applications.append(app)
        else:
            log.warning(f"  Missing PDF resume for {app['job'].id}; skipping")

    applications = ready_applications
    if not applications:
        log.info("No applications have a usable PDF resume. Done.")
        return

    # ── 4. Submit ──────────────────────────────────────────────────────────────
    if dry_run:
        log.info("Phase 4: [DRY RUN] Skipping submission")
        for app in applications:
            log.info(
                f"  Would apply: {app['job'].title} @ {app['job'].company} "
                f"via {app['job'].apply_method}"
            )
        return

    log.info("Phase 4: Submission")
    submitted = 0
    for app in applications:
        job = app["job"]
        resume_pdf = app.get("resume_pdf")
        if not resume_pdf or not resume_pdf.exists():
            log.warning(f"  No PDF for {job.id}, skipping submission")
            continue

        try:
            result = await submit(
                job=job,
                resume_pdf=resume_pdf,
                cover_letter=app.get("cover_letter", ""),
            )
            record_application(
                job=job,
                result=result,
                tailored_resume=app["tailored_resume"],
                cover_letter=app.get("cover_letter", ""),
                score_details=app.get("score_details"),
                resume_variant=app.get("resume_variant", ""),
            )
            status = "✓" if result.success else "✗"
            log.info(
                f"  {status} {job.title} @ {job.company} "
                f"[{result.method}] {result.message or result.error}"
            )
            if result.success:
                submitted += 1

        except Exception as e:
            log.error(f"  Submission crash for {job.id}: {e}")

    log.info(f"Phase 4 complete: {submitted}/{len(applications)} submitted")

    # ── 5. Follow-ups ──────────────────────────────────────────────────────────
    if BEHAVIOR.send_followups:
        log.info("Phase 5: Follow-up emails")
        send_followup_emails(dry_run=False)

    # ── Done ───────────────────────────────────────────────────────────────────
    stats = get_stats()
    log.info("=" * 60)
    log.info("Run complete")
    log.info(f"  Total applications: {stats['total']}")
    log.info(f"  Avg match score:    {stats['avg_score']}")
    log.info(f"  By source:          {stats['by_source']}")
    log.info("=" * 60)
    _rebuild_feed()


# ── CLI ────────────────────────────────────────────────────────────────────────

def print_stats():
    init_db()
    _rebuild_feed()
    s = get_stats()
    print(f"""
╔══════════════════════════════╗
║  JobBot Stats                ║
╠══════════════════════════════╣
║  Total applied : {s['total']:<12} ║
║  Pending       : {s['applied']:<12} ║
║  Interviewing  : {s['interviewing']:<12} ║
║  Offers        : {s['offers']:<12} ║
║  Rejected      : {s['rejected']:<12} ║
║  Errors        : {s['errors']:<12} ║
║  Avg score     : {s['avg_score']:<12} ║
╚══════════════════════════════╝
By source: {s['by_source']}
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobBot — Autonomous Job Applicator")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Score & select resumes but don't submit",
    )
    parser.add_argument("--followups",  action="store_true", help="Only send follow-up emails")
    parser.add_argument("--stats",      action="store_true", help="Print stats and exit")
    parser.add_argument("--limit",      type=int,            help="Max applications this run")
    parser.add_argument(
        "--sweep-tier",
        choices=["daily", "weekly", "monthly", "all"],
        default=SWEEPS.active_tier,
        help="Choose which company-priority tier to sweep",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the local dashboard server",
    )
    args = parser.parse_args()

    if args.dashboard:
        from dashboard_server import run_dashboard_server

        run_dashboard_server()
    elif args.stats:
        print_stats()
    elif args.followups:
        init_db()
        send_followup_emails()
    else:
        asyncio.run(
            run(
                dry_run=args.dry_run,
                limit=args.limit,
                sweep_tier=args.sweep_tier,
            )
        )
