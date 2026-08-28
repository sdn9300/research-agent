"""
Unit and integration tests for Candidate Profile persistence, atomic writes, and version migrations.
Validates Phase 1 tasks, Hard-Blocking Gates (HG-2, HG-3, HG-5), and Edge Cases.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest

from candidate_profile.models import CandidateProfile
from candidate_profile.storage import CandidateProfileStore, PersistenceError
from candidate_profile.migrations import (
    CURRENT_SCHEMA_VERSION,
    MigrationRegistry,
    UnmigratableSchemaVersionError,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_profile() -> CandidateProfile:
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return CandidateProfile.model_validate_json(f.read())


@pytest.fixture
def temp_store(tmp_path: Path) -> CandidateProfileStore:
    return CandidateProfileStore(base_dir=tmp_path)


def test_hg2_round_trip_serialization_fidelity(real_profile: CandidateProfile, temp_store: CandidateProfileStore):
    """HG-2: Round-trip serialization fidelity.
    Pydantic -> JSON -> Pydantic and Pydantic -> Disk -> Pydantic on real fixture
    must produce field-for-field equivalence.
    """
    # 1. In-memory round-trip
    dumped_json = real_profile.model_dump_json()
    reloaded_profile = CandidateProfile.model_validate_json(dumped_json)

    assert reloaded_profile.identity.legal_name == real_profile.identity.legal_name
    assert reloaded_profile.identity.contact.email == real_profile.identity.contact.email
    assert len(reloaded_profile.skills) == len(real_profile.skills)
    assert len(reloaded_profile.experience) == len(real_profile.experience)
    assert reloaded_profile.preferences.target_roles == real_profile.preferences.target_roles
    assert reloaded_profile.model_dump() == real_profile.model_dump()

    # 2. Disk persistence round-trip
    temp_store.put(real_profile)
    disk_loaded = temp_store.get(real_profile.profile_metadata.candidate_id)

    assert disk_loaded is not None
    assert disk_loaded.model_dump() == real_profile.model_dump()


def test_hg3_and_ec_cp_pers_01_atomic_write_crash_safety(
    real_profile: CandidateProfile, temp_store: CandidateProfileStore, monkeypatch: pytest.MonkeyPatch
):
    """HG-3 & EC-CP-PERS-01 & EC-CP-CONC-02:
    Simulate crash/failure during write verification. The prior valid file must be untouched.
    """
    candidate_id = real_profile.profile_metadata.candidate_id
    # 1. Put initial valid profile
    temp_store.put(real_profile)

    initial_loaded = temp_store.get(candidate_id)
    assert initial_loaded is not None
    assert initial_loaded.identity.legal_name == "Soumyadeep Nath"

    # 2. Attempt to write an update, but simulate an error during byte-verification
    modified_profile = real_profile.model_copy(deep=True)
    modified_profile.identity.legal_name = "Corrupted Name Attempt"

    # Monkeypatch verification to raise error as if file verification or byte validation failed
    def mock_validate_json(json_str: str):
        raise ValueError("Simulated corrupt byte-verification failure")

    monkeypatch.setattr(CandidateProfile, "model_validate_json", mock_validate_json)

    with pytest.raises(PersistenceError) as exc_info:
        temp_store.put(modified_profile)

    assert "Integrity verification failed" in str(exc_info.value) or "Atomic write failed" in str(exc_info.value)

    # 3. Restore monkeypatch and verify original profile on disk is 100% intact
    monkeypatch.undo()

    reloaded = temp_store.get(candidate_id)
    assert reloaded is not None
    assert reloaded.identity.legal_name == "Soumyadeep Nath"
    assert reloaded.identity.legal_name != "Corrupted Name Attempt"

    # 4. Assert no leftover temp files in directory
    temp_files = list(temp_store.profiles_dir.glob("*.tmp"))
    assert len(temp_files) == 0


def test_hg5_and_ec_cp_migr_01_migration_chain(real_profile: CandidateProfile, tmp_path: Path):
    """HG-5 & EC-CP-MIGR-01 & EC-CP-MIGR-02:
    Schema version migration chain executes and converts older versions;
    unregistered version hops fail loudly with UnmigratableSchemaVersionError.
    """
    custom_registry = MigrationRegistry()

    # Register a synthetic migration: "0.9.0" -> "1.0.0" (e.g., adding default target_industries)
    @custom_registry.register(from_version="0.9.0", to_version="1.0.0")
    def migrate_0_9_to_1_0(data: dict) -> dict:
        data = dict(data)
        if "preferences" in data and "target_industries" not in data["preferences"]:
            data["preferences"]["target_industries"] = ["Technology"]
        return data

    store = CandidateProfileStore(base_dir=tmp_path, migration_registry=custom_registry)

    # 1. Create a legacy 0.9.0 raw dict
    raw_dict = json.loads(real_profile.model_dump_json())
    raw_dict["profile_metadata"]["schema_version"] = "0.9.0"
    raw_dict["preferences"].pop("target_industries", None)

    candidate_id = raw_dict["profile_metadata"]["candidate_id"]
    profile_path = store.profiles_dir / f"{candidate_id}.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(raw_dict, f)

    # 2. Loading should trigger migration to CURRENT_SCHEMA_VERSION ("1.0.0")
    migrated_profile = store.get(candidate_id)
    assert migrated_profile is not None
    assert migrated_profile.profile_metadata.schema_version == CURRENT_SCHEMA_VERSION
    assert migrated_profile.preferences.target_industries == ["Technology"]

    # 3. Test unmigratable schema version (EC-CP-MIGR-01)
    raw_dict["profile_metadata"]["schema_version"] = "0.1.0"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(raw_dict, f)

    with pytest.raises(UnmigratableSchemaVersionError) as exc_info:
        store.get(candidate_id)
    assert "No migration path registered" in str(exc_info.value)


def test_store_non_existent_candidate_returns_none(temp_store: CandidateProfileStore):
    """get() returns None for unknown candidate_id."""
    assert temp_store.get("non-existent-uuid") is None


def test_list_versions_records_snapshots(real_profile: CandidateProfile, temp_store: CandidateProfileStore):
    """list_versions() returns recorded snapshot history tags."""
    cand_id = real_profile.profile_metadata.candidate_id
    assert temp_store.list_versions(cand_id) == []

    temp_store.put(real_profile)
    versions = temp_store.list_versions(cand_id)
    assert len(versions) == 1
    assert versions[0].startswith("v_")

    # Put a second version
    temp_store.put(real_profile)
    versions_after = temp_store.list_versions(cand_id)
    assert len(versions_after) == 2
