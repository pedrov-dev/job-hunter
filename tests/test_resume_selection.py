from pathlib import Path

from config import ResumeVariant
from src import tailor
from src.discovery import JobPosting


def _write_simple_pdf(path: Path, text: str) -> None:
    escaped = text.replace("\\", "\\\\").replace("(", r"\(").replace(")", r"\)")
    stream = f"BT\n/F1 12 Tf\n72 720 Td\n({escaped}) Tj\nET\n"
    stream_bytes = stream.encode("latin-1")
    objects = [
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        "2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n",
        (
            "3 0 obj\n"
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>\n"
            "endobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n{stream}"
            "endstream\nendobj\n"
        ),
        "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    pdf = "%PDF-1.4\n"
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(pdf.encode("latin-1")))
        pdf += obj

    xref_start = len(pdf.encode("latin-1"))
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += (
        "trailer\n"
        f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )
    path.write_bytes(pdf.encode("latin-1"))


def test_select_resume_variant_prefers_title_and_industry_matches(tmp_path, monkeypatch):
    general = tmp_path / "general.pdf"
    leadership = tmp_path / "ai_leadership.pdf"
    automation = tmp_path / "automation.pdf"
    _write_simple_pdf(general, "General Resume")
    _write_simple_pdf(leadership, "AI Leadership Resume")
    _write_simple_pdf(automation, "Automation Resume")

    monkeypatch.setattr(
        tailor,
        "RESUME_LIBRARY",
        [
            ResumeVariant(
                key="general",
                filename="general.pdf",
                title_keywords=["consultant"],
                industries=["technology"],
                is_default=True,
            ),
            ResumeVariant(
                key="leadership",
                filename="ai_leadership.pdf",
                title_keywords=["head of ai", "ai strategy"],
                industries=["financial services", "fintech"],
            ),
            ResumeVariant(
                key="automation",
                filename="automation.pdf",
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
    assert "AI Leadership Resume" in content


def test_select_resume_variant_falls_back_to_default_resume(tmp_path, monkeypatch):
    general = tmp_path / "general.pdf"
    specialist = tmp_path / "specialist.pdf"
    _write_simple_pdf(general, "General Resume")
    _write_simple_pdf(specialist, "Specialist Resume")

    monkeypatch.setattr(
        tailor,
        "RESUME_LIBRARY",
        [
            ResumeVariant(
                key="general",
                filename="general.pdf",
                title_keywords=[],
                industries=[],
                is_default=True,
            ),
            ResumeVariant(
                key="specialist",
                filename="specialist.pdf",
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
    assert "General Resume" in content
