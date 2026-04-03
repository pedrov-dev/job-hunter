import json
from types import SimpleNamespace
from typing import Any, cast

from src.discovery import JobPosting
from tracking import tracker


def test_build_dashboard_feed_creates_empty_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "applications.db")
    monkeypatch.setattr(tracker, "FEED_PATH", tmp_path / "dashboard_feed.json")

    tracker.init_db()

    feed = tracker.build_dashboard_feed()

    assert feed["stats"]["total"] == 0
    assert feed["applications"] == []
    tracker._rebuild_feed()
    assert tracker.FEED_PATH.exists()


def test_status_updates_are_reflected_in_feed(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "DB_PATH", tmp_path / "applications.db")
    monkeypatch.setattr(tracker, "FEED_PATH", tmp_path / "dashboard_feed.json")

    tracker.init_db()
    job = JobPosting(
        id="job-123",
        title="AI Engineer",
        company="Acme",
        location="Remote",
        remote=True,
        url="https://example.com/jobs/123",
        source="career_page",
        apply_method="external",
        match_score=88,
    )
    result = cast(Any, SimpleNamespace(
        job_id=job.id,
        success=True,
        method="career_page",
        message="Applied successfully",
        error="",
    ))

    tracker.record_application(
        job=job,
        result=result,
        tailored_resume="Resume text",
        cover_letter="Cover letter",
        score_details={"score": 88},
        resume_variant="ai_engineer",
    )
    tracker.update_status(job.id, "interviewing", notes="Phone screen booked")

    feed = json.loads(tracker.FEED_PATH.read_text())

    assert feed["stats"]["interviewing"] == 1
    assert feed["applications"][0]["status"] == "interviewing"
    assert feed["applications"][0]["notes"] == "Phone screen booked"
