"""
Naukri.com adapter implementation for Usher Phase 1.
Implements the BaseATSAdapter for the Naukri apply flow.
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


class NaukriAdapter(BaseATSAdapter):
    """Adapter for Naukri.com native apply flow."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.NAUKRI)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates Tier-0 and Tier-1 dictionaries for Naukri specifically."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("email address", lambda p: p.email)
        self.resolver.register_tier0("email id", lambda p: p.email)
        self.resolver.register_tier0("mobile number", lambda p: p.phone)
        self.resolver.register_tier0("current location", lambda p: p.location)

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("expected ctc", lambda p: p.salary_expectation or "")
        self.resolver.register_tier1("salary expectation", lambda p: p.salary_expectation or "")
        self.resolver.register_tier1("notice period", lambda p: p.notice_period or "")

    def detect(self, page: Page, url: str) -> bool:
        """Returns True if the URL points to a Naukri job or apply page."""
        return "naukri.com" in url.lower()

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Parses visible fields in the Naukri apply modal/page and maps them using the resolver.
        (For Phase 1 MVP, this focuses on screening questions and common fields).
        """
        resolutions = []
        
        try:
            # Wait for form container (assuming typical Naukri apply modal)
            # In a real scenario, this would use a robust selector for the form container.
            # Using a generic input selector for the sake of the MVP structure.
            page.wait_for_selector("input, textarea", timeout=5000)
            
            inputs = page.locator("input:visible, textarea:visible").all()
            for inp in inputs:
                # Get the associated label or placeholder
                label_id = inp.get_attribute("id")
                label_text = ""
                
                if label_id:
                    label_el = page.locator(f"label[for='{label_id}']")
                    if label_el.count() > 0:
                        label_text = label_el.first.inner_text()
                
                if not label_text:
                    label_text = inp.get_attribute("placeholder") or inp.get_attribute("name") or "unknown_field"
                
                is_textarea = inp.evaluate("el => el.tagName.toLowerCase() === 'textarea'")
                
                res = self.resolver.resolve(
                    field_label=label_text,
                    profile=profile,
                    is_free_text=is_textarea,
                    job_context=job.description or ""
                )
                
                res.selector_used = f"input[id='{label_id}']" if label_id else f"input[name='{inp.get_attribute('name')}']"
                resolutions.append(res)
                
        except PlaywrightTimeoutError:
            logger.warning("[NaukriAdapter] Timeout waiting for form inputs.")
            
        return resolutions

    def fill(
        self,
        page: Page,
        resolutions: List[FieldResolution],
    ) -> None:
        """Fills the form with resolved values meeting the confidence threshold."""
        for res in resolutions:
            if res.confidence >= config.confidence_threshold and res.resolved_value and res.selector_used:
                try:
                    logger.info("[NaukriAdapter] Filling '%s' with confidence %.2f", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[NaukriAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Uploads the resume PDF."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            # Naukri typically uses an input[type='file'] for resume upload
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[NaukriAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[NaukriAdapter] No file input found for resume upload.")
                return False
        except Exception as e:
            logger.error("[NaukriAdapter] Error attaching resume: %s", e)
            return False

    def submit_or_hold(
        self,
        page: Page,
        mode: SubmissionMode,
        job: JobApplicationTarget,
        resume: Optional[ResumeArtifact] = None,
        resolutions: Optional[List[FieldResolution]] = None,
    ) -> ApplicationAttemptResult:
        """Implements the DRAFT pause and AUTO submission logic."""
        
        resolutions = resolutions or []
        
        # Check if any field fell below confidence or was tier 3 (which forces manual review)
        requires_manual = any(
            r.confidence < config.confidence_threshold or r.resolution_tier == "tier3_llm_heavy" 
            for r in resolutions
        )
        
        status = "DRAFT_PENDING_REVIEW"
        
        if requires_manual:
            logger.info("[NaukriAdapter] Manual review forced due to low confidence or free-text fields.")
            status = "MANUAL_REQUIRED"
            
        if mode == SubmissionMode.DRAFT or status == "MANUAL_REQUIRED":
            logger.info("[NaukriAdapter] Pausing in DRAFT/MANUAL mode for review.")
            # In a real environment, we would pause here (e.g., input("Press Enter to continue..."))
            # For automation/adapter boundaries, we return the status indicating it's waiting for review.
            pass
        elif mode == SubmissionMode.AUTO:
            try:
                # Example: click the submit button
                submit_btn = page.locator("button:has-text('Submit'), button:has-text('Apply')")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    logger.info("[NaukriAdapter] AUTO mode: Submit button clicked.")
                    status = "SUBMITTED"
                else:
                    status = "AMBIGUOUS_OUTCOME"
            except Exception as e:
                logger.error("[NaukriAdapter] AUTO mode submit failed: %s", e)
                status = "FAILED"

        return ApplicationAttemptResult(
            attempt_id=f"attempt_naukri_{job.job_id}",
            job=job,
            resume_used=resume,
            status=status,
            field_resolutions=resolutions,
        )
