"""
Unit tests for BaseATSAdapter interface contract and stub implementation.
Verifies compliance with PAA-AD-1.0 §4.
"""

from typing import List, Optional
from playwright.sync_api import Page

from usher.adapters.base import BaseATSAdapter
from usher.schemas import (
    ApplicationAttemptResult,
    ApplicationChannel,
    CandidateProfile,
    FieldResolution,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
)


class MockTestAdapter(BaseATSAdapter):
    """Concrete mock adapter for testing interface compliance."""

    def __init__(self):
        super().__init__(channel=ApplicationChannel.NAUKRI)

    def detect(self, page: Page, url: str) -> bool:
        return "naukri.com" in url

    def map_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        job: JobApplicationTarget,
    ) -> List[FieldResolution]:
        return [
            FieldResolution(
                field_label="Email",
                resolution_tier="tier0_selector",
                resolved_value=profile.email,
                confidence=1.0,
                source="candidate_profile",
                selector_used="input[name='email']",
            ),
            FieldResolution(
                field_label="Salary Expectation",
                resolution_tier="tier1_fuzzy",
                resolved_value=profile.salary_expectation,
                confidence=0.90,
                source="candidate_profile",
            ),
        ]

    def fill(
        self,
        page: Page,
        resolutions: List[FieldResolution],
    ) -> None:
        for res in resolutions:
            if res.confidence >= 0.85 and res.selector_used:
                # Mock action
                pass

    def attach_resume(
        self,
        page: Page,
        resume: ResumeArtifact,
    ) -> bool:
        return bool(resume.file_checksum)

    def submit_or_hold(
        self,
        page: Page,
        mode: SubmissionMode,
        job: JobApplicationTarget,
        resume: Optional[ResumeArtifact] = None,
        resolutions: Optional[List[FieldResolution]] = None,
    ) -> ApplicationAttemptResult:
        status = "DRAFT_PENDING_REVIEW" if mode == SubmissionMode.DRAFT else "SUBMITTED"
        return ApplicationAttemptResult(
            attempt_id=f"attempt_{job.job_id}",
            job=job,
            resume_used=resume,
            status=status,
            field_resolutions=resolutions or [],
        )


def test_mock_adapter_contract():
    """Verify BaseATSAdapter subclass implements all required abstract methods."""
    adapter = MockTestAdapter()
    assert adapter.name == "mocktest"
    assert adapter.channel == ApplicationChannel.NAUKRI

    job = JobApplicationTarget(
        job_id="job_naukri_01",
        title="AI Engineer",
        company="Naukri Hiring",
        apply_url="https://www.naukri.com/apply/01",
        source_platform="naukri",
    )

    profile = CandidateProfile(
        full_name="Soumyadeep Nath",
        email="soumyadeep@example.com",
        phone="+91 98765 43210",
        location="Kolkata, India",
        salary_expectation="12 LPA",
    )

    resume = ResumeArtifact(
        tailoring_run_id="run_999",
        file_path="/path/resume.pdf",
        file_checksum="hash1234",
        profile_version="v1",
    )

    # 1. Detection
    assert adapter.detect(page=None, url="https://www.naukri.com/apply/01") is True
    assert adapter.detect(page=None, url="https://www.indeed.com/apply/01") is False

    # 2. Field Mapping
    resolutions = adapter.map_fields(page=None, profile=profile, job=job)
    assert len(resolutions) == 2
    assert resolutions[0].resolved_value == "soumyadeep@example.com"
    assert resolutions[1].confidence >= 0.85

    # 3. Resume Attachment
    attached = adapter.attach_resume(page=None, resume=resume)
    assert attached is True

    # 4. Submission Gatekeeper (DRAFT mode)
    draft_result = adapter.submit_or_hold(
        page=None,
        mode=SubmissionMode.DRAFT,
        job=job,
        resume=resume,
        resolutions=resolutions,
    )
    assert draft_result.status == "DRAFT_PENDING_REVIEW"
    assert draft_result.job.job_id == "job_naukri_01"

    # 5. Submission Gatekeeper (AUTO mode)
    auto_result = adapter.submit_or_hold(
        page=None,
        mode=SubmissionMode.AUTO,
        job=job,
        resume=resume,
        resolutions=resolutions,
    )
    assert auto_result.status == "SUBMITTED"
