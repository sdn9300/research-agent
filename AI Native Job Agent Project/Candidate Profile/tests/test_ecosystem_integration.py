"""
Ecosystem integration tests verifying compatibility across:
- candidate_profile package installation
- Gleaner (#1) query parameterization
- AlignResume (#2) projection
- Overture (#3) outreach context
- Usher (#7) auto-apply schema compatibility
- Conductor Agent (#6) CandidateProfileBridge
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
import pytest

from candidate_profile import (
    CandidateProfile,
    CandidateProfileStore,
    HistoryRef,
    to_application_view,
    to_gleaner_query,
    to_outreach_context,
    to_resume_profile,
    to_usher_profile,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_profile() -> CandidateProfile:
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return CandidateProfile.model_validate_json(f.read())


def test_package_importability():
    """Verifies that candidate_profile is cleanly importable as an installed package."""
    import candidate_profile
    assert hasattr(candidate_profile, "CandidateProfile")
    assert hasattr(candidate_profile, "CandidateProfileStore")
    assert hasattr(candidate_profile, "to_gleaner_query")
    assert hasattr(candidate_profile, "to_usher_profile")
    assert hasattr(candidate_profile, "merge_candidate_profile")


def test_gleaner_query_integration(real_profile: CandidateProfile):
    """Verifies that to_gleaner_query generates parameters directly consumable by Gleaner."""
    gleaner_query = to_gleaner_query(real_profile)

    assert gleaner_query.role == "AI Engineer"
    assert gleaner_query.location == "Remote"
    assert "AI Engineer" in gleaner_query.target_roles
    assert "Remote" in gleaner_query.locations
    assert gleaner_query.remote_ok is True

    # Check that filters format can consume role and location
    role_keywords = gleaner_query.role.lower().split()
    assert "ai" in role_keywords
    assert "engineer" in role_keywords


def test_usher_schema_integration(real_profile: CandidateProfile):
    """Verifies that to_usher_profile generates data fully conforming to Usher's schema."""
    usher_prof = to_usher_profile(real_profile)

    assert usher_prof.full_name == "Soumyadeep Nath"
    assert usher_prof.email == "soumyadeepnath@example.com"
    assert usher_prof.location == "Remote / Hybrid"
    assert usher_prof.github_url == "https://github.com/sdn9300"
    assert len(usher_prof.education) == 1
    assert usher_prof.education[0].institution == "Techno Main Salt Lake"
    assert usher_prof.education[0].start_year == 2020
    assert usher_prof.education[0].end_year == 2024
    assert len(usher_prof.skills) >= 5
    assert len(usher_prof.experience) == 3


def test_conductor_bridge_workflow(real_profile: CandidateProfile, tmp_path: Path):
    """Verifies Conductor's CandidateProfileBridge end-to-end."""
    # Add Conductor Agent to sys.path if needed
    conductor_root = Path(__file__).parent.parent.parent / "Conductor Agent"
    if str(conductor_root) not in sys.path:
        sys.path.insert(0, str(conductor_root))

    from conductor.adapters.candidate_profile_bridge import CandidateProfileBridge

    store = CandidateProfileStore(base_dir=tmp_path)
    bridge = CandidateProfileBridge(store=store)

    # 1. Save profile
    bridge.save_profile(real_profile)

    # 2. Load profile
    cand_id = real_profile.profile_metadata.candidate_id
    loaded = bridge.load_profile(cand_id)
    assert loaded is not None

    # 3. Project for nodes
    resume = bridge.project_for_align_resume(loaded)
    gleaner = bridge.project_for_gleaner(loaded)
    overture = bridge.project_for_overture(loaded)
    usher_view = bridge.project_for_usher(loaded)
    usher_prof = bridge.project_for_usher_profile(loaded)

    assert resume.contact.name == "Soumyadeep Nath"
    assert gleaner.role == "AI Engineer"
    assert overture.candidate_name == "Soumyadeep Nath"
    assert usher_view.legal_name == "Soumyadeep Nath"
    assert usher_prof.full_name == "Soumyadeep Nath"

    # 4. Simulate AlignResume node applying tailoring patch
    now = datetime.now(timezone.utc)
    tailor_ref = HistoryRef(
        run_id="run-bridge-001",
        component="align_resume",
        timestamp=now,
        outcome="tailored_successfully",
        score=0.96,
        detail_ref="align/runs/run-bridge-001.json",
    )
    updated = bridge.apply_patch(
        current=loaded,
        writer_component="align_resume",
        section="tailoring_history",
        value=tailor_ref,
        persist=True,
    )

    assert len(updated.tailoring_history) == 1
    assert updated.profile_metadata.last_writer_component == "align_resume"

    # Verify persistence
    reloaded = bridge.load_profile(cand_id)
    assert reloaded is not None
    assert len(reloaded.tailoring_history) == 1
    assert reloaded.tailoring_history[0].run_id == "run-bridge-001"
