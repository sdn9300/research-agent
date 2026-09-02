# PDF Auto-Apply Agent — Problem Statement

| Field | Value |
|---|---|
| Document ID | `PAA-PS-1.0` |
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent (proposed codename: **Usher**) |
| Layer | Application |
| Version | 1.0 |
| Status | Draft — Pending Review |
| Date | 27 August 2026 |
| Depends On | Component 1 (The Gleaner), Component 2 (AlignResume), Component 10 (Candidate Profile JSON) |
| Feeds Into | Component 6 (Conductor Orchestrator), Component 8 (Memory Module) |

---

## 1. Executive Summary

The Gleaner discovers relevant postings at scale and AlignResume tailors a resume for each one, but the pipeline currently terminates at *"a correct, tailored PDF exists on disk."* Everything past that point — opening the application, transcribing the same contact details for the two-hundredth time, uploading the right file, answering a handful of platform-specific questions, and clicking submit — is manual, repetitive, and does not scale with the throughput the earlier components are already capable of. Component 7 closes this gap: it is the CONDUCTOR component that converts a *tailored artifact* into a *submitted application*, without compromising the honesty guarantees the rest of the portfolio already enforces.

## 2. Position in CONDUCTOR

Component 7 sits in the **Application** layer, downstream of Discovery and Intelligence, upstream of Learning:

```
[1] Gleaner ──▶ job posting + apply URL
[2] AlignResume ──▶ tailored resume PDF
[10] Candidate Profile JSON ──▶ canonical candidate facts
                              │
                              ▼
                 [7] PDF AUTO-APPLY AGENT
                              │
                              ▼
                   [8] Memory Module ──▶ outcome history
```

It is the only component in the pipeline that writes to a *third party's* system rather than to CONDUCTOR's own data layer — which is the reason this document treats scope and non-goals with unusual care.

## 3. Problem Definition

As of this writing, three of the ten CONDUCTOR components are complete and produce real output at real volume: The Gleaner surfaces postings, Future Fit contextualizes market demand, and AlignResume produces a genuinely tailored, guardrailed PDF per posting. The candidate's actual bottleneck has therefore already shifted — it is no longer "finding jobs" or "writing a resume," it is **the mechanical act of transcription**: copying the same name, email, phone number, education dates, and portfolio links into a new web form, dozens of times a week, across platforms with only superficially different layouts. This is precisely the kind of task that is high-volume, low-judgment, and error-prone under fatigue — exactly the profile of work that should be automated first, and exactly the profile of work where a careless automation would do more damage than a careless human, because the human at least notices when they've made an obvious typo.

## 4. Current State (As-Is)

1. Candidate manually opens each shortlisted posting.
2. Candidate manually re-types or copy-pastes contact information, education history, and links into the platform's form.
3. Candidate manually locates and uploads the correct AlignResume-tailored PDF for that specific posting.
4. Candidate manually answers any screening questions (notice period, CTC expectation, work authorization, free-text prompts).
5. Candidate manually reviews and submits.
6. Outcome (submitted / rejected / no response) is tracked informally or not at all, meaning Memory Module (Component 8) has no reliable input even once it exists.

Steps 1–5 repeat, close to identically, for every posting AlignResume tailors a resume for. Step 6's absence means the loop CONDUCTOR is ultimately meant to close — apply, observe outcome, improve targeting — cannot currently close at all.

## 5. Desired State (To-Be)

1. Conductor Orchestrator (Component 6) hands Component 7 a `JobApplicationTarget` (from Gleaner) and a `ResumeArtifact` (from AlignResume).
2. Component 7 detects the platform, resolves as many form fields as it can with high confidence directly from Candidate Profile JSON, and explicitly declines to guess at the rest.
3. The candidate reviews a completed **draft** — not a black box, a specific, inspectable, pre-filled form — and confirms or corrects it.
4. On confirmation, Component 7 submits, uploads the correct resume, and returns a structured `ApplicationAttemptResult`, regardless of whether the attempt succeeded, needed a human, or failed outright.
5. That result becomes Memory Module's first reliable input, closing the outcome-tracking gap noted above.
6. Only after a platform has accumulated a clean track record in step 3 does the candidate unlock fully autonomous (**AUTO**) submission for that platform — trust is earned per platform, not assumed globally on day one.

## 6. Stakeholders

| Stakeholder | Interest |
|---|---|
| Soumyadeep Nath (operator, sole user) | Time saved per application; zero fabricated or incorrect data submitted under his name; full audit trail. |
| Recruiters / ATS receiving the application | Receive accurate, non-duplicated, non-spammy applications indistinguishable in content quality from a manually completed one. |
| Job platforms (Naukri, Indeed, LinkedIn, and ATS vendors reached via redirect) | Their Terms of Service and anti-automation posture must be respected, not engineered around (see §11 and Mission Plan §9). |
| Downstream CONDUCTOR components (Memory Module, Conductor Orchestrator) | Require a well-formed, non-silent output contract regardless of attempt outcome. |

## 7. Scope

