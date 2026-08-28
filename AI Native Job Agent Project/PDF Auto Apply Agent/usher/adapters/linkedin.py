"""
LinkedIn Easy Apply ATS adapter implementation for Usher Phase 2.
Implements the BaseATSAdapter with strict anti-bot and security boundaries (ADR-PAA-004, EC-PAA-SEC-01).
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


class LinkedInEasyApplyAdapter(BaseATSAdapter):
    """Adapter for LinkedIn Easy Apply multi-step modal flows."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.LINKEDIN_EASY_APPLY)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates Tier-0 and Tier-1 dictionaries for LinkedIn Easy Apply standard fields."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("email address", lambda p: p.email)
        self.resolver.register_tier0("email", lambda p: p.email)
        self.resolver.register_tier0("phone country code", lambda p: "+91")
        self.resolver.register_tier0("mobile phone number", lambda p: p.phone)
        self.resolver.register_tier0("phone number", lambda p: p.phone)
        self.resolver.register_tier0("city", lambda p: p.location.split(",")[0].strip() if p.location else "")
        self.resolver.register_tier0("location", lambda p: p.location)
        self.resolver.register_tier0("linkedin profile", lambda p: p.linkedin_url or "")
        self.resolver.register_tier0("website", lambda p: p.portfolio_url or p.github_url or "")

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("work authorization", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("authorized to work", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("visa sponsorship", lambda p: "No")
        self.resolver.register_tier1("require sponsorship", lambda p: "No")
        self.resolver.register_tier1("notice period", lambda p: p.notice_period or "")
        self.resolver.register_tier1("years of experience", lambda p: "3")

    def detect(self, page: Page, url: str) -> bool:
        """Returns True if the URL or page points to LinkedIn Easy Apply."""
        return "linkedin.com" in url.lower()

    def check_security_challenges(self, page: Page) -> bool:
        """
        Strict check for LinkedIn security verifications, Arkose Labs, phone PIN, or CAPTCHA (EC-PAA-SEC-01, ADR-PAA-004).
        Immediate hand-off to candidate.
        """
        try:
            security_selectors = [
                "#checkpointUrl",
                "iframe[src*='arkoselabs']",
                "iframe[src*='captcha']",
                "#captcha-internal",
                "text='Quick security check'",
                "text='Let us know you're not a robot'",
                "text='Security Verification'",
                "input[name='pin']",
                ".challenge-dialog",
            ]
            for sel in security_selectors:
                if page.locator(sel).count() > 0:
                    logger.warning("[LinkedInAdapter] Security/Bot challenge detected via selector: %s", sel)
                    return True
        except Exception as e:
            logger.debug("[LinkedInAdapter] Error checking security challenges: %s", e)
        return False

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Extracts visible form fields from the LinkedIn Easy Apply modal and resolves them.
        """
        resolutions: List[FieldResolution] = []

        try:
            # Wait for easy apply modal or form inputs
            page.wait_for_selector(".jobs-easy-apply-modal, form, input", timeout=5000)
            inputs = page.locator(".jobs-easy-apply-modal input:visible, .jobs-easy-apply-modal select:visible, .jobs-easy-apply-modal textarea:visible, input:visible, textarea:visible").all()

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
            logger.warning("[LinkedInAdapter] Timeout waiting for Easy Apply inputs.")
        except Exception as e:
            logger.error("[LinkedInAdapter] Error during field mapping: %s", e)

        return resolutions

    def fill(
        self,
        page: Page,
        resolutions: List[FieldResolution],
    ) -> None:
        """Fills fields meeting the confidence threshold."""
        for res in resolutions:
            if res.confidence >= config.confidence_threshold and res.resolved_value and res.selector_used:
                try:
                    logger.info("[LinkedInAdapter] Filling '%s' (confidence: %.2f)", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[LinkedInAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Uploads the verified resume PDF to the LinkedIn Easy Apply modal."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[LinkedInAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[LinkedInAdapter] No resume upload input found in modal.")
                return False
        except Exception as e:
            logger.error("[LinkedInAdapter] Error attaching resume: %s", e)
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
        Enforces DRAFT pause vs. AUTO mode on LinkedIn.
        Always triggers MANUAL_REQUIRED on security checkpoints or low confidence.
        Forces DRAFT_PENDING_REVIEW on Tier 3 free-text questions even in AUTO mode (EC-PAA-MAP-03).
        """
        resolutions = resolutions or []

        # Anti-bot / security challenge check (EC-PAA-SEC-01, ADR-PAA-004)
        if self.check_security_challenges(page):
            logger.warning("[LinkedInAdapter] Security checkpoint encountered -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_linkedin_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
                error_code="SECURITY_CHECKPOINT",
                error_message="Anti-automation security checkpoint detected. Handing off to candidate."
            )

        # Check confidence on standard fields vs Tier 3 free-text presence
        has_low_confidence = any(
            r.confidence < config.confidence_threshold and r.resolution_tier != "tier3_llm_heavy"
            for r in resolutions
        )
        has_tier3_free_text = any(r.resolution_tier == "tier3_llm_heavy" for r in resolutions)

        if has_low_confidence:
            logger.info("[LinkedInAdapter] Low confidence standard field detected -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_linkedin_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
            )

        # Per EC-PAA-MAP-03: Tier 3 answers ALWAYS route to review even in AUTO mode
        if has_tier3_free_text or mode == SubmissionMode.DRAFT:
            logger.info("[LinkedInAdapter] Pausing at DRAFT_PENDING_REVIEW (mode=%s, tier3=%s).", mode.value, has_tier3_free_text)
            return ApplicationAttemptResult(
                attempt_id=f"attempt_linkedin_{job.job_id}",
                job=job,
                resume_used=resume,
                status="DRAFT_PENDING_REVIEW",
                field_resolutions=resolutions,
            )

        if mode == SubmissionMode.AUTO:
            try:
                # In LinkedIn Easy Apply, final button is "Submit application"
                submit_btn = page.locator("button:has-text('Submit application'), button[aria-label='Submit application']")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    logger.info("[LinkedInAdapter] AUTO mode: Submit clicked on LinkedIn.")
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_linkedin_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="SUBMITTED",
                        field_resolutions=resolutions,
                    )
                else:
                    # If on a intermediate step like "Review" or "Next"
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_linkedin_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="AMBIGUOUS_OUTCOME",
                        field_resolutions=resolutions,
                        error_message="Submit application button not found on final modal step."
                    )
            except Exception as e:
                logger.error("[LinkedInAdapter] AUTO submit failed: %s", e)
                return ApplicationAttemptResult(
                    attempt_id=f"attempt_linkedin_{job.job_id}",
                    job=job,
                    resume_used=resume,
                    status="FAILED",
                    field_resolutions=resolutions,
                    error_message=str(e),
                )

        return ApplicationAttemptResult(
            attempt_id=f"attempt_linkedin_{job.job_id}",
            job=job,
            resume_used=resume,
            status="SKIPPED",
            field_resolutions=resolutions,
        )
