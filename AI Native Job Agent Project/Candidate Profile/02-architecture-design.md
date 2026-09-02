# Candidate Profile (JSON) — Architecture Design

**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Document ID:** CONDUCTOR-CP-AD-v2.0  
**Status:** Approved Technical Architecture  
**Governance Anchor:** Law 4 (Canonical Candidate Profile Single Source of Truth)  
**Predecessor Document:** 01-mission-plan.md  
**Companion Documents:** 00-problem-statement.md · 03-implementation-plan.md · 04-evaluation-plan.md · 05-edge-case-plan.md  

---

## 1. Architectural Overview

Candidate Profile is a canonical, versioned Pydantic v2 schema — not a background daemon, not a probabilistic process. It has no internal LLM calls in its read/write path and serves as the single place where "who the candidate is" is defined once, validated on every write, and served consistently to all 9 sibling sub-agents in the Unified CareerOS ecosystem.

```
+---------------------------------------------------------------------------------------------------+
|                            CANDIDATE PROFILE (JSON) — Component #10                               |
|                                                                                                   |
|  Canonical, versioned, Pydantic v2 schema.                                                        |
|  Persisted via Memory Module's [8] atomic SQLite/JSON storage interface (ADR-CP-4).               |
|                                                                                                   |
|  OWNED-SECTION WRITERS (Append-Only History References)                                           |
|  ───────────────────────────────────────────────────────                                          |
|  [2] AlignResume          ──► tailoring_history                                                   |
|  [3] Overture Outreach    ──► outreach_history                                                    |
|  [7] PDF Auto-Apply       ──► application_history                                                 |
|  [9] Sentiment Classifier ──► interaction_signals                                                 |
|                                                                                                   |
|  READ-ONLY PROJECTION CONSUMERS (Zero-Drift Adapters)                                             |
|  ──────────────────────────────────────────────────────                                          |
|  [1] Gleaner            ◄── preferences (via to_search_criteria)                                |
|  [4] Research Agent       ◄── preferences (industry/role scope)                                   |
|  [2] AlignResume          ◄── identity, education, skills, experience (via to_resume_profile)     |
|  [7] PDF Auto-Apply       ◄── identity, education, experience, tailoring (via to_application_view)|
|  [3] Overture Outreach    ◄── identity.contact, preferences (via to_outreach_context)             |
|  [5] Future-Fit           ◄── (indirect) supplies skills.taxonomy_ref vocabulary                  |
|                                                                                                   |
|  RUNTIME HOST & REDUCER                                                                           |
|  ──────────────────────────────────────────────────────                                          |
|  [0] Conductor Orchestrator threads CandidateProfile as LangGraph shared state;                   |
|      executes merge_candidate_profile() reducer; owns profile_metadata.                           |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Core Design Principle

**One canonical schema. Many thin, mechanically-derived projections. Zero hand-maintained duplicates.** (ADR-CP-1)

---

## 3. Data Model (Pydantic v2)

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

class ProficiencyLevel(str, Enum):
    BASIC = "basic"
    EARLY_PRACTICAL = "early_practical"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class SourceProvenance(BaseModel):
    """Attached to claim-bearing fields (skills, experience) — truthfulness anchor."""
    model_config = ConfigDict(extra="forbid")
    source_type: str                    # "resume_v12" | "manual_entry" | "llm_extracted"
    source_ref: Optional[str] = None    # e.g. groq model id, source filename
    verified: bool = False              # Human-confirmed flag
    recorded_at: datetime

class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    phone: Optional[str] = None
    linkedin: Optional[HttpUrl] = None
    github: Optional[HttpUrl] = None
    portfolio: Optional[HttpUrl] = None

class Identity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_name: str = Field(min_length=1)
    location: str = Field(min_length=1)
    contact: ContactInfo

class EducationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    institution: str
    program: str
    status: str                         # "in_progress" | "completed"
    start_date: str
    end_date: Optional[str] = None
    honors: Optional[str] = None

class SkillRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    taxonomy_ref: Optional[str] = None # Soft-link to Future-Fit taxonomy slug (ADR-CP-6)
    proficiency_self_assessed: ProficiencyLevel
    evidence_refs: List[str] = Field(default_factory=list)
    source: SourceProvenance

class ExperienceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    kind: str                           # "project" | "employment" | "tutoring"
    stack: List[str] = Field(default_factory=list)
    bullets: List[str] = Field(default_factory=list)
    live_url: Optional[HttpUrl] = None
    repo_url: Optional[HttpUrl] = None
    source: SourceProvenance

class ApplicationPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_roles: List[str] = Field(min_length=1)
    target_industries: List[str] = Field(default_factory=list)
    locations: List[str] = Field(min_length=1)
    remote_ok: bool = True
    seniority_qualifiers: List[str] = Field(default_factory=list)

class HistoryRef(BaseModel):
    """Lightweight summary reference into owning component store (ADR-CP-3)."""
    model_config = ConfigDict(extra="forbid")
    run_id: str
    component: str
    timestamp: datetime
    outcome: str
    score: Optional[float] = None
    detail_ref: str                     # Pointer to full artifact in owning store

class ProfileMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str                   # UUID; single-tenant today, multi-tenant ready
    schema_version: str = "1.0.0"
    created_at: datetime
    updated_at: datetime
    last_writer_component: str

class CandidateProfile(BaseModel):
    """The single canonical source of truth for candidate facts."""
    model_config = ConfigDict(extra="forbid")
    profile_metadata: ProfileMetadata
    identity: Identity
    education: List[EducationRecord]
    skills: List[SkillRecord]
    experience: List[ExperienceRecord]
    preferences: ApplicationPreferences
    tailoring_history: List[HistoryRef] = Field(default_factory=list)
    outreach_history: List[HistoryRef] = Field(default_factory=list)
    application_history: List[HistoryRef] = Field(default_factory=list)
    interaction_signals: List[HistoryRef] = Field(default_factory=list)
```

