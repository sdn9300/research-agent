# CareerOS Platform — Problem Statement

## 1. Executive summary

The current job-search portfolio contains most of the capabilities required for an excellent AI-native career agent: job discovery, market analysis, company research, resume tailoring, cold outreach, portal applications, recruiter-response classification, scheduling, candidate data management, event history, and a personal knowledge vault. The problem is that these capabilities are distributed across independently evolving projects with overlapping control loops, storage models, approval flows, and cross-folder imports.

CareerOS Platform is the integration layer that turns these projects into one dependable job-search ecosystem. It does not seek to merge all code into a monolith. Instead, it establishes clear data ownership, one lifecycle coordinator, durable event contracts, a universal approval mechanism, and a safe way for specialized components to collaborate.

The intended outcome is a single candidate experience:

> A qualified opportunity is discovered, deduplicated, researched, tailored using verified candidate evidence, reviewed by the candidate, actioned through the appropriate channel, tracked through recruiter response and interview scheduling, and retained as a searchable evidence trail without duplicated outreach, unsupported claims, or unapproved external actions.

## 2. Current ecosystem

### 2.1 AI Native Job Agent components

The AI Native Job Agent project already provides the execution-oriented capabilities:

| Component | Current responsibility in CareerOS |
|---|---|
| Candidate Profile | Canonical candidate identity, verified skills, experience evidence, preferences, and deterministic projections for downstream agents. |
| Conductor | LangGraph-based lifecycle coordinator with discovery, research, tailoring, approval, channel routing, and persistence nodes. |
| Memory Module | Append-only application event ledger, materialized lifecycle state, idempotency, cooldowns, and replay. |
| Gleaner / Job Scraping | Board-specific collection, normalization, filtering, and job discovery. |
| Research Agent | Citation-grounded company intelligence and claim verification. |
| AlignResume | Job-description-aware resume tailoring and user-facing resume review/export. |
| Overture Outreach | Drafting, previewing, and dispatching cold outreach through Gmail. |
| Usher / PDF Auto-Apply | Policy-gated, multi-ATS form preparation and submission. |
| Sentiment Classifier | Recruiter-response intent, urgency, recommendation, and feedback signals. |
| Future Fit | Skill-demand trends, associations, and forecast views. |

### 2.2 Masai Live Docs components

Masai Live Docs supplies the context and interaction systems that complete the candidate journey:

| Component | Current responsibility in CareerOS |
|---|---|
| Second Brain / Synapse-AI | Immutable capture, PARA-organized case notes, local embeddings, Graph-RAG, Obsidian vault, artifact retrieval, and vault health checks. |
| MCP Chief of Staff | Gmail-thread intake, priority triage, contextual drafting, human review, calendar interpretation, and operational audit reports. |
| EdgeDash Loop Engineering | Multi-source market discovery, listing storage, fit scoring, skills-gap analysis, verification, and MCP query tools. |

## 3. Core problem

The ecosystem has functional components but no fully governed platform boundary. Without an integration architecture, the same candidate or application fact can be created in multiple places, decisions can be made by multiple loops, and a local shortcut can accidentally become a production dependency.

The six dimensions of the problem are below.

### 3.1 Fragmented lifecycle ownership

Conductor, EdgeDash, Chief of Staff, and Second Brain each contain workflow or state-management behavior. If they all manage an application independently, the ecosystem can produce contradictory states such as:

- An application marked rejected in a vault note but eligible for outreach in a separate database.
- A recruiter interview invitation recognized in Chief of Staff but not reflected in Conductor's application lifecycle.
- A new job found by EdgeDash and Gleaner being processed twice because the two discovery loops use different identities.
- A human approving a reply in one interface while another executor cannot reliably verify that approval.

CareerOS must have exactly one owner for each class of truth.

### 3.2 Duplicate and informal integration paths

Some existing integrations use direct Python imports across sibling project folders or depend on a local path layout. This is useful during exploration but fragile as a production boundary because:

- package resolution varies by working directory and deployment environment;
- component versions cannot be stated or validated explicitly;
- retries can write to an unintended local database;
- a module can appear connected while silently falling back to an isolated local implementation;
- security and credential boundaries are blurred.

The platform needs versioned contracts and declared dependencies rather than implicit path coupling.

### 3.3 Competing data stores and projections

Candidate Profile, the Memory Module, Conductor checkpointing, Second Brain notes, EdgeDash SQLite storage, and component-local logs each store relevant facts. These stores serve different purposes, but their roles must be separated:

- Candidate Profile is candidate truth.
- Memory Module is application-lifecycle truth.
- Conductor checkpoints are recoverable workflow execution state.
- Second Brain is immutable evidence, knowledge, and human-readable context.
- EdgeDash is market/discovery intelligence.
- Component logs are observability evidence.

