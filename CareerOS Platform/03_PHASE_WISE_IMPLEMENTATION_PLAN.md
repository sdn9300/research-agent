# CareerOS Platform — Phase-Wise Implementation Plan

## 1. Delivery approach

CareerOS will be delivered as a sequence of small, independently valuable integration increments. No phase may require a destructive migration or make a live external action the default. Each phase ends with a demonstrable acceptance gate and a rollback path.

The work assumes a single-candidate, local-first deployment initially. Estimates are deliberately expressed as phases rather than calendar promises; the practical duration depends on the available engineering capacity and the amount of interface repair discovered during certification.

## 2. Global delivery rules

- Preserve existing component repositories and their test suites.
- Do not add new cross-project `sys.path` manipulation or copied source trees.
- Keep all external actions in `dry_run` until the action-governance phase is accepted.
- Add a contract test before connecting a new producer or consumer.
- Use feature flags for integration backends and keep the legacy path reversible until acceptance criteria are met.
- Update actual component status in documentation; do not carry forward stale “not started” claims after code exists.

## 3. Phase 0 — Baseline certification and integration charter

### Goal

Create a reliable starting point by certifying the actual code, test suites, package boundaries, and duplicate source trees before adding behavior.

### Tasks

1. Create the seven CareerOS ADRs listed in the architecture design.
2. Produce a component manifest with repository location, package entry point, runtime command, test command, current version, owner, and supported interfaces.
3. Identify the canonical implementation when a component has duplicated source directories or documentation copies.
4. Run the existing isolated test suites and record the result, dependencies, skipped tests, and network assumptions.
5. Inventory every current cross-project import, direct database access, hard-coded path, and credential lookup.
6. Classify each integration as one of: implemented and verified, implemented but fragile, specified only, or obsolete.
7. Freeze new direct integrations until they use the contract package or an approved transitional adapter.

### Deliverables

- `COMPONENT_MANIFEST.md`
- `INTEGRATION_COMPATIBILITY_MATRIX.md`
- `CURRENT_STATE_CERTIFICATION.md`
- ADR-CAREEROS-001 through ADR-CAREEROS-007
- an issue backlog sorted by safety, data integrity, and dependency risk

### Acceptance criteria

- Every runtime component has one declared package or service entry point.
- Every current direct cross-project import is documented with a removal phase.
- Existing test status is reproducible from documented commands.
- No user-owned uncommitted work is changed during certification.

### Rollback

Read-only phase; no operational rollback is required.

## 4. Phase 1 — Shared contracts and identity model

### Goal

Create the smallest possible shared `career_os_contracts` package so integrations can exchange validated data without importing each other's internals.

### Tasks

1. Define Pydantic and JSON Schema models for:
   - opportunity observations;
   - application records and lifecycle events;
   - candidate projections;
   - company briefs;
   - recruiter-response signals;
   - artifact references;
   - approval requests and decisions;
   - structured error and retry results.
2. Define the canonical identifiers: `candidate_id`, `opportunity_id`, `application_id`, `thread_id`, `artifact_id`, `approval_id`, `event_id`, and `correlation_id`.
3. Define the event envelope, schema-version policy, event registry, and deprecated-event mapping.
4. Generate contract fixtures for valid, invalid, duplicate, redacted, and legacy payloads.
5. Add consumer-driven compatibility tests for Candidate Profile, Memory Module, Conductor, Research Agent, Chief of Staff, Second Brain, EdgeDash, Overture, and Usher.
6. Publish the package as an editable local dependency during development; pin releases once interfaces stabilize.

### Implementation notes

- Preserve existing component payloads through mapping adapters first. Do not perform a big-bang schema rewrite.
- Use additive schema changes with defaults where possible; breaking changes require a new major version or an explicit migration adapter.
- Treat raw message body, resume text, and browser cookies as restricted artifact data, not ordinary event fields.

### Acceptance criteria

- All core components serialize and validate at least one shared fixture.
- Invalid schemas fail before an event enters the ledger.
- Contract tests prove that old payloads map to the new event model or produce an actionable rejection.
- No runtime integration requires relative imports into another project folder.

### Rollback

Keep adapters behind `CONTRACTS_BACKEND=legacy|career_os_v1` until each connection passes its contract suite.

## 5. Phase 2 — Trusted core spine

### Goal

Make Conductor, Candidate Profile, and Memory Module the dependable control/data spine without changing the external candidate experience.

