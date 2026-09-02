# Candidate Profile (JSON) — Evaluation Plan

**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Document ID:** CONDUCTOR-CP-EP-v2.0  
**Status:** Approved Quality Assurance Standard  
**Governance Anchor:** Law 4 (Canonical Candidate Profile Single Source of Truth)  
**Predecessor Document:** 03-implementation-plan.md  
**Companion Documents:** 00-problem-statement.md · 01-mission-plan.md · 02-architecture-design.md · 05-edge-case-plan.md  

---

## 1. Hard-Blocking Evaluation Gates (HG-1 to HG-6)

> [!IMPORTANT]
> All six hard-blocking gates must pass before any dependent sub-agent (Usher, Gleaner, AlignResume) is authorized to build production dependencies on this schema.

| ID | Gate Name | Acceptance Procedure | Implementation Phase |
|---|---|---|---|
| **HG-1** | Real-Data Ingestion Fidelity | 100% Pydantic validation pass rate on real `resume.pdf`; assert 0 schema patches needed. | Phase 0 |
| **HG-2** | Round-Trip Serialization | Pydantic $\rightarrow$ JSON $\rightarrow$ Pydantic on real fixture; assert 100% field-for-field equivalence excluding `updated_at`. | Phase 1 |
| **HG-3** | Atomic-Write Crash Safety | Kill write process mid-write (SIGKILL); assert prior valid file on disk is untouched and loads cleanly. | Phase 1 |
| **HG-4** | Ownership-Violation Rejection | Adversarial suite: every component attempts an illegal section write; assert every attempt raises `OwnershipViolationError`. | Phase 3 |
| **HG-5** | Schema-Version Migration Chain | Synthetic semver hop (`1.0.0` $\rightarrow$ `1.1.0`) with registered migration function passes lossless round-trip test. | Phase 1 |
| **HG-6** | Strict `extra="forbid"` Enforcement | Injected unknown field on every model raises immediate `ValidationError`, never silently accepted. | Phase 0 |

---

## 2. Monitored Telemetry Gates (MG-1 to MG-5)

| ID | Metric | What it Signals | Expected Steady-State |
|---|---|---|---|
| **MG-1** | Validation Failure Rate | Production writes hitting unmapped schema edges | Trend toward 0% |
| **MG-2** | Schema Version Drift Rate | Components pinned to legacy semver | 0 pinned to legacy |
| **MG-3** | Accumulated Profile Read Latency | History array growth impact on read performance | Flat $< 50$ms |
| **MG-4** | Ownership Violation Attempt Rate | Sub-agent coding bugs trying illegal writes | Exactly 0 |
| **MG-5** | `taxonomy_ref` Null Rate | Future-Fit skill vocabulary coverage | Decreasing over time |

---

## 3. Automated Test Execution Suite

```bash
# 1. Run all Candidate Profile unit & schema tests
pytest tests/test_candidate_profile.py -v

# 2. Run adversarial ownership-violation suite
pytest tests/test_profile_ownership.py -v

# 3. Run atomic persistence crash simulation
pytest tests/test_profile_persistence.py -v

# 4. Run projection adapter tests (AlignResume, Gleaner, Overture, Usher)
pytest tests/test_profile_projections.py -v
```
