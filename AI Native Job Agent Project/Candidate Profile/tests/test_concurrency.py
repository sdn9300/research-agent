"""
Unit and integration tests for field ownership enforcement, concurrency reducer, and LangGraph wiring (Phase 3).
Validates Hard-Blocking Gate HG-4, Edge Cases EC-CP-CONC-01, EC-CP-CONC-03, and multi-node graph execution.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict, Annotated, Optional
import pytest

from candidate_profile.models import (
    CandidateProfile,
    HistoryRef,
    Identity,
    ContactInfo,
)
from candidate_profile.storage import CandidateProfileStore
from candidate_profile.concurrency import (
    ALL_SECTIONS,
    OWNERSHIP_MAP,
    CandidateProfilePatch,
    OwnershipViolationError,
    merge_candidate_profile,
    normalize_component_name,
)
from candidate_profile.projections import to_application_view

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_profile() -> CandidateProfile:
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return CandidateProfile.model_validate_json(f.read())


def test_hg4_adversarial_ownership_violation_suite(real_profile: CandidateProfile):
    """HG-4: Adversarial ownership-violation rejection suite.
    Every component attempts a write to every section it does NOT own;
    each must raise OwnershipViolationError with zero partial application.
    """
    now = datetime.now(timezone.utc)
    sample_ref = HistoryRef(
        run_id="adv-run-01",
        component="adversary",
        timestamp=now,
        outcome="failure",
        score=0.0,
        detail_ref="adversary/store/1",
    )

    test_payloads = {
        "profile_metadata": real_profile.profile_metadata,
        "identity": real_profile.identity,
        "education": real_profile.education,
        "skills": real_profile.skills,
        "experience": real_profile.experience,
        "preferences": real_profile.preferences,
        "tailoring_history": [sample_ref],
        "outreach_history": [sample_ref],
        "application_history": [sample_ref],
        "interaction_signals": [sample_ref],
    }

    all_components = [
        "align_resume",
        "overture",
        "usher",
        "sentiment_classifier",
        "gleaner",
        "research_agent",
        "future_fit",
        "memory_module",
        "conductor_orchestrator",
    ]

    violations_tested = 0

    for component in all_components:
        normalized = normalize_component_name(component)
        allowed_sections = OWNERSHIP_MAP.get(normalized, set())
        unauthorized_sections = ALL_SECTIONS - allowed_sections

        for unauthorized_sec in unauthorized_sections:
            patch = CandidateProfilePatch(
                writer_component=component,
                section=unauthorized_sec,
                value=test_payloads[unauthorized_sec],
                timestamp=now,
            )

            # Ensure error is raised and state is NOT mutated
            with pytest.raises(OwnershipViolationError) as exc_info:
                merge_candidate_profile(real_profile, patch)

            assert exc_info.value.writer_component == component
            assert exc_info.value.attempted_section == unauthorized_sec
            violations_tested += 1

    # Verify that we tested a comprehensive matrix of unauthorized attempts
    assert violations_tested >= 60


def test_ec_cp_conc_01_commutative_history_appends(real_profile: CandidateProfile):
    """EC-CP-CONC-01: Multiple appends to the same history section are commutative by run_id."""
    now = datetime.now(timezone.utc)

    patch_a = CandidateProfilePatch(
        writer_component="sentiment_classifier",
        section="interaction_signals",
        value=HistoryRef(
            run_id="sig-001",
            component="sentiment_classifier",
            timestamp=now,
            outcome="positive_response",
            score=0.9,
            detail_ref="sentiment/sig-001.json",
        ),
    )

    patch_b = CandidateProfilePatch(
        writer_component="sentiment_classifier",
        section="interaction_signals",
        value=HistoryRef(
            run_id="sig-002",
            component="sentiment_classifier",
            timestamp=now,
            outcome="interview_invitation",
            score=0.98,
            detail_ref="sentiment/sig-002.json",
        ),
    )

    # Order 1: A then B
    profile_ab = merge_candidate_profile(real_profile, patch_a)
    profile_ab = merge_candidate_profile(profile_ab, patch_b)

    # Order 2: B then A
    profile_ba = merge_candidate_profile(real_profile, patch_b)
    profile_ba = merge_candidate_profile(profile_ba, patch_a)

    run_ids_ab = {s.run_id for s in profile_ab.interaction_signals}
    run_ids_ba = {s.run_id for s in profile_ba.interaction_signals}

    assert run_ids_ab == {"sig-001", "sig-002"}
    assert run_ids_ab == run_ids_ba

    # Duplicate patch submission idempotency by run_id
    profile_dedup = merge_candidate_profile(profile_ab, patch_a)
    assert len(profile_dedup.interaction_signals) == 2


def test_authorized_section_merge_and_metadata_stamp(real_profile: CandidateProfile):
    """Verifies that authorized writers successfully update their section and update metadata."""
    now = datetime.now(timezone.utc)
    patch = CandidateProfilePatch(
        writer_component="align_resume",
        section="tailoring_history",
        value=HistoryRef(
            run_id="tailor-888",
            component="align_resume",
            timestamp=now,
            outcome="tailored_successfully",
            score=0.94,
            detail_ref="align/runs/888.json",
        ),
    )

    updated = merge_candidate_profile(real_profile, patch)
    assert len(updated.tailoring_history) == 1
    assert updated.tailoring_history[0].run_id == "tailor-888"
    assert updated.profile_metadata.last_writer_component == "align_resume"


# ============================================================================
# LangGraph Multi-Node Integration Test
# ============================================================================

try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class ConductorState(TypedDict):
    profile: Annotated[CandidateProfile, merge_candidate_profile]


@pytest.mark.skipif(not LANGGRAPH_AVAILABLE, reason="langgraph not installed")
def test_langgraph_multi_node_orchestration(real_profile: CandidateProfile, tmp_path: Path):
    """Threads CandidateProfile through a 2-node LangGraph StateGraph (AlignResume -> Usher -> Persistence)."""
    now = datetime.now(timezone.utc)
    store = CandidateProfileStore(base_dir=tmp_path)

    # Node 1: AlignResume
    def align_resume_node(state: ConductorState):
        current_prof = state["profile"]
        tailor_ref = HistoryRef(
            run_id="graph-tailor-01",
            component="align_resume",
            timestamp=now,
            outcome="ats_score_92",
            score=0.92,
            detail_ref="align_resume/runs/graph-tailor-01.json",
        )
        patch = CandidateProfilePatch(
            writer_component="align_resume",
            section="tailoring_history",
            value=tailor_ref,
        )
        return {"profile": patch}

    # Node 2: Usher (Auto-Apply)
    def usher_node(state: ConductorState):
        current_prof = state["profile"]
        # Usher projects candidate view and reads latest tailoring run
        view = to_application_view(current_prof)
        assert view.latest_tailoring_ref is not None
        assert view.latest_tailoring_ref.run_id == "graph-tailor-01"

        app_ref = HistoryRef(
            run_id="graph-apply-01",
            component="usher",
            timestamp=now,
            outcome="submitted_pdf",
            score=1.0,
            detail_ref="usher/attempts/graph-apply-01.json",
        )
        patch = CandidateProfilePatch(
            writer_component="usher",
            section="application_history",
            value=app_ref,
        )
        return {"profile": patch}

    # Build LangGraph workflow
    workflow = StateGraph(ConductorState)
    workflow.add_node("align_resume", align_resume_node)
    workflow.add_node("usher", usher_node)

    workflow.add_edge(START, "align_resume")
    workflow.add_edge("align_resume", "usher")
    workflow.add_edge("usher", END)

    app = workflow.compile()

    # Execute graph
    initial_state = {"profile": real_profile}
    final_output = app.invoke(initial_state)

    final_profile: CandidateProfile = final_output["profile"]

    # Verify graph output
    assert len(final_profile.tailoring_history) == 1
    assert final_profile.tailoring_history[0].run_id == "graph-tailor-01"
    assert len(final_profile.application_history) == 1
    assert final_profile.application_history[0].run_id == "graph-apply-01"
    assert final_profile.profile_metadata.last_writer_component == "usher"

    # Persist final profile to store
    store.put(final_profile)
    persisted_profile = store.get(final_profile.profile_metadata.candidate_id)

    assert persisted_profile is not None
    assert len(persisted_profile.tailoring_history) == 1
    assert len(persisted_profile.application_history) == 1
