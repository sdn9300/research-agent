"""
Unit tests for Candidate Profile per-component projections and adapters (Phase 2).
Validates projections for AlignResume, Gleaner, Overture, Usher, and Research Agent.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from pydantic import ValidationError

from candidate_profile.models import (
    ApplicationPreferences,
    CandidateProfile,
    ContactInfo,
    EducationRecord,
    ExperienceRecord,
    HistoryRef,
    Identity,
    ProficiencyLevel,
    ProfileMetadata,
    SkillRecord,
    SourceProvenance,
)
from candidate_profile.projections import (
    ApplicationView,
    GleanerQuery,
    OutreachContext,
    ResearchScope,
    ResumeProfile,
    to_application_view,
    to_gleaner_query,
    to_outreach_context,
    to_research_scope,
    to_resume_profile,
    to_search_criteria,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_profile() -> CandidateProfile:
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return CandidateProfile.model_validate_json(f.read())


def test_to_resume_profile_align_resume_retrofit(real_profile: CandidateProfile):
    """Verifies AlignResume's ResumeProfile projection and experience partitioning."""
    resume = to_resume_profile(real_profile)

    assert isinstance(resume, ResumeProfile)
    assert resume.contact.name == "Soumyadeep Nath"
    assert resume.contact.email == "soumyadeepnath@example.com"
    assert "https://github.com/sdn9300" in resume.contact.links
    assert "https://www.linkedin.com/in/sdn9300" in resume.contact.links

    # Skills mapped cleanly
    assert "Python" in resume.skills
    assert "LangGraph" in resume.skills
    assert "TypeScript" in resume.skills

    # Real profile experiences are all projects -> mapped to resume.projects
    assert len(resume.projects) == 3
    project_names = [p.name for p in resume.projects]
    assert "Conductor Agent (Lead Architect & Developer)" in project_names
    assert "AlignResume (AI-Powered Resume Optimization Platform)" in project_names
    assert "Overture (Smart Cold Email Outreach Platform)" in project_names

    # Education mapped
    assert len(resume.education) == 1
    assert resume.education[0].school == "Techno Main Salt Lake"
    assert resume.education[0].degree == "Bachelor of Technology in Computer Science and Engineering"


def test_to_resume_profile_employment_partitioning():
    """Verifies that kind='employment' items are mapped to experience rather than projects."""
    now = datetime.now(timezone.utc)
    prov = SourceProvenance(source_type="manual", recorded_at=now)

    profile = CandidateProfile(
        profile_metadata=ProfileMetadata(
            candidate_id="cand-emp-1",
            created_at=now,
            updated_at=now,
            last_writer_component="test",
        ),
        identity=Identity(
            legal_name="Bob Worker",
            location="Remote",
            contact=ContactInfo(email="bob@example.com"),
        ),
        education=[],
        skills=[],
        experience=[
            ExperienceRecord(
                title="Senior Backend Engineer at TechCorp",
                kind="employment",
                stack=["Go", "PostgreSQL"],
                bullets=["Scaled API to 10k RPS"],
                source=prov,
            ),
            ExperienceRecord(
                title="SideProject Alpha",
                kind="project",
                stack=["Python"],
                bullets=["Built side project"],
                source=prov,
            ),
        ],
        preferences=ApplicationPreferences(
            target_roles=["Backend Engineer"],
            locations=["Remote"],
        ),
    )

    resume = to_resume_profile(profile)
    assert len(resume.experience) == 1
    assert resume.experience[0].title == "Senior Backend Engineer at TechCorp"
    assert resume.experience[0].bullets == ["Scaled API to 10k RPS"]

    assert len(resume.projects) == 1
    assert resume.projects[0].name == "SideProject Alpha"
    assert resume.projects[0].technologies == ["Python"]


def test_to_gleaner_query_and_to_search_criteria(real_profile: CandidateProfile):
    """Verifies Gleaner search parameterization projection."""
    query = to_gleaner_query(real_profile)
    criteria = to_search_criteria(real_profile)

    assert isinstance(query, GleanerQuery)
    assert query.role == "AI Engineer"
    assert query.location == "Remote"
    assert "AI Engineer" in query.target_roles
    assert "Agentic Systems Engineer" in query.target_roles
    assert "Remote" in query.locations
    assert query.remote_ok is True
    assert "Artificial Intelligence" in query.target_industries

    assert criteria.model_dump() == query.model_dump()


def test_to_outreach_context(real_profile: CandidateProfile):
    """Verifies Overture cold email campaign context projection."""
    ctx = to_outreach_context(real_profile)

    assert isinstance(ctx, OutreachContext)
    assert ctx.candidate_name == "Soumyadeep Nath"
    assert ctx.email == "soumyadeepnath@example.com"
    assert ctx.phone == "+91-9876543210"
    assert ctx.github == "https://github.com/sdn9300"
    assert "AI Engineer" in ctx.target_roles
    assert "Artificial Intelligence" in ctx.target_industries


def test_to_application_view_and_ec_cp_int_01(real_profile: CandidateProfile):
    """Verifies Usher application view projection and EC-CP-INT-01 (empty tailoring history)."""
    # 1. Empty tailoring history (EC-CP-INT-01)
    view_empty = to_application_view(real_profile)
    assert isinstance(view_empty, ApplicationView)
    assert view_empty.candidate_id == real_profile.profile_metadata.candidate_id
    assert view_empty.legal_name == "Soumyadeep Nath"
    assert view_empty.tailoring_history == []
    assert view_empty.latest_tailoring_ref is None

    # 2. Populated tailoring history
    now = datetime.now(timezone.utc)
    profile_with_history = real_profile.model_copy(deep=True)
    history_item_1 = HistoryRef(
        run_id="run-1",
        component="AlignResume",
        timestamp=now,
        outcome="success",
        score=0.85,
        detail_ref="align/runs/1.json",
    )
    history_item_2 = HistoryRef(
        run_id="run-2",
        component="AlignResume",
        timestamp=now,
        outcome="success",
        score=0.95,
        detail_ref="align/runs/2.json",
    )
    profile_with_history.tailoring_history = [history_item_1, history_item_2]

    view_populated = to_application_view(profile_with_history)
    assert len(view_populated.tailoring_history) == 2
    assert view_populated.latest_tailoring_ref is not None
    assert view_populated.latest_tailoring_ref.run_id == "run-2"
    assert view_populated.latest_tailoring_ref.score == 0.95


def test_to_research_scope(real_profile: CandidateProfile):
    """Verifies Research Agent scope projection."""
    scope = to_research_scope(real_profile)

    assert isinstance(scope, ResearchScope)
    assert "AI Engineer" in scope.target_roles
    assert "Artificial Intelligence" in scope.target_industries
    assert "Remote" in scope.locations


def test_projections_extra_forbid():
    """Verifies all projection models enforce extra='forbid'."""
    with pytest.raises(ValidationError):
        GleanerQuery(
            role="Dev",
            location="Remote",
            unauthorized_key="bad",
        )

    with pytest.raises(ValidationError):
        OutreachContext(
            candidate_name="Alice",
            email="alice@example.com",
            extra_field="fail",
        )

    with pytest.raises(ValidationError):
        ResearchScope(
            target_roles=["Dev"],
            invalid_param=True,
        )
