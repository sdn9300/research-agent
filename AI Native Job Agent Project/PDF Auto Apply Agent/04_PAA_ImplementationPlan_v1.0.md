# PDF Auto-Apply Agent — Phase-wise Implementation Plan

| Field | Value |
|---|---|
| Document ID | `PAA-IP-1.0` |
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent (proposed codename: **Usher**) |
| Layer | Application |
| Version | 1.0 |
| Status | Draft — Pending Review |
| Date | 27 August 2026 |
| Depends On | `PAA-AD-1.0` (schemas, adapters, ADRs referenced throughout) |

---

## 1. Overview & Sequencing Logic

Six phases, each with an explicit entry condition, deliverables, and exit gate — no phase begins before the previous one's gate is met (Mission Plan §6). Effort estimates assume the candidate's established ~8–10 focused hours/week pace. Phase 3 onward can absorb Kubernetes/Docker learning from the concurrent DevOps roadmap without blocking, per that roadmap's own "retrofit, don't duplicate" principle.

## 2. Phase 0 — Foundations & Contracts *(≈1 week)*

**Objective.** Lock down data contracts, environment, and integration seams before any adapter code is written.

**Entry criteria.** `PAA-AD-1.0` reviewed and accepted; Candidate Profile JSON and Harvester schema dependencies at least provisionally reconciled (Problem Statement §10).

**Deliverables**
- `schemas.py` — all Pydantic v2 models from Architecture Design §3.
- `config.yaml` — platform priority order, default submission mode, rate limits, Groq model routing thresholds.
- Playwright environment bootstrap, including persistent per-platform session-state storage.
- Logging/audit scaffold — every attempt writes a JSON record (+ optional screenshot) to a local `attempts/` directory, live from day one.
- Stub `BaseATSAdapter` abstract class with no concrete implementations yet.

**Tasks**
1. Author `schemas.py` and validate against a hand-written fixture `CandidateProfile` and `JobApplicationTarget`.
2. Stand up Playwright, confirm a blank Chromium context opens and closes cleanly.
3. Implement the `attempts/` audit-log writer, independent of any adapter, and test it against a dummy `ApplicationAttemptResult`.
4. Define `config.yaml` structure and the confidence threshold constant (0.85, Architecture Design §5).
5. Write the `BaseATSAdapter` interface and one no-op test adapter to confirm the interface is actually implementable end-to-end.
6. Reconcile schema field names against Harvester's and Component 10's actual outputs where available; document any remaining mismatch as an open item.

**Exit gate.** Schemas validate against fixtures; a smoke test opens Playwright, writes one dummy attempt record, and closes cleanly.

## 3. Phase 1 — Naukri MVP *(≈2–3 weeks)*

**Objective.** Prove the end-to-end happy path on a single, profile-based platform (ADR-PAA-005).

**Deliverables**
- `NaukriAdapter` implementing all five `BaseATSAdapter` methods.
- Tier-0 selector dictionary for Naukri's apply modal.
- Tier-2 (LLaMA 3.1 8B) integration for supplementary screening questions.
- Interactive DRAFT-mode pause-and-review flow (CLI confirmation is sufficient for v1).
- `AttachmentHandler` shared utility, built here and reused by every later adapter.

**Tasks**
1. Implement `NaukriAdapter.detect()` against known Naukri URL/DOM patterns.
2. Build the Tier-0 selector dictionary from a sample of real Naukri apply flows.
3. Implement `map_fields()` calling the four-tier resolver in order, stopping at the first tier that clears the confidence threshold.
4. Implement `fill()` and `attach_resume()`, the latter calling the shared `AttachmentHandler`.
5. Implement `submit_or_hold()` for `DRAFT` mode only (AUTO deferred to Phase 2).
6. Wire the Outcome Recorder so every attempt — including failures — produces an `ApplicationAttemptResult`.
7. Run a 20-application manually-audited test batch; hand-verify every field against ground truth.
8. Fix root causes of any Phase-1 shortfall before declaring the gate met (never patch with a broader selector, per Mission Plan principle 6).

**Exit gate.** ≥90% of the 20-application audited batch reach `DRAFT_PENDING_REVIEW` with zero fabricated or incorrect standard-field values; zero platform lockouts or flags observed.

## 4. Phase 2 — Indeed + LinkedIn Easy Apply *(≈3–4 weeks)*

**Objective.** Generalize the architecture across two structurally different platforms and introduce AUTO-mode graduation.

**Deliverables**
- `IndeedAdapter` and `LinkedInEasyApplyAdapter`, each independently meeting the Phase 1 accuracy bar.
- First working AUTO-mode trust-graduation logic (Evaluation Plan §5), gated strictly behind a clean Phase 1 track record on Naukri.
- Generalized resume-upload handling proven reusable, not platform-specific.

