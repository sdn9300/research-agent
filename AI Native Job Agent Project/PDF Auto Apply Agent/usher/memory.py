"""
Memory Module (CONDUCTOR Component 8) integration adapter for Usher.
Handles persistence of ApplicationAttemptResult records and pre-flight duplicate detection (EC-PAA-SUB-02, EC-PAA-DAT-04).
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from .config import config
from .schemas import ApplicationAttemptResult

logger = logging.getLogger(__name__)


class MemoryModuleAdapter:
    """Outbound adapter and local client for CONDUCTOR Component 8 (Memory Module)."""

    def __init__(self, storage_file_path: Optional[Path] = None):
        self.storage_file = storage_file_path or (config.base_dir / config.attempts_dir / "memory_module_records.json")
        self.attempts: List[ApplicationAttemptResult] = []
        self._job_id_index: Set[str] = set()
        self._target_signature_index: Set[str] = set()
        self._load_memory()

    def _generate_signature(self, company: str, title: str) -> str:
        """Generates normalized signature for duplicate target detection."""
        comp = company.strip().lower()
        tit = title.strip().lower()
        return f"{comp}::{tit}"

    def _load_memory(self) -> None:
        """Loads existing application history into in-memory index."""
        if not self.storage_file.exists():
            logger.info("[MemoryModule] Storage file %s does not exist. Initializing empty.", self.storage_file)
            return

        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                records = json.load(f)

            for rec in records:
                try:
                    result = ApplicationAttemptResult(**rec)
                    self.attempts.append(result)
                    self._job_id_index.add(result.job.job_id)
                    sig = self._generate_signature(result.job.company, result.job.title)
                    self._target_signature_index.add(sig)
                except Exception as ex:
                    logger.debug("[MemoryModule] Error parsing stored record: %s", ex)

            logger.info("[MemoryModule] Loaded %d application records from memory.", len(self.attempts))
        except Exception as e:
            logger.error("[MemoryModule] Failed to load memory store: %s", e)

    def _save_memory(self) -> None:
        """Persists all application records to disk."""
        try:
            self.storage_file.parent.mkdir(parents=True, exist_ok=True)
            data = [attempt.model_dump(mode="json") for attempt in self.attempts]
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error("[MemoryModule] Failed to save memory store: %s", e)

    def has_applied(self, job_id: str, company: str, title: str) -> bool:
        """
        Pre-flight check against past application history.
        Returns True if already applied by job_id (EC-PAA-SUB-02) or near-duplicate (EC-PAA-DAT-04).
        """
        if job_id in self._job_id_index:
            logger.info("[MemoryModule] Job ID '%s' already exists in history.", job_id)
            return True

        sig = self._generate_signature(company, title)
        if sig in self._target_signature_index:
            logger.info("[MemoryModule] Near-duplicate target '%s' at '%s' already attempted.", title, company)
            return True

        return False

    def persist_attempt(self, result: ApplicationAttemptResult) -> None:
        """
        Appends an application attempt result into Component 8's persistent store.
        Updates index immediately.
        """
        self.attempts.append(result)
        self._job_id_index.add(result.job.job_id)
        sig = self._generate_signature(result.job.company, result.job.title)
        self._target_signature_index.add(sig)
        self._save_memory()
        logger.info(
            "[MemoryModule] Persisted attempt '%s' (status: %s) for job '%s'.",
            result.attempt_id, result.status, result.job.title
        )

    def get_stats(self) -> Dict[str, int]:
        """Returns summary statistics across stored applications."""
        stats: Dict[str, int] = {
            "total": len(self.attempts),
            "SUBMITTED": 0,
            "DRAFT_PENDING_REVIEW": 0,
            "MANUAL_REQUIRED": 0,
            "AMBIGUOUS_OUTCOME": 0,
            "FAILED": 0,
            "SKIPPED": 0,
        }
        for a in self.attempts:
            stats[a.status] = stats.get(a.status, 0) + 1
        return stats
