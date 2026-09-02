# Candidate Profile JSON (Data Layer) — Component #10

**System:** CONDUCTOR — Autonomous Job Search Pipeline  
**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Schema Version:** `1.0.0`  
**Specification Version:** `CONDUCTOR-CP-IP-v2.0`  
**Stack:** Python 3.10+, Pydantic v2, FastMCP, Prometheus Client  

---

## 1. Overview & Architectural Role

Candidate Profile is CONDUCTOR's canonical, versioned shared-state data contract and FastMCP server. It serves as the deterministic source of truth for candidate identity, skills, experience, and job search preferences, while maintaining lightweight append-only rollups of cross-component interactions.

> **Core Architectural Principle (ADR-CP-1):**  
> *"One canonical schema. Many thin, mechanically-derived projections. Zero hand-maintained duplicates."*

```
CANDIDATE PROFILE (JSON & FastMCP) — Component #10
══════════════════════════════════════════════════
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

 FASTMCP TOOLS & PROJECTIONS
 ─────────────────────────────────────────────────
 get_candidate_profile      → Full canonical profile JSON
 get_candidate_projection   → Projections for AlignResume, Gleaner, Overture, Usher, Research
 patch_candidate_section    → Ownership-gated LangGraph reducer merge & persistence
 check_skill_provenance     → Anti-fabrication source provenance verification
```

---

## 2. FastMCP Server & Tools

Run the FastMCP server standalone:
```bash
conductor-cp-mcp
```

### Exposed FastMCP Tools

1. **`get_candidate_profile(candidate_id: str)`**
   - Retrieves the full, validated canonical candidate profile as JSON.

2. **`get_candidate_projection(candidate_id: str, projection_type: str)`**
   - Projects candidate facts for specific downstream nodes:
     - `"align_resume"` $\rightarrow$ `ResumeProfile`
     - `"gleaner"` $\rightarrow$ `GleanerQuery`
     - `"overture"` $\rightarrow$ `OutreachContext`
     - `"usher"` $\rightarrow$ `ApplicationView`
     - `"usher_profile"` $\rightarrow$ `UsherCandidateProfile`
     - `"research"` $\rightarrow$ `ResearchScope`

3. **`patch_candidate_section(candidate_id: str, writer_component: str, section: str, value: Any)`**
   - Enforces field ownership partitioning (**ADR-CP-2, HG-4**).
   - Merges delta via commutative reducer and persists atomically to disk.

4. **`check_skill_provenance(candidate_id: str, skill_name: str)`**
   - Returns anti-fabrication verification record (`source_type`, `verified`, `evidence_refs`, `taxonomy_ref`).

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
    to_usher_profile,       # Usher Schema Match (#7)
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
