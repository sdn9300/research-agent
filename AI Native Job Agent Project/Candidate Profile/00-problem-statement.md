# Candidate Profile (JSON) — Problem Statement

**Component:** #10 — Candidate Profile JSON (Data & Anchor Layer)  
**Parent System:** CONDUCTOR / UNIFIED CAREEROS — Autonomous Job Search Pipeline  
**Document ID:** CONDUCTOR-CP-PS-v2.0  
**Status:** Approved for Implementation  
**Author:** Soumyadeep Nath  
**Date:** August 2026  
**Intended Path:** `conductor/specs/candidate-profile/00-problem-statement.md`  
**Governance Anchor:** Law 4 (Canonical Candidate Profile Single Source of Truth)  
**Companion Documents:** 01-mission-plan.md · 02-architecture-design.md · 03-implementation-plan.md · 04-evaluation-plan.md · 05-edge-case-plan.md  

---

## 1. Problem Context

CONDUCTOR / UNIFIED CAREEROS is architected as ten LangGraph-compatible components coordinating around a shared state object. Nine of those components — The Harvester [1], AlignResume [2], Overture [3], Research Agent [4], Future Fit [5], MCP Chief of Staff [6], Usher (PDF Auto-Apply Agent) [7], Memory Module [8], and Sentiment Classifier [9] — are process nodes: each discovers, transforms, or acts on candidate-related data, but none of them *is* the candidate.

Historically, each treated "the candidate" as an external, informally-shaped input:
- AlignResume shipped its own `ResumeProfile` domain model, built before any canonical candidate schema existed.
- Usher (PDF Auto-Apply) explicitly named two open schema dependencies blocking its Phase 0 sign-off: Harvester's canonical job-field names, and Candidate Profile JSON's finalized shape.
- Overture Outreach and Chief of Staff parsed contact and profile facts from disparate text fields.

This is the standard N-consumers / no-schema failure mode: every component built against an implicit contract encodes its own private assumptions, and those assumptions silently diverge the moment a second component makes a different one. The failure surfaces as fabricated resume claims, broken ATS field mappings, or duplicate applications.

---

## 2. Problem Statement

CONDUCTOR has historically lacked a single, versioned, validated, and anti-fabrication-guarded representation of the candidate that its process components can safely read from and write to.

This document formalizes **Candidate Profile JSON [10]**, resolving the active schema blocker for **Usher (#7) Phase 0** and **The Harvester (#1) Phase 0**, and establishing the immutable truth anchor for all downstream resume tailoring, outreach generation, and automated ATS application submissions.

---

## 3. Why Now

Two concrete forcing functions:
1. **Usher (#7) is schema-blocked today:** Its Phase 0 sign-off cannot proceed until the Candidate Profile shape is finalized. This specification directly resolves that blocker.
2. **The Harvester (#1) is the next scheduled build:** Harvester's search parameterization requires a structured source of truth for candidate role, location, and seniority preferences (`preferences`). Sequencing this spec ahead of Harvester implementation avoids schema inversion where scraper column names dictate candidate identity.
3. **Memory Module (#8) v2.0 is complete:** Memory Module's storage engine and FastMCP tool mesh are now fully specified, providing a concrete persistence substrate for Candidate Profile.

---

## 4. Stakeholder Integration Matrix

| Component | Status (Aug 2026) | Relationship to Candidate Profile | Consequence of Continued Absence |
|---|---|---|---|
| **[1] Harvester** | Spec complete | Read-only consumer of `preferences` (via `to_search_criteria()`) | Search criteria hand-coded per run, not centrally editable |
| **[2] AlignResume** | Live, deployed (Vercel) | Heavy read consumer (`identity`, `education`, `skills`, `experience`); writer of `tailoring_history` | `ResumeProfile` stays a hand-maintained duplicate, permanently drift-prone |
| **[3] Overture Outreach** | Implemented (pytest, Docker) | Read consumer (`identity.contact`, `preferences`); writer of `outreach_history` | No shared record of what's already been sent, to whom, or when |
| **[4] Research Agent** | Spec complete | Read-only consumer of `preferences` (industry/role scope) | Re-derives candidate targeting logic locally instead of reading it once |
| **[5] Future Fit** | Live, deployed (Streamlit) | Indirect — canonical source for `skills.taxonomy_ref` | No controlled vocabulary linking candidate skills to market-demand data |
| **[6] MCP Chief of Staff** | Spec complete | Read consumer of `identity.contact`; host of Approval Gate | Recruiter replies lack unified candidate context for draft generation |
| **[7] Usher (PDF Auto-Apply)**| Spec complete (**Phase 0 unblocked by this spec**) | Heavy read consumer; writer of `application_history` | Sign-off cannot proceed — this was the direct, named blocker |
| **[8] Memory Module** | **Spec complete (v2.0 FastMCP / SQLite WAL)** | Storage substrate for this schema (Architecture Design, ADR-CP-4) | State events and profile metadata unsynchronized |
| **[9] Sentiment Classifier** | Live, deployed (v1.0.1) | Writer of `interaction_signals` | Classified signals have no durable home tied to the candidate |
| **[0] Conductor Orchestrator**| Spec complete | Runtime host — threads Candidate Profile as LangGraph shared state | Orchestrator's core data contract is undefined |

---

## 5. Scope Boundaries

### In Scope
- Canonical Pydantic v2 schema for candidate identity, contact info, education, skills, experience/projects, and application preferences.
- Anti-fabrication source provenance metadata (`SourceProvenance`) on claim-bearing fields (`skills`, `experience`).
- Cross-component history rollups: `tailoring_history`, `outreach_history`, `application_history`, `interaction_signals`.
- Mechanical projection adapters: `to_resume_profile()`, `to_search_criteria()`, `to_outreach_context()`, `to_application_view()`.
- Disjoint field-ownership partitioning and LangGraph reducer (`merge_candidate_profile()`).
- Atomic persistence contract with Memory Module storage layer (`get`, `put`, `list_versions`).
- Explicit semver versioning and migration strategy (`schema_version`).

### Out of Scope
- Job-posting schema (owned by The Harvester).
- Automated LLM extraction prompts (ingestion pipeline concern).
- Memory Module's internal SQLite table DDL (owned by Memory Module [8]).
- Direct browser form filling or email dispatch (owned by Usher [7] and Chief of Staff [6]).
- Multi-tenant authentication (single-operator system in v1/v2).

---

## 6. Success Criteria

1. Every component in §4 has an unambiguous, typed read/write contract against this schema with zero `TBD` fields.
2. Usher's Candidate-Profile-side schema dependency is formally marked resolved.
3. The schema validates the candidate's actual resume data (resume.pdf, About Me documents) with zero manual patching (Gate HG-1).
4. Pydantic $\rightarrow$ JSON $\rightarrow$ Pydantic round-trip is 100% lossless (Gate HG-2).
5. All illegal cross-section write attempts raise `OwnershipViolationError` (Gate HG-4).
