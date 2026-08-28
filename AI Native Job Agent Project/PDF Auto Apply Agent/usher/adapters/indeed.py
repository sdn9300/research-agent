"""
Indeed ATS adapter implementation for Usher Phase 2.
Implements the BaseATSAdapter for Indeed standard and multi-step apply flows.
"""

import logging
from typing import List, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .base import BaseATSAdapter
from ..attachment import AttachmentHandler
from ..config import config
from ..resolver import FieldResolver
from ..schemas import (
    ApplicationAttemptResult,
    ApplicationChannel,
    CandidateProfile,
    FieldResolution,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
)

logger = logging.getLogger(__name__)


class IndeedAdapter(BaseATSAdapter):
    """Adapter for Indeed native and multi-step apply flows."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.INDEED)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates Tier-0 and Tier-1 dictionaries for Indeed standard fields."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("name", lambda p: p.full_name)
        self.resolver.register_tier0("full name", lambda p: p.full_name)
        self.resolver.register_tier0("first name", lambda p: p.full_name.split()[0] if p.full_name else "")
        self.resolver.register_tier0("last name", lambda p: " ".join(p.full_name.split()[1:]) if len(p.full_name.split()) > 1 else "")
        self.resolver.register_tier0("email", lambda p: p.email)
        self.resolver.register_tier0("email address", lambda p: p.email)
        self.resolver.register_tier0("phone number", lambda p: p.phone)
        self.resolver.register_tier0("phone", lambda p: p.phone)
        self.resolver.register_tier0("location", lambda p: p.location)
        self.resolver.register_tier0("city", lambda p: p.location.split(",")[0].strip() if p.location else "")

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("work authorization", lambda p: p.work_authorization or "Authorized to work")
        self.resolver.register_tier1("authorized to work", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("sponsorship", lambda p: "No" if p.work_authorization else "Yes")
        self.resolver.register_tier1("salary expectation", lambda p: p.salary_expectation or "")
        self.resolver.register_tier1("expected salary", lambda p: p.salary_expectation or "")
        self.resolver.register_tier1("notice period", lambda p: p.notice_period or "")

    def detect(self, page: Page, url: str) -> bool:
        """Returns True if the URL points to Indeed job or apply page."""
        return "indeed.com" in url.lower()

    def check_security_challenges(self, page: Page) -> bool:
        """
        Detects CAPTCHA, Cloudflare challenges, or anti-bot verification (EC-PAA-SEC-01).
        Never attempts to solve or bypass (ADR-PAA-004).
        """
        try:
            challenge_selectors = [
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']",
                "iframe[src*='challenges.cloudflare.com']",
                "#challenge-form",
                ".cf-turnstile-wrapper",
                "text='Verifying you are human'",
                "text='Please verify you are a human'",
                "#captcha-container",
            ]
            for sel in challenge_selectors:
                if page.locator(sel).count() > 0:
                    logger.warning("[IndeedAdapter] Anti-automation challenge detected via selector: %s", sel)
                    return True
        except Exception as e:
            logger.debug("[IndeedAdapter] Error during challenge detection: %s", e)
        return False

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Extracts visible form fields on current Indeed step and maps them using FieldResolver.
        """
        resolutions: List[FieldResolution] = []

        try:
            page.wait_for_selector("input, textarea, select", timeout=5000)
            inputs = page.locator("input:visible, textarea:visible, select:visible").all()

            for inp in inputs:
                input_type = inp.get_attribute("type") or "text"
                if input_type in ["hidden", "submit", "button", "file"]:
                    continue

                label_id = inp.get_attribute("id")
                label_text = ""

                if label_id:
                    label_el = page.locator(f"label[for='{label_id}']")
                    if label_el.count() > 0:
                        label_text = label_el.first.inner_text().strip()

                if not label_text:
                    aria_label = inp.get_attribute("aria-label")
                    placeholder = inp.get_attribute("placeholder")
                    name_attr = inp.get_attribute("name")
                    label_text = aria_label or placeholder or name_attr or "unknown_field"

                is_textarea = inp.evaluate("el => el.tagName.toLowerCase() === 'textarea'")

                res = self.resolver.resolve(
                    field_label=label_text,
                    profile=profile,
                    is_free_text=is_textarea,
                    job_context=job.description or ""
                )

                if label_id:
                    res.selector_used = f"#{label_id}"
                elif inp.get_attribute("name"):
                    res.selector_used = f"[name='{inp.get_attribute('name')}']"
                else:
                    res.selector_used = None

                resolutions.append(res)

        except PlaywrightTimeoutError:
            logger.warning("[IndeedAdapter] Timeout waiting for form inputs on Indeed.")
        except Exception as e:
            logger.error("[IndeedAdapter] Error during field mapping: %s", e)

        return resolutions

    def fill(
        self,
        page: Page,
        resolutions: List[FieldResolution],
    ) -> None:
        """Fills fields meeting the 0.85 confidence threshold."""
        for res in resolutions:
            if res.confidence >= config.confidence_threshold and res.resolved_value and res.selector_used:
                try:
                    logger.info("[IndeedAdapter] Filling '%s' (confidence: %.2f)", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[IndeedAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Uploads the verified resume PDF to Indeed."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[IndeedAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[IndeedAdapter] No resume upload input found.")
                return False
        except Exception as e:
            logger.error("[IndeedAdapter] Error attaching resume on Indeed: %s", e)
            return False

    def submit_or_hold(
        self,
        page: Page,
        mode: SubmissionMode,
        job: JobApplicationTarget,
        resume: Optional[ResumeArtifact] = None,
        resolutions: Optional[List[FieldResolution]] = None,
    ) -> ApplicationAttemptResult:
        """
        Enforces DRAFT pause vs. AUTO mode on Indeed.
        Guarantees fallback on security challenge or low confidence.
        """
        resolutions = resolutions or []

        # Anti-bot check (EC-PAA-SEC-01)
        if self.check_security_challenges(page):
            logger.warning("[IndeedAdapter] Security challenge triggered MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_indeed_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
                error_code="CAPTCHA_CHALLENGE",
                error_message="Anti-automation security challenge detected."
            )

        # Check confidence on standard fields vs Tier 3 free-text presence
        has_low_confidence = any(
            r.confidence < config.confidence_threshold and r.resolution_tier != "tier3_llm_heavy"
            for r in resolutions
        )
        has_tier3_free_text = any(r.resolution_tier == "tier3_llm_heavy" for r in resolutions)

        if has_low_confidence:
            logger.info("[IndeedAdapter] Low confidence standard field detected -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_indeed_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
            )

        if has_tier3_free_text or mode == SubmissionMode.DRAFT:
            logger.info("[IndeedAdapter] Pausing at DRAFT_PENDING_REVIEW (mode=%s, tier3=%s).", mode.value, has_tier3_free_text)
            return ApplicationAttemptResult(
                attempt_id=f"attempt_indeed_{job.job_id}",
                job=job,
                resume_used=resume,
                status="DRAFT_PENDING_REVIEW",
                field_resolutions=resolutions,
            )

        if mode == SubmissionMode.AUTO:
            try:
                submit_btn = page.locator("button:has-text('Submit your application'), button:has-text('Apply now'), button[type='submit']")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    logger.info("[IndeedAdapter] AUTO mode: Submit clicked on Indeed.")
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_indeed_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="SUBMITTED",
                        field_resolutions=resolutions,
                    )
                else:
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_indeed_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="AMBIGUOUS_OUTCOME",
                        field_resolutions=resolutions,
                        error_message="Submit button not found on final screen."
                    )
            except Exception as e:
                logger.error("[IndeedAdapter] AUTO submit failed: %s", e)
                return ApplicationAttemptResult(
                    attempt_id=f"attempt_indeed_{job.job_id}",
                    job=job,
                    resume_used=resume,
                    status="FAILED",
                    field_resolutions=resolutions,
                    error_message=str(e),
                )

        return ApplicationAttemptResult(
            attempt_id=f"attempt_indeed_{job.job_id}",
            job=job,
            resume_used=resume,
            status="SKIPPED",
            field_resolutions=resolutions,
        )
