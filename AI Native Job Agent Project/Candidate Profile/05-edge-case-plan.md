# Candidate Profile (JSON) — Edge Case Plan

**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Document ID:** CONDUCTOR-CP-ECP-v2.0  
**Status:** Approved Fault Tolerance Specification  
**Governance Anchor:** Law 4 (Canonical Candidate Profile Single Source of Truth)  
**Predecessor Document:** 04-evaluation-plan.md  
**Companion Documents:** 00-problem-statement.md · 01-mission-plan.md · 02-architecture-design.md · 03-implementation-plan.md  

---

## 1. Registry Structure & Severity Classification

- **Critical:** Data loss or candidate identity corruption risk; blocks release outright.
- **High:** Must have an automated unit/integration test closing it before phase gate sign-off.
- **Medium:** Documented and monitored via Monitored Gates; does not block release on its own.
- **Low:** Handled by design with negligible runtime impact.

---

## 2. Category-by-Category Edge Case Matrix

### Category A: Schema & Data Validation

| ID | Scenario | Severity | Architectural Handling |
|---|---|---|---|
| **EC-CP-SCHEMA-01** | Component submits a write containing an unmapped or extra field | Medium | Rejected via `extra="forbid"`; error names offending field; write is completely aborted. |
| **EC-CP-SCHEMA-02** | Required string is present but empty (e.g. `legal_name = ""`) | Low | Field validators enforce `min_length=1` on identity and target role strings. |
| **EC-CP-SCHEMA-03** | `SkillRecord` has no `taxonomy_ref` match in Future-Fit export | Low | Stored with `taxonomy_ref=None`; surfaced via MG-5 telemetry, non-blocking. |

### Category B: Concurrency & LangGraph State Merges

| ID | Scenario | Severity | Architectural Handling |
|---|---|---|---|
| **EC-CP-CONC-01** | Two LangGraph branches append to same history section in same tick | High | Append-only merge is commutative and keyed by `run_id`; reducer handles list concatenation safely. |
| **EC-CP-CONC-02** | Process killed mid-write (temp file created, rename incomplete) | High | Atomic OS rename guarantees original file is untouched; orphaned `.tmp` file is ignored on restart. |
| **EC-CP-CONC-03** | Unauthorized section write (e.g. Harvester attempts to modify `skills`) | Critical | Reducer raises `OwnershipViolationError`; zero mutation applied; logged to MG-4 telemetry. |

### Category C: Version Migration

| ID | Scenario | Severity | Architectural Handling |
|---|---|---|---|
| **EC-CP-MIGR-01** | Profile on older semver loaded without registered migration step | High | Fails loud with `UnmigratableSchemaVersionError`; zero implicit type coercion. |
| **EC-CP-MIGR-02** | Bug in migration function drops fields during version hop | Critical | Every migration function ships with mandatory lossless round-trip test (Gate HG-5). |

### Category D: Storage & Persistence

| ID | Scenario | Severity | Architectural Handling |
|---|---|---|---|
| **EC-CP-PERS-01** | Truncated disk write due to full disk | High | Write to `.tmp` file first, byte-verify and re-parse schema, then atomically rename. Abort on failure. |
| **EC-CP-PERS-02** | Storage adapter interface missing during early development | Medium | Minimal `get`/`put` interface implemented inline during Phase 1 matching Memory Module contract. |

### Category E: Sibling Subsystem Integration

| ID | Scenario | Severity | Architectural Handling |
|---|---|---|---|
| **EC-CP-INT-01** | Usher reads `tailoring_history` before AlignResume has ever run | Medium | Empty list `[]` is valid typed state; Usher safely skips tailoring-ref lookup. |
| **EC-CP-INT-02** | Harvester reads `target_roles` before bootstrap preferences populated | Medium | `target_roles` has `min_length=1`; bootstrap fails loud rather than allowing unconstrained scraping. |
| **EC-CP-INT-03** | Future-Fit renames taxonomy slugs, orphaning existing `taxonomy_ref` | Medium | References validated at write time; orphaned refs surfaced via MG-5 drift telemetry and reconciled manually. |

### Category F: Multi-Tenant & Identity Initialization

| ID | Scenario | Severity | Architectural Handling |
|---|---|---|---|
| **EC-CP-ID-01** | System extended to multi-candidate support | Low | `candidate_id` is a first-class field from `1.0.0` onward; multi-tenant requires routing changes only. |
| **EC-CP-ID-02** | Candidate bootstrapped twice from different resume versions | Medium | `candidate_id` generated once at bootstrap; subsequent runs execute explicit merge path, never duplicate. |
