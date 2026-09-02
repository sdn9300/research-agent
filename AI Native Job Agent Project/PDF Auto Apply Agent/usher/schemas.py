"""
Pydantic v2 schemas and data contracts for CONDUCTOR Component 7 (Usher).
Authoritative implementation matching PAA-AD-1.0 §3.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ApplicationChannel(str, Enum):
    """Supported and target ATS platforms/channels."""
    NAUKRI = "naukri"
    INDEED = "indeed"
    LINKEDIN_EASY_APPLY = "linkedin_easy_apply"
    GENERIC_ATS_GREENHOUSE = "generic_ats_greenhouse"
    GENERIC_ATS_LEVER = "generic_ats_lever"
    GENERIC_ATS_WORKDAY = "generic_ats_workday"
    GENERIC_ATS_UNKNOWN = "generic_ats_unknown"
    UNSUPPORTED = "unsupported"


class SubmissionMode(str, Enum):
    """Execution mode governing submission gatekeeping."""
    DRAFT = "draft"  # Default: pre-fill and pause for human confirmation
    AUTO = "auto"    # Autonomous submission (earned per platform post-graduation)
    SKIP = "skip"    # Known-unsupported or policy-excluded, not attempted


class EducationEntry(BaseModel):
    """Educational qualification details."""
    model_config = ConfigDict(extra="ignore")

    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    percentage_or_cgpa: Optional[str] = None


class ExperienceEntry(BaseModel):
    """Past work experience details."""
    model_config = ConfigDict(extra="ignore")

    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class CandidateProfile(BaseModel):
    """
    Canonical candidate facts from Component 10.
    Sole source of truth for standard application field values.
    """
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = "sdn9300"
    full_name: str
    email: str
    phone: str
    location: str
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    education: List[EducationEntry] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    salary_expectation: Optional[str] = None
    notice_period: Optional[str] = None
    work_authorization: Optional[str] = "Authorized to work in India"
    last_verified_at: Optional[datetime] = None
    version_hash: Optional[str] = None


class JobApplicationTarget(BaseModel):
    """
    Inbound job opportunity payload from The Gleaner (Component 1).
    Reconciled against Gleaner's canonical schema.
    """
    model_config = ConfigDict(extra="ignore")

    job_id: str
    title: str
    company: str
    apply_url: str
    source_platform: str
    location: Optional[str] = None
    posted_at: Optional[str] = None
    description: Optional[str] = None
    detected_channel: Optional[ApplicationChannel] = None
    is_verified_company: bool = True  # From Research Agent (Component 4)

    @field_validator("apply_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v or not v.strip().startswith(("http://", "https://")):
            raise ValueError(f"Invalid application URL: {v}")
        return v.strip()


class ResumeArtifact(BaseModel):
    """
    Tailored resume artifact received from AlignResume (Component 2).
    """
    model_config = ConfigDict(extra="ignore")

    tailoring_run_id: str
    file_path: str
    file_checksum: str  # SHA-256 hash of the generated PDF file
    profile_version: str  # Hash or version of Candidate Profile JSON used
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FieldResolution(BaseModel):
    """
    Resolution outcome for an individual form field.
    """
    model_config = ConfigDict(extra="ignore")

    field_label: str
    resolution_tier: Literal[
        "tier0_selector", "tier1_fuzzy", "tier2_llm_light", "tier3_llm_heavy", "unresolved"
    ]
    resolved_value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: Literal["candidate_profile", "generated", "manual_required"]
    selector_used: Optional[str] = None
    reasoning: Optional[str] = None


class ApplicationAttemptResult(BaseModel):
    """
    Structured outcome record produced for every single attempt.
    Outbound contract consumed by Memory Module (Component 8).
    """
    model_config = ConfigDict(extra="ignore")

    attempt_id: str
    job: JobApplicationTarget
    resume_used: Optional[ResumeArtifact] = None
    status: Literal[
        "SUBMITTED",
        "DRAFT_PENDING_REVIEW",
        "MANUAL_REQUIRED",
        "AMBIGUOUS_OUTCOME",
        "FAILED",
        "SKIPPED",
    ]
    field_resolutions: List[FieldResolution] = Field(default_factory=list)
    screenshot_path: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    groq_tokens_used: int = 0
    groq_cost_estimate_usd: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConductorState(BaseModel):
    """
    Shared state contract for CONDUCTOR Orchestrator (Component 6) LangGraph execution.
    Contains inbound data from upstream components (1, 2, 4, 10) and outbound results for Component 8.
    """
    model_config = ConfigDict(extra="allow")

    job: JobApplicationTarget
    profile: CandidateProfile
    resume: ResumeArtifact
    research_brief: Optional[str] = None
    submission_mode: Optional[SubmissionMode] = None
    attempt_result: Optional[ApplicationAttemptResult] = None
    error: Optional[str] = None

