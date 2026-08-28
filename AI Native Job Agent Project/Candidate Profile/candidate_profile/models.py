"""
Canonical Pydantic v2 data models for CONDUCTOR Component #10: Candidate Profile JSON.
Reference: CONDUCTOR-CP-AD-v1.0 (Architecture Design §3)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class ProficiencyLevel(str, Enum):
    BASIC = "basic"
    EARLY_PRACTICAL = "early_practical"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SourceProvenance(BaseModel):
    """Attached only to claim-bearing fields (skills, experience) — the
    fields AlignResume's and Usher's anti-fabrication guardrails check
    against. Not applied to fields with nothing to fabricate (contact info,
    preferences)."""
    model_config = ConfigDict(extra="forbid")

    source_type: str  # "resume_v12" | "manual_entry" | "llm_extracted"
    source_ref: str | None = None  # e.g. groq model id, source filename
    verified: bool = False  # human-confirmed, not just extracted
    recorded_at: datetime


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    phone: str | None = None
    linkedin: HttpUrl | None = None
    github: HttpUrl | None = None
    portfolio: HttpUrl | None = None


class Identity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    contact: ContactInfo


class EducationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str
    program: str
    status: str  # "in_progress" | "completed"
    start_date: str
    end_date: str | None = None
    honors: str | None = None


class SkillRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    taxonomy_ref: str | None = None  # nullable pointer into Future Fit's taxonomy (ADR-CP-6)
    proficiency_self_assessed: ProficiencyLevel
    evidence_refs: list[str] = Field(default_factory=list)  # project/bullet references
    source: SourceProvenance


class ExperienceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    kind: str  # "project" | "employment" | "tutoring"
    stack: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    live_url: HttpUrl | None = None
    repo_url: HttpUrl | None = None
    source: SourceProvenance


class ApplicationPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_roles: list[str] = Field(min_length=1)  # required — see EC-CP-INT-02
    target_industries: list[str] = Field(default_factory=list)
    locations: list[str] = Field(min_length=1)
    remote_ok: bool = True
    seniority_qualifiers: list[str] = Field(default_factory=list)  # "fresher", "junior"


class HistoryRef(BaseModel):
    """A reference into another component's own store — never the full
    artifact. See ADR-CP-3."""
    model_config = ConfigDict(extra="forbid")

    run_id: str
    component: str
    timestamp: datetime
    outcome: str
    score: float | None = None
    detail_ref: str  # pointer into the owning component's store


class ProfileMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str  # UUID; single-tenant today, multi-tenant-ready
    schema_version: str = "1.0.0"
    created_at: datetime
    updated_at: datetime
    last_writer_component: str


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_metadata: ProfileMetadata
    identity: Identity
    education: list[EducationRecord] = Field(default_factory=list)
    skills: list[SkillRecord] = Field(default_factory=list)
    experience: list[ExperienceRecord] = Field(default_factory=list)
    preferences: ApplicationPreferences
    tailoring_history: list[HistoryRef] = Field(default_factory=list)
    outreach_history: list[HistoryRef] = Field(default_factory=list)
    application_history: list[HistoryRef] = Field(default_factory=list)
    interaction_signals: list[HistoryRef] = Field(default_factory=list)
