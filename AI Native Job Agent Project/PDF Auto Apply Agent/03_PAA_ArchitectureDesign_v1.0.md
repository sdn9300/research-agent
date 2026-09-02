# PDF Auto-Apply Agent — Architecture Design

| Field | Value |
|---|---|
| Document ID | `PAA-AD-1.0` |
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent (proposed codename: **Usher**) |
| Layer | Application |
| Version | 1.0 |
| Status | Draft — Pending Review |
| Date | 27 August 2026 |
| Depends On | `PAA-PS-1.0`, `PAA-MP-1.0` |

---

## 1. Architectural Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    (6) CONDUCTOR ORCHESTRATOR                         │
│              invokes Component 7 as a pipeline step                   │
└───────────────────────────────┬───────────────────────────────────────┘
                                 │
        ┌────────────────────────┼─────────────────────────┐
        ▼                        ▼                          ▼
┌────────────────┐     ┌───────────────────┐     ┌──────────────────────┐
│ (1) GLEANER    │     │ (2) ALIGNRESUME    │     │ (10) CANDIDATE PROFILE │
│ JobApplication   │     │ ResumeArtifact /   │     │      JSON              │
│ Target           │     │ TailoringRun       │     │  (canonical facts)     │
└────────┬─────────┘     └─────────┬──────────┘     └───────────┬────────────┘
         │                         │                             │
         └───────────┬─────────────┴──────────────┬──────────────┘
                      ▼                            ▼
        ┌────────────────────────────────────────────────────────────┐
        │              (7) PDF AUTO-APPLY AGENT  ("Usher")             │
        │                                                                │
        │  ┌────────────────┐   ┌──────────────────┐   ┌─────────────┐  │
        │  │ Platform        │   │ Field Resolver    │   │ Submission   │  │
        │  │ Detector /      │──▶│ (Tier 0 → Tier 3)  │──▶│ Gatekeeper   │  │
        │  │ Adapter Router  │   │                    │   │ DRAFT / AUTO │  │
        │  └────────────────┘   └──────────────────┘   └──────┬──────┘  │
        └───────────────────────────────────────────────────────┼─────────┘
                                                                  ▼
                                              ┌─────────────────────────────┐
                                              │  (8) MEMORY MODULE            │
                                              │  ApplicationAttemptResult     │
                                              └───────────────────────────────┘
```

Component 7 is designed to be invocable as a discrete node/tool within the LangGraph-based Conductor Orchestrator shape defined in the candidate's Mission & Long-Term Plan v1.5 (§10.6): it reads `JobApplicationTarget` and `CandidateProfile` from shared state and writes `ApplicationAttemptResult` back into that same shared state, rather than assuming a bespoke calling convention.

## 2. Component Breakdown

| Sub-module | Responsibility |
|---|---|
| **Platform Detector / Adapter Router** | Inspects `apply_url` and, once the browser lands, the DOM, to select the correct `BaseATSAdapter` implementation. |
| **Field Resolver** | Runs the tiered resolution ladder (§5) against each detected form field, producing a `FieldResolution` with a confidence score. |
| **Attachment Handler** | Locates the correct resume file from a `ResumeArtifact`, verifies its checksum against AlignResume's latest `TailoringRun`, and performs the upload. Shared across all adapters (DRY). |
| **Submission Gatekeeper** | Enforces DRAFT vs. AUTO mode; the sole component permitted to trigger a final submit action. |
| **Outcome Recorder** | Assembles and persists the `ApplicationAttemptResult`, screenshots, and audit log for every attempt, regardless of outcome. |

## 3. Data Contracts / Schemas

The following are **provisional contracts** proposed by this document. `JobApplicationTarget`'s upstream fields and `CandidateProfile`'s full shape must be reconciled against Gleaner's and Component 10's actual finalized schemas before Phase 0 sign-off (Problem Statement §10).

```python
from enum import Enum
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel, HttpUrl

class ApplicationChannel(str, Enum):
    NAUKRI = "naukri"
    INDEED = "indeed"
    LINKEDIN_EASY_APPLY = "linkedin_easy_apply"
    GENERIC_ATS_GREENHOUSE = "generic_ats_greenhouse"
    GENERIC_ATS_LEVER = "generic_ats_lever"
    GENERIC_ATS_WORKDAY = "generic_ats_workday"
    GENERIC_ATS_UNKNOWN = "generic_ats_unknown"
    UNSUPPORTED = "unsupported"

