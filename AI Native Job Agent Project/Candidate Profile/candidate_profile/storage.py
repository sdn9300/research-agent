"""
Pluggable storage interface and atomic JSON file persistence for Candidate Profile.
Reference: CONDUCTOR-CP-AD-v1.0 (Architecture Design §5, ADR-CP-4, §11)
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from candidate_profile.models import CandidateProfile
from candidate_profile.migrations import (
    CURRENT_SCHEMA_VERSION,
    MigrationRegistry,
    default_migration_registry,
    migrate_profile,
)
from candidate_profile.observability import (
    record_profile_write,
    record_schema_version,
    record_validation_failure,
)


class PersistenceError(Exception):
    """Raised when profile persistence or atomic write verification fails."""
    pass


class CandidateProfileStore:
    """JSON file storage backend implementing atomic writes and versioning."""

    def __init__(
        self,
        base_dir: str | Path = "./data/candidate_profile",
        migration_registry: Optional[MigrationRegistry] = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.profiles_dir = self.base_dir / "profiles"
        self.versions_dir = self.base_dir / "versions"
        self.migration_registry = migration_registry or default_migration_registry

        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)

    def _get_profile_path(self, candidate_id: str) -> Path:
        return self.profiles_dir / f"{candidate_id}.json"

    def _get_versions_dir_for_candidate(self, candidate_id: str) -> Path:
        cand_versions_dir = self.versions_dir / candidate_id
        cand_versions_dir.mkdir(parents=True, exist_ok=True)
        return cand_versions_dir

    def get(self, candidate_id: str) -> Optional[CandidateProfile]:
        """Load and validate a candidate profile by candidate_id.

        If persisted under an older schema version, migrates through the migration chain.
        Returns None if profile does not exist.
        """
        profile_path = self._get_profile_path(candidate_id)
        if not profile_path.exists():
            return None

        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                raw_dict = json.load(f)
        except Exception as e:
            raise PersistenceError(f"Failed to read candidate profile at {profile_path}: {e}") from e

        # Handle version migration if necessary
        schema_version = raw_dict.get("profile_metadata", {}).get("schema_version", CURRENT_SCHEMA_VERSION)
        if schema_version != CURRENT_SCHEMA_VERSION:
            raw_dict = migrate_profile(
                raw_dict,
                target_version=CURRENT_SCHEMA_VERSION,
                registry=self.migration_registry,
            )

        try:
            profile = CandidateProfile.model_validate(raw_dict)
            record_schema_version(candidate_id, profile.profile_metadata.schema_version)
            return profile
        except ValidationError as e:
            record_validation_failure(field="storage_load")
            raise PersistenceError(f"Corrupted candidate profile data at {profile_path}: {e}") from e

    def put(self, profile: CandidateProfile) -> None:
        """Atomically persist a candidate profile.

        Writes to a temp file in the same directory, byte-verifies by re-parsing,
        and atomically renames over the target path. The prior valid file is never
        touched if verification or writing fails.
        """
        start_time = time.perf_counter()
        candidate_id = profile.profile_metadata.candidate_id
        last_writer = profile.profile_metadata.last_writer_component or "unknown"
        target_path = self._get_profile_path(candidate_id)

        # Serialize payload
        try:
            serialized_json = profile.model_dump_json(indent=2)
        except Exception as e:
            record_profile_write(component=last_writer, success=False, latency_sec=time.perf_counter() - start_time)
            raise PersistenceError(f"Failed to serialize CandidateProfile: {e}") from e

        # Write to temporary file in the target directory (ensuring atomic rename on the same filesystem)
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=self.profiles_dir,
                prefix=f"{candidate_id}_",
                suffix=".tmp",
                delete=False,
                encoding="utf-8",
            ) as f:
                temp_path = Path(f.name)
                temp_file = temp_path
                f.write(serialized_json)
                f.flush()
                os.fsync(f.fileno())

            # Byte-verify / re-parse integrity before atomic commit
            with open(temp_path, "r", encoding="utf-8") as f:
                verify_content = f.read()

            try:
                verified_profile = CandidateProfile.model_validate_json(verify_content)
                if verified_profile.profile_metadata.candidate_id != candidate_id:
                    raise ValueError("Candidate ID mismatch during verification")
            except Exception as val_err:
                record_validation_failure(field="atomic_byte_verify")
                raise PersistenceError(
                    f"Integrity verification failed for candidate {candidate_id}: {val_err}"
                ) from val_err

            # Atomically replace target path
            os.replace(temp_path, target_path)
            temp_file = None  # successfully renamed

            # Snapshot to version archive
            self._save_version_snapshot(candidate_id, serialized_json)

            # Record telemetry
            elapsed = time.perf_counter() - start_time
            record_profile_write(component=last_writer, success=True, latency_sec=elapsed)
            record_schema_version(candidate_id, profile.profile_metadata.schema_version)

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            record_profile_write(component=last_writer, success=False, latency_sec=elapsed)
            if temp_file and temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            if isinstance(e, PersistenceError):
                raise
            raise PersistenceError(f"Atomic write failed for candidate {candidate_id}: {e}") from e

    def _save_version_snapshot(self, candidate_id: str, content: str) -> None:
        """Save a timestamped snapshot of the profile."""
        versions_dir = self._get_versions_dir_for_candidate(candidate_id)
        now_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        version_file = versions_dir / f"v_{now_ts}.json"
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(content)

    def list_versions(self, candidate_id: str) -> List[str]:
        """List all recorded version snapshot tags for a candidate."""
        cand_versions_dir = self.versions_dir / candidate_id
        if not cand_versions_dir.exists():
            return []

        snapshots = sorted([f.stem for f in cand_versions_dir.glob("v_*.json")])
        return snapshots


# Default singleton instance for top-level convenience functions
_default_store = CandidateProfileStore()


def get(candidate_id: str) -> Optional[CandidateProfile]:
    """Retrieve CandidateProfile by candidate_id using default store."""
    return _default_store.get(candidate_id)


def put(profile: CandidateProfile) -> None:
    """Atomically persist CandidateProfile using default store."""
    _default_store.put(profile)


def list_versions(candidate_id: str) -> List[str]:
    """List version snapshot tags for candidate_id using default store."""
    return _default_store.list_versions(candidate_id)
