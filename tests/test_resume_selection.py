from config import ResumeVariant
from core import tailor
from core.discovery import JobPosting


def test_select_resume_variant_prefers_title_and_industry_matches(tmp_path, monkeypatch):
    general = tmp_path / "general.md"
    leadership = tmp_path / "ai_leadership.md"
    automation = tmp_path / "automation.md"
    general.write_text("# General Resume", encoding="utf-8")
    leadership.write_text("# AI Leadership Resume", encoding="utf-8")
    automation.write_text("# Automation Resume", encoding="utf-8")

    monkeypatch.setattr(
        tailor,
        "RESUME_LIBRARY",
        [
            ResumeVariant(
                key="general",
                filename="general.md",
                title_keywords=["consultant"],
                industries=["technology"],
                is_default=True,
            ),
            ResumeVariant(
                key="leadership",
                filename="ai_leadership.md",
                title_keywords=["head of ai", "ai strategy"],
                industries=["financial services", "fintech"],
            ),
            ResumeVariant(
                key="automation",
                filename="automation.md",
                title_keywords=["automation"],
                industries=["operations"],
            ),
        ],
    )
    monkeypatch.setattr(tailor, "RESUME_DIR", tmp_path)

    job = JobPosting(
        title="Head of AI",
        company="Fintech Co",
        description="Lead AI strategy across financial services and lending products.",
    )

    variant, content = tailor.select_resume_variant(job)

    assert variant.key == "leadership"
    assert content == "# AI Leadership Resume"


def test_select_resume_variant_falls_back_to_default_resume(tmp_path, monkeypatch):
    general = tmp_path / "general.md"
    specialist = tmp_path / "specialist.md"
    general.write_text("# General Resume", encoding="utf-8")
    specialist.write_text("# Specialist Resume", encoding="utf-8")

    monkeypatch.setattr(
        tailor,
        "RESUME_LIBRARY",
        [
            ResumeVariant(
                key="general",
                filename="general.md",
                title_keywords=[],
                industries=[],
                is_default=True,
            ),
            ResumeVariant(
                key="specialist",
                filename="specialist.md",
                title_keywords=["ml engineer"],
                industries=["healthcare"],
            ),
        ],
    )
    monkeypatch.setattr(tailor, "RESUME_DIR", tmp_path)

    job = JobPosting(
        title="Customer Success Manager",
        company="Acme",
        description="Own renewals and customer relationships.",
    )

    variant, content = tailor.select_resume_variant(job)

    assert variant.key == "general"
    assert content == "# General Resume"
