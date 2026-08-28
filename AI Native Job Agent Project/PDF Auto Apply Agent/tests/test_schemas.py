"""
Unit tests for Usher Pydantic v2 schemas and data contracts.
Verifies compliance with PAA-AD-1.0 §3.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from pydantic import ValidationError

from usher.schemas import (
    ApplicationAttemptResult,
    ApplicationChannel,
    CandidateProfile,
    FieldResolution,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_candidate_profile_schema():
    """Verify CandidateProfile deserializes correctly from fixture."""
    fixture_path = FIXTURES_DIR / "sample_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    profile = CandidateProfile.model_validate(data)
    assert profile.full_name == "Soumyadeep Nath"
    assert profile.email == "soumyadeep@example.com"
    assert len(profile.education) == 1
    assert profile.education[0].institution == "Techno Main Salt Lake"
    assert len(profile.experience) == 1
    assert profile.experience[0].company == "AI Native Systems Lab"
    assert "Playwright" in profile.skills
    assert profile.salary_expectation == "12 LPA"
    assert profile.notice_period == "Immediate / 15 Days"


def test_job_application_target_schema():
    """Verify JobApplicationTarget validates valid and invalid URLs."""
    fixture_path = FIXTURES_DIR / "sample_job_target.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    job = JobApplicationTarget.model_validate(data)
    assert job.job_id == "job_naukri_ai_eng_99812"
    assert job.company == "Kolkata AI Labs"
    assert job.detected_channel == ApplicationChannel.NAUKRI

    # Invalid URL test
    with pytest.raises(ValidationError):
        JobApplicationTarget(
            job_id="job_invalid",
            title="AI Dev",
            company="Bad Company",
            apply_url="not-a-valid-url",
            source_platform="naukri",
        )


def test_resume_artifact_schema():
    """Verify ResumeArtifact fields and checksum presence."""
    fixture_path = FIXTURES_DIR / "sample_resume_artifact.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resume = ResumeArtifact.model_validate(data)
    assert resume.tailoring_run_id == "align_resume_run_881923"
    assert len(resume.file_checksum) == 64
    assert resume.profile_version == "a1b2c3d4e5f67890"


def test_field_resolution_confidence_bounds():
    """Verify confidence score is strictly bounded between 0.0 and 1.0."""
    res = FieldResolution(
        field_label="Email",
        resolution_tier="tier0_selector",
        resolved_value="soumyadeep@example.com",
        confidence=0.98,
        source="candidate_profile",
    )
    assert res.confidence == 0.98

    # Confidence > 1.0 must fail
    with pytest.raises(ValidationError):
        FieldResolution(
            field_label="Phone",
            resolution_tier="tier0_selector",
            resolved_value="123456",
            confidence=1.5,
            source="candidate_profile",
        )

    # Confidence < 0.0 must fail
    with pytest.raises(ValidationError):
        FieldResolution(
            field_label="Phone",
            resolution_tier="tier0_selector",
            resolved_value="123456",
            confidence=-0.1,
            source="candidate_profile",
        )


def test_application_attempt_result_lifecycle():
    """Verify ApplicationAttemptResult assembly across all valid status codes."""
    valid_statuses = [
        "SUBMITTED",
        "DRAFT_PENDING_REVIEW",
        "MANUAL_REQUIRED",
        "AMBIGUOUS_OUTCOME",
        "FAILED",
        "SKIPPED",
    ]

    job = JobApplicationTarget(
        job_id="job_123",
        title="Software Engineer",
        company="Tech Corp",
        apply_url="https://techcorp.com/careers/123",
        source_platform="indeed",
    )

    for status in valid_statuses:
        attempt = ApplicationAttemptResult(
            attempt_id=f"attempt_{status.lower()}",
            job=job,
            status=status,
            started_at=datetime.now(timezone.utc),
        )
        assert attempt.status == status

    # Invalid status must fail
    with pytest.raises(ValidationError):
        ApplicationAttemptResult(
            attempt_id="attempt_invalid",
            job=job,
            status="PROBABLY_WORKED",  # Explicitly forbidden by ADR-PAA-002 / PAA-AD-1.0
        )
