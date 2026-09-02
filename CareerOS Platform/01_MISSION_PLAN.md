# CareerOS Platform — Mission Plan

## 1. Mission

Build a unified, trustworthy job-search operating system that helps a candidate discover, evaluate, pursue, and learn from opportunities while keeping the candidate in control of every consequential external action.

CareerOS will automate collection, analysis, evidence retrieval, drafting, tracking, and preparation. It will not automate judgement away. The candidate remains the final authority for outreach, applications, calendar commitments, and material profile changes.

## 2. Product principles

### 2.1 One owner per fact

Every domain fact has one authoritative owner. Other systems consume an event or read projection; they do not silently maintain competing truth.

### 2.2 Human approval is a security boundary

An approval is not a UI preference. It is a durable decision bound to an action, artifact hash, recipient or target, expiry, and policy version. Executors must validate it immediately before a live action.

### 2.3 Evidence before eloquence

Generated text is useful only when grounded. Candidate claims require verified candidate evidence; company claims require sources; personalized replies should cite known thread, job, or research context.

### 2.4 Event history is durable; views are replaceable

The event ledger records immutable business facts. Dashboards, vault notes, application summaries, and analytics datasets are materialized projections that can be rebuilt.

### 2.5 Graceful degradation beats false automation

When a provider, scraper, model, browser, or adapter fails, the system produces an explicit fallback: a draft, a review packet, an alert, or a retryable event. It never invents success or silently drops work.

### 2.6 Local-first and privacy-aware

Store the minimum necessary data; keep credentials isolated; redact sensitive data from telemetry; and prefer local retrieval and deterministic processing where practical.

### 2.7 Independent components, integrated experience

Each existing project remains independently runnable and portfolio-ready. CareerOS supplies the contracts and operating model that allow them to produce one coherent candidate experience.

## 3. Objectives

### Objective A — Establish a canonical control plane

Conductor becomes the only component permitted to advance an application lifecycle. It invokes specialized agents through adapters and records every outcome to the Memory Module.

### Objective B — Establish reliable data contracts

Create a versioned contract package shared by producers and consumers. It defines identifiers, events, command/result envelopes, projections, approval decisions, validation errors, and PII handling labels.

### Objective C — Unify discovery without duplicate action

Gleaner and EdgeDash feed a normalized opportunity intake. A single entity-resolution/deduplication process decides whether an opportunity becomes an application candidate.

### Objective D — Create an evidence and context fabric

Second Brain receives durable, redacted application artifacts and produces searchable context. It enriches drafting and preparation but never drives safety-critical state transitions by itself.

### Objective E — Close the inbound recruiter loop

Chief of Staff and Sentiment Classifier convert inbound recruiter messages into linked application events, proposed actions, and interview scheduling requests. Ambiguity is routed to candidate review.

### Objective F — Centralize action governance

One approval service governs Overture, Usher, and calendar actions. Dry run is the default. Live mode is explicit, time-limited, scoped, and auditable.

### Objective G — Make the ecosystem observable and recoverable

An operator can trace an application across components, replay its lifecycle from events, explain why it was skipped, and distinguish an action that was planned, approved, attempted, and confirmed.

## 4. Non-goals

- Making a job application or outbound email without affirmative approval.
- Consolidating every repository into a single codebase.
- Letting a vector-search answer override a deterministic cooldown or provenance check.
- Storing raw credentials, tokens, or full email bodies in broad analytics datasets.
- Requiring cloud infrastructure before local end-to-end reliability is proven.

## 5. Success measures

| Area | Target outcome |
|---|---|
| Lifecycle integrity | 100% of application transitions arise from valid, idempotent events. |
| Action safety | 0 live sends, submissions, or bookings without a valid unexpired approval. |
| Deduplication | Duplicate opportunities converge to one canonical opportunity/application identity. |
| Truthfulness | Unsupported candidate skills are blocked or explicitly flagged before resume export. |
| Recoverability | Replaying the event ledger reproduces application materialized state exactly. |
| Observability | A correlation ID traces each run across Conductor, adapters, actions, and projections. |
| Resilience | Dependency failure results in a visible fallback or retry state, never a silent loss. |
| Candidate value | A candidate can see the next required decision, related evidence, and full history in one place. |

## 6. Operating model

### 6.1 Lifecycle stages

1. **Observe** — Gleaner or EdgeDash finds a potential opportunity.
2. **Qualify** — Normalize, score, deduplicate, and check cooldown/policy.
3. **Investigate** — Research Agent produces a cited company brief.
4. **Prepare** — AlignResume creates an evidence-checked tailored artifact and draft strategy.
5. **Decide** — Candidate reviews the opportunity and approves, edits, rejects, or defers the proposed action.
6. **Execute** — Overture, Usher, or calendar adapter performs the authorized action in dry-run or live mode.
7. **Respond** — Chief of Staff and Sentiment Classifier process inbound communication.
8. **Learn** — Memory Module, Second Brain, and Future Fit produce history, knowledge, and trend signals.

### 6.2 Human decision points

The platform must ask for a decision when any of the following applies:

- an email will be sent;
- a calendar event will be created or accepted;
- a portal form will be submitted;
- a free-text ATS answer was generated rather than deterministically resolved;
- the candidate profile will be materially changed;
- an inbound thread cannot be confidently correlated with an application;
- a source, skill, or claim fails a grounding check;
- an action violates a cooldown, rate limit, or policy and the candidate elects to consider an override.

### 6.3 Automation tiers

| Tier | Permitted behavior | Example |
|---|---|---|
| 0 — Observe | Read, parse, normalize, and score without external side effects. | Fetch job board results. |
| 1 — Prepare | Create drafts and artifacts, but do not transmit or submit. | Tailor a resume or draft a reply. |
| 2 — Stage | Create an approval request with explicit action payload. | Queue a recruiter reply. |
| 3 — Execute | Perform one approved external action and record the result. | Send one reviewed email. |
| 4 — Learn | Create internal summaries and projections from events. | Add a redacted application note to Second Brain. |

## 7. Strategic delivery sequence

The mission will be delivered in four releases:

1. **Foundation release** — contracts, ownership, packaging, and test baseline.
2. **Core lifecycle release** — Conductor, Candidate Profile, and Memory Module operate as the trusted spine.
3. **Connected intelligence release** — discovery, research, vault context, recruiter response, and scheduling are linked through the spine.
4. **Governed action release** — one approval queue governs email, portal, and calendar execution, followed by observability and reliability hardening.

The detailed tasks and acceptance gates are defined in `03_PHASE_WISE_IMPLEMENTATION_PLAN.md`.

## 8. Governance commitments

- No credentials are copied between repositories.
- No raw email or resume content enters telemetry by default.
- No new cross-project direct path imports are added.
- Every schema change has a version, migration path, and compatibility test.
- Every action executor honors `dry_run`, policy evaluation, idempotency, and approval validation.
- Every component exposes its actual capability level; prototype behavior is not presented as a completed production integration.
