"""
Unit tests for Candidate Profile FastMCP Server Tools (Phase 4 v2.0).
Validates get_candidate_profile, get_candidate_projection, patch_candidate_section, and check_skill_provenance.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest

from candidate_profile.models import CandidateProfile, HistoryRef
from candidate_profile.storage import CandidateProfileStore
from candidate_profile.server import (
    check_skill_provenance,
    create_mcp_server,
    get_candidate_profile,
    get_candidate_projection,
    patch_candidate_section,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def setup_test_store(tmp_path: Path):
    """Initializes a clean CandidateProfileStore loaded with real profile for each test."""
    store = CandidateProfileStore(base_dir=tmp_path)
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        profile = CandidateProfile.model_validate_json(f.read())
    store.put(profile)

    # Inject into MCP server
    create_mcp_server(store=store)
    return store, profile


def test_mcp_get_candidate_profile(setup_test_store):
    """Tests get_candidate_profile FastMCP tool."""
    _, profile = setup_test_store
    cand_id = profile.profile_metadata.candidate_id

    # 1. Existing candidate
    res = get_candidate_profile(candidate_id=cand_id)
    assert "error" not in res
    assert res["identity"]["legal_name"] == "Soumyadeep Nath"
    assert res["profile_metadata"]["candidate_id"] == cand_id

    # 2. Non-existent candidate
    res_unknown = get_candidate_profile(candidate_id="unknown-uuid")
    assert "error" in res_unknown


def test_mcp_get_candidate_projection(setup_test_store):
    """Tests get_candidate_projection FastMCP tool across all projection types."""
    _, profile = setup_test_store
    cand_id = profile.profile_metadata.candidate_id

    # 1. AlignResume
    proj_resume = get_candidate_projection(candidate_id=cand_id, projection_type="align_resume")
    assert "error" not in proj_resume
    assert proj_resume["contact"]["name"] == "Soumyadeep Nath"
    assert "Python" in proj_resume["skills"]
    assert len(proj_resume["projects"]) == 3

    # 2. Gleaner
    proj_gleaner = get_candidate_projection(candidate_id=cand_id, projection_type="gleaner")
    assert "error" not in proj_gleaner
    assert proj_gleaner["role"] == "AI Engineer"
    assert proj_gleaner["location"] == "Remote"

    # 3. Overture
    proj_overture = get_candidate_projection(candidate_id=cand_id, projection_type="overture")
    assert "error" not in proj_overture
    assert proj_overture["candidate_name"] == "Soumyadeep Nath"
    assert proj_overture["email"] == "soumyadeepnath@example.com"

    # 4. Usher Views
    proj_usher_view = get_candidate_projection(candidate_id=cand_id, projection_type="usher")
    assert "error" not in proj_usher_view
    assert proj_usher_view["legal_name"] == "Soumyadeep Nath"

    proj_usher_prof = get_candidate_projection(candidate_id=cand_id, projection_type="usher_profile")
    assert "error" not in proj_usher_prof
    assert proj_usher_prof["full_name"] == "Soumyadeep Nath"

    # 5. Research Scope
    proj_research = get_candidate_projection(candidate_id=cand_id, projection_type="research")
    assert "error" not in proj_research
    assert "AI Engineer" in proj_research["target_roles"]

    # 6. Invalid projection type
    proj_bad = get_candidate_projection(candidate_id=cand_id, projection_type="invalid_type")
    assert "error" in proj_bad


def test_mcp_patch_candidate_section(setup_test_store):
    """Tests patch_candidate_section FastMCP tool for authorized writes and violation rejection."""
    store, profile = setup_test_store
    cand_id = profile.profile_metadata.candidate_id
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Authorized patch: AlignResume -> tailoring_history
    tailor_payload = {
        "run_id": "mcp-tailor-101",
        "component": "align_resume",
        "timestamp": now_iso,
        "outcome": "ats_tailored",
        "score": 0.96,
        "detail_ref": "align/runs/101.json",
    }
    patch_res = patch_candidate_section(
        candidate_id=cand_id,
        writer_component="align_resume",
        section="tailoring_history",
        value=tailor_payload,
    )
    assert patch_res["status"] == "success"
    assert patch_res["updated_section"] == "tailoring_history"

    # Verify persistence
    reloaded = store.get(cand_id)
    assert len(reloaded.tailoring_history) == 1
    assert reloaded.tailoring_history[0].run_id == "mcp-tailor-101"

    # 2. Unauthorized patch: Gleaner attempting to mutate identity
    bad_patch_res = patch_candidate_section(
        candidate_id=cand_id,
        writer_component="gleaner",
        section="identity",
        value={"legal_name": "Hacked Name"},
    )
    assert bad_patch_res["status"] == "error"
    assert bad_patch_res["error_type"] == "OwnershipViolationError"

    # Verify original identity remains unchanged
    reloaded_unhacked = store.get(cand_id)
    assert reloaded_unhacked.identity.legal_name == "Soumyadeep Nath"


def test_mcp_check_skill_provenance(setup_test_store):
    """Tests check_skill_provenance FastMCP tool for anti-fabrication truthfulness verification."""
    _, profile = setup_test_store
    cand_id = profile.profile_metadata.candidate_id

    # 1. Existing verified skill
    check_python = check_skill_provenance(candidate_id=cand_id, skill_name="Python")
    assert check_python["found"] is True
    assert check_python["skill_name"] == "Python"
    assert check_python["source_type"] == "resume_v12"
    assert check_python["verified"] is True
    assert "conductor-agent" in check_python["evidence_refs"]

    # 2. Case-insensitive skill matching
    check_langgraph = check_skill_provenance(candidate_id=cand_id, skill_name="langgraph")
    assert check_langgraph["found"] is True
    assert check_langgraph["skill_name"] == "LangGraph"

    # 3. Non-existent / fabricated skill
    check_fake = check_skill_provenance(candidate_id=cand_id, skill_name="Quantum Computing Fortran")
    assert check_fake["found"] is False
    assert "not in candidate's verified record" in check_fake["message"]
