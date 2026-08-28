"""
Unit tests for Usher OutcomeRecorder and audit logging.
Verifies compliance with PAA-AD-1.0 §2, PAA-EP-1.0 §2.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from usher.config import UsherConfig
from usher.recorder import OutcomeRecorder
from usher.schemas import (
    ApplicationAttemptResult,
    FieldResolution,
    JobApplicationTarget,
    ResumeArtifact,
)


def test_outcome_recorder_write_and_retrieve():
    """Verify outcome recorder writes standalone JSON artifact and audit line."""
    with tempfile.TemporaryDirectory() as temp_dir:
        cfg = UsherConfig(
            base_dir=Path(temp_dir),
            attempts_dir="test_attempts",
            screenshots_dir="test_attempts/screenshots",
        )
        recorder = OutcomeRecorder(cfg=cfg)

        job = JobApplicationTarget(
            job_id="job_test_001",
            title="AI Systems Engineer",
            company="Anthropic Labs",
            apply_url="https://anthropic.com/careers/apply/001",
            source_platform="greenhouse",
        )

        resume = ResumeArtifact(
            tailoring_run_id="run_123",
            file_path="/path/to/resume.pdf",
            file_checksum="abcdef1234567890",
            profile_version="v1.0",
        )

        resolution = FieldResolution(
            field_label="Full Name",
            resolution_tier="tier0_selector",
            resolved_value="Soumyadeep Nath",
            confidence=1.0,
            source="candidate_profile",
        )

        result = ApplicationAttemptResult(
            attempt_id="attempt_test_9999",
            job=job,
            resume_used=resume,
            status="DRAFT_PENDING_REVIEW",
            field_resolutions=[resolution],
            groq_tokens_used=120,
            groq_cost_estimate_usd=0.0001,
        )

        # 1. Record attempt
        artifact_path = recorder.record_attempt(result)
        assert artifact_path.exists()

        # 2. Retrieve attempt by ID
        retrieved = recorder.get_attempt("attempt_test_9999")
        assert retrieved is not None
        assert retrieved.attempt_id == "attempt_test_9999"
        assert retrieved.status == "DRAFT_PENDING_REVIEW"
        assert retrieved.job.company == "Anthropic Labs"
        assert len(retrieved.field_resolutions) == 1
        assert retrieved.field_resolutions[0].resolved_value == "Soumyadeep Nath"

        # 3. Verify audit log entry
        audit_log = cfg.full_attempts_dir / "audit_log.jsonl"
        assert audit_log.exists()
        lines = audit_log.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        log_entry = json.loads(lines[0])
        assert log_entry["attempt_id"] == "attempt_test_9999"

        # 4. List attempts
        all_attempts = recorder.list_attempts()
        assert len(all_attempts) == 1
        assert all_attempts[0].attempt_id == "attempt_test_9999"
