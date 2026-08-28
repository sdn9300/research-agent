"""
Trust Graduation System for PDF Auto-Apply Agent ("Usher").
Tracks consecutive clean DRAFT-mode attempts per platform to unlock AUTO mode (PAA-EP-1.0 §5, PAA-AD-1.0 §8).
Enforces streak reset on failure/correction and permanent lockout on safety/ethics warnings.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel, Field

from .config import config
from .schemas import ApplicationChannel

logger = logging.getLogger(__name__)


class PlatformGraduationRecord(BaseModel):
    channel: ApplicationChannel
    consecutive_clean_runs: int = 0
    total_successful_runs: int = 0
    total_failed_runs: int = 0
    total_manual_corrections: int = 0
    is_auto_unlocked: bool = False
    is_locked_out: bool = False
    lockout_reason: Optional[str] = None


class PlatformGraduationTracker:
    """Manages trust graduation state and AUTO mode qualification across platforms."""

    def __init__(self, state_file_path: Optional[Path] = None):
        self.state_file = state_file_path or (config.base_dir / config.graduation.state_file)
        self.records: Dict[ApplicationChannel, PlatformGraduationRecord] = {}
        self._load_state()

    def _get_threshold(self, channel: ApplicationChannel) -> int:
        channel_key = channel.value if isinstance(channel, ApplicationChannel) else str(channel)
        return config.graduation.platform_thresholds.get(
            channel_key, config.graduation.default_threshold
        )

    def _load_state(self) -> None:
        """Loads graduation state from JSON file or initializes empty records."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                for key, data in raw_data.items():
                    try:
                        chan = ApplicationChannel(key)
                        self.records[chan] = PlatformGraduationRecord(**data)
                    except ValueError:
                        continue
                logger.info("[GraduationTracker] Loaded graduation state from %s", self.state_file)
                return
            except Exception as e:
                logger.warning("[GraduationTracker] Failed to load graduation state: %s. Starting fresh.", e)

        # Initialize defaults for all channels
        for channel in ApplicationChannel:
            self.records[channel] = PlatformGraduationRecord(channel=channel)

    def _save_state(self) -> None:
        """Persists graduation state to JSON file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                channel.value: record.model_dump()
                for channel, record in self.records.items()
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            logger.error("[GraduationTracker] Failed to save graduation state: %s", e)

    def get_record(self, channel: Optional[ApplicationChannel]) -> PlatformGraduationRecord:
        """Returns the graduation record for a given channel."""
        if not channel or channel == ApplicationChannel.UNSUPPORTED:
            return PlatformGraduationRecord(channel=ApplicationChannel.UNSUPPORTED)
        if channel not in self.records:
            self.records[channel] = PlatformGraduationRecord(channel=channel)
        return self.records[channel]

    def record_attempt(
        self,
        channel: Optional[ApplicationChannel],
        status: str,
        had_manual_corrections: bool = False,
    ) -> PlatformGraduationRecord:
        """
        Records the outcome of an attempt and updates graduation streak.
        - Clean DRAFT_PENDING_REVIEW or SUBMITTED without manual corrections -> advances streak.
        - Any failure or manual correction -> resets streak to 0 (Adaptive Examiner level-up logic).
        """
        if not channel or channel == ApplicationChannel.UNSUPPORTED:
            return PlatformGraduationRecord(channel=ApplicationChannel.UNSUPPORTED)

        record = self.get_record(channel)
        threshold = self._get_threshold(channel)

        if record.is_locked_out:
            logger.warning("[GraduationTracker] Channel %s is locked out; ignoring attempt record.", channel.value)
            return record

        is_clean_success = (status in ["SUBMITTED", "DRAFT_PENDING_REVIEW"]) and not had_manual_corrections

        if is_clean_success:
            record.consecutive_clean_runs += 1
            record.total_successful_runs += 1
            logger.info(
                "[GraduationTracker] Platform '%s' clean run #%d / %d",
                channel.value, record.consecutive_clean_runs, threshold
            )
            if record.consecutive_clean_runs >= threshold:
                if not record.is_auto_unlocked:
                    logger.info(
                        "[GraduationTracker] Platform '%s' graduated! AUTO mode unlocked.",
                        channel.value
                    )
                record.is_auto_unlocked = True
        else:
            # Reset streak upon failure or manual intervention
            logger.warning(
                "[GraduationTracker] Platform '%s' streak reset to 0 (status=%s, manual_corrections=%s)",
                channel.value, status, had_manual_corrections
            )
            if had_manual_corrections:
                record.total_manual_corrections += 1
            if status in ["FAILED", "MANUAL_REQUIRED"]:
                record.total_failed_runs += 1

            record.consecutive_clean_runs = 0
            record.is_auto_unlocked = False

        self._save_state()
        return record

    def is_auto_mode_unlocked(self, channel: Optional[ApplicationChannel]) -> bool:
        """Checks if AUTO mode is unlocked for the specified platform."""
        if not channel or channel == ApplicationChannel.UNSUPPORTED:
            return False
        record = self.get_record(channel)
        if record.is_locked_out:
            return False
        return record.is_auto_unlocked

    def lockout_platform(self, channel: ApplicationChannel, reason: str) -> None:
        """
        Permanently locks out a platform from AUTO mode (e.g. on security/compliance incident per EC-PAA-SEC-04).
        Requires manual reset.
        """
        record = self.get_record(channel)
        record.is_locked_out = True
        record.is_auto_unlocked = False
        record.consecutive_clean_runs = 0
        record.lockout_reason = reason
        logger.error(
            "[GraduationTracker] Platform '%s' locked out permanently: %s",
            channel.value, reason
        )
        self._save_state()

    def reset_platform(self, channel: ApplicationChannel) -> None:
        """Manually resets platform stats and clears lockout."""
        self.records[channel] = PlatformGraduationRecord(channel=channel)
        self._save_state()
