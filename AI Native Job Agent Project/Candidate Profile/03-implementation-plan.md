# Candidate Profile (JSON) — Phase-Wise Implementation Plan

**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Document ID:** CONDUCTOR-CP-IP-v2.0  
**Status:** Approved Implementation Schedule  
**Governance Anchor:** Law 4 (Canonical Candidate Profile Single Source of Truth)  
**Predecessor Document:** 02-architecture-design.md  
**Companion Documents:** 00-problem-statement.md · 01-mission-plan.md · 04-evaluation-plan.md · 05-edge-case-plan.md  

---

## 1. Phase Overview

Implementation aligns with **Unified CareerOS Phase 2 (Profile & Memory Core)**:

```
 PHASE 0              PHASE 1                  PHASE 2                    PHASE 3                       PHASE 4
 Schema Skeleton ──►  Persistence &      ──►   Per-Component      ──►     Concurrency, Ownership  ──►   FastMCP Mesh,
 & Environment (S)    Versioning (M)           Projections &              Enforcement & Reducer         Observability &
                            │                   Retrofits (M)             Wiring (M)                    Hardening (S)
                            │
                            └── Formally Resolves Usher's Phase 0
                                & Gleaner's Phase 0 Schema Blockers
```

| Phase | Objective | Relative Effort | Target Exit Criteria |
|---|---|---|---|
| **Phase 0** | Schema Skeleton & Real-Data Fixtures | S (1–2 days) | 100% Pydantic validation on real candidate resume.pdf (Gate HG-1) |
| **Phase 1** | Persistence, Atomic Write & Versioning | M (2–3 days) | Atomic crash safety verified (HG-3); unblocks Usher & Gleaner Phase 0 |
| **Phase 2** | Mechanical Projections & AlignResume Retrofit | M (2–3 days) | Adapters verified; `to_resume_profile` feeds AlignResume without drift |
| **Phase 3** | Field Ownership Enforcement & LangGraph Reducer | M (2–3 days) | Reducer raises `OwnershipViolationError` on adversarial writes (HG-4) |
| **Phase 4** | FastMCP Server Tools, Telemetry & Hardening | S (1–2 days) | FastMCP endpoints active; 500+ history records load in < 50ms (MG-3) |

---

## 2. Phase-by-Phase Technical Tasks

### Phase 0 — Schema Skeleton & Environment
- Implement all Pydantic v2 models (`CandidateProfile`, `Identity`, `SkillRecord`, `ExperienceRecord`, `SourceProvenance`, `HistoryRef`, `ProfileMetadata`).
- Enforce `model_config = ConfigDict(extra="forbid")` on every model.
- Hand-populate real candidate fixture from `resume.pdf` and verify zero schema patches needed.
- **Exit Criteria:** Gate HG-1 & HG-6 pass.

### Phase 1 — Persistence, Atomic Write & Versioning
- Implement atomic `get`/`put`/`list_versions` storage interface using temp-file-and-rename pattern.
- Implement `schema_version` migration chain scaffold.
- Implement round-trip serialization tests (Pydantic $\rightarrow$ JSON $\rightarrow$ Pydantic).
- **Exit Criteria:** Gate HG-2 & HG-3 pass; **Usher Phase 0 schema dependency formally marked resolved**.

### Phase 2 — Mechanical Projections & AlignResume Retrofit
- Implement `to_resume_profile()` mapping canonical facts to AlignResume's domain model.
- Implement `to_search_criteria()` for Gleaner.
- Implement `to_outreach_context()` for Overture.
- Implement `to_application_view()` for Usher.
- Verify adapter projection fidelity and round-trip consistency.
- **Exit Criteria:** All 4 projection adapters passing 100% unit tests.

### Phase 3 — Field Ownership Enforcement & LangGraph Reducer
- Implement `merge_candidate_profile()` state reducer.
- Implement write guard raising `OwnershipViolationError` on unauthorized section writes.
- Test commutative list concatenation for history sections (`tailoring_history`, `outreach_history`, `application_history`, `interaction_signals`).
- **Exit Criteria:** Gate HG-4 passes across adversarial matrix.

### Phase 4 — FastMCP Server Tools, Telemetry & Hardening
- Build FastMCP tool wrappers (`get_candidate_profile`, `get_candidate_projection`, `patch_candidate_section`, `check_skill_provenance`).
- Instrument Prometheus observability metrics (writes, validation failures, latency).
- Load test with 500+ accumulated history entries asserting $< 50$ms read latency.
- **Exit Criteria:** All 4 FastMCP tools return valid JSON; Monitored Gates MG-1 to MG-5 initialized.