class JobApplicationTarget(BaseModel):
    job_id: str
    title: str
    company: str
    apply_url: HttpUrl
    source_platform: str            # from Gleaner's canonical schema (provisional)
    detected_channel: Optional[ApplicationChannel] = None

class ResumeArtifact(BaseModel):
    tailoring_run_id: str           # from AlignResume's TailoringRun
    file_path: str
    file_checksum: str
    profile_version: str            # Candidate Profile JSON version this was tailored against
    generated_at: datetime

class FieldResolution(BaseModel):
    field_label: str
    resolution_tier: Literal[
        "tier0_selector", "tier1_fuzzy", "tier2_llm_light", "tier3_llm_heavy", "unresolved"
    ]
    resolved_value: Optional[str]
    confidence: float               # 0.0 - 1.0
    source: Literal["candidate_profile", "generated", "manual_required"]

class SubmissionMode(str, Enum):
    DRAFT = "draft"                 # default — pauses before final submit
    AUTO = "auto"                   # opt-in per platform, post trust-graduation
    SKIP = "skip"                   # known-unsupported, not attempted

class ApplicationAttemptResult(BaseModel):
    attempt_id: str
    job: JobApplicationTarget
    resume_used: ResumeArtifact
    status: Literal[
        "SUBMITTED", "DRAFT_PENDING_REVIEW", "MANUAL_REQUIRED",
        "AMBIGUOUS_OUTCOME", "FAILED", "SKIPPED"
    ]
    field_resolutions: list[FieldResolution]
    screenshot_path: Optional[str]
    error_code: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]
    groq_tokens_used: int = 0
    groq_cost_estimate_usd: float = 0.0
```

Note the deliberate absence of any status value that means "probably worked." `AMBIGUOUS_OUTCOME` exists specifically so the system never assumes success from a confirmation page it doesn't recognize (Edge Case `EC-PAA-SUB-01`).

## 4. Adapter Pattern

Mirrors The Gleaner's abstract adapter pattern directly — a deliberate, DRY reuse of an already-proven design rather than a new pattern invented for this component:

```python
from abc import ABC, abstractmethod
from playwright.sync_api import Page

class BaseATSAdapter(ABC):
    @abstractmethod
    def detect(self, page: Page, url: str) -> bool: ...

    @abstractmethod
    def map_fields(self, page: Page, profile: "CandidateProfile") -> list[FieldResolution]: ...

    @abstractmethod
    def fill(self, page: Page, resolutions: list[FieldResolution]) -> None: ...

    @abstractmethod
    def attach_resume(self, page: Page, resume: ResumeArtifact) -> bool: ...

    @abstractmethod
    def submit_or_hold(self, page: Page, mode: SubmissionMode) -> ApplicationAttemptResult: ...
