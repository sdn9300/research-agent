# CareerOS Platform — Evaluation Plan

## 1. Evaluation purpose

CareerOS must be evaluated as an integrated, safety-sensitive system rather than as a collection of individually plausible demos. Evaluation verifies five things:

1. lifecycle facts are correct and replayable;
2. integrations respect ownership and contracts;
3. LLM-assisted outputs are grounded and safely routed;
4. external actions are impossible without valid approval;
5. the system remains useful when components fail.

## 2. Evaluation layers

| Layer | Question | Primary evidence |
|---|---|---|
| Unit | Does one deterministic function satisfy its contract? | component tests |
| Contract | Can two components exchange the same versioned payload? | JSON Schema and consumer-driven tests |
| Integration | Do real adapters update the intended stores once? | fixture-backed integration tests |
| End-to-end | Does a candidate journey work across components? | dry-run scenario tests |
| Safety | Can a forbidden action happen under retries, failures, or configuration drift? | negative tests and audit inspection |
| Operational | Can an operator trace, recover, and replay a run? | fault injection and runbooks |

## 3. Test environments

### 3.1 Deterministic fixture environment

Default CI environment. Uses frozen job listings, company research facts, candidate profile data, email threads, calendar availability, fake portals, and deterministic LLM/classifier outputs. It performs no network calls and no external writes.

### 3.2 Sandboxed integration environment

Uses local databases, filesystem artifact storage, local MCP servers, and mocked Gmail/ATS providers. It validates actual package wiring, database migrations, event delivery, and projection behavior.

### 3.3 Consent-based live smoke environment

Used only after all dry-run gates pass. It uses a test Gmail account, test calendar, test recipient/domain, and explicitly permitted target portal. Live tests never use a real recruiter, employer, or job application unless the candidate separately approves that action outside the test suite.

## 4. Data fixtures

Maintain versioned fixture sets for:

- duplicate job postings from different sources;
- near-duplicate postings with meaningful differences;
- verified and unsupported candidate skills;
- grounded and ungrounded research claims;
- recruiter responses covering every intent class;
- ambiguous or unrelated recruiter emails;
- open, conflicting, canceled, and time-zone-shifted calendar invitations;
- ATS forms with deterministic fields, free-text prompts, CAPTCHA, and unsupported widgets;
- provider timeouts, malformed payloads, duplicate delivery, and process restarts.

Fixtures must use fictional names, redacted artifacts, or consented synthetic data.

## 5. Key quality gates

### Gate 1 — Contract integrity

**Objective:** Every producer and consumer agrees on schemas and identifiers.

**Tests:**

- JSON Schema validation for all events and commands.
- Backward-compatible payload fixtures for supported legacy adapters.
- Rejection of unknown required fields, invalid timestamps, missing IDs, and invalid PII classifications.
- Consumer-driven tests for all cross-component mappings.

**Pass criteria:** 100% of registered contracts validate or fail with an explicit structured error; no component relies on an undocumented path import.

### Gate 2 — Lifecycle and replay integrity

**Objective:** Memory Module reproduces the current application lifecycle from immutable events.

**Tests:**

- `JOB_DISCOVERED → RESUME_TAILORED → OUTREACH_SENT → RESPONSE_CLASSIFIED` transition sequence.
- rejected, offered, withdrawn, ghosted, and manually overridden states.
- idempotent duplicate event delivery.
- out-of-order but causally valid delivery where supported.
- full rebuild of materialized tables from event history.

**Pass criteria:** Rebuild equivalence is exact for lifecycle state and event count; duplicate retries do not introduce duplicate transitions.

### Gate 3 — Candidate truthfulness and research grounding

**Objective:** No generated content implies unsupported candidate experience or ungrounded company facts.

**Tests:**

- skill provenance check for every new tailored-resume skill claim;
- citation presence and source validity for Research Agent `CompanyBrief` claims;
- RAG retrieval tests with stale, irrelevant, and conflicting notes;
- artifact metadata tests for prompt/model/version/source references.

**Pass criteria:** Unsupported claims are blocked or flagged for review; every company-brief claim is cited or removed; a RAG timeout never manufactures context.

### Gate 4 — Opportunity quality and deduplication

**Objective:** Discovery sources do not create duplicate outreach or applications.

**Tests:**

- same URL from multiple collectors;
- tracking-parameter variants of the same URL;
- same company/title but different locations or requisition IDs;
- reposted roles after an expiry period;
- identical job description on company and job-board URLs.

**Pass criteria:** Same opportunity resolves to one canonical identity; genuinely distinct roles remain distinct; resolution decisions are explainable in logs.

### Gate 5 — Inbound recruiter loop