---

## 4. Field Ownership & Update-Pattern Matrix

| Section | Authoritative Writer | Readers | Update Pattern |
|---|---|---|---|
| `profile_metadata` | Conductor [0] (System-managed) | All Components | Auto-updated on every accepted write |
| `identity` | Bootstrap / manual, human-gated | AlignResume, Usher, Overture, Chief of Staff | Full-section overwrite, human-confirmed only |
| `education` | Bootstrap / manual, human-gated | AlignResume, Usher | Full-list overwrite, human-gated |
| `skills` | Bootstrap / manual + extractor, human-gated | AlignResume, Usher, Future-Fit | Key-merge on `name`; unverified default `False` |
| `experience` | Bootstrap / manual, human-gated | AlignResume, Usher, Overture | Full-list overwrite / append, human-gated |
| `preferences` | Manual, human-set | Gleaner, Research Agent, Overture | Full-section overwrite, human-gated |
| `tailoring_history` | AlignResume (refs only) | Usher, Conductor | Append-only |
| `outreach_history` | Overture (refs only) | Sentiment Classifier, Conductor | Append-only |
| `application_history` | PDF Auto-Apply (refs only) | Conductor, Memory Module | Append-only |
| `interaction_signals` | Sentiment Classifier (refs only) | Conductor, Memory Module | Append-only |

No section has more than one authoritative writer. Cross-section writes raise `OwnershipViolationError` (ADR-CP-2).

---

## 5. LangGraph State Reducer (`merge_candidate_profile`)

```python
OWNERSHIP = {
    "bootstrap": {"identity", "education", "skills", "experience", "preferences"},
    "align_resume": {"tailoring_history"},
    "overture": {"outreach_history"},
    "pdf_auto_apply": {"application_history"},
    "sentiment_classifier": {"interaction_signals"},
    "conductor": {"profile_metadata"}
}
APPEND_ONLY_SECTIONS = {"tailoring_history", "outreach_history", "application_history", "interaction_signals"}

def merge_candidate_profile(current: CandidateProfile, patch: CandidateProfilePatch) -> CandidateProfile:
    """LangGraph-compatible deterministic state reducer enforcing strict field ownership."""
    if patch.section not in OWNERSHIP.get(patch.writer_component, set()):
        raise OwnershipViolationError(f"{patch.writer_component} cannot write to {patch.section}")

    if patch.section in APPEND_ONLY_SECTIONS:
        updated = getattr(current, patch.section) + [patch.value]
    else:
        updated = patch.value

    return current.model_copy(update={
        patch.section: updated,
        "profile_metadata": current.profile_metadata.model_copy(update={
            "updated_at": datetime.utcnow(),
            "last_writer_component": patch.writer_component
        })
    })
```

