from unittest.mock import MagicMock, patch
from pathlib import Path
from usher.conductor import auto_apply_node, run_auto_apply_pipeline
from usher.schemas import (
    CandidateProfile,
    ConductorState,
    JobApplicationTarget,
    ResumeArtifact,
    SubmissionMode,
    ApplicationAttemptResult,
)

import uuid

def make_sample_data(tmp_path):
    f = tmp_path / "tailored_resume.pdf"
    f.write_bytes(b"%PDF-1.4 sample content")
    from usher.attachment import AttachmentHandler
    checksum = AttachmentHandler.calculate_checksum(f)

    uid = uuid.uuid4().hex[:8]
    job = JobApplicationTarget(
        job_id=f"conductor_{uid}",
        title=f"Lead ML Engineer {uid}",
        company=f"OpenAI_{uid}",
        apply_url=f"https://boards.greenhouse.io/openai/jobs/{uid}",
        source_platform="greenhouse",
        is_verified_company=True
    )
    profile = CandidateProfile(
        full_name="Soumyadeep Nath",
        email="soumyadeep@example.com",
        phone="+919876543210",
        location="Kolkata, India"
    )
    resume = ResumeArtifact(
        tailoring_run_id="run_align_999",
        file_path=str(f),
        file_checksum=checksum,
        profile_version="v2.1"
    )
    return job, profile, resume

def test_conductor_langgraph_node_execution(tmp_path):
    job, profile, resume = make_sample_data(tmp_path)

    state = {
        "job": job.model_dump(),
        "profile": profile.model_dump(),
        "resume": resume.model_dump(),
        "research_brief": "OpenAI builds frontier AI systems.",
        "submission_mode": "draft"
    }

    # Execute LangGraph node function
    output_state = auto_apply_node(state)

    assert "attempt_result" in output_state
    attempt = output_state["attempt_result"]
    assert attempt is not None
    assert attempt["job"]["job_id"] == job.job_id
    assert attempt["status"] in ["DRAFT_PENDING_REVIEW", "SUBMITTED", "MANUAL_REQUIRED"]
    assert output_state["error"] is None

def test_conductor_langgraph_node_handles_error():
    # Pass malformed state
    bad_state = {
        "job": {"invalid": "data"},
        "profile": {},
        "resume": {}
    }

    output_state = auto_apply_node(bad_state)
    assert output_state["error"] is not None
