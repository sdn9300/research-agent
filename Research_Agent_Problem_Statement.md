# Problem Statement: Research Agent [Node 4]

*Specification Document — `speckit.specify` phase*
*System: AI-Native Job Agent Architecture*
*Subsystem ID: [4] — Intelligence Layer*

---

## 1. Problem Context

The AI-Native Job Agent Architecture currently has a structural gap between **discovery** and **application**. Gleaner [3] discovers job postings; AlignResume [1] and Overture Outreach [2] act on a candidate's behalf to apply and reach out. But nothing in the system currently performs the intermediate step a competent human job-seeker performs naturally: *researching the target company before tailoring materials or making contact.*

Without this intermediate layer, AlignResume tailors resumes against a job description alone, and Overture Outreach personalizes cold emails with no company-specific grounding beyond what's scraped into the JD itself. This is a meaningful fidelity gap — resume tailoring and outreach personalization are both materially stronger when grounded in actual company context (recent developments, technical stack signals, stated culture, funding stage), not just the job posting text.

The Research Agent is specified to close this gap: an autonomous subsystem that, given a company name and the existing job-description context, produces a structured, evidence-grounded intelligence brief consumable by every downstream agent in the system.

---

## 2. Why This Problem, and Why Now

Beyond its functional necessity in the broader architecture, this subsystem was deliberately selected as the next build priority for a second, independent reason: it is the single component whose construction *requires* closing four concurrently identified capability gaps — agentic orchestration, retrieval-augmented generation, evaluation harness design, and observability instrumentation — rather than addressing them as isolated, disconnected exercises. Building Research Agent is therefore both a system-completeness requirement and a portfolio gap-closing requirement simultaneously, satisfying the principle (§5, working principles) that effort should not be spent on demonstration projects disconnected from the system already under construction.

---

## 3. Problem Statement (Formal)

