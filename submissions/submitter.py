"""
submissions/submitter.py
------------------------
Handles application submission across all channels.
Each submitter returns a SubmissionResult.
"""

from __future__ import annotations

import asyncio
import logging
import random
import smtplib
from dataclasses import dataclass
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from playwright.async_api import Page, async_playwright

from config import BEHAVIOR, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER
from core.discovery import JobPosting

log = logging.getLogger("jobbot.submissions")


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class SubmissionResult:
    job_id:   str
    success:  bool
    method:   str
    message:  str = ""
    error:    str = ""


# ── Human-like delays ─────────────────────────────────────────────────────────

async def human_delay(min_s: float | None = None, max_s: float | None = None):
    lo = min_s or BEHAVIOR.min_delay_seconds
    hi = max_s or BEHAVIOR.max_delay_seconds
    await asyncio.sleep(random.uniform(lo, hi))


# ── Indeed Apply ──────────────────────────────────────────────────────────────

class IndeedApply:
    """
    Indeed's apply flow (external redirect + form).
    Many jobs redirect to the company ATS — handled by GenericFormApply.
    """

    async def apply(self, job: JobPosting, resume_pdf: Path) -> SubmissionResult:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=BEHAVIOR.headless_browser)
            page = await (await browser.new_context()).new_page()
            try:
                await page.goto(job.url)
                await page.wait_for_timeout(2000)

                # Look for "Apply now" button
                apply_btn = page.locator(
                    'a[id*="applyButtonLinkContainer"], button:has-text("Apply now")'
                ).first
                if await apply_btn.count() == 0:
                    return SubmissionResult(
                        job_id=job.id, success=False,
                        method="indeed", error="No apply button found"
                    )

                await apply_btn.click()
                await page.wait_for_timeout(2500)

                # Check if we were redirected to an external ATS
                current_url = page.url
                if "indeed.com" not in current_url:
                    # Delegate to generic ATS handler
                    return await GenericFormApply().apply_on_page(
                        page, job, resume_pdf, method="indeed_redirect"
                    )

                # Native Indeed apply flow
                return await self._fill_indeed_form(page, job, resume_pdf)

            except Exception as e:
                return SubmissionResult(
                    job_id=job.id, success=False, method="indeed", error=str(e)
                )
            finally:
                await browser.close()

    async def _fill_indeed_form(
        self,
        page: Page,
        job: JobPosting,
        resume_pdf: Path,
    ) -> SubmissionResult:
        # Upload resume
        file_input = page.locator('input[type="file"]').first
        if await file_input.count() > 0:
            await file_input.set_input_files(str(resume_pdf))
            await page.wait_for_timeout(1500)

        # Submit
        submit = page.locator('button[type="submit"]').first
        if await submit.count() > 0:
            await submit.click()
            return SubmissionResult(
                job_id=job.id, success=True, method="indeed",
                message="Applied via Indeed native form"
            )

        return SubmissionResult(
            job_id=job.id, success=False, method="indeed",
            error="Could not find submit button"
        )


# ── Generic ATS form apply ────────────────────────────────────────────────────

class GenericFormApply:
    """
    Best-effort form filler for Greenhouse, Lever, Ashby, Workday, etc.
    Fills common fields and uploads resume.
    """

    FIELD_MAP = {
        # (selector_hint, value_key)
        "first_name":  "Pedro",        # TODO: pull from config/profile
        "last_name":   "Ventura",
        "email":       "your@email.com",
        "phone":       "+52 55 0000 0000",
        "website":     "https://yourwebsite.com",
        "location":    "Mexico City, Mexico",
    }

    async def apply(self, job: JobPosting, resume_pdf: Path) -> SubmissionResult:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=BEHAVIOR.headless_browser)
            page = await (await browser.new_context()).new_page()
            try:
                await page.goto(job.url)
                await page.wait_for_timeout(2000)
                return await self.apply_on_page(page, job, resume_pdf)
            except Exception as e:
                return SubmissionResult(
                    job_id=job.id, success=False,
                    method="career_page", error=str(e)
                )
            finally:
                await browser.close()

    async def apply_on_page(
        self, page: Page, job: JobPosting, resume_pdf: Path, method: str = "career_page"
    ) -> SubmissionResult:
        await human_delay(1, 2)

        # Upload resume
        for selector in ['input[type="file"]', 'input[accept*="pdf"]']:
            fi = page.locator(selector).first
            if await fi.count() > 0 and await fi.is_visible():
                await fi.set_input_files(str(resume_pdf))
                await page.wait_for_timeout(1000)
                break

        # Fill text fields by common name/id/placeholder patterns
        for hint, value in self.FIELD_MAP.items():
            selectors = [
                f'input[name*="{hint}"]',
                f'input[id*="{hint}"]',
                f'input[placeholder*="{hint.replace("_", " ")}"]',
            ]
            for sel in selectors:
                el = page.locator(sel).first
                try:
                    if await el.count() > 0 and await el.is_visible():
                        current = await el.input_value()
                        if not current:
                            await el.fill(value)
                        break
                except Exception:
                    pass

        await human_delay(1, 2)

        # Try to submit
        for submit_sel in [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
        ]:
            btn = page.locator(submit_sel).first
            if await btn.count() > 0 and await btn.is_enabled():
                await btn.click()
                log.info(f"Submitted via {method}")
                return SubmissionResult(
                    job_id=job.id, success=True, method=method,
                    message="Submitted via form"
                )

        return SubmissionResult(
            job_id=job.id, success=False, method=method,
            error="Submit button not found"
        )


# ── Email apply ───────────────────────────────────────────────────────────────

class EmailApply:
    """
    Sends application directly to a hiring email.
    Attach tailored resume PDF and embed cover letter in body.
    """

    def apply(
        self,
        job: JobPosting,
        resume_pdf: Path,
        cover_letter: str,
        recipient_email: str,
    ) -> SubmissionResult:
        try:
            msg = MIMEMultipart("mixed")
            msg["From"]    = SMTP_USER
            msg["To"]      = recipient_email
            msg["Subject"] = f"Application: {job.title} — Pedro Ventura"  # TODO from config

            body = f"""Dear Hiring Team,

{cover_letter}

Best regards,
Pedro Ventura

---
Applied via: {job.url}
"""
            msg.attach(MIMEText(body, "plain"))

            # Attach resume PDF
            with open(resume_pdf, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                'attachment; filename="Pedro_Ventura_Resume.pdf"'
            )
            msg.attach(part)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)

            return SubmissionResult(
                job_id=job.id, success=True, method="email",
                message=f"Emailed to {recipient_email}"
            )

        except Exception as e:
            return SubmissionResult(
                job_id=job.id, success=False, method="email", error=str(e)
            )


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def submit(
    job: JobPosting,
    resume_pdf: Path,
    cover_letter: str = "",
    email_recipient: str = "",
) -> SubmissionResult:
    """Route application to the right submitter based on job metadata."""

    if job.apply_method == "email" and email_recipient:
        return EmailApply().apply(job, resume_pdf, cover_letter, email_recipient)

    elif job.source == "indeed":
        return await IndeedApply().apply(job, resume_pdf)

    else:
        # Greenhouse, Lever, Ashby, or any career page
        return await GenericFormApply().apply(job, resume_pdf)
