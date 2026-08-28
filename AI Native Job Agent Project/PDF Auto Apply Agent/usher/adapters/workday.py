"""
Workday ATS adapter implementation for Usher Phase 3.
Handles Workday job applications (myworkdayjobs.com) with account wall detection (EC-PAA-SUB-03).
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


class WorkdayAdapter(BaseATSAdapter):
    """Adapter for Workday job portals (myworkdayjobs.com / workday.com)."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.GENERIC_ATS_WORKDAY)
        self.resolver = FieldResolver()
        self._setup_resolver()

    def _setup_resolver(self):
        """Populates Tier-0 and Tier-1 dictionaries for Workday standard fields."""
        # Tier 0 Exact matches
        self.resolver.register_tier0("first name", lambda p: p.full_name.split()[0] if p.full_name else "")
        self.resolver.register_tier0("last name", lambda p: " ".join(p.full_name.split()[1:]) if len(p.full_name.split()) > 1 else "")
        self.resolver.register_tier0("email address", lambda p: p.email)
        self.resolver.register_tier0("email", lambda p: p.email)
        self.resolver.register_tier0("phone number", lambda p: p.phone)
        self.resolver.register_tier0("phone", lambda p: p.phone)
        self.resolver.register_tier0("city", lambda p: p.location.split(",")[0].strip() if p.location else "")
        self.resolver.register_tier0("postal code", lambda p: "700001")

        # Tier 1 Fuzzy matches
        self.resolver.register_tier1("work authorization", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("authorized to work", lambda p: p.work_authorization or "Yes")
        self.resolver.register_tier1("sponsorship", lambda p: "No")
        self.resolver.register_tier1("how did you hear about us", lambda p: "Job Board")
        self.resolver.register_tier1("notice period", lambda p: p.notice_period or "")

    def detect(self, page: Page, url: str) -> bool:
        """Returns True if the URL or DOM matches Workday signatures."""
        url_lower = url.lower()
        if "myworkdayjobs.com" in url_lower or "workday.com" in url_lower:
            return True

        try:
            if page.locator("[data-automation-id='workdayApplication'], [data-automation-id='applyButton']").count() > 0:
                return True
        except Exception:
            pass

        return False

    def check_account_wall(self, page: Page) -> bool:
        """
        Detects mandatory account creation / login barrier on Workday (EC-PAA-SUB-03).
        Workday account creation is out of scope through Phase 3 -> routes to MANUAL_REQUIRED.
        """
        try:
            account_wall_selectors = [
                "[data-automation-id='createAccountLink']",
                "[data-automation-id='signInLink']",
                "a:has-text('Create Account')",
                "button:has-text('Create Account')",
                "input[data-automation-id='password']",
                "text='Create an Account'",
                "text='Sign in to your account'",
            ]
            for sel in account_wall_selectors:
                if page.locator(sel).count() > 0:
                    logger.warning("[WorkdayAdapter] Account creation wall detected via selector: %s", sel)
                    return True
        except Exception as e:
            logger.debug("[WorkdayAdapter] Error checking account wall: %s", e)
        return False

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        """
        Extracts visible form inputs from Workday application page and resolves them.
        """
        resolutions: List[FieldResolution] = []

        try:
            page.wait_for_selector("input, select, textarea", timeout=5000)
            inputs = page.locator("input:visible, select:visible, textarea:visible").all()

            for inp in inputs:
                input_type = inp.get_attribute("type") or "text"
                if input_type in ["hidden", "submit", "button", "file", "password"]:
                    continue

                label_id = inp.get_attribute("id")
                data_automation_id = inp.get_attribute("data-automation-id")
                label_text = ""

                if label_id:
                    label_el = page.locator(f"label[for='{label_id}']")
                    if label_el.count() > 0:
                        label_text = label_el.first.inner_text().strip()

                if not label_text and data_automation_id:
                    # Workday often puts readable tokens in data-automation-id (e.g. legalNameSection_firstName)
                    cleaned = data_automation_id.replace("legalNameSection_", "").replace("addressSection_", "")
                    label_text = " ".join([word.lower() for word in cleaned.split("_")])

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

                if data_automation_id:
                    res.selector_used = f"[data-automation-id='{data_automation_id}']"
                elif label_id:
                    res.selector_used = f"#{label_id}"
                elif inp.get_attribute("name"):
                    res.selector_used = f"[name='{inp.get_attribute('name')}']"
                else:
                    res.selector_used = None

                resolutions.append(res)

        except PlaywrightTimeoutError:
            logger.warning("[WorkdayAdapter] Timeout waiting for Workday form inputs.")
        except Exception as e:
            logger.error("[WorkdayAdapter] Error during field mapping: %s", e)

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
                    logger.info("[WorkdayAdapter] Filling '%s' (confidence: %.2f)", res.field_label, res.confidence)
                    page.fill(res.selector_used, res.resolved_value)
                except Exception as e:
                    logger.warning("[WorkdayAdapter] Failed to fill field '%s': %s", res.field_label, e)

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        """Attaches the verified resume PDF to Workday file upload input."""
        file_path = AttachmentHandler.get_verified_path(resume)
        if not file_path:
            return False

        try:
            file_input = page.locator("[data-automation-id='file-upload-input-drop-zone'], input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(file_path))
                logger.info("[WorkdayAdapter] Attached resume %s successfully.", file_path.name)
                return True
            else:
                logger.warning("[WorkdayAdapter] No Workday resume upload input found.")
                return False
        except Exception as e:
            logger.error("[WorkdayAdapter] Error attaching resume: %s", e)
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
        Enforces DRAFT pause vs. AUTO mode on Workday.
        Checks for Account Creation Wall (EC-PAA-SUB-03) -> MANUAL_REQUIRED.
        """
        resolutions = resolutions or []

        # Account creation / signup wall check (EC-PAA-SUB-03)
        if self.check_account_wall(page):
            logger.warning("[WorkdayAdapter] Account creation wall encountered -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_workday_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
                error_code="ACCOUNT_CREATION_REQUIRED",
                error_message="Platform requires account creation before application can proceed."
            )

        has_low_confidence = any(
            r.confidence < config.confidence_threshold and r.resolution_tier != "tier3_llm_heavy"
            for r in resolutions
        )
        has_tier3_free_text = any(r.resolution_tier == "tier3_llm_heavy" for r in resolutions)

        if has_low_confidence:
            logger.info("[WorkdayAdapter] Low confidence standard field -> MANUAL_REQUIRED.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_workday_{job.job_id}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                field_resolutions=resolutions,
            )

        if has_tier3_free_text or mode == SubmissionMode.DRAFT:
            logger.info("[WorkdayAdapter] Pausing at DRAFT_PENDING_REVIEW.")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_workday_{job.job_id}",
                job=job,
                resume_used=resume,
                status="DRAFT_PENDING_REVIEW",
                field_resolutions=resolutions,
            )

        if mode == SubmissionMode.AUTO:
            try:
                submit_btn = page.locator("[data-automation-id='bottom-navigation-next-button']:has-text('Submit'), button:has-text('Submit Application')")
                if submit_btn.count() > 0:
                    submit_btn.first.click()
                    logger.info("[WorkdayAdapter] AUTO mode: Submit clicked.")
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_workday_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="SUBMITTED",
                        field_resolutions=resolutions,
                    )
                else:
                    return ApplicationAttemptResult(
                        attempt_id=f"attempt_workday_{job.job_id}",
                        job=job,
                        resume_used=resume,
                        status="AMBIGUOUS_OUTCOME",
                        field_resolutions=resolutions,
                        error_message="Submit button not found on Workday application page."
                    )
            except Exception as e:
                logger.error("[WorkdayAdapter] AUTO submit failed: %s", e)
                return ApplicationAttemptResult(
                    attempt_id=f"attempt_workday_{job.job_id}",
                    job=job,
                    resume_used=resume,
                    status="FAILED",
                    field_resolutions=resolutions,
                    error_message=str(e),
                )

        return ApplicationAttemptResult(
            attempt_id=f"attempt_workday_{job.job_id}",
            job=job,
            resume_used=resume,
            status="SKIPPED",
            field_resolutions=resolutions,
        )