> Given a target company name and an associated job description (sourced from Gleaner's output), design and implement an autonomous agent capable of independently planning a research strategy, retrieving information from the public web, grounding all synthesized claims in retrievable source evidence, and producing a structured, schema-conformant intelligence brief — while measurably detecting and rejecting any output claim that cannot be traced to a retrieved source.

The core engineering difficulty is not retrieval or summarization individually — both are well-understood, mechanically simple operations. The difficulty is **composing them under an agentic control structure that exercises judgment about what to search for, when sufficient evidence has been gathered, and whether its own output is trustworthy** — and doing so in a way that is measurably verifiable rather than asserted.

---

## 4. Scope

### In Scope

| Capability | Description |
|---|---|
| Autonomous planning | Agent determines what to search for given company name + JD context, rather than executing a fixed query template |
| Tool-mediated retrieval | Web search and scraping (Firecrawl) exposed as callable tools, invoked conditionally by the agent's planning logic |
| RAG-grounded synthesis | All factual claims in the output must be generated from retrieved, embedded, and indexed source content — not from the model's parametric memory |
| Citation-level traceability | Every claim in the `CompanyBrief` output must resolve to a specific retrieved chunk ID and source URL |
| Self-verification | A dedicated guardrail node rejects or flags ungrounded claims before final output |
| Evaluation harness | A fixed test set with ground-truth facts, scored automatically per run for accuracy, latency, and cost |
| Observability | Per-run logging of prompt version, retrieved chunks, latency, token cost, and eval outcome |

### Out of Scope (Non-Goals)

| Excluded capability | Rationale |
|---|---|
| Multi-company batch research at launch | Single-company correctness must be proven before throughput is addressed |
| Direct integration with AlignResume/Overture Outreach | Deferred to Conductor's orchestration layer; Research Agent exposes a clean output contract, not a direct pipeline |
| Real-time/streaming research updates | A point-in-time brief is sufficient for the resume-tailoring and outreach use cases; continuous monitoring is a distinct, later problem |
| Fine-tuning or training any model | The agent is built entirely on prompting + retrieval + orchestration over existing foundation models, consistent with current skill-acquisition priorities |
| Proprietary/paid data sources | Public web sources only, to keep the system cost-bounded and reproducible without external contracts |

---

## 5. Stakeholders (System Consumers)

| Consumer | Dependency on Research Agent output |
|---|---|
| AlignResume [1] | Consumes `CompanyBrief.tech_signals` and `culture_notes` to ground resume tailoring beyond the raw JD |
| Overture Outreach [2] | Consumes `CompanyBrief.summary` and `recent_news` to personalize cold-email content with verifiable specifics |
| Conductor [6] | Treats Research Agent as a routable unit of work via the `AgentTask` contract; needs reliable success/failure signaling |
| Candidate Profile JSON [10] | Provides the candidate-side context (target industries, role focus) that shapes what the agent prioritizes researching |
| The practitioner (interview readiness) | Must be able to explain every architectural decision below in a live technical interview |

---

## 6. Functional Requirements

| ID | Requirement |
|---|---|
| FR-1 | Given `{company_name, job_description}`, the agent shall produce a `CompanyBrief` object conforming to the schema defined in Phase 0 |
| FR-2 | The agent shall determine, autonomously, which and how many sources to retrieve — bounded by a maximum tool-call budget to prevent runaway cost |
| FR-3 | Every factual claim in `CompanyBrief` shall carry a citation referencing a specific retrieved chunk ID |
| FR-4 | The self-check node shall reject the brief (or strip unsupported claims) if any claim lacks a valid citation |
| FR-5 | The agent shall log, per run: prompt/template version, all retrieved chunk IDs, total latency, total token cost, and final pass/fail eval status (if run in eval mode) |
| FR-6 | The agent shall expose a stable input/output contract independent of internal implementation, so Conductor can invoke it without knowledge of LangGraph internals |

---

## 7. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Correctness over completeness** — an incomplete brief with only verified claims is preferred over a complete brief containing unverifiable ones |
| NFR-2 | **Bounded cost** — a hard ceiling on tool calls and token spend per run, to keep evaluation runs and production use financially predictable |
| NFR-3 | **Latency** — target under ~15 seconds per company for an interactive use case (resume tailoring shouldn't stall on a slow research call) |
| NFR-4 | **Reproducibility** — given the same company and a pinned prompt version, output quality should be consistent across runs, not wildly variable |
| NFR-5 | **Auditability** — every run must be fully reconstructable from logs alone (what was searched, what was retrieved, what was claimed, why it passed/failed self-check) |

---

## 8. Success Criteria

| Criterion | Measurable target |
|---|---|
| Factual accuracy | ≥ 80% of ground-truth facts correctly surfaced across the 15–20 company eval set |
| Citation integrity | 100% of claims in passing outputs resolve to a valid, retrievable chunk ID (zero tolerance — this is the guardrail's entire purpose) |
| Cost predictability | Average cost-per-run documented and stable within a known range across the eval set |
| Regression detection | A deliberately degraded prompt change is caught by the eval gate before merge, in CI |
| Downstream usability | At least one manual integration test where AlignResume or Overture Outreach consumes a real `CompanyBrief` and produces a visibly improved (more specific) output versus the JD-only baseline |

---

## 9. Constraints

- Built using LangGraph for explicit state-machine orchestration — not a linear chain — per the architectural reasoning already established (agentic behavior requires conditional branching, not fixed sequencing)
- Vector store: Chroma for local development velocity; Qdrant remains an option if production-parity becomes a later priority
- LLM backend: Groq (LLaMA 3.3 70B), consistent with the rest of the portfolio's existing infrastructure and cost profile
- No paid search APIs beyond what's already budgeted (Firecrawl, already in use via Gleaner)

---

## 10. Assumptions

- Company names passed in from Gleaner are reasonably well-formed (no fuzzy entity resolution required at this stage)
- Public web sources contain sufficient information for the target company set (early-stage/very small companies may have thin source coverage — flagged as a known limitation, not a silent failure)
- The eval fact-set, once written, will not be modified to make passing easier — its integrity as ground truth is what makes the resulting accuracy number defensible in an interview

---

## 11. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Agent over-searches, inflating cost/latency | Hard tool-call budget per run (NFR-2) |
| Self-check node is too lenient, passing ungrounded claims | Eval set explicitly includes adversarial test cases designed to catch this before trusting the guardrail |
| Thin source coverage for small/obscure companies | Brief explicitly marks low-confidence sections rather than fabricating to fill gaps — consistent with the truthfulness-guardrail philosophy already applied in AlignResume |
| Retrieval drifts from synthesis (chunks retrieved but not actually used in the final claim) | Self-check explicitly cross-references each claim against the retrieved set, not just "were chunks retrieved at all" |

---

## 12. Relationship to Existing Architecture Decision Records

This specification assumes and extends two decisions already made elsewhere in the system: (1) LangGraph over ad-hoc chaining, justified by the need for conditional, judgment-driven control flow rather than fixed sequencing; and (2) citation-grounded guardrails as a recurring design pattern, first established in AlignResume's hallucination guardrail and now generalized from "don't fabricate resume credentials" to "don't fabricate research claims." A formal ADR documenting both decisions in the Research Agent context should be authored during Phase 7 (documentation/packaging).

---

*Document status: Specification — `speckit.specify` phase complete. Next: `speckit.plan` (technical architecture, schemas, ADRs).*
