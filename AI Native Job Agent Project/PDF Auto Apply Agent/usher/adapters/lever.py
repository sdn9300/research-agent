"""
Lever ATS adapter implementation for Usher Phase 3.
Handles Lever-hosted job postings and application forms (jobs.lever.co).
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


class LeverAdapter(BaseATSAdapter):
    """Adapter for Lever job applications (jobs.lever.co / custom domains)."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.GENERIC_ATS_LEVER)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates Tier-0 and Tier-1 dictionaries for Lever standard fields."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("name", lambda p: p.full_name)
        self.resolver.register_tier0("full name", lambda p: p.full_name)
        self.resolver.register_tier0("email", lambda p: p.email)
        self.resolver.register_tier0("phone", lambda p: p.phone)
        self.resolver.register_tier0("current company", lambda p: p.experience[0].company if p.experience else "")
        self.resolver.register_tier0("org", lambda p: p.experience[0].company if p.experience else "")
        self.resolver.register_tier0("linkedin url", lambda p: p.linkedin_url or "")
        self.resolver.register_tier0("github url", lambda p: p.github_url or "")
        self.resolver.register_tier0("portfolio url", lambda p: p.portfolio_url or "")
        self.resolver.register_tier0("other website", lambda p: p.portfolio_url or p.github_url or "")

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("work authorization", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("authorized to work", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("sponsorship", lambda p: "No")
        self.resolver.register_tier1("notice period", lambda p: p.notice_period or "")
        self.resolver.register_tier1("salary expectation", lambda p: p.salary_expectation or "")
        self.resolver.register_tier1("additional information", lambda p: "")

    def detect(self, page: Page, url: str) -> bool:
        """Returns True if the URL or DOM matches Lever signatures."""
        url_lower = url.lower()
        if "lever.co" in url_lower:
            return True

        try:
            if page.locator(".lever-form, form.application-form, .posting-headline, #application-form").count() > 0:
                return True
        except Exception:
            pass

        return False

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Extracts visible form inputs from Lever application form and resolves them.
        """
        resolutions: List[FieldResolution] = []

        try:
            page.wait_for_selector("form, input", timeout=5000)
            inputs = page.locator(".application-form input:visible, form input:visible, form textarea:visible, input:visible, textarea:visible").all()

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
            logger.warning("[LeverAdapter] Timeout waiting for form inputs.")
        except Exception as e:
            logger.error("[LeverAdapter] Error during field mapping: %s", e)

        return resolutions

    def fill(
        self,
        page: Page,
        resolutions: List[FieldResolution],
    ) -> None:
        """Fills form fields with confidence >= 0.85."""
        for res in resolutions:
            if res.confidence >= config.confidence_threshold and res.resolved_value and res.selector_used:
                try:
                    logger.info("[LeverAdapter] Filling '%s' (confidence: %.2f)", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[LeverAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Attaches the verified resume PDF to the Lever file upload input."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            # Lever standard resume file input
            file_input = page.locator("input[type='file'][name='resume'], input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[LeverAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[LeverAdapter] No resume file input found.")
                return False
        except Exception as e:
            logger.error("[LeverAdapter] Error attaching resume: %s", e)
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
        Enforces DRAFT pause vs. AUTO mode on Lever.
        Forces MANUAL_REQUIRED on low-confidence fields.
        Forces DRAFT_PENDING_REVIEW on Tier-3 free-text questions.
        """
        resolutions = resolutions or []

        has_low_confidence = any(
            r.confidence < config.confidence_threshold and r.resolution_tier != "tier3_llm_heavy"
            for r in resolutions
        )
        has_tier3_free_text = any(r.resolution_tier == "tier3_llm_heavy" for r in resolutions)

        if has_low_confidence:
            logger.info("[LeverAdapter] Low confidence standard field -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_lever_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
            )

        if has_tier3_free_text or mode == SubmissionMode.DRAFT:
            logger.info("[LeverAdapter] Pausing at DRAFT_PENDING_REVIEW.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_lever_{job.job_id}",
                job=job,
                resume_used=resume,
                status="DRAFT_PENDING_REVIEW",
                field_resolutions=resolutions,
            )

        if mode == SubmissionMode.AUTO:
            try:
                submit_btn = page.locator("#btn-submit, button[type='submit'], button:has-text('Submit application')")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    logger.info("[LeverAdapter] AUTO mode: Submit clicked.")
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_lever_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="SUBMITTED",
                        field_resolutions=resolutions,
                    )
                else:
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_lever_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="AMBIGUOUS_OUTCOME",
                        field_resolutions=resolutions,
                        error_message="Submit button not found on Lever application page."
                    )
            except Exception as e:
                logger.error("[LeverAdapter] AUTO submit failed: %s", e)
                return ApplicationAttemptResult(
                    attempt_id=f"attempt_lever_{job.job_id}",
                    job=job,
                    resume_used=resume,
                    status="FAILED",
                    field_resolutions=resolutions,
                    error_message=str(e),
                )

        return ApplicationAttemptResult(
            attempt_id=f"attempt_lever_{job.job_id}",
            job=job,
            resume_used=resume,
            status="SKIPPED",
            field_resolutions=resolutions,
        )
