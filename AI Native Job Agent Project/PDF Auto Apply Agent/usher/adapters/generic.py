"""
Generic ATS adapter fallback implementation for Usher Phase 3.
Acts as last-resort fallback for arbitrary, unrecognized career portals.
Strict Safety Guarantee: Never eligible for AUTO mode (PAA-EP-1.0 §5, PAA-IP-1.0 §5).
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


class GenericATSAdapter(BaseATSAdapter):
    """
    Fallback adapter for unrecognized career portals.
    Uses LLM-assisted field mapping and is strictly bounded to DRAFT_PENDING_REVIEW only.
    """

    def __init__(self):
        super().__init__(channel=ApplicationChannel.GENERIC_ATS_UNKNOWN)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates common generic field synonyms."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("name", lambda p: p.full_name)
        self.resolver.register_tier0("full name", lambda p: p.full_name)
        self.resolver.register_tier0("first name", lambda p: p.full_name.split()[0] if p.full_name else "")
        self.resolver.register_tier0("last name", lambda p: " ".join(p.full_name.split()[1:]) if len(p.full_name.split()) > 1 else "")
        self.resolver.register_tier0("email", lambda p: p.email)
        self.resolver.register_tier0("phone", lambda p: p.phone)
        self.resolver.register_tier0("location", lambda p: p.location)

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("linkedin", lambda p: p.linkedin_url or "")
        self.resolver.register_tier1("github", lambda p: p.github_url or "")
        self.resolver.register_tier1("portfolio", lambda p: p.portfolio_url or "")
        self.resolver.register_tier1("website", lambda p: p.portfolio_url or p.github_url or "")
        self.resolver.register_tier1("work authorization", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("sponsorship", lambda p: "No")

    def detect(self, page: Page, url: str) -> bool:
        """Fallback adapter: detects any page containing a form or input fields."""
        try:
            if page.locator("form, input:visible").count() > 0:
                return True
        except Exception:
            pass
        return True

    def check_signup_wall(self, page: Page) -> bool:
        """Detects if page is blocked by a signup or login barrier (EC-PAA-SUB-03)."""
        try:
            wall_selectors = [
                "input[type='password']",
                "text='Create an account to apply'",
                "text='Sign in with'",
                "text='Sign up to apply'",
            ]
            for sel in wall_selectors:
                if page.locator(sel).count() > 0:
                    logger.warning("[GenericATSAdapter] Signup/Login wall detected via selector: %s", sel)
                    return True
        except Exception as e:
            logger.debug("[GenericATSAdapter] Error checking signup wall: %s", e)
        return False

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Extracts visible form inputs across generic DOM structures and resolves them.
        """
        resolutions: List[FieldResolution] = []

        try:
            page.wait_for_selector("input, textarea, select", timeout=5000)
            inputs = page.locator("form input:visible, form textarea:visible, form select:visible, input:visible, textarea:visible").all()

            for inp in inputs:
                input_type = inp.get_attribute("type") or "text"
                if input_type in ["hidden", "submit", "button", "file", "password"]:
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
            logger.warning("[GenericATSAdapter] Timeout waiting for generic form inputs.")
        except Exception as e:
            logger.error("[GenericATSAdapter] Error during generic field mapping: %s", e)

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
                    logger.info("[GenericATSAdapter] Filling '%s' (confidence: %.2f)", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[GenericATSAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Attaches resume PDF to file upload input."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[GenericATSAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[GenericATSAdapter] No file input found on generic page.")
                return False
        except Exception as e:
            logger.error("[GenericATSAdapter] Error attaching resume: %s", e)
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
        Safety Constraint: GenericATSAdapter NEVER auto-submits.
        Always terminates at DRAFT_PENDING_REVIEW or MANUAL_REQUIRED.
        """
        resolutions = resolutions or []

        # Signup wall check (EC-PAA-SUB-03)
        if self.check_signup_wall(page):
            logger.warning("[GenericATSAdapter] Signup wall encountered -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_generic_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
                error_code="ACCOUNT_CREATION_REQUIRED",
                error_message="Platform requires signup before application."
            )

        has_low_confidence = any(
            r.confidence < config.confidence_threshold and r.resolution_tier != "tier3_llm_heavy"
            for r in resolutions
        )

        if has_low_confidence:
            logger.info("[GenericATSAdapter] Low confidence standard field -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_generic_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
            )

        # Enforce safety ceiling: GenericATSAdapter never auto-submits, even if mode is AUTO
        if mode == SubmissionMode.AUTO:
            logger.info("[GenericATSAdapter] AUTO mode requested, but GenericATSAdapter is restricted to DRAFT_PENDING_REVIEW (PAA-EP-1.0 §5).")

        return ApplicationAttemptResult(
            attempt_id=f"attempt_generic_{job.job_id}",
            job=job,
            resume_used=resume,
            status="DRAFT_PENDING_REVIEW",
            field_resolutions=resolutions,
        )
