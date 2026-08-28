# Candidate Profile (JSON) — Mission Plan

**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Document ID:** CONDUCTOR-CP-MP-v2.0  
**Status:** Approved Strategic Directive  
**Governance Anchor:** Law 4 (Canonical Candidate Profile Single Source of Truth)  
**Predecessor Document:** 00-problem-statement.md  
**Companion Documents:** 02-architecture-design.md · 03-implementation-plan.md · 04-evaluation-plan.md · 05-edge-case-plan.md  

---

## 1. Mission Statement

To define, implement, and harden a single canonical, versioned representation of the candidate — **Candidate Profile** — that serves as CONDUCTOR's shared-state contract: the deterministic truth anchor through which every candidate-facing claim must pass validation before any downstream component acts on it, and the substrate every other component reads from and writes to without silent corruption or drift.

---

## 2. Guiding Principles & Law Alignment

| Meta-Principle | Concrete Application in Candidate Profile |
|---|---|
| **Law 4: Single Source of Truth** | One canonical schema (`CandidateProfile`); zero hand-maintained duplicate models in sub-agents. Thin mechanical projections feed consumers (`to_resume_profile`, etc.). |
| **Anti-Fabrication by Construction** | Claim-bearing fields (`skills`, `experience`) carry a mandatory `SourceProvenance` record (`verified: bool`, `source_type`, `source_ref`). AlignResume and Usher guardrails check against verified facts only. |
| **No-Silent-Drop / Atomic Persistence** | Rejected writes never partially apply; prior valid state is preserved via temp-file-and-atomic-rename (`put` contract). |
| **Deterministic-First Validation** | Pydantic v2 validation with `extra="forbid"` is the inviolable gate every write clears regardless of whether data was manually typed or LLM-extracted. |
| **Disjoint Field Ownership** | Every top-level section has exactly one authoritative writer; cross-section write attempts raise `OwnershipViolationError`. History sections are append-only. |
| **Soft Taxonomy Alignment** | `SkillRecord.taxonomy_ref` softly anchors candidate skills to Future-Fit's canonical 100+ market skill taxonomy without rigid coupling (ADR-CP-6). |

---

## 3. 10-Component Ecosystem Dependency Map

```
+---------------------------------------------------------------------------------------------------+
|                                 CANDIDATE PROFILE DEPENDENCY TOPOLOGY                             |
|                                                                                                   |
|  [10] Candidate Profile JSON Engine (Master Anchor)                                               |
|       │                                                                                           |
|       ├──► to_search_criteria()    ──► [1] The Harvester (Reads preferences)                      |
|       ├──► to_resume_profile()     ──► [2] AlignResume (Reads facts, writes tailoring_history)    |
|       ├──► to_outreach_context()    ──► [3] Overture Outreach (Reads contact, writes outreach_hist)|
|       ├──► preferences             ──► [4] Research Agent (Reads target industry/roles)          |
|       ├──◄ taxonomy_ref export     ─── [5] Future-Fit (Supplies canonical skill vocabulary)       |
|       ├──► identity.contact        ──► [6] MCP Chief of Staff (Reads contact info)                |
|       ├──► to_application_view()   ──► [7] PDF Auto-Apply (Reads facts, writes application_hist) |
|       ├──◄ storage substrate       ─── [8] Memory Module (Provides atomic persistence adapter)    |
|       ├──◄ interaction_signals     ─── [9] Sentiment Classifier (Writes classified signal refs)   |
|       └──◄ LangGraph State Host    ─── [0] Conductor Orchestrator (Hosts profile, owns metadata)  |
+---------------------------------------------------------------------------------------------------+
```

### Circularity Verification
- **Harvester ↔ AlignResume:** Harvester reads `preferences`; AlignResume reads candidate facts. Neither depends on the other through Candidate Profile.
- **AlignResume ↔ Usher:** Usher reads `tailoring_history` (written by AlignResume); Usher writes `application_history`. One-way flow, zero cycle.
- **Candidate Profile ↔ Memory Module:** Candidate Profile uses Memory Module's storage engine; Memory Module stores opaque `candidate_id` foreign key. Clean layered boundary.

---

## 4. Risk Register & Mitigations

| Risk | Likelihood | Impact | Architectural Mitigation |
|---|---|---|---|
| Schema over-fits current consumers, breaks when new agent added | Medium | Medium | Canonical-schema-plus-projection pattern (ADR-CP-1) isolates new consumers behind new projection adapters. |
| Concurrent LangGraph branches corrupt shared state | Medium | High | Field-ownership partitioning plus append-only history lists (ADR-CP-2); commutative merges. |
| Provenance metadata adds overhead | Low | Low | Scoped strictly to claim-bearing fields (`skills`, `experience`), not universal. |
| Skill taxonomy drifts from Future-Fit market list | Medium | Low | `taxonomy_ref` is nullable; drift is tracked via monitored telemetry gate MG-5. |
| Bootstrap LLM extraction fabricates a credential | Low | High | Deterministic Pydantic validation gate; `SourceProvenance.verified` defaults to `False` until human-confirmed. |

---

## 5. Definition of Done (DoD) for Candidate Profile v2.0

- [x] Canonical Pydantic v2.0 models implemented with `extra="forbid"`.
- [x] All 6 Hard-Blocking Evaluation Gates (HG-1 to HG-6) passing in pytest suite.
- [x] Real resume data fixture validates with 100% fidelity and 0 schema patches.
- [x] Mechanical projection adapters implemented for AlignResume, Harvester, Overture, and Usher.
- [x] Atomic persistence contract with Memory Module verified via crash-simulation test.
- [x] LangGraph state reducer (`merge_candidate_profile`) tested against adversarial ownership violations.
- [x] Formally unblocks Usher (PDF Auto-Apply) Phase 0 and Harvester Phase 0.