### Tasks

1. Configure Conductor to use Candidate Profile projection APIs rather than flat resume text or scattered hard-coded data.
2. Complete one-time migration of the active master resume into Candidate Profile, preserving the original artifact and a rollback reference.
3. Use `EventSourcedMemoryStore` as the business-event implementation behind Conductor's storage abstraction.
4. Keep Conductor checkpoint storage separate from the business event ledger.
5. Add entity resolution for normalized opportunity URL, company domain, role title, source, and content hash.
6. Implement deterministic ledger queries for duplicate opportunity, duplicate application, active company cooldown, application history, and stale status.
7. Make every graph node emit structured events and candidate patches only for its owned data section.
8. Add transactional outbox records for all committed lifecycle events.

### Acceptance criteria

- A dry-run graph creates an application trace with one `application_id` from discovery through persistence.
- Duplicate events and retried runs do not create a second application or state transition.
- A rejection event suppresses subsequent eligible outreach according to cooldown policy.
- Replaying the ledger recreates materialized application state.
- Conductor can resume a failed run without using the event ledger as a workflow checkpoint store.

### Rollback

- Retain the legacy Conductor memory backend behind a configuration flag.
- Preserve master-resume source artifacts until migration validation is signed off.
- Do not delete local component stores; mark them read-only during comparison.

## 6. Phase 3 — Unified discovery and evidence preparation

### Goal

Connect opportunity discovery, market intelligence, research, and tailored artifacts to the core spine while retaining human review before action.

### Tasks

1. Normalize Gleaner and EdgeDash output into `OpportunityObserved` events.
2. Establish source precedence and merge logic when several boards expose the same job.
3. Make EdgeDash a market-intelligence and scoring adapter; remove any path where it independently advances an application.
4. Invoke Research Agent through a bounded adapter and persist a cited `CompanyBriefCompleted` event.
5. Invoke AlignResume using `CandidateProfile.to_resume_profile()` and Research context.
6. Enforce skill-provenance validation on every newly introduced resume claim.
7. Create artifact records for raw JD, company brief, tailored resume, gap analysis, and review packet.
8. Add a projection worker that archives redacted artifacts to Second Brain with `application_id`, source artifact IDs, and lifecycle status metadata.
9. Replace synchronous vault writes on critical execution paths with queued, idempotent projection events.

### Acceptance criteria

- The same job observed through two inputs creates one canonical opportunity.
- A Research Agent brief retains citations, confidence flags, and correlation metadata.
- An unsupported candidate skill is blocked or surfaced for explicit candidate correction.
- Second Brain note creation can fail or lag without blocking Conductor's durable application lifecycle.
- A candidate can query Second Brain for an application and see linked evidence after projection catches up.

### Rollback

- Disable EdgeDash and Second Brain adapters independently.
- Continue using Gleaner-only discovery if market intelligence is unavailable.
- Preserve job and resume artifacts locally when vault projection is unavailable; enqueue retryable projection events.

## 7. Phase 4 — Recruiter inbox and interview loop

### Goal

Turn inbound recruiter communication into linked, reviewable application events and scheduling proposals.

### Tasks

1. Define a canonical `InboundEmailReceived` and `ResponseClassified` contract.
2. Build deterministic thread-to-application correlation using Gmail thread IDs, outbound message IDs, recipients, company domains, and candidate-confirmed links.
3. Route uncertain correlations to a review queue; never generate a default application record solely to satisfy a missing link.
4. Use Sentiment Classifier for the canonical 12-class recruiter intent and calibrated urgency signal.
5. Map the classifier result to Chief of Staff priority and candidate-facing recommended actions.
6. Persist recruiter-response, rejection, interview-proposal, and scheduling outcome events to the Memory Module.
7. Use Chief of Staff to draft replies and surface calendar availability, but stage all sends and bookings as central approval requests.
8. Extract only sanitized recruiter skill signals for Future Fit.
9. Establish a shared Gmail channel abstraction only after this contract is stable; credentials remain isolated through a credential provider.

### Acceptance criteria

- A known outbound message receives an inbound reply that resolves to the correct application automatically.
- A hard rejection updates lifecycle state and cooldown exactly once.
- An interview invitation produces a staged action with parsed times, time zone, conflict status, and no automatic booking.
- An ambiguous recruiter email produces a review task rather than contaminating an unrelated application history.
- Future Fit receives no raw email body.

### Rollback

