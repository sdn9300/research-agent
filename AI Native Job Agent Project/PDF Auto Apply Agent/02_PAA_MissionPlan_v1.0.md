# PDF Auto-Apply Agent — Mission Plan

| Field | Value |
|---|---|
| Document ID | `PAA-MP-1.0` |
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent (proposed codename: **Usher**) |
| Layer | Application |
| Version | 1.0 |
| Status | Draft — Pending Review |
| Date | 27 August 2026 |
| Companion to | `PAA-PS-1.0` (Problem Statement), `PAA-AD-1.0` (Architecture Design) |

---

## 1. Mission Statement

To convert every tailored resume the pipeline produces into a correctly, honestly, and auditable submitted application — with the mechanical work automated and the judgment calls reserved for the candidate — while treating each real recruiter on the receiving end with the same accuracy and respect a careful human applicant would.

## 2. Strategic Alignment

This component is not an isolated convenience feature. Per the candidate's own 10–15 year Mission & Long-Term Plan (v1.5), Phase 3 (AI/Agentic Engineer) is explicitly described as already underway "ahead of schedule" through exactly this kind of production agent work, and Phase 5 (AI Automation & Agentic Orchestration Founder) treats the CONDUCTOR portfolio itself as the working prototype of that eventual business. Component 7 is a direct, concrete instance of that thesis: an agent that reasons about a messy, heterogeneous, real-world interface (job-application forms across incompatible platforms) and acts on it correctly — which is functionally the same skill the Forward Deployed Engineer phase (Phase 4) will later demand at enterprise scale, just rehearsed here first at personal scale.

It is also, more immediately, the component that unblocks Memory Module (Component 8): Memory Module cannot track outcomes for applications that were never recorded as having been submitted. Component 7 is therefore a hard prerequisite for the Learning layer of CONDUCTOR to function at all.

## 3. Guiding Principles

These carry over directly from the operating principles already established across AlignResume, Future Fit, and the Sentiment Classifier, applied to this component's specific risks:

