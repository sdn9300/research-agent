"""
Attachment handling utility for verifying and resolving resume artifacts.
Implements the shared AttachmentHandler utility for Phase 1 and beyond.
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional

from .schemas import ResumeArtifact

logger = logging.getLogger(__name__)


class AttachmentHandler:
    """Verifies and resolves PDF resume artifacts before upload."""

    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Calculates the SHA-256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @staticmethod
    def get_verified_path(resume: ResumeArtifact) -> Optional[Path]:
        """
        Verifies the file exists and its checksum matches the artifact.
        Returns the resolved Path if valid, or None if invalid.
        """
        file_path = Path(resume.file_path)

        if not file_path.exists():
            logger.error(
                "[AttachmentHandler] Resume file not found at path: %s",
                file_path
            )
            return None

        if not file_path.is_file():
            logger.error(
                "[AttachmentHandler] Path is not a regular file: %s",
                file_path
            )
            return None

        actual_checksum = AttachmentHandler.calculate_checksum(file_path)
        if actual_checksum != resume.file_checksum:
            logger.error(
                "[AttachmentHandler] Checksum mismatch for %s. Expected: %s, Got: %s",
                file_path, resume.file_checksum, actual_checksum
            )
            return None

        logger.info("[AttachmentHandler] Verified resume artifact: %s", file_path)
        return file_path
