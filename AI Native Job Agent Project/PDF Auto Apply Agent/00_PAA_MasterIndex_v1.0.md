# CONDUCTOR — Component 7: PDF Auto-Apply Agent
## Master Specification Index

| Field | Value |
|---|---|
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent |
| Proposed codename | **Usher** — the one who walks a completed application up to the recruiter's desk. Optional; every document below uses the literal component name, so adopt the codename or ignore it without touching anything downstream. |
| Layer | Application (alongside AlignResume [2] and Overture Outreach [3]) |
| Status | Specification complete — implementation not started |
| Suite version | 1.0 |
| Date | 27 August 2026 |

This suite follows the same six-artifact Spec-Driven Development structure already used for The Harvester (Component 1) and the Sentiment Classifier (Component 9): a document is authoritative for its own domain, cross-references the others by ID rather than repeating their content, and is versioned independently so a later revision to, say, the Evaluation Plan doesn't force a re-issue of the Architecture Design.

### Document Set

| # | Document | ID | Answers |
|---|---|---|---|
| 1 | Problem Statement | `PAA-PS-1.0` | Why does this component need to exist, and what exactly is it *not* trying to do? |
| 2 | Mission Plan | `PAA-MP-1.0` | What is the strategic frame, the phased roadmap, and the operating principles? |
| 3 | Architecture Design | `PAA-AD-1.0` | How is it built — components, schemas, adapters, and the five decisions with the most consequence (ADRs)? |
| 4 | Phase-wise Implementation Plan | `PAA-IP-1.0` | In what order does it get built, and what closes each phase's gate? |
| 5 | Evaluation Plan | `PAA-EP-1.0` | How do we know it works, and how well does it have to work before it's trusted with more autonomy? |
| 6 | Edge Case Plan | `PAA-EC-1.0` | What are the specific, named ways this breaks, and what does the system do in each case? |

### Reading Order

For a first read: **1 → 2 → 3 → 4 → 5 → 6**. For a working session where the architecture is already internalized and the task is "build Phase N": jump straight to **4**, cross-referencing **3** for schemas and **6** for the edge cases that phase must handle.

### Position in CONDUCTOR

```
DATA LAYER            [10] Candidate Profile JSON  ─┐
DISCOVERY              [1] The Harvester            ─┼─▶  [7] PDF AUTO-APPLY AGENT  ─▶  [8] Memory Module
APPLICATION             [2] AlignResume              ─┘         (this suite)
COORDINATION           [6] Conductor Orchestrator  ──────────▶  invokes [7] as a pipeline step
```

Component 7 sits in the Application layer. It is the last automated step before a real human recruiter sees the candidate's name — which is the single fact that shapes almost every architectural and ethical decision in Documents 2, 3, and 6.

### One-Paragraph Summary

The Harvester finds jobs and AlignResume tailors a resume for each one, but the final, most repetitive step — opening the application, typing the same eleven fields for the two-hundredth time, uploading the right PDF, and clicking submit — is still entirely manual. Component 7 automates that final mile using a tiered, cost-aware field-resolution strategy (deterministic first, LLM-assisted only where genuinely needed), a per-platform adapter pattern identical in spirit to The Harvester's, and a human-confirmed **DRAFT** mode as the default — because a wrong field submitted under a real name to a real recruiter is a materially worse failure than a slow one. Autonomous **AUTO** mode is something the system earns per platform, not something it starts with.

### Cross-Document Reference Key

| Referenced as | Found in |
|---|---|
| `ApplicationAttemptResult`, `FieldResolution`, `JobApplicationTarget`, `ResumeArtifact`, `BaseATSAdapter` | Architecture Design §3–4 |
| ADR-PAA-001 through ADR-PAA-005 | Architecture Design §7 |
| Phase 0 – Phase 5 | Implementation Plan §2–7 |
| Weighted scoring rubric, Platform Standing metric | Evaluation Plan §3–4 |
| `EC-PAA-[CAT]-[NN]` edge case IDs | Edge Case Plan |

### Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial suite issued. |