**Objective:** Recruiter replies reliably update the correct application and stage, rather than execute, actions.

**Tests:**

- twelve-class classifier fixture set with expected urgency and recommendation;
- known Gmail thread correlated to an application;
- uncertain correlation routed to review;
- rejection triggers one cooldown;
- interview invitation produces a time-zone-aware proposed event;
- calendar conflict produces a reviewable alternative rather than booking.

**Pass criteria:** All known-thread fixtures link correctly; all ambiguous fixtures avoid automatic mutation; no calendar event is created before approval.

### Gate 6 — Action authorization

**Objective:** Live external actions cannot bypass approval.

**Tests:**

- missing, expired, consumed, mismatched, and modified approval payloads;
- dry-run approval presented to live-mode executor;
- duplicate executor invocation after network timeout;
- changed resume attachment or recipient after approval;
- direct executor invocation without Conductor.

**Pass criteria:** Every invalid request is rejected before external side effect; approved retries are idempotent; audit history states exactly why a request was denied.

### Gate 7 — Resilience and recovery

**Objective:** The platform fails visibly and recoverably.

**Tests:**

- event dispatcher crash between commit and publish;
- consumer crash after processing but before acknowledgement;
- MCP query timeout;
- Research, LLM, Gmail, calendar, ATS, and storage failure;
- malformed third-party response;
- restart during Conductor graph execution;
- Second Brain projection failure.

**Pass criteria:** Committed lifecycle events are not lost; retries are bounded and observable; a fallback draft/manual packet is produced when action automation fails.

## 6. Metrics

| Metric | Definition | Initial target |
|---|---|---|
| Contract pass rate | valid producer/consumer fixtures ÷ total fixtures | 100% for supported versions |
| Ledger rebuild equivalence | matching rebuilt application records ÷ expected records | 100% |
| Duplicate suppression precision | correctly suppressed duplicates ÷ all suppression decisions | ≥ 99% on frozen fixtures |
| False suppression rate | unique roles wrongly blocked ÷ unique-role fixtures | 0% on critical fixtures |
| Provenance block rate | unsupported claims blocked or flagged ÷ injected unsupported claims | 100% |
| Approval bypass rate | unauthorized external actions ÷ attempted unauthorized actions | 0% |
| Action idempotency | duplicate external effects ÷ duplicate invocation tests | 0% |
| Inbound-link precision | correct automatic thread links ÷ automatic links | ≥ 99% on known fixtures |
| Recovery success | recoverable failure scenarios restored ÷ attempted scenarios | 100% |
| Trace completeness | completed runs with correlation IDs across boundaries ÷ completed runs | 100% |
| PII leakage | restricted values found in sanitized logs / telemetry | 0 |

Thresholds should be tightened only after the fixture set becomes representative. A high metric on a tiny, non-adversarial fixture set is not graduation evidence.

## 7. Evaluation scenarios

### Scenario A — Successful cold outreach path

1. Gleaner and EdgeDash observe the same job.
2. Entity resolution creates one opportunity.
3. Conductor checks cooldown and starts research.
4. Research produces a cited brief.
5. AlignResume creates a tailored resume; an unsupported skill injection is blocked.
6. Candidate approves a reviewed outreach draft.
7. Overture performs a dry-run send and records one outcome.
8. Second Brain receives a redacted evidence projection.

### Scenario B — Portal application with free-text risk

1. A qualified company career-page opportunity reaches Usher.
2. Deterministic fields resolve successfully.
3. An open-ended question requires LLM text.
4. Usher marks the action as manual-review-required.
5. No live submission is made without an edited/reapproved payload.

### Scenario C — Rejection and cooldown loop

1. An inbound rejection is correlated to a past application.
2. Sentiment Classifier emits the rejection signal.
3. Memory Module records one rejection and cooldown.
4. A new job from the same company is observed.
5. Conductor suppresses outreach and records a clear reason.

### Scenario D — Dependency failure

1. Second Brain query fails during draft preparation.
2. Conductor continues using candidate profile and local approved context.
3. The resulting draft is clearly marked as missing optional knowledge context.
4. The vault projection retries later without duplicating artifacts.

## 8. Reporting and release evidence

Every phase release must publish:

- test run summary with environment and commit/version metadata;
- contract compatibility report;
- end-to-end trace artifact for the release scenario;
- negative-test report for approval bypass and PII redaction;
- known limitations and deferred risks;
- migration and rollback verification notes.

## 9. Graduation decision

CareerOS graduates from integration prototype to dependable operating ecosystem only when all seven gates pass in the sandboxed environment, the dry-run end-to-end scenario is stable, and a scoped live smoke test succeeds without a policy violation, duplicate side effect, or unexplained state divergence.