---

## 6. Mechanical Projection Adapters

```python
def to_resume_profile(profile: CandidateProfile) -> ResumeProfile:
    """Projects canonical facts into AlignResume's domain model."""
    return ResumeProfile(
        name=profile.identity.legal_name,
        contact=profile.identity.contact.model_dump(),
        skills=[s.name for s in profile.skills if s.source.verified],
        experience=[e.model_dump() for e in profile.experience if e.source.verified],
        education=[ed.model_dump() for ed in profile.education]
    )

def to_search_criteria(preferences: ApplicationPreferences) -> SearchCriteria:
    """Projects search preferences into Gleaner's scraping criteria."""
    return SearchCriteria(
        roles=preferences.target_roles,
        locations=preferences.locations,
        remote=preferences.remote_ok,
        seniority=preferences.seniority_qualifiers
    )

def to_outreach_context(profile: CandidateProfile) -> OutreachContext:
    """Projects identity and experience into Overture's persona builder."""
    return OutreachContext(
        sender_name=profile.identity.legal_name,
        email=profile.identity.contact.email,
        github=str(profile.identity.contact.github) if profile.identity.contact.github else None,
        key_skills=[s.name for s in profile.skills[:6] if s.source.verified]
    )

def to_application_view(profile: CandidateProfile) -> ApplicationView:
    """Projects profile facts and tailoring history into Usher form-filler."""
    return ApplicationView(
        identity=profile.identity.model_dump(),
        education=[e.model_dump() for e in profile.education],
        experience=[e.model_dump() for e in profile.experience if e.source.verified],
        tailoring_runs=profile.tailoring_history
    )
```

---

## 7. Persistence & Storage Contract

Persistence routes through Memory Module's storage engine (ADR-CP-4):

```python
def get(candidate_id: str) -> CandidateProfile | None: ...
def put(profile: CandidateProfile) -> None: ...           # Atomic temp-file-and-rename
def list_versions(candidate_id: str) -> list[str]: ...
```

`put()` writes to a temporary file (`.tmp`), re-parses and validates the schema, then performs an atomic OS rename over the canonical file. Failed validation aborts the rename, leaving prior state untouched.

---

## 8. FastMCP Tool Mesh Catalog

| Providing Server | Tool Name | Parameters | Return Schema |
|---|---|---|---|
| **Candidate Profile** | `get_candidate_profile` | `(candidate_id: str)` | `CandidateProfile` |
| **Candidate Profile** | `get_candidate_projection` | `(projection_type: str)` | `ProjectionPayload` |
| **Candidate Profile** | `patch_candidate_section` | `(section: str, patch: dict)` | `CandidateProfile` |
| **Candidate Profile** | `check_skill_provenance` | `(skill_name: str)` | `ProvenanceStatus` |

---

## 9. Architecture Decision Records (ADRs)

- **ADR-CP-1 (Canonical Schema vs. Duplicated Schemas):** Single canonical model on disk; thin projection adapters (`to_resume_profile`, etc.) feed consumers.
- **ADR-CP-2 (Field Ownership Partitioning):** Disjoint section ownership. History sections are append-only. Reducer raises `OwnershipViolationError` on illegal cross-writes.
- **ADR-CP-3 (Summary References in History):** Candidate Profile stores lightweight `HistoryRef` summary records (`run_id`, `outcome`, `score`, `detail_ref`); full artifacts remain in owning sub-agent stores.
- **ADR-CP-4 (Storage Substrate):** Persistence routes through Memory Module's storage engine (atomic temp-file-and-rename verification).
- **ADR-CP-5 (Explicit Versioning & `extra="forbid"`):** Semver migration chains; unknown fields rejected strictly.
- **ADR-CP-6 (Skills Taxonomy Soft Alignment):** `SkillRecord.taxonomy_ref` softly links candidate skills to Future-Fit's canonical 100+ skill taxonomy.
