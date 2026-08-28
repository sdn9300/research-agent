"""
Core execution pipeline for CONDUCTOR Component 7 (PDF Auto-Apply Agent / Usher).
Orchestrates pre-flight guardrails, adapter execution, graduation updates, and memory persistence.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .adapters import get_adapter_for_url
from .browser import PlaywrightSessionManager
from .config import config
from .graduation import PlatformGraduationTracker
from .memory import MemoryModuleAdapter
from .recorder import OutcomeRecorder
from .schemas import (
    ApplicationAttemptResult,
    ApplicationChannel,
    CandidateProfile,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
)

logger = logging.getLogger(__name__)


class AutoApplyPipeline:
    """End-to-end orchestration pipeline for applying to a job opportunity."""

    def __init__(
        self,
        session_manager: Optional[PlaywrightSessionManager] = None,
        recorder: Optional[OutcomeRecorder] = None,
        graduation_tracker: Optional[PlatformGraduationTracker] = None,
        memory_adapter: Optional[MemoryModuleAdapter] = None,
    ):
        self.session_manager = session_manager or PlaywrightSessionManager()
        self.recorder = recorder or OutcomeRecorder()
        self.graduation_tracker = graduation_tracker or PlatformGraduationTracker()
        self.memory = memory_adapter or MemoryModuleAdapter()

    def _preflight_check(
        self,
        job: JobApplicationTarget,
        profile: CandidateProfile,
    ) -> Optional[ApplicationAttemptResult]:
        """
        Executes pre-flight guardrails before launching browser.
        Returns an ApplicationAttemptResult if the attempt must be halted early.
        """
        # EC-PAA-ETH-02: Scam / unverified company check
        if not job.is_verified_company:
            logger.warning("[Pipeline] Job %s at '%s' is not verified. Skipping (EC-PAA-ETH-02).", job.job_id, job.company)
            return ApplicationAttemptResult(
                attempt_id=f"attempt_{uuid.uuid4().hex[:12]}",
                job=job,
                status="SKIPPED",
                error_code="UNVERIFIED_COMPANY",
                error_message="Job target failed company authenticity verification.",
            )

        # EC-PAA-SUB-02 & EC-PAA-DAT-04: Duplicate target check against memory history
        if self.memory.has_applied(job.job_id, job.company, job.title):
            logger.info("[Pipeline] Already applied to job %s (%s at %s). Skipping.", job.job_id, job.title, job.company)
            return ApplicationAttemptResult(
                attempt_id=f"attempt_{uuid.uuid4().hex[:12]}",
                job=job,
                status="SKIPPED",
                error_code="ALREADY_APPLIED",
                error_message="Job target or near-duplicate previously attempted.",
            )

        # EC-PAA-DAT-01: Candidate Profile completeness check
        if not (profile.full_name and profile.email and profile.phone and profile.location):
            logger.error("[Pipeline] Candidate profile is missing mandatory contact fields (EC-PAA-DAT-01).")
            return ApplicationAttemptResult(
                attempt_id=f"attempt_{uuid.uuid4().hex[:12]}",
                job=job,
                status="SKIPPED",
                error_code="PROFILE_INCOMPLETE",
                error_message="Candidate profile missing required fields (full_name, email, phone, location).",
            )

        return None

    def execute(
        self,
        job: JobApplicationTarget,
        profile: CandidateProfile,
        resume: ResumeArtifact,
        mode: Optional[SubmissionMode] = None,
        custom_adapter=None,
    ) -> ApplicationAttemptResult:
        """
        Executes the full application flow for a target job.
        """
        start_time = datetime.now(timezone.utc)

        # 1. Run Pre-flight Checks
        preflight_result = self._preflight_check(job, profile)
        if preflight_result:
            self.recorder.save_attempt(preflight_result)
            self.memory.persist_attempt(preflight_result)
            return preflight_result

        # 2. Select Adapter
        adapter = custom_adapter or get_adapter_for_url(job.apply_url)
        if not adapter:
            logger.warning("[Pipeline] No adapter found for URL: %s", job.apply_url)
            result = ApplicationAttemptResult(
                attempt_id=f"attempt_{uuid.uuid4().hex[:12]}",
                job=job,
                resume_used=resume,
                status="MANUAL_REQUIRED",
                error_code="UNSUPPORTED_PLATFORM",
                error_message=f"No ATS adapter available for {job.apply_url}",
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )
            self.recorder.save_attempt(result)
            self.memory.persist_attempt(result)
            return result

        # 3. Determine Submission Mode (Honor trust graduation)
        channel = adapter.channel
        if mode:
            effective_mode = mode
        elif self.graduation_tracker.is_auto_mode_unlocked(channel):
            effective_mode = SubmissionMode.AUTO
            logger.info("[Pipeline] Platform '%s' graduated! Operating in AUTO mode.", channel.value)
        else:
            effective_mode = config.default_submission_mode

        # 4. Launch Browser Session and Execute Adapter Flow
        screenshot_path = None
        attempt_result = None

        try:
            with self.session_manager.create_session(channel.value) as (browser, browser_ctx, page):
                logger.info("[Pipeline] Navigating to apply URL: %s", job.apply_url)
                page.goto(job.apply_url, timeout=config.browser.timeout_ms)
                page.wait_for_load_state("domcontentloaded")

                # Field Mapping
                resolutions = adapter.map_fields(page, profile, job)

                # Form Filling
                adapter.fill(page, resolutions)

                # Resume Attachment
                adapter.attach_resume(page, resume)

                # Capture review screenshot before hold/submit
                temp_id = f"attempt_{job.job_id}_{int(start_time.timestamp())}"
                screenshot_path = str(self.session_manager.capture_screenshot(page, temp_id, suffix="review"))

                # Final Submit or Hold Gatekeeping
                attempt_result = adapter.submit_or_hold(
                    page=page,
                    mode=effective_mode,
                    job=job,
                    resume=resume,
                    resolutions=resolutions,
                )
                attempt_result.screenshot_path = screenshot_path
                attempt_result.started_at = start_time
                attempt_result.completed_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("[Pipeline] Execution failed with exception: %s", e)
            attempt_result = ApplicationAttemptResult(
                attempt_id=f"attempt_{uuid.uuid4().hex[:12]}",
                job=job,
                resume_used=resume,
                status="FAILED",
                error_code="EXECUTION_ERROR",
                error_message=str(e),
                screenshot_path=screenshot_path,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
            )

        # 5. Update Trust Graduation Tracker
        had_manual = (attempt_result.status == "MANUAL_REQUIRED")
        self.graduation_tracker.record_attempt(
            channel=channel,
            status=attempt_result.status,
            had_manual_corrections=had_manual,
        )

        # 6. Audit Recording & Memory Module Persistence
        self.recorder.save_attempt(attempt_result)
        self.memory.persist_attempt(attempt_result)

        logger.info(
            "[Pipeline] Completed application attempt %s with outcome: %s",
            attempt_result.attempt_id, attempt_result.status
        )
        return attempt_result