- Continue Chief of Staff's local triage behavior while disabling the CareerOS event adapter.
- Maintain manual application linking when thread correlation confidence is below threshold.

## 8. Phase 5 — Universal approval and governed execution

### Goal

Replace component-local action approval with a central, auditable authorization boundary for email, portal, and calendar actions.

### Tasks

1. Implement `ApprovalRequest` and `ApprovalDecision` storage, audit history, policy versioning, and expiry.
2. Create a single operator review queue capable of showing proposed email, application form summary, resume artifact, research citations, risk flags, and scheduling details.
3. Make Conductor create approval requests rather than directly call Overture, Usher, or calendar functions.
4. Require every executor to validate approval scope, target, payload hash, mode, expiry, and idempotency immediately before live execution.
5. Require a new approval after material changes to email content, recipient, resume artifact, ATS answer, application URL, or calendar time.
6. Keep `dry_run` default; introduce live mode only as a specific user-selected action intent.
7. Add policy checks for rate limits, company cooldowns, duplicate contact, verified company, form risk tier, CAPTCHA, authentication, and attachment availability.
8. Record distinct events for requested, approved, attempted, confirmed, rejected, expired, and failed actions.

### Acceptance criteria

- An executor rejects a missing, expired, mismatched, or already-consumed approval.
- An approved dry-run action cannot become a live action through configuration drift.
- Sending an email twice after a retry does not create two external sends.
- Unknown ATS fields and LLM-generated free-text responses require review before submission.
- Candidate review can edit an action, producing a new action hash and approval.

### Rollback

- Set global execution mode to `dry_run`.
- Disable live executor credentials while retaining drafts and approval history.
- Preserve component-local manual workflows as fallback, without bypassing core audit records.

## 9. Phase 6 — Observability, resilience, and deployment

### Goal

Make the integrated platform operable, diagnosable, and recoverable.

### Tasks

1. Propagate `correlation_id`, `application_id`, `event_id`, and `approval_id` through every adapter call, log entry, and metric.
2. Add structured telemetry for event delivery, queue lag, adapter latency, retries, policy denials, projection failures, model usage, and executor outcomes.
3. Redact PII by default and test telemetry redaction.
4. Add dead-letter handling and operator replay tools for failed projection/notification events.
5. Implement transactional-outbox dispatcher health checks and idempotent consumer tracking.
6. Create a Docker Compose local integration profile with documented secrets injection and backup paths.
7. Prepare a Postgres and durable-broker deployment profile only after local integration has passed acceptance gates.
8. Add backup, restoration, retention, deletion, and credential-rotation runbooks.

### Acceptance criteria

- An operator can trace an application from opportunity observation to final outcome using a correlation ID.
- A simulated consumer failure creates a visible retry/dead-letter record with a safe replay path.
- Restoring the ledger and replaying projections reproduces known application state and vault content.
- Logs and metrics contain no restricted raw artifacts or secrets.

### Rollback

- Run in local-process mode with the existing component stores while preserving exported event records.
- Disable asynchronous consumers individually without losing committed events.

## 10. Phase 7 — End-to-end graduation

### Goal

Demonstrate a complete, safe, reproducible candidate journey and formally graduate the integration from prototype to operating ecosystem.

### Required scenario

```text
Observe job
  → normalize and deduplicate
  → verify cooldown
  → research company
  → tailor resume with provenance check
  → request approval
  → execute approved email or portal dry run
  → receive recruiter response
  → classify and link it
  → stage reply or interview action
  → record outcome
  → project artifacts to Second Brain
  → emit sanitized skill-demand analytics
```

### Graduation criteria

- The scenario passes in a deterministic fixture environment.
- Each participating component's existing tests still pass.
- Failure injection covers at least one failure in every integration boundary.
- Event replay and idempotent retry tests pass.
- Human-approval bypass tests pass for every external action executor.
- Documentation accurately describes implemented capabilities and known limitations.
- The candidate can inspect the review queue, application history, evidence trail, and final outcome without querying multiple unrelated stores.

## 11. Work priority order

If capacity is constrained, prioritize in this order:

1. contracts and canonical ownership;
2. event ledger / Conductor / Candidate Profile spine;
3. approval validation;
4. discovery deduplication and evidence/provenance;
5. inbound recruiter loop;
6. Second Brain and Future Fit projections;
7. deployment refinements.

This order protects correctness and safety before adding automation breadth.
