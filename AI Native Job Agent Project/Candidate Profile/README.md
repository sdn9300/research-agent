# Candidate Profile JSON (Data Layer) — Component #10

**System:** CONDUCTOR — Autonomous Job Search Pipeline  
**Component:** #10 — Candidate Profile JSON (Data Layer)  
**Schema Version:** `1.0.0`  
**Stack:** Python 3.10+, Pydantic v2, Prometheus Client  

---

## 1. Overview & Architectural Role

Candidate Profile is CONDUCTOR's canonical, versioned shared-state data contract. It serves as the deterministic source of truth for candidate identity, skills, experience, and job search preferences, while maintaining lightweight append-only rollups of cross-component interactions.

> **Core Architectural Principle (ADR-CP-1):**  
> *"One canonical schema. Many thin, mechanically-derived projections. Zero hand-maintained duplicates."*

```
CANDIDATE PROFILE (JSON) — Component #10
══════════════════════════════════════════
 Canonical, versioned, Pydantic v2 schema.
 Persisted via atomic verify-and-swap storage interface.

 OWNED-SECTION WRITERS (Append-Only / Partitioned)
 ─────────────────────────────────────────────────
 [6] Conductor Orchestrator → profile_metadata (system-managed)
 Bootstrap / Manual        → identity, education, skills, experience, preferences
 [2] AlignResume            → tailoring_history
 [3] Overture Outreach      → outreach_history
 [7] Usher (Auto-Apply)     → application_history
 [9] Sentiment Classifier   → interaction_signals

 READ-ONLY PROJECTION CONSUMERS
 ─────────────────────────────────────────────────
 [1] Gleaner                ← preferences (via to_gleaner_query)
 [4] Research Agent         ← preferences (via to_research_scope)
 [2] AlignResume            ← identity, education, skills, experience (via to_resume_profile)
 [7] Usher                  ← identity, education, experience, tailoring_history (via to_application_view)
 [3] Overture               ← identity.contact, preferences (via to_outreach_context)
 [5] Future Fit             ← supplies skills.taxonomy_ref vocabulary
```

---

## 2. Field Dictionary & Schema Reference

All models enforce `model_config = ConfigDict(extra="forbid")` to reject unknown fields.

### `ProfileMetadata`
| Field | Type | Description |
|---|---|---|
| `candidate_id` | `str` (UUID) | Unique candidate identifier. Multi-tenant ready. |
| `schema_version` | `str` | Semantic version of the schema (defaults to `"1.0.0"`). |
| `created_at` | `datetime` | UTC timestamp of candidate creation. |
| `updated_at` | `datetime` | UTC timestamp of last successful write. |
| `last_writer_component` | `str` | Name of the component that applied the last update. |

### `Identity` & `ContactInfo`
| Field | Type | Constraints | Description |
|---|---|---|---|
| `legal_name` | `str` | `min_length=1` | Candidate's legal name. |
| `location` | `str` | `min_length=1` | Candidate's home location (e.g. `"Remote / Hybrid"`). |
| `contact.email` | `EmailStr` | Valid email syntax | Primary communication email address. |
| `contact.phone` | `str | None` | Optional | Contact telephone / mobile number. |
| `contact.linkedin` | `HttpUrl | None` | Valid HTTP(S) URL | Candidate's LinkedIn profile link. |
| `contact.github` | `HttpUrl | None` | Valid HTTP(S) URL | Candidate's GitHub profile link. |
| `contact.portfolio` | `HttpUrl | None` | Valid HTTP(S) URL | Personal website or portfolio URL. |

### `SourceProvenance` *(Anti-Fabrication)*
Attached to claim-bearing models (`SkillRecord`, `ExperienceRecord`) to support anti-hallucination guardrails:
| Field | Type | Description |
|---|---|---|
| `source_type` | `str` | Provenance source (e.g. `"resume_v12"`, `"manual_entry"`, `"llm_extracted"`). |
| `source_ref` | `str | None` | Optional origin pointer (filename, model ID, prompt hash). |
| `verified` | `bool` | Human-verified gate (defaults to `False`). |
| `recorded_at` | `datetime` | UTC timestamp when claim was extracted/recorded. |

### `SkillRecord`
| Field | Type | Description |
|---|---|---|
| `name` | `str` | Skill name (e.g. `"Python"`, `"LangGraph"`). |
| `taxonomy_ref` | `str | None` | Nullable slug linking to Future Fit's market taxonomy (`ADR-CP-6`). |
| `proficiency_self_assessed` | `ProficiencyLevel` | Enum: `basic`, `early_practical`, `intermediate`, `advanced`. |
| `evidence_refs` | `list[str]` | List of project / bullet identifiers demonstrating the skill. |
| `source` | `SourceProvenance` | Claim provenance tracking. |

