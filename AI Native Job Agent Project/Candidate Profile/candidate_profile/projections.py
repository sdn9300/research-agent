"""
Per-component projection models and adapter functions for CONDUCTOR consumers.
Reference: CONDUCTOR-CP-AD-v1.0 (Architecture Design §2, §9, ADR-CP-1)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from candidate_profile.models import (
    CandidateProfile,
    ContactInfo,
    EducationRecord,
    ExperienceRecord,
    HistoryRef,
)


# ============================================================================
# 1. AlignResume Projection (#2)
# ============================================================================

class ContactProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    links: List[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = ""
    title: str = ""
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    description: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school: str = ""
    degree: Optional[str] = None
    field: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None


class CertificationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    issuer: Optional[str] = None
    date: Optional[str] = None


class ResumeProfile(BaseModel):
    """AlignResume's canonical input shape (TypeScript parity)."""
    model_config = ConfigDict(extra="forbid")

    contact: ContactProfile
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)


def to_resume_profile(profile: CandidateProfile) -> ResumeProfile:
    """Mechanically projects a CandidateProfile onto AlignResume's ResumeProfile."""
    links: List[str] = []
    if profile.identity.contact.github:
        links.append(str(profile.identity.contact.github))
    if profile.identity.contact.linkedin:
        links.append(str(profile.identity.contact.linkedin))
    if profile.identity.contact.portfolio:
        links.append(str(profile.identity.contact.portfolio))

    contact = ContactProfile(
        name=profile.identity.legal_name,
        email=str(profile.identity.contact.email) if profile.identity.contact.email else None,
        phone=profile.identity.contact.phone,
        location=profile.identity.location,
        links=links,
    )

    experience_entries: List[ExperienceEntry] = []
    project_entries: List[ProjectEntry] = []

    for exp in profile.experience:
        if exp.kind.lower() == "project":
            project_entries.append(
                ProjectEntry(
                    name=exp.title,
                    bullets=list(exp.bullets),
                    technologies=list(exp.stack),
                )
            )
        else:
            experience_entries.append(
                ExperienceEntry(
                    company=exp.title,
                    title=exp.title,
                    bullets=list(exp.bullets),
                )
            )

    education_entries = [
        EducationEntry(
            school=edu.institution,
            degree=edu.program,
            startDate=edu.start_date,
            endDate=edu.end_date,
        )
        for edu in profile.education
    ]

    return ResumeProfile(
        contact=contact,
        summary="",
        skills=[skill.name for skill in profile.skills],
        experience=experience_entries,
        projects=project_entries,
        education=education_entries,
        certifications=[],
    )


# ============================================================================
# 2. Gleaner Projection (#1 — formerly Gleaner)
# ============================================================================

class GleanerQuery(BaseModel):
    """Gleaner's search parameterization query shape."""
    model_config = ConfigDict(extra="forbid")

    role: str
    location: str
    target_roles: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    remote_ok: bool = True
    seniority_qualifiers: List[str] = Field(default_factory=list)


SearchCriteria = GleanerQuery


def to_gleaner_query(profile: CandidateProfile) -> GleanerQuery:
    """Projects CandidateProfile preferences onto Gleaner's search query."""
    primary_role = profile.preferences.target_roles[0] if profile.preferences.target_roles else ""
    primary_location = profile.preferences.locations[0] if profile.preferences.locations else ""

    return GleanerQuery(
        role=primary_role,
        location=primary_location,
        target_roles=list(profile.preferences.target_roles),
        locations=list(profile.preferences.locations),
        target_industries=list(profile.preferences.target_industries),
        remote_ok=profile.preferences.remote_ok,
        seniority_qualifiers=list(profile.preferences.seniority_qualifiers),
    )


to_search_criteria = to_gleaner_query


# ============================================================================
# 3. Overture Outreach Projection (#3)
# ============================================================================

class OutreachContext(BaseModel):
    """Overture's candidate context for cold email campaigns."""
    model_config = ConfigDict(extra="forbid")

    candidate_name: str
    email: str
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    target_roles: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)


