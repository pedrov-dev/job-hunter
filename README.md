# JobBot

JobBot is a Windows-friendly Python automation tool for discovering jobs, scoring them against your resume, generating tailored application materials, submitting applications, and tracking outcomes locally.

It currently supports:

- Job discovery from Indeed RSS and public career pages backed by Greenhouse, Lever, or Ashby
- OpenAI-powered scoring and resume tailoring
- Optional cover letter generation
- PDF resume generation with WeasyPrint
- Submission flows for Indeed, generic ATS forms, and email applications
- Local SQLite tracking plus a JSON feed for the dashboard

## Requirements

- Python 3.12+
- An OpenAI API key
- Optional: Anthropic key and SMTP credentials for email applications and follow-ups
- Playwright browser binaries installed for scraping and submissions

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
playwright install
```

Copy [.env.example](.env.example) to `.env` and fill in the values you need.

## Configuration

The main settings live in [config.py](config.py):

- Search criteria such as job titles, keywords, locations, salary floor, and company filters
- AI settings such as provider, model, scoring threshold, and cover letter behavior
- Run behavior such as per-run application limit, browser mode, and follow-up timing

The master resume must be saved at [resumes/master_resume.md](resumes/master_resume.md).

## Run

The main entry point is [main.py](main.py).

```powershell
python main.py
python main.py --dry-run
python main.py --followups
python main.py --stats
python main.py --limit 5
```

`python main.py` runs the full pipeline:

1. Discover jobs
2. Score each job against the master resume
3. Tailor the resume and optional cover letter
4. Convert the tailored resume to PDF
5. Submit applications
6. Send follow-up emails if enabled

Use `--dry-run` to stop before submission, `--followups` to only send follow-ups, and `--stats` to print the stored application summary.

## Outputs

The app writes local state and generated files under the repository root:

- [data/applications.db](data/applications.db) for application history
- [data/dashboard_feed.json](data/dashboard_feed.json) for the dashboard
- [data/seen_jobs.json](data/seen_jobs.json) for deduplication
- [output/](output) for per-job tailored resumes, cover letters, and job JSON
- [logs/jobbot.log](logs/jobbot.log) for runtime logs

## Dashboard

The dashboard UI lives in [ui/dashboard.html](ui/dashboard.html). It is a static front end that reads the JSON feed produced by the tracker.

## Project Layout

- [main.py](main.py): CLI entry point and pipeline orchestration
- [config.py](config.py): search, AI, and behavior configuration
- [core/discovery.py](core/discovery.py): job discovery and deduplication
- [core/tailor.py](core/tailor.py): scoring, resume tailoring, and cover letter generation
- [core/resume_pdf.py](core/resume_pdf.py): Markdown to PDF conversion
- [submissions/submitter.py](submissions/submitter.py): application submission handlers
- [tracking/tracker.py](tracking/tracker.py): SQLite persistence and dashboard feed generation
- [ui/dashboard.html](ui/dashboard.html): local dashboard UI

## Notes

- The project is intentionally hands-on: browser automation and form filling may need selector updates when target sites change.
- The repository does not currently include an automated test suite.
- Keep [requirements.txt](requirements.txt), [requirements-dev.txt](requirements-dev.txt), and [pyproject.toml](pyproject.toml) aligned when dependencies change.