### `ExperienceRecord`
| Field | Type | Description |
|---|---|---|
| `title` | `str` | Role title or project name. |
| `kind` | `str` | Classification (`"project"`, `"employment"`, `"tutoring"`). |
| `stack` | `list[str]` | List of technologies / frameworks used. |
| `bullets` | `list[str]` | Quantified achievement bullets. |
| `live_url` | `HttpUrl | None` | Production deployment URL. |
| `repo_url` | `HttpUrl | None` | Version control repository URL. |
| `source` | `SourceProvenance` | Claim provenance tracking. |

### `EducationRecord`
| Field | Type | Description |
|---|---|---|
| `institution` | `str` | Name of college / university / academy. |
| `program` | `str` | Degree program and major. |
| `status` | `str` | `"in_progress"` or `"completed"`. |
| `start_date` | `str` | Year/month of enrollment. |
| `end_date` | `str | None` | Year/month of graduation or completion. |
| `honors` | `str | None` | Academic distinctions, GPA, or honors. |

### `ApplicationPreferences`
| Field | Type | Constraints | Description |
|---|---|---|---|
| `target_roles` | `list[str]` | `min_length=1` | Required target job titles for Gleaner and Research Agent. |
| `target_industries` | `list[str]` | `default=[]` | Preferred market domains (e.g. `"AI"`, `"SaaS"`). |
| `locations` | `list[str]` | `min_length=1` | Required geographic search targets. |
| `remote_ok` | `bool` | `default=True` | Willingness to accept remote opportunities. |
| `seniority_qualifiers` | `list[str]` | `default=[]` | Seniority levels (e.g. `["junior", "mid"]`). |

### `HistoryRef` *(Lightweight Cross-Component References)*
Pointers to artifacts in downstream stores (`ADR-CP-3`):
| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | Producing agent's unique run / dispatch ID. |
| `component` | `str` | Originating component name. |
| `timestamp` | `datetime` | UTC timestamp of event completion. |
| `outcome` | `str` | Status code or summary result. |
| `score` | `float | None` | ATS match score, sentiment rating, or evaluation metric. |
| `detail_ref` | `str` | URI pointer into component's private artifact store. |

---

## 3. Storage & Atomic Persistence

The persistence layer guarantees **zero silent corruption** and **crash safety**:

```python
from candidate_profile import CandidateProfileStore, CandidateProfile

store = CandidateProfileStore(base_dir="./data/candidate_profile")

# Save (Atomic Temp-Write -> Byte Verify -> Atomic Replace)
store.put(profile)

# Retrieve (with automatic schema migration)
profile = store.get("c1f72b9a-4c28-4e89-9a25-8321e06d9a10")

# Version Snapshots
snapshots = store.list_versions("c1f72b9a-4c28-4e89-9a25-8321e06d9a10")
```

---

## 4. Downstream Projections (ADR-CP-1)

Consume canonical data without hand-maintained duplicate models:

```python
from candidate_profile import (
    to_resume_profile,      # AlignResume (#2)
    to_gleaner_query,       # Gleaner (#1)
    to_outreach_context,    # Overture (#3)
    to_application_view,    # Usher Auto-Apply (#7)
    to_research_scope,      # Research Agent (#4)
)

resume_profile = to_resume_profile(profile)
gleaner_query = to_gleaner_query(profile)
usher_view = to_application_view(profile)
```

---

## 5. Concurrency & LangGraph State Reducer

LangGraph state graphs thread `CandidateProfile` using the `merge_candidate_profile` reducer:

```python
from typing import TypedDict, Annotated
from candidate_profile import CandidateProfile, CandidateProfilePatch, merge_candidate_profile

class ConductorState(TypedDict):
    profile: Annotated[CandidateProfile, merge_candidate_profile]

# Nodes emit isolated, owned-section patches
def align_resume_node(state: ConductorState):
    patch = CandidateProfilePatch(
        writer_component="align_resume",
        section="tailoring_history",
        value=HistoryRef(
            run_id="run-101",
            component="align_resume",
            timestamp=now,
            outcome="success",
            score=0.94,
            detail_ref="align/runs/101.json",
        )
    )
    return {"profile": patch}
```

---

## 6. Observability & Telemetry

Prometheus metrics exposed for production monitoring:

- `candidate_profile_writes_total{component, status}` — Write attempts and success/error rates.
- `candidate_profile_validation_failures_total{field}` — Schema violations by field (**MG-1**).
- `candidate_profile_schema_version_gauge{candidate_id, schema_version}` — Profile version distribution (**MG-2**).
- `candidate_profile_write_latency_seconds` — Histogram of persistence latency.
- `candidate_profile_ownership_violations_total{component}` — Unauthorized write attempts (**MG-4**).

Monitoring helpers:
```python
from candidate_profile import check_schema_version_drift, compute_taxonomy_coverage

# Evaluate schema drift (MG-2)
drift = check_schema_version_drift(profile)

# Evaluate Future Fit skill coverage (MG-5)
coverage = compute_taxonomy_coverage(profile)
print(f"Taxonomy null rate: {coverage['null_rate'] * 100}%")
```
