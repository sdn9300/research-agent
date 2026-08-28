"""
Unit tests for Candidate Profile Pydantic v2 data models.
Validates Phase 0 tasks, Hard-Blocking Gates (HG-1, HG-6), and Edge Cases.
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

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_hg1_real_candidate_profile_fixture_validation():
    """HG-1: 100% Pydantic validation pass rate against real candidate data.
    Loads real_candidate_profile.json (derived from master_resume.txt) with zero manual patching.
    """
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    assert fixture_path.exists(), f"Fixture missing at {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as f:
        json_data = f.read()

    profile = CandidateProfile.model_validate_json(json_data)
    assert profile.identity.legal_name == "Soumyadeep Nath"
    assert profile.identity.contact.email == "soumyadeepnath@example.com"
    assert len(profile.skills) >= 5
    assert len(profile.experience) == 3
    assert profile.preferences.remote_ok is True
    assert profile.profile_metadata.schema_version == "1.0.0"


def test_hg6_and_ec_cp_schema_01_extra_forbid_on_all_models():
    """HG-6 & EC-CP-SCHEMA-01: extra='forbid' is enforced on every model.
    Injecting an unknown field must fail immediately with a ValidationError naming the offending field.
    """
    now = datetime.now(timezone.utc)

    # 1. SourceProvenance
    with pytest.raises(ValidationError) as exc_info:
        SourceProvenance(
            source_type="resume_v12",
            source_ref="resume.pdf",
            verified=True,
            recorded_at=now,
            unknown_field="injected",
        )
    assert "unknown_field" in str(exc_info.value)

    # 2. ContactInfo
    with pytest.raises(ValidationError) as exc_info:
        ContactInfo(
            email="test@example.com",
            phone="1234567890",
            extra_field="bad",
        )
    assert "extra_field" in str(exc_info.value)

    # 3. Identity
    with pytest.raises(ValidationError) as exc_info:
        Identity(
            legal_name="John Doe",
            location="Remote",
            contact=ContactInfo(email="john@example.com"),
            unauthorized_key=123,
        )
    assert "unauthorized_key" in str(exc_info.value)

    # 4. EducationRecord
    with pytest.raises(ValidationError) as exc_info:
        EducationRecord(
            institution="MIT",
            program="CS",
            status="completed",
            start_date="2020",
            gpa="4.0",  # not in schema
        )
    assert "gpa" in str(exc_info.value)

    # 5. SkillRecord
    prov = SourceProvenance(source_type="manual", recorded_at=now)
    with pytest.raises(ValidationError) as exc_info:
        SkillRecord(
            name="Python",
            proficiency_self_assessed=ProficiencyLevel.ADVANCED,
            source=prov,
            years_experience=5,  # not in schema
        )
    assert "years_experience" in str(exc_info.value)

    # 6. ExperienceRecord
    with pytest.raises(ValidationError) as exc_info:
        ExperienceRecord(
            title="Senior Engineer",
            kind="employment",
            source=prov,
            salary="100k",  # not in schema
        )
    assert "salary" in str(exc_info.value)

    # 7. ApplicationPreferences
    with pytest.raises(ValidationError) as exc_info:
        ApplicationPreferences(
            target_roles=["AI Engineer"],
            locations=["Remote"],
            min_base_pay=150000,  # not in schema
        )
    assert "min_base_pay" in str(exc_info.value)

    # 8. HistoryRef
    with pytest.raises(ValidationError) as exc_info:
        HistoryRef(
            run_id="run-1",
            component="AlignResume",
            timestamp=now,
            outcome="success",
            detail_ref="/store/1",
            extra_data="fail",
        )
    assert "extra_data" in str(exc_info.value)

    # 9. ProfileMetadata
    with pytest.raises(ValidationError) as exc_info:
        ProfileMetadata(
            candidate_id="id-1",
            created_at=now,
            updated_at=now,
            last_writer_component="init",
            tenant_id="custom",  # not in schema
        )
    assert "tenant_id" in str(exc_info.value)

    # 10. CandidateProfile
    with pytest.raises(ValidationError) as exc_info:
        CandidateProfile(
            profile_metadata=ProfileMetadata(
                candidate_id="id-1",
                created_at=now,
                updated_at=now,
                last_writer_component="init",
            ),
            identity=Identity(
                legal_name="John Doe",
                location="Remote",
                contact=ContactInfo(email="john@example.com"),
            ),
            education=[],
            skills=[],
            experience=[],
            preferences=ApplicationPreferences(
                target_roles=["Engineer"],
                locations=["Remote"],
            ),
            injected_top_level="hacked",
        )
    assert "injected_top_level" in str(exc_info.value)


def test_ec_cp_schema_02_empty_strings_rejected_on_identity_and_preferences():
    """EC-CP-SCHEMA-02: Required string fields reject empty strings via min_length=1."""
    # Empty legal_name
    with pytest.raises(ValidationError) as exc_info:
        Identity(
            legal_name="",
            location="Remote",
            contact=ContactInfo(email="test@example.com"),
        )
    assert "legal_name" in str(exc_info.value)

    # Empty location
    with pytest.raises(ValidationError) as exc_info:
        Identity(
            legal_name="Jane Doe",
            location="",
            contact=ContactInfo(email="test@example.com"),
        )
    assert "location" in str(exc_info.value)


def test_ec_cp_int_02_preferences_target_roles_and_locations_required():
    """EC-CP-INT-02: target_roles and locations must have at least 1 entry."""
    # Empty target_roles list
    with pytest.raises(ValidationError) as exc_info:
        ApplicationPreferences(
            target_roles=[],
            locations=["Remote"],
        )
    assert "target_roles" in str(exc_info.value)

    # Empty locations list
    with pytest.raises(ValidationError) as exc_info:
        ApplicationPreferences(
            target_roles=["Developer"],
            locations=[],
        )
    assert "locations" in str(exc_info.value)


def test_ec_cp_schema_03_skill_record_nullable_taxonomy_ref():
    """EC-CP-SCHEMA-03: taxonomy_ref is nullable and storable with None."""
    now = datetime.now(timezone.utc)
    prov = SourceProvenance(source_type="manual_entry", recorded_at=now)

    skill = SkillRecord(
        name="NicheCustomSkill",
        taxonomy_ref=None,
        proficiency_self_assessed=ProficiencyLevel.BASIC,
        source=prov,
    )
    assert skill.taxonomy_ref is None
    assert skill.proficiency_self_assessed == ProficiencyLevel.BASIC
    assert skill.evidence_refs == []


def test_history_refs_and_collections():
    """Validates HistoryRef records and the 4 append-only history lists in CandidateProfile."""
    now = datetime.now(timezone.utc)
    h_ref = HistoryRef(
        run_id="run-align-001",
        component="AlignResume",
        timestamp=now,
        outcome="tailored_successfully",
        score=0.92,
        detail_ref="align_resume/runs/run-align-001.json",
    )

    prov = SourceProvenance(source_type="manual_entry", recorded_at=now)
    profile = CandidateProfile(
        profile_metadata=ProfileMetadata(
            candidate_id="cand-12345",
            created_at=now,
            updated_at=now,
            last_writer_component="AlignResume",
        ),
        identity=Identity(
            legal_name="Alice Smith",
            location="New York, NY",
            contact=ContactInfo(
                email="alice@example.com",
                linkedin="https://linkedin.com/in/alice",
                github="https://github.com/alice",
                portfolio="https://alice.dev",
            ),
        ),
        education=[
            EducationRecord(
                institution="Stanford University",
                program="M.S. in Computer Science",
                status="in_progress",
                start_date="2023-09",
            )
        ],
        skills=[
            SkillRecord(
                name="Python",
                taxonomy_ref="python",
                proficiency_self_assessed=ProficiencyLevel.ADVANCED,
                evidence_refs=["project-1"],
                source=prov,
            )
        ],
        experience=[
            ExperienceRecord(
                title="Lead AI Engineer",
                kind="employment",
                stack=["Python", "FastAPI"],
                bullets=["Built agentic workflows."],
                live_url="https://app.example.com",
                repo_url="https://github.com/example/app",
                source=prov,
            )
        ],
        preferences=ApplicationPreferences(
            target_roles=["Senior AI Engineer"],
            locations=["Remote", "New York"],
            remote_ok=True,
            seniority_qualifiers=["senior"],
        ),
        tailoring_history=[h_ref],
        outreach_history=[],
        application_history=[],
        interaction_signals=[],
    )

    assert len(profile.tailoring_history) == 1
    assert profile.tailoring_history[0].score == 0.92
    assert profile.tailoring_history[0].outcome == "tailored_successfully"
    assert profile.education[0].status == "in_progress"
    assert profile.education[0].end_date is None