def to_outreach_context(profile: CandidateProfile) -> OutreachContext:
    """Projects CandidateProfile onto Overture's outreach campaign context."""
    contact = profile.identity.contact
    return OutreachContext(
        candidate_name=profile.identity.legal_name,
        email=str(contact.email),
        phone=contact.phone,
        linkedin=str(contact.linkedin) if contact.linkedin else None,
        github=str(contact.github) if contact.github else None,
        portfolio=str(contact.portfolio) if contact.portfolio else None,
        target_roles=list(profile.preferences.target_roles),
        target_industries=list(profile.preferences.target_industries),
        locations=list(profile.preferences.locations),
    )


# ============================================================================
# 4. Usher PDF Auto-Apply Projections (#7)
# ============================================================================

class ApplicationView(BaseModel):
    """Usher's candidate view for auto-filling portal fields and generating packages."""
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    legal_name: str
    location: str
    contact: ContactInfo
    education: List[EducationRecord] = Field(default_factory=list)
    experience: List[ExperienceRecord] = Field(default_factory=list)
    tailoring_history: List[HistoryRef] = Field(default_factory=list)
    latest_tailoring_ref: Optional[HistoryRef] = None


def to_application_view(profile: CandidateProfile) -> ApplicationView:
    """Projects CandidateProfile onto Usher's auto-apply view."""
    latest_ref = profile.tailoring_history[-1] if profile.tailoring_history else None
    return ApplicationView(
        candidate_id=profile.profile_metadata.candidate_id,
        legal_name=profile.identity.legal_name,
        location=profile.identity.location,
        contact=profile.identity.contact,
        education=list(profile.education),
        experience=list(profile.experience),
        tailoring_history=list(profile.tailoring_history),
        latest_tailoring_ref=latest_ref,
    )


class UsherEducationEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    percentage_or_cgpa: Optional[str] = None


class UsherExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    company: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    location: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)


class UsherCandidateProfile(BaseModel):
    """Direct schema match for Usher's internal CandidateProfile contract."""
    model_config = ConfigDict(extra="ignore")

    candidate_id: str
    full_name: str
    email: str
    phone: str
    location: str
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    education: List[UsherEducationEntry] = Field(default_factory=list)
    experience: List[UsherExperienceEntry] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    salary_expectation: Optional[str] = None
    notice_period: Optional[str] = None
    work_authorization: Optional[str] = "Authorized to work in India"


def to_usher_profile(profile: CandidateProfile) -> UsherCandidateProfile:
    """Projects canonical CandidateProfile onto Usher's domain schema."""
    contact = profile.identity.contact

    usher_edu: List[UsherEducationEntry] = []
    for edu in profile.education:
        start_yr = int(edu.start_date.split("-")[0]) if edu.start_date and edu.start_date.split("-")[0].isdigit() else None
        end_yr = int(edu.end_date.split("-")[0]) if edu.end_date and edu.end_date.split("-")[0].isdigit() else None
        usher_edu.append(
            UsherEducationEntry(
                institution=edu.institution,
                degree=edu.program,
                field_of_study=edu.program,
                start_year=start_yr,
                end_year=end_yr,
                percentage_or_cgpa=edu.honors,
            )
        )

    usher_exp: List[UsherExperienceEntry] = []
    for exp in profile.experience:
        usher_exp.append(
            UsherExperienceEntry(
                company=exp.title,
                role=exp.title,
                highlights=list(exp.bullets),
                is_current=False,
            )
        )

    return UsherCandidateProfile(
        candidate_id=profile.profile_metadata.candidate_id,
        full_name=profile.identity.legal_name,
        email=str(contact.email),
        phone=contact.phone or "+91-9876543210",
        location=profile.identity.location,
        github_url=str(contact.github) if contact.github else None,
        linkedin_url=str(contact.linkedin) if contact.linkedin else None,
        portfolio_url=str(contact.portfolio) if contact.portfolio else None,
        education=usher_edu,
        experience=usher_exp,
        skills=[s.name for s in profile.skills],
    )


# ============================================================================
# 5. Research Agent Projection (#4)
# ============================================================================

class ResearchScope(BaseModel):
    """Research Agent's candidate targeting scope."""
    model_config = ConfigDict(extra="forbid")

    target_roles: List[str] = Field(default_factory=list)
    target_industries: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)


def to_research_scope(profile: CandidateProfile) -> ResearchScope:
    """Projects CandidateProfile onto Research Agent's targeting scope."""
    return ResearchScope(
        target_roles=list(profile.preferences.target_roles),
        target_industries=list(profile.preferences.target_industries),
        locations=list(profile.preferences.locations),
    )
