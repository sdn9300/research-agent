"""
Outcome Recorder and Audit Logger for Usher.
Ensures every application attempt produces a persisted, structured JSON artifact
and replayable audit trail (PAA-AD-1.0 §2, PAA-EP-1.0 §2).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .config import UsherConfig, config as default_config
from .schemas import ApplicationAttemptResult

logger = logging.getLogger(__name__)


class OutcomeRecorder:
    """Persists structured ApplicationAttemptResult records and maintains audit logs."""

    def __init__(self, cfg: Optional[UsherConfig] = None):
        self.config = cfg or default_config

    def record_attempt(self, result: ApplicationAttemptResult) -> Path:
        """
        Saves the attempt result as a standalone JSON artifact and appends to audit log.
        Guarantees fallback-artifact principle: no attempt is dropped silently.
        """
        if not result.completed_at:
            result.completed_at = datetime.now(timezone.utc)

        # 1. Save individual attempt JSON artifact
        attempt_filename = f"{result.attempt_id}.json"
        artifact_path = self.config.full_attempts_dir / attempt_filename

        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        # 2. Append single-line JSON to attempts audit log
        audit_log_path = self.config.full_attempts_dir / "audit_log.jsonl"
        with open(audit_log_path, "a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")

        logger.info(
            "[OutcomeRecorder] Recorded attempt %s with status %s to %s",
            result.attempt_id,
            result.status,
            artifact_path,
        )
        return artifact_path

    # Alias for pipeline consistency
    save_attempt = record_attempt

    def get_attempt(self, attempt_id: str) -> Optional[ApplicationAttemptResult]:
        """Loads a previously recorded attempt result by ID."""
        artifact_path = self.config.full_attempts_dir / f"{attempt_id}.json"
        if not artifact_path.exists():
            return None

        with open(artifact_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ApplicationAttemptResult.model_validate(data)

    def list_attempts(self, limit: int = 100) -> List[ApplicationAttemptResult]:
        """Returns the most recent attempt records."""
        attempts = []
        for file_path in sorted(self.config.full_attempts_dir.glob("*.json"), reverse=True):
            if file_path.name == "audit_log.json":
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                attempts.append(ApplicationAttemptResult.model_validate(data))
                if len(attempts) >= limit:
                    break
            except Exception as e:
                logger.warning("[OutcomeRecorder] Failed to parse %s: %s", file_path, e)
        return attempts