No system should infer that because it stores a useful copy, it has authority to change the source record.

### 3.4 Safety risk from external actions

Email sends, calendar bookings, portal submissions, and profile updates can have real-world consequences. The ecosystem already includes approval discipline, dry-run modes, and policy gates, but these controls are currently implemented in more than one component. A local UI check is insufficient if an executor can be called through another route.

CareerOS requires one explicit, auditable approval decision that each action executor verifies immediately before it sends, books, or submits. The default operating mode must remain dry run.

### 3.5 Trust, provenance, and grounding risk

The system uses LLMs for research, classification, drafting, resume tailoring, and summarization. This creates several related risks:

- a tailored resume may claim an unsupported skill;
- a research brief may introduce an ungrounded company claim;
- a RAG result may be stale or weakly relevant;
- a generated free-text ATS answer may be unsafe to auto-submit;
- a recruiter response may be misclassified.

Candidate Profile evidence, Research Agent citations, and Second Brain sources should enrich human review, not bypass it. Deterministic guardrails must make unsupported output visible and non-actionable.

### 3.6 Operational immaturity at ecosystem scale

Most components are local-first and individually testable. A unified system additionally needs correlation IDs, event replay, schema compatibility checks, failure injection, data-retention rules, secrets isolation, and an end-to-end recovery story. Adding infrastructure prematurely would create unnecessary work; failing to add these foundations before live automation would create unacceptable risk.

## 4. Stakeholders

| Stakeholder | Need | CareerOS response |
|---|---|---|
| Candidate | Relevant opportunities, control, honesty, and a clear next action. | One review queue, evidence-backed drafts, explicit approvals, and a complete history. |
| Recruiter / hiring company | Professional, non-spammy interaction and accurate information. | Cooldowns, deduplication, rate limits, provenance checks, and human review. |
| Component developer | Stable contracts and freedom to evolve one component without breaking all others. | Contract package, adapter boundaries, versioning, and integration tests. |
| Operator / maintainer | Diagnosable failures and recoverable state. | Event ledger, transactional outbox, correlation IDs, metrics, and replay. |
| Portfolio reviewer | Clear system boundaries and demonstrable engineering judgement. | Independently demoable components with a visible integration control plane. |

## 5. Desired state

CareerOS will be successful when it provides a reliable, human-supervised application lifecycle with the following properties:

1. Every candidate action has a unique candidate, opportunity, application, artifact, and correlation identity.
2. Every lifecycle transition is represented by an idempotent, append-only business event.
3. Conductor is the only component that decides which lifecycle step runs next.
4. Candidate Profile owns candidate facts; Memory Module owns application state; Second Brain owns evidence and retrieval projections.
5. EdgeDash and Gleaner produce normalized opportunities rather than separately initiating applications.
6. Chief of Staff turns inbound communication into structured signals and staged actions without owning lifecycle truth.
7. Overture, Usher, and calendar execution cannot perform a live external action without a valid approval decision.
8. Every LLM-derived output records its sources, confidence, model/prompt version, and applicable guardrail result.
9. The ecosystem degrades to reviewable drafts and manual packets when dependencies fail.
10. Existing projects retain their independent repositories, demos, and portfolio value.

## 6. Scope

### In scope

- A shared contract model, event taxonomy, and adapter boundary.
- Integration of discovery, application lifecycle, context, inbound response, approval, action execution, and learning signals.
- A local-first deployment path and a clear path to a durable deployed platform.
- Standardized governance, observability, evaluation, and edge-case handling.
- Documentation and test requirements for all cross-component behavior.

### Out of scope

- Rebuilding every component from scratch.
- Fully autonomous, unreviewed outreach, calendar booking, or application submission.
- Sharing Gmail OAuth tokens, API keys, or `.env` files across projects.
- Replacing the Obsidian vault with a database-only user interface.
- Introducing Kubernetes, a large message broker cluster, or multi-tenant SaaS behavior before actual scale requires it.
- Treating an LLM's confidence as proof of candidate eligibility or company facts.

## 7. Constraints and assumptions

- The first user is a single candidate running primarily local workflows on Windows.
- Existing projects remain separately testable and independently presentable.
- The system handles sensitive candidate, employer, email, and resume data.
- External sites and APIs are unreliable, rate-limited, and may require manual interaction.
- At-least-once delivery is acceptable only when event consumers and executors are idempotent.
- The platform must continue to be useful when live LLMs or network services are unavailable.

## 8. Problem statement

> Design and incrementally implement a local-first, event-driven CareerOS integration layer that combines the existing job-search, market-intelligence, inbox, and knowledge projects into one trustworthy candidate workflow. The platform must preserve independent component boundaries while enforcing canonical ownership, durable lifecycle history, evidence-based generation, and explicit human approval for every external action.
