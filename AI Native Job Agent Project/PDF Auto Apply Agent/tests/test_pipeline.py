from unittest.mock import MagicMock
from pathlib import Path
from usher.pipeline import AutoApplyPipeline
from usher.memory import MemoryModuleAdapter
from usher.graduation import PlatformGraduationTracker
from usher.recorder import OutcomeRecorder
from usher.schemas import CandidateProfile, JobApplicationTarget, ResumeArtifact, SubmissionMode

def make_profile(**kwargs):
    defaults = {
        "full_name": "Soumyadeep Nath",
        "email": "soumyadeep@example.com",
        "phone": "+919876543210",
        "location": "Kolkata, India"
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)

def make_job(**kwargs):
    defaults = {
        "job_id": "pipeline_101",
        "title": "Senior AI Researcher",
        "company": "Anthropic",
        "apply_url": "https://boards.greenhouse.io/anthropic/jobs/101",
        "source_platform": "greenhouse",
        "is_verified_company": True
    }
    defaults.update(kwargs)
    return JobApplicationTarget(**defaults)

def make_resume(tmp_path):
    f = tmp_path / "resume.pdf"
    f.write_bytes(b"%PDF-1.4 mock")
    from usher.attachment import AttachmentHandler
    checksum = AttachmentHandler.calculate_checksum(f)
    return ResumeArtifact(
        tailoring_run_id="tailor_101",
        file_path=str(f),
        file_checksum=checksum,
        profile_version="v1"
    )

def test_pipeline_preflight_unverified_company(tmp_path):
    """EC-PAA-ETH-02: Unverified company target is skipped."""
    pipeline = AutoApplyPipeline(
        memory_adapter=MemoryModuleAdapter(tmp_path / "mem.json"),
        graduation_tracker=PlatformGraduationTracker(tmp_path / "grad.json"),
        recorder=OutcomeRecorder()
    )

    job = make_job(is_verified_company=False)
    profile = make_profile()
    resume = make_resume(tmp_path)

    result = pipeline.execute(job, profile, resume)
    assert result.status == "SKIPPED"
    assert result.error_code == "UNVERIFIED_COMPANY"

def test_pipeline_preflight_duplicate_target(tmp_path):
    """EC-PAA-SUB-02: Already applied target is skipped."""
    mem = MemoryModuleAdapter(tmp_path / "mem.json")
    pipeline = AutoApplyPipeline(
        memory_adapter=mem,
        graduation_tracker=PlatformGraduationTracker(tmp_path / "grad.json"),
        recorder=OutcomeRecorder()
    )

    job = make_job()
    profile = make_profile()
    resume = make_resume(tmp_path)

    # First attempt persisted to memory
    from usher.schemas import ApplicationAttemptResult
    res = ApplicationAttemptResult(
        attempt_id="att_101",
        job=job,
        status="DRAFT_PENDING_REVIEW"
    )
    pipeline.memory.persist_attempt(res)

    # Second attempt on same job
    result2 = pipeline.execute(job, profile, resume)
    assert result2.status == "SKIPPED"
    assert result2.error_code == "ALREADY_APPLIED"

def test_pipeline_preflight_incomplete_profile(tmp_path):
    """EC-PAA-DAT-01: Incomplete candidate profile is skipped."""
    pipeline = AutoApplyPipeline(
        memory_adapter=MemoryModuleAdapter(tmp_path / "mem.json"),
        graduation_tracker=PlatformGraduationTracker(tmp_path / "grad.json"),
        recorder=OutcomeRecorder()
    )

    job = make_job()
    profile = make_profile(full_name="")
    resume = make_resume(tmp_path)

    result = pipeline.execute(job, profile, resume)
    assert result.status == "SKIPPED"
    assert result.error_code == "PROFILE_INCOMPLETE"
