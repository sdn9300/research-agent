"""
Greenhouse ATS adapter implementation for Usher Phase 3.
Handles Greenhouse-hosted job boards and embedded application forms.
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


class GreenhouseAdapter(BaseATSAdapter):
    """Adapter for Greenhouse job applications (boards.greenhouse.io / grnh.se / custom domains)."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.GENERIC_ATS_GREENHOUSE)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates Tier-0 and Tier-1 dictionaries for Greenhouse standard fields."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("first name", lambda p: p.full_name.split()[0] if p.full_name else "")
        self.resolver.register_tier0("last name", lambda p: " ".join(p.full_name.split()[1:]) if len(p.full_name.split()) > 1 else "")
        self.resolver.register_tier0("email", lambda p: p.email)
        self.resolver.register_tier0("phone", lambda p: p.phone)
        self.resolver.register_tier0("linkedin profile", lambda p: p.linkedin_url or "")
        self.resolver.register_tier0("website", lambda p: p.portfolio_url or p.github_url or "")
        self.resolver.register_tier0("github", lambda p: p.github_url or "")

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("work authorization", lambda p: p.work_authorization or "Authorized")
        self.resolver.register_tier1("authorized to work", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("require sponsorship", lambda p: "No")
        self.resolver.register_tier1("location", lambda p: p.location)
        self.resolver.register_tier1("notice period", lambda p: p.notice_period or "")

    def detect(self, page: Page, url: str) -> bool:
        """Returns True if the URL or DOM matches Greenhouse signatures."""
        url_lower = url.lower()
        if "greenhouse.io" in url_lower or "grnh.se" in url_lower:
            return True

        # DOM check for embedded Greenhouse forms
        try:
            if page.locator("#application_form, #app_body, form#job_application").count() > 0:
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
        Extracts visible form inputs from Greenhouse application form and resolves them.
        """
        resolutions: List[FieldResolution] = []

        try:
            page.wait_for_selector("form, input", timeout=5000)
            inputs = page.locator("form input:visible, form textarea:visible, form select:visible, input:visible, textarea:visible").all()

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
            logger.warning("[GreenhouseAdapter] Timeout waiting for form inputs.")
        except Exception as e:
            logger.error("[GreenhouseAdapter] Error during field mapping: %s", e)

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
                    logger.info("[GreenhouseAdapter] Filling '%s' (confidence: %.2f)", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[GreenhouseAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Attaches the verified resume PDF to the Greenhouse resume upload input."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            # Greenhouse standard resume file input
            file_input = page.locator("input[type='file'][id*='resume'], input[type='file'][name*='resume'], input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[GreenhouseAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[GreenhouseAdapter] No resume file input found.")
                return False
        except Exception as e:
            logger.error("[GreenhouseAdapter] Error attaching resume: %s", e)
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
        Enforces DRAFT pause vs. AUTO mode on Greenhouse.
        Forces MANUAL_REQUIRED on low-confidence standard fields.
        Forces DRAFT_PENDING_REVIEW on Tier-3 free-text questions.
        """
        resolutions = resolutions or []

        has_low_confidence = any(
            r.confidence < config.confidence_threshold and r.resolution_tier != "tier3_llm_heavy"
            for r in resolutions
        )
        has_tier3_free_text = any(r.resolution_tier == "tier3_llm_heavy" for r in resolutions)

        if has_low_confidence:
            logger.info("[GreenhouseAdapter] Low confidence standard field -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_greenhouse_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
            )

        if has_tier3_free_text or mode == SubmissionMode.DRAFT:
            logger.info("[GreenhouseAdapter] Pausing at DRAFT_PENDING_REVIEW.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_greenhouse_{job.job_id}",
                job=job,
                resume_used=resume,
                status="DRAFT_PENDING_REVIEW",
                field_resolutions=resolutions,
            )

        if mode == SubmissionMode.AUTO:
            try:
                submit_btn = page.locator("#submit_app, button:has-text('Submit Application'), input[type='submit']")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    logger.info("[GreenhouseAdapter] AUTO mode: Submit clicked.")
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_greenhouse_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="SUBMITTED",
                        field_resolutions=resolutions,
                    )
                else:
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_greenhouse_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="AMBIGUOUS_OUTCOME",
                        field_resolutions=resolutions,
                        error_message="Submit button not found on Greenhouse application page."
                    )
            except Exception as e:
                logger.error("[GreenhouseAdapter] AUTO submit failed: %s", e)
                return ApplicationAttemptResult(
                    attempt_id=f"attempt_greenhouse_{job.job_id}",
                    job=job,
                    resume_used=resume,
                    status="FAILED",
                    field_resolutions=resolutions,
                    error_message=str(e),
                )

        return ApplicationAttemptResult(
            attempt_id=f"attempt_greenhouse_{job.job_id}",
            job=job,
            resume_used=resume,
            status="SKIPPED",
            field_resolutions=resolutions,
        )