| In Scope (v1.0 target) | Rationale |
|---|---|
| Naukri (native apply flow) | Phase 1 MVP platform — see Architecture Design ADR-PAA-005. |
| Indeed (native "Indeed Apply" flow) | Phase 2 — existing Indeed MCP connector already used for discovery. |
| LinkedIn Easy Apply | Phase 2 — highly standardized UI, but higher anti-automation posture; deferred behind Naukri. |
| Greenhouse, Lever, Workday (vendor-fingerprinted heuristics) | Phase 3 — covers a meaningful share of GenAI/IT-services postings. |
| Draft-and-confirm submission (default) | Non-negotiable default; see Mission Plan §3, ADR-PAA-002. |

| Explicitly Out of Scope (v1.0) | Rationale |
|---|---|
| Platforms whose Terms of Service unambiguously prohibit automated submission | Excluded at the configuration level, not runtime-detected. See Edge Case `EC-PAA-ETH-01`. |
| CAPTCHA-solving or anti-bot circumvention of any kind | See ADR-PAA-004. Detected challenges are a hand-off trigger, never an engineering target. |
| Applications requiring new account creation on the target platform | Routed to `MANUAL_REQUIRED`; revisit only if it becomes a high-frequency blocker. |
| Bulk/indiscriminate application to postings the candidate has not vetted | This component executes applications the pipeline has already decided are worth pursuing; it does not decide *which* postings to pursue. |
| Government portals and phone/paper application processes | Structurally incompatible with a browser-automation approach. |

## 8. Non-Goals

- This is **not** a job-discovery tool (that is Component 1) or a resume-tailoring tool (that is Component 2). It consumes their outputs.
- This is **not** a tool for maximizing application *volume*. Its success metric is accuracy and time-saved on applications the candidate has already decided to make, not the number of applications submitted.
- This is **not** a general-purpose web-form-filling utility. It is scoped specifically to job-application forms with a known, bounded set of field types.
- This is **not** a system designed to operate without the candidate's periodic review. `AUTO` mode is an earned, monitored state — not the system's resting state.

## 9. Success Criteria

| Criterion | Target |
|---|---|
| Time from "resume tailored" to "application submitted or queued for review" | Reduced from an estimated 8–12 minutes manual to under 90 seconds supervised, by Phase 2 exit. |
| Fabricated or incorrect data reaching a real submission | **Zero, for the life of the project.** This is a hard gate, not a percentage (see Evaluation Plan §4). |
| Applications producing a structured, auditable outcome record | 100% of attempts — success, partial, or failure — per the fallback-artifact principle already established across the portfolio. |
| Supported-platform coverage of Research-Agent-surfaced postings | ≥70% routed to a supported adapter rather than `MANUAL_REQUIRED`/`UNSUPPORTED`, by Phase 3 exit. |

## 10. Assumptions & Dependencies

- **Candidate Profile JSON (Component 10)** exposes, at minimum, contact details, education history, links, and an explicit `salary_expectation` / `notice_period` field where the candidate has chosen to set one. Its exact finalized schema is a dependency to reconcile before Phase 0 sign-off — Architecture Design §3 proposes a provisional shape.
- **The Gleaner (Component 1)** emits a job record containing, at minimum, a stable `job_id`, `apply_url`, and `source_platform`. The precise field names of Gleaner's canonical schema are assumed compatible, not independently verified in this document.
- **AlignResume (Component 2)** exposes a `TailoringRun` record with a resolvable file path and a version marker that can be checked against the current Candidate Profile JSON version (see Edge Case `EC-PAA-DAT-03`).
- **Research Agent (Component 4)**, where available, supplies company context that improves the quality of free-text answers, but Component 7 must degrade gracefully — never block — when Research Agent output is absent.

## 11. Constraints

- **Single-account, personal use.** This component operates only on the candidate's own account, with the candidate's own true information. It is not designed, and must not be extended, for multi-identity or third-party use.
- **Platform Terms of Service.** Several target platforms restrict automated form submission in their terms. This component's default posture (draft-and-confirm, no anti-bot circumvention, per-platform exclusion list) is a constraint that shapes the architecture, not an afterthought bolted on at the end — see Mission Plan §9 and Edge Case category `ETH`.
- **Cost.** LLM calls are billed per token against the Groq API already used elsewhere in the portfolio; the architecture must keep the common case (standard fields) at effectively zero marginal LLM cost (see Architecture Design §5).
- **Auditability.** Every attempt must be reconstructable after the fact — what was filled, from what source, at what confidence, and what the platform showed at submission time.

## 12. Glossary

| Term | Definition |
|---|---|
| **Adapter** | A platform-specific module implementing a common interface (`BaseATSAdapter`) for detecting, filling, and submitting on one platform or ATS vendor. |
| **ATS** | Applicant Tracking System — the software (Greenhouse, Lever, Workday, iCIMS, etc.) that receives and manages applications on behalf of an employer. |
| **DRAFT mode** | The default submission mode: the form is completed but not submitted until the candidate confirms. |
| **AUTO mode** | An opt-in, per-platform mode unlocked after a trust-graduation threshold, in which submission proceeds without a pause. |
| **Field resolution** | The process of determining what value, if any, belongs in a given form field, and with what confidence. |
| **Fallback artifact** | A structured output produced for every attempt, including failures — nothing is dropped silently, matching the principle already established in the Sentiment Classifier. |

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial draft. |