```

Concrete implementations, in build order: `NaukriAdapter` (Phase 1) → `IndeedAdapter`, `LinkedInEasyApplyAdapter` (Phase 2) → `GreenhouseAdapter`, `LeverAdapter`, `WorkdayAdapter`, `GenericATSAdapter` (Phase 3, vendor-fingerprinted by URL/DOM pattern, with `GenericATSAdapter` as the true last-resort fallback for anything unrecognized).

## 5. Field Resolution Strategy — Four Tiers, Escalating Only as Needed

| Tier | Mechanism | Cost | Used for |
|---|---|---|---|
| **Tier 0** | Exact selector dictionary, maintained per adapter | None | Standard fields with a known, stable DOM signature (email, phone, resume-upload input). |
| **Tier 1** | Fuzzy label-text match against a synonym dictionary | None (no LLM call) | Fields not caught by Tier 0 but with a recognizable label ("Mobile Number" → phone). |
| **Tier 2** | Groq LLaMA 3.1 8B — label + Candidate Profile schema → best-field guess + confidence | Low | Ambiguous or unusually-labeled standard fields. |
| **Tier 3** | Groq LLaMA 3.3 70B — grounded free-text generation | Higher, bounded | Genuinely open-ended prompts ("Why do you want to work here?"), always routed to `DRAFT_PENDING_REVIEW` regardless of mode. |

This is the same cost-aware, escalate-only-when-needed shape already proven in the Sentiment Classifier's rule-based/LLM split — applied here to form fields instead of recruiter emails. **Below a confidence threshold of 0.85, a field is never auto-filled**, at any tier; it is marked `MANUAL_REQUIRED` instead of guessed (Edge Case `EC-PAA-MAP-04`). Tier-3 output is explicitly instructed never to introduce a claim, employer, or metric absent from Candidate Profile JSON, AlignResume's tailoring rationale, or Research Agent's company brief — reusing AlignResume's existing truthfulness-guardrail concept rather than re-deriving it from scratch.

## 6. Browser Automation Layer

Playwright (Python), driven by the adapters above. See ADR-PAA-001 for the full comparison against alternatives. Session state (cookies/tokens) is persisted locally per platform via Playwright's storage-state mechanism, never transmitted to any third party.

## 7. Architecture Decision Records

### ADR-PAA-001: Browser Automation Engine

**Status:** Accepted · **Date:** 2026-08-27

**Context.** Reliable, scriptable control of a real browser is needed to navigate, fill forms, upload files, and detect confirmation states across heterogeneous platforms.

**Decision.** Playwright (Python bindings), reusing the project's existing Playwright expertise from AlignResume's headless PDF-export pipeline.

**Options Considered**

| Option | Complexity | Cost | Fit |
|---|---|---|---|
| Playwright | Low (team-familiar) | Free, self-hosted | Deterministic auto-waiting; shared tooling with AlignResume |
| Selenium | Medium | Free, self-hosted | Older, more boilerplate, weaker auto-waiting |
| Stealth/undetected-chromedriver forks | Medium–High | Free | Rejected outright — purpose-built for anti-bot evasion, incompatible with Mission Plan §9 |
| LLM-native agentic browsing (Browser-use / Stagehand style) | High | Higher (per-action LLM cost) | Better for truly novel DOMs; too costly/non-deterministic as the *default* engine |

**Consequences.** Consistent tooling and shared team knowledge with AlignResume; adapters must be maintained against upstream DOM drift (mitigated by the Adapter Health Check, Evaluation Plan §6). LLM-native browsing is reserved as a Phase 3+ fallback specifically for the Generic ATS long tail, not the default.

---

### ADR-PAA-002: Default Submission Mode

**Status:** Accepted · **Date:** 2026-08-27

**Context.** A mis-submitted or inaccurate application carries real reputational cost — it reaches a real recruiter under the candidate's real name — and several platforms' terms constrain unattended automated submission.

**Decision.** Default mode is **DRAFT**: the agent completes the form and pauses before the final submit action. **AUTO** is an explicit, per-platform opt-in unlocked only after a trust-graduation threshold (Evaluation Plan §5).

**Options Considered**

| Option | Pros | Cons |
|---|---|---|
| Always-AUTO | Maximizes speed | Unacceptable blast radius if a field is silently mis-mapped; violates honesty-by-construction principle |
| Always-manual (agent fills, human always clicks submit) | Safest | Doesn't scale toward the stated time-savings objective as the permanent end-state |
| DRAFT default, AUTO earned per platform (chosen) | Balances speed and safety; trust is observable, not assumed | Requires building and tracking a graduation metric |

**Consequences.** Phase 1–2 will feel closer to "smart autofill" than "full autonomy" — intentional. AUTO-mode graduation becomes a first-class, monitored metric.

---

### ADR-PAA-003: Field Resolution Strategy

**Status:** Accepted · **Date:** 2026-08-27

**Context.** The large majority of fields on a given platform are highly standardized; a small minority require judgment or free text.

**Decision.** Four-tier resolution ladder (§5), escalating only as far as a given field requires, mirroring the cost-aware pattern already proven in the Sentiment Classifier.

**Trade-off Analysis.** An LLM-first design (send the full form DOM to a large model every time) was rejected on both cost/latency grounds and determinism grounds — the fields where correctness matters most (contact details) are exactly the fields that should least depend on model sampling variance.

**Consequences.** Cost stays low for the common case; latency budget concentrates on the genuinely hard fields; Tier-0/1 dictionaries require ongoing maintenance, addressed by the Adapter Health Check.

---

### ADR-PAA-004: Anti-Automation Encounters

**Status:** Accepted · **Date:** 2026-08-27

**Context.** Several platforms deploy CAPTCHA or behavioral bot-detection challenges. Defeating these is both technically fragile and contractually fraught — most platforms' terms explicitly prohibit circumventing anti-automation controls.

**Decision.** Any detected CAPTCHA/challenge is an immediate, hard trigger for `MANUAL_REQUIRED`: the agent pauses, screenshots the state, and hands control back to the candidate. It never attempts to solve, bypass, or outsource-solve such challenges.

**Options Considered.** Third-party CAPTCHA-solving integration and stealth/fingerprint-evasion techniques were both rejected outright, on ethical and Terms-of-Service grounds — see Mission Plan §9. Note this is a materially different ethical context from The Gleaner's read-only "stealth" discovery scraping: here the agent is authenticated and submitting data as an identified applicant, where circumvention carries a different, higher weight.

**Consequences.** Some fraction of applications on more aggressively bot-defended platforms (notably LinkedIn) will always fall through to `MANUAL_REQUIRED`. This is an accepted, monitored ceiling — not a defect to "fix" through evasion.

---

### ADR-PAA-005: Platform Sequencing

**Status:** Accepted, open for revision once Phase 1 metrics are in · **Date:** 2026-08-27

**Context.** An MVP platform is needed to prove the architecture before adapters multiply.

**Decision.** Phase 1 targets **Naukri** only.

**Rationale.** (a) Already a Gleaner-scraped source, so job-target ingestion is solved. (b) Naukri's apply flow is heavily profile-based, narrowing Phase 1's field-mapping surface mostly to supplementary screening questions rather than a full contact-info form — a gentler ramp. (c) The dominant channel for the stated Kolkata/remote-India job search, so Phase 1 value lands immediately on the highest-volume channel rather than a low-traffic proof of concept.

**Options Considered.** LinkedIn Easy Apply first was rejected for MVP — most standardized UI, but also the most aggressively monitored for automation, a worse platform to learn the architecture on. Indeed was a reasonable close second, kept as Phase 2's first addition given the existing Indeed MCP connector already in the toolchain for discovery.

**Consequences.** Generic ATS coverage — a meaningful share of Research-Agent-surfaced GenAI/IT-services postings — is deferred to Phase 3; until then, such postings route to `MANUAL_REQUIRED` by design, not by defect.

## 8. Submission Gatekeeper — Modes in Detail

| Mode | Behavior |
|---|---|
| `DRAFT` (default) | Form fully completed and resume attached; browser pauses at the review/submit page for candidate confirmation. Phase 1 implementation: interactive pause (candidate confirms in-session); later phases may queue drafts for asynchronous batch review. |
| `AUTO` | Skips the pause; unlocked only per-platform after trust graduation (Evaluation Plan §5). Free-text (Tier-3) answers *always* route to review even in `AUTO` mode — see Edge Case `EC-PAA-MAP-03`. |
| `SKIP` | Platform or form recognized as unsupported before any field is touched; logged immediately as `SKIPPED`, no attempt made. |

## 9. Session & Credential Management

Platform session cookies/tokens are stored locally, per platform, using Playwright's storage-state mechanism. No credentials are transmitted to Groq or any third party — the LLM tiers only ever receive field labels, candidate-profile values already authorized for that purpose, and job-context text, never authentication material.

## 10. Integration Contracts

| Direction | Component | Contract |
|---|---|---|
| Inbound | (1) The Gleaner | `JobApplicationTarget` (provisional — reconcile against Gleaner's finalized 7-field schema) |
| Inbound | (2) AlignResume | `ResumeArtifact` derived from `TailoringRun` |
| Inbound | (10) Candidate Profile JSON | `CandidateProfile` (provisional shape, §3) |
| Inbound (optional, enriching) | (4) Research Agent | Company brief text, improves Tier-3 draft quality; absence must never block an attempt |
| Outbound | (8) Memory Module | `ApplicationAttemptResult`, one per attempt, always |
| Bidirectional | (6) Conductor Orchestrator | Invokes Component 7 as a LangGraph-compatible node/tool operating on shared state |

## 11. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Reliability | An adapter failure never corrupts or silently drops the attempt record. |
| Auditability | Every attempt reconstructable from its `ApplicationAttemptResult` + screenshot. |
| Cost ceiling | Tier-0/1 resolve the majority of fields at zero marginal LLM cost (see Evaluation Plan §2). |
| Latency | Under 90 seconds from target received to `DRAFT_PENDING_REVIEW`, for a supported platform, by Phase 2. |
| Security | No credential or session material ever leaves the local execution environment. |
| Portability | Containerizable via Docker for eventual Kubernetes Job/Deployment execution under Conductor (Mission Plan §8). |

## 12. Technology Stack Summary

| Layer | Technology |
|---|---|
| Browser automation | Playwright (Python) |
| Data contracts | Pydantic v2 |
| LLM (light) | Groq — LLaMA 3.1 8B |
| LLM (heavy) | Groq — LLaMA 3.3 70B |
| Config | YAML (platform priority, rate limits, mode defaults) |
| Persistence (v1.0) | Local JSON attempt log + screenshot directory |
| Containerization (Phase 5+) | Docker |

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial draft. |
