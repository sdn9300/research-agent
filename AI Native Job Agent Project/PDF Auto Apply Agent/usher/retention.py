"""
Audit and Screenshot Retention Policy Manager for Usher (Phase 5).
Implements age-based pruning of screenshots and attempt artifacts to prevent unbounded disk growth.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from .config import config

logger = logging.getLogger(__name__)


class RetentionReport(BaseModel):
    screenshots_deleted: int = 0
    attempt_files_deleted: int = 0
    bytes_reclaimed: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetentionManager:
    """Manages age-based artifact lifecycle and disk space reclamation."""

    def __init__(
        self,
        screenshots_dir: Optional[Path] = None,
        attempts_dir: Optional[Path] = None,
        max_screenshot_age_days: Optional[int] = None,
        max_attempt_age_days: Optional[int] = None,
    ):
        self.screenshots_dir = screenshots_dir or config.full_screenshots_dir
        self.attempts_dir = attempts_dir or config.full_attempts_dir
        self.max_screenshot_age_days = (
            max_screenshot_age_days if max_screenshot_age_days is not None
            else config.retention.max_screenshot_age_days
        )
        self.max_attempt_age_days = (
            max_attempt_age_days if max_attempt_age_days is not None
            else config.retention.max_attempt_log_age_days
        )

    def clean_screenshots(self, max_age_days: Optional[int] = None) -> (int, int):
        """
        Deletes screenshot PNG files older than the specified max age.
        Returns (count_deleted, bytes_reclaimed).
        """
        age_days = max_age_days if max_age_days is not None else self.max_screenshot_age_days
        cutoff_time = time.time() - (age_days * 86400)
        deleted_count = 0
        reclaimed_bytes = 0

        if not self.screenshots_dir.exists():
            return 0, 0

        for file_path in self.screenshots_dir.glob("*.png"):
            try:
                stat = file_path.stat()
                if stat.st_mtime < cutoff_time:
                    size = stat.st_size
                    file_path.unlink()
                    deleted_count += 1
                    reclaimed_bytes += size
                    logger.debug("[RetentionManager] Purged old screenshot: %s", file_path.name)
            except Exception as e:
                logger.warning("[RetentionManager] Failed to purge %s: %s", file_path, e)

        logger.info(
            "[RetentionManager] Cleaned %d screenshots older than %d days (%d KB reclaimed).",
            deleted_count, age_days, reclaimed_bytes // 1024
        )
        return deleted_count, reclaimed_bytes

    def clean_attempt_logs(self, max_age_days: Optional[int] = None) -> (int, int):
        """
        Deletes individual attempt JSON artifacts older than the specified max age.
        Preserves core index files (memory_module_records.json, graduation_state.json, audit_log.jsonl).
        Returns (count_deleted, bytes_reclaimed).
        """
        age_days = max_age_days if max_age_days is not None else self.max_attempt_age_days
        cutoff_time = time.time() - (age_days * 86400)
        deleted_count = 0
        reclaimed_bytes = 0

        protected_files = {
            "memory_module_records.json",
            "graduation_state.json",
            "audit_log.jsonl",
        }

        if not self.attempts_dir.exists():
            return 0, 0

        for file_path in self.attempts_dir.glob("*.json"):
            if file_path.name in protected_files:
                continue

            try:
                stat = file_path.stat()
                if stat.st_mtime < cutoff_time:
                    size = stat.st_size
                    file_path.unlink()
                    deleted_count += 1
                    reclaimed_bytes += size
                    logger.debug("[RetentionManager] Purged old attempt record: %s", file_path.name)
            except Exception as e:
                logger.warning("[RetentionManager] Failed to purge %s: %s", file_path, e)

        logger.info(
            "[RetentionManager] Cleaned %d attempt logs older than %d days (%d KB reclaimed).",
            deleted_count, age_days, reclaimed_bytes // 1024
        )
        return deleted_count, reclaimed_bytes

    def run_retention_policy(self) -> RetentionReport:
        """Executes full retention policy across screenshots and attempt logs."""
        s_del, s_bytes = self.clean_screenshots()
        a_del, a_bytes = self.clean_attempt_logs()

        return RetentionReport(
            screenshots_deleted=s_del,
            attempt_files_deleted=a_del,
            bytes_reclaimed=s_bytes + a_bytes,
        )