**Tasks**
1. Build `IndeedAdapter`, reusing the shared `AttachmentHandler` and resolver ladder unchanged.
2. Build `LinkedInEasyApplyAdapter`, with explicit extra caution around its known-aggressive anti-automation posture (ADR-PAA-004) — expect a materially higher `MANUAL_REQUIRED` rate here, and treat that as correct behavior, not a defect.
3. Implement the trust-graduation counter and the AUTO-mode unlock check per platform.
4. Re-run the 20-application audit methodology independently for each new platform.
5. Confirm free-text (Tier-3) fields still route to review even where AUTO mode is unlocked (Edge Case `EC-PAA-MAP-03`).

**Exit gate.** Both adapters independently meet Phase 1's accuracy bar; LinkedIn's CAPTCHA/challenge hand-off rate is documented as a monitored, not blocking, metric.

## 5. Phase 3 — Generic ATS Heuristic Layer *(≈4–5 weeks)*

**Objective.** Extend coverage to the long tail of company-hosted ATS platforms reached via redirect.

**Deliverables**
- Vendor-fingerprinted sub-adapters: `GreenhouseAdapter`, `LeverAdapter`, `WorkdayAdapter`, each detecting by URL pattern or DOM fingerprint rather than one universal heuristic.
- `GenericATSAdapter` as the genuine last resort — Tier-3 LLM-assisted field-label matching for anything none of the above recognize.
- Expanded Tier-0 dictionaries per vendor.

**Tasks**
1. Collect a sample set of real Greenhouse/Lever/Workday postings surfaced via Research Agent and Harvester.
2. Build vendor detection first (cheap, deterministic), before any field-mapping work.
3. Implement each vendor sub-adapter's Tier-0 dictionary from the sample set.
4. Implement `GenericATSAdapter`'s LLM-assisted fallback, explicitly bounded to never auto-submit — always `DRAFT_PENDING_REVIEW` or `MANUAL_REQUIRED` given the higher uncertainty here.
5. Measure the coverage metric: % of Research-Agent-surfaced postings resolving to a supported channel vs. `UNSUPPORTED`.

**Exit gate.** ≥70% coverage of Research-Agent-surfaced postings.

## 6. Phase 4 — Conductor & Memory Module Integration *(≈1–2 weeks)*

**Objective.** Wire Component 7 into the orchestrated pipeline.

**Deliverables**
- Conductor Orchestrator (Component 6) can invoke Component 7 as a pipeline step, passing `JobApplicationTarget` and `CandidateProfile` and receiving `ApplicationAttemptResult`.
- `ApplicationAttemptResult` records persisted in the format Memory Module (Component 8) expects to consume.
- One complete, unassisted, end-to-end run: Harvester discovers → AlignResume tailors → Auto-Apply Agent attempts → Memory Module records — for at least one real job.

**Tasks**
1. Define the exact invocation contract Conductor will use (function signature or LangGraph node interface).
2. Confirm shared-state compatibility with the Conductor architecture described in the candidate's Mission & Long-Term Plan v1.5, §10.6.
3. Implement the Memory Module output adapter (or a stub matching its expected schema, if Memory Module itself is not yet built).
4. Run one real, full pipeline pass and manually verify every hop.

**Exit gate.** One fully orchestrated run completes with no manual glue code between components.

## 7. Phase 5 — Hardening, Observability & Trust Graduation *(ongoing)*

**Objective.** Move from "working" to "trustworthy over time."

**Deliverables**
- Scheduled Adapter Health Check (Evaluation Plan §6) — a recurring smoke test per adapter that detects breakage from upstream DOM changes before a real attempt does.
- Cost dashboard (Groq token spend per attempt, trending).
- Screenshot/audit retention policy.
- Continued, per-platform AUTO-mode graduation as track record accumulates.
- Docker containerization for eventual Kubernetes execution under Conductor.

**Tasks**
1. Build the Adapter Health Check as a standalone scheduled job, independent of live application attempts.
2. Instrument Groq cost tracking per attempt and aggregate into a simple dashboard.
3. Define and implement screenshot/log retention rules (age-based cleanup).
4. Containerize the component; confirm it runs correctly inside Docker with the same behavior as bare-metal.

**Exit gate.** None fixed — this phase runs continuously, monitored against the metrics in the Evaluation Plan.

## 8. Phase Summary Table

| Phase | Focus | Est. Effort | Exit Gate (abridged) |
|---|---|---|---|
| 0 | Foundations & contracts | ~1 week | Schemas + smoke test pass |
| 1 | Naukri MVP | ~2–3 weeks | ≥90% accuracy, zero flags |
| 2 | Indeed + LinkedIn Easy Apply | ~3–4 weeks | Both meet Phase 1 bar |
| 3 | Generic ATS layer | ~4–5 weeks | ≥70% posting coverage |
| 4 | Conductor + Memory Module integration | ~1–2 weeks | One clean end-to-end run |
| 5 | Hardening & trust graduation | Ongoing | Continuous monitoring |

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial draft. |
