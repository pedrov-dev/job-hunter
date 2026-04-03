"""
core/resume_pdf.py
------------------
Converts a Markdown resume to a clean PDF ready for upload.
Uses weasyprint (pip install weasyprint).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

log = logging.getLogger("jobbot.resume_pdf")

# Cache: avoid re-rendering the same resume text twice
_cache: dict[str, Path] = {}


def md_to_pdf(markdown_text: str, output_path: Path) -> Path:
    """
    Converts Markdown → HTML → PDF.
    Returns the path to the generated PDF.
    """
    try:
        import markdown
        from weasyprint import CSS, HTML
    except ImportError:
        raise ImportError(
            "Install with: pip install markdown weasyprint\n"
            "WeasyPrint also needs system libs: "
            "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html"
        )

    # Cache by content hash
    content_hash = hashlib.md5(markdown_text.encode()).hexdigest()[:10]
    if content_hash in _cache and _cache[content_hash].exists():
        log.debug(f"Resume PDF cache hit: {content_hash}")
        return _cache[content_hash]

    # Markdown → HTML
    html_body = markdown.markdown(
        markdown_text,
        extensions=["tables", "extra"],
    )

    full_html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ margin: 18mm 16mm; size: A4; }}
  body {{
    font-family: "Georgia", serif;
    font-size: 10.5pt;
    line-height: 1.45;
    color: #1a1a1a;
  }}
  h1 {{ font-size: 18pt; margin-bottom: 2pt; }}
  h2 {{ font-size: 12pt; border-bottom: 1pt solid #ccc;
        margin-top: 12pt; margin-bottom: 4pt; text-transform: uppercase;
        letter-spacing: 0.06em; color: #333; }}
  h3 {{ font-size: 10.5pt; font-weight: bold; margin: 6pt 0 2pt; }}
  p  {{ margin: 2pt 0 4pt; }}
  ul {{ margin: 2pt 0 4pt 16pt; padding: 0; }}
  li {{ margin-bottom: 2pt; }}
  a  {{ color: #2563eb; text-decoration: none; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 9.5pt; }}
  td, th {{ padding: 2pt 6pt; }}
</style>
</head>
<body>{html_body}</body>
</html>
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=full_html).write_pdf(str(output_path))
    _cache[content_hash] = output_path
    log.info(f"PDF written: {output_path}")
    return output_path