1. **Spec before code.** This suite exists before a single line of Playwright is written.
2. **Fallback artifacts are first-class.** Every attempt — success, partial, or failure — produces a structured `ApplicationAttemptResult`. Nothing is dropped silently.
3. **Cost-aware, tiered architecture.** Standard fields resolve deterministically at near-zero cost; LLM assistance is reserved for the genuinely ambiguous minority (mirrors the Sentiment Classifier's rule-based/LLM split).
4. **Honesty by construction, not by review.** The system is architecturally incapable of submitting a value that doesn't trace back to Candidate Profile JSON, AlignResume's output, or explicit candidate input — the same posture as AlignResume's truthfulness guardrail, extended to this component rather than reinvented.
5. **Draft-and-confirm before autonomy.** Trust is earned per platform through an observable track record, not assumed at launch. This mirrors the same adaptive-difficulty logic already built into the candidate's own Adaptive Coding Examiner (level up on success, drop on failure, hold on partial) — applied here to a system's autonomy level instead of a learner's problem difficulty.
6. **Root-cause debugging.** An adapter failure is diagnosed to the specific DOM or platform change that caused it, never patched with a broader selector that risks a false match elsewhere.
7. **Graceful degradation over brittle failure.** An unrecognized field, platform, or challenge routes to `MANUAL_REQUIRED` — it does not guess, and it does not silently fail.

## 4. Objectives & Key Results

**Objective 1 — Eliminate the manual "final mile" without sacrificing accuracy.**
- KR1: ≥80% of DRAFT-mode attempts on supported platforms require zero manual field correction, by Phase 2 exit.
- KR2: Median time from "resume tailored" to "submitted or queued for review" under 2 minutes, by Phase 2 exit.
- KR3: Zero fabricated or incorrect data reaching a real submission, for the life of the project (hard gate).

**Objective 2 — Prove the CONDUCTOR orchestration pattern end-to-end.**
- KR1: One fully orchestrated Harvester → AlignResume → Auto-Apply → Memory Module run completes with no manual glue code, by Phase 4 exit.
- KR2: Component 7 is invocable as a discrete node/tool compatible with the LangGraph-based Conductor shape defined in the candidate's Mission & Long-Term Plan v1.5, §10.6.

**Objective 3 — Build durable, reusable automation infrastructure for the wider portfolio.**
- KR1: The attachment-handling and browser-session utilities are extracted as shared modules, reusable by any future browser-automation component.
- KR2: The adapter interface is documented well enough that onboarding one new platform adapter takes under one focused week, by Phase 3 exit.

## 5. High-Level Roadmap

| Phase | Focus | Gate to Exit |
|---|---|---|
| 0 — Foundations | Contracts, environment, logging scaffold | Schemas validate against fixtures; blank Playwright session opens successfully. |
| 1 — Naukri MVP | Single-platform happy path | ≥90% of a 20-application audited batch reach `DRAFT_PENDING_REVIEW` correctly; zero platform flags. |
| 2 — Indeed + LinkedIn Easy Apply | Multi-platform generalization; first AUTO-mode graduation | Both adapters independently meet Phase 1's accuracy bar. |
| 3 — Generic ATS layer | Greenhouse / Lever / Workday heuristics | ≥70% of Research-Agent-surfaced postings resolve to a supported channel. |
| 4 — Conductor & Memory Module integration | Orchestration wiring | One full end-to-end run with no manual glue code. |
| 5 — Hardening & trust graduation | Observability, regression, AUTO-mode expansion | Ongoing — no fixed exit; monitored continuously. |

Full task-level detail for each phase lives in `PAA-IP-1.0`.

## 6. Go/No-Go Gates

Consistent with the military-style planning already used across the candidate's other project plans:

| Gate | Condition to proceed | If not met |
|---|---|---|
| Phase 0 → 1 | Candidate Profile JSON and Harvester schema dependencies (Problem Statement §10) reconciled, even provisionally. | Hold Phase 1; do not begin adapter code against an unstable contract. |
| Phase 1 → 2 | Phase 1 exit gate met (see roadmap table). | Extend Phase 1; diagnose root cause of any shortfall before adding a second platform. |
| Any platform → AUTO mode | Trust-graduation threshold met for that specific platform (Evaluation Plan §5). | That platform remains DRAFT-only indefinitely — there is no time-based override. |
| Any platform, at any time | A Platform Standing incident occurs (account flag/warning — Edge Case `EC-PAA-SEC-04`). | Immediate, manual rollback to DRAFT-only; AUTO mode requires explicit re-approval, not automatic restoration. |

## 7. Risk Register (High-Level)

Scenario-level detail lives in the Edge Case Plan (`PAA-EC-1.0`); this table captures the risk categories at the strategic level.

| Risk | Category | Mitigation |
|---|---|---|
| Platform ToS / compliance exposure | Ethical / Legal | Per-platform exclusion list at config level (§9); no anti-bot circumvention (ADR-PAA-004). |
| Anti-bot detection or account flags | Technical / Reputational | Detect-and-handoff posture; circuit-breaker on repeated failures; immediate DRAFT-only rollback on any flag. |
| Field mis-mapping → incorrect data submitted | Correctness | Confidence-scored resolution with a hard threshold below which fields are never auto-filled (Architecture Design §5). |
| Candidate Profile JSON drift from reality | Data integrity | `last_verified_at` staleness warning surfaced at session start (Edge Case `EC-PAA-DAT-02`). |
| Adapter breakage from upstream DOM changes | Maintenance | Scheduled Adapter Health Check (Evaluation Plan §6). |
| Over-automation eroding application quality/voice | Reputational | Free-text answers always route to `DRAFT_PENDING_REVIEW`, even in AUTO mode (Edge Case `EC-PAA-MAP-03`). |

## 8. Resource & Tooling Plan

| Resource | Role |
|---|---|
| Playwright (Python) | Browser automation engine — reuses expertise already built for AlignResume's PDF export pipeline. |
| Groq API — LLaMA 3.1 8B | Tier-2 field-label classification (cheap, fast). |
| Groq API — LLaMA 3.3 70B | Tier-3 free-text draft generation (grounded, higher-stakes). |
| Pydantic v2 | Data contracts (`schemas.py`), consistent with the rest of the portfolio. |
| Candidate Profile JSON (Component 10) | Sole source of truth for candidate facts — never invented, never guessed. |
| Docker | Eventual containerization for Kubernetes Job/Deployment execution under Conductor, consistent with the DevOps roadmap's Phase 6–7 work. |

## 9. Ethical Use & Platform Compliance Principles

Recorded here plainly, in the same register as the rest of this risk-aware plan — not as a disclaimer, but as an operating constraint the architecture is built around from the start:

- **Single identity, true data, personal use only.** This is not a scraping tool, a spam tool, or a multi-account tool.
- **Platforms whose terms unambiguously prohibit automated submission are excluded at the configuration level.** Postings from such platforms route to `MANUAL_REQUIRED` by policy, not by runtime detection — see Edge Case `EC-PAA-ETH-01`.
- **Anti-automation challenges (CAPTCHA, behavioral checks) are a hard stop, never an engineering target.** See ADR-PAA-004 in the Architecture Design.
- **Rate limits are respected, not tested.** The system is designed to look, from the platform's perspective, like a careful and moderately paced human user — not to maximize throughput against a defended system.
- **Any account-level flag or warning triggers an immediate, manual, non-automatic rollback** to DRAFT-only for that platform (§6, Edge Case `EC-PAA-SEC-04`).

## 10. Definition of Done — v1.0

Component 7 is considered at v1.0 when: Phases 0–4 have exited their gates; at least Naukri, Indeed, and LinkedIn Easy Apply are supported adapters; the Conductor Orchestrator can invoke it as a pipeline step; Memory Module receives a well-formed `ApplicationAttemptResult` for every attempt; and zero fabrication or Platform Standing incidents have occurred across the full test and early-production history.

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial draft. |
