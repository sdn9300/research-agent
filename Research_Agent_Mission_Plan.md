# Mission Plan: Research Agent [Node 4]

*Operational Planning Document*
*System: AI-Native Job Agent Architecture*
*Mission Class: Intelligence Layer — Single Specialist Agent Build*
*Status: PRE-EXECUTION*

---

## 1. Mission Statement

> Deploy an autonomous Research Agent capable of producing citation-grounded company intelligence briefs, closing the agentic-orchestration, RAG, eval, and observability capability gaps in a single coordinated build, within an 4-week execution window.

This mission is the first of two coordinated builds (Research Agent, then Conductor) that together complete the Intelligence and Coordination layers of the AI-Native Job Agent Architecture.

---

## 2. Mission Objectives

| ID | Objective | Definition of Done |
|---|---|---|
| MO-1 | Establish schema and constitution layer | All four Phase-0 schemas committed to `/specs`, zero code written |
| MO-2 | Achieve functioning RAG retrieval core | Given a company name, system retrieves and embeds relevant source chunks with metadata intact |
| MO-3 | Achieve functioning agentic graph | LangGraph state machine produces a citation-grounded `CompanyBrief` end-to-end |
| MO-4 | Achieve measurable evaluation capability | Documented accuracy/latency/cost score across a 15–20 company test set |
| MO-5 | Achieve interview-defensible documentation | ADRs, README, and architecture diagram complete; practitioner can explain every decision unaided |

---

## 3. Phased Execution Timeline

| Phase | Mission Objective(s) Served | Duration | Go/No-Go Gate |
|---|---|---|---|
| Phase 0 — Constitution & Specification | MO-1 | Week 1 | Gate 1 |
| Phase 1 — RAG Retrieval Core | MO-2 | Week 2 | Gate 2 |
| Phase 2 — Agentic Graph Construction | MO-3 | Week 3 | Gate 3 |
| Phase 3 — Eval & Observability | MO-4 | Week 4 | Gate 4 (Mission Success Gate) |
| Phase 4 — Documentation & Packaging | MO-5 | Week 4 (overlap) | Gate 5 (Mission Closeout) |

---

## 4. Go/No-Go Execution Gates

### Gate 1 — End of Phase 0
**Criteria to proceed:**
- [ ] `CompanyBrief` schema finalized and committed
- [ ] `AgentTask` schema finalized and committed
- [ ] Eval fact-set (15–20 companies, 3–5 facts each) written and frozen — no further edits permitted post-freeze
- [ ] Candidate Profile JSON schema confirmed compatible with Research Agent's read requirements

**No-Go condition:** If the eval fact-set is not frozen before Phase 1 begins, mission is paused — building against a moving target invalidates the eventual accuracy metric.

---

### Gate 2 — End of Phase 1
**Criteria to proceed:**
- [ ] Web search tool function operational and independently testable
- [ ] Firecrawl scrape tool function operational and independently testable
- [ ] Chunking + embedding pipeline writes to Chroma successfully
- [ ] Retrieval returns top-k chunks with source URL + chunk ID metadata intact

**No-Go condition:** If retrieved chunks lose source metadata, halt — this metadata is load-bearing for the citation guardrail in Phase 2 and cannot be retrofitted cheaply.

---

### Gate 3 — End of Phase 2
**Criteria to proceed:**
- [ ] All five graph nodes (`plan`, `search/scrape`, `retrieve`, `synthesize`, `self_check`) operational
- [ ] End-to-end run on at least 3 manually-verified companies produces correctly cited output
- [ ] Self-check node demonstrably rejects at least one deliberately-injected ungrounded claim (adversarial test)

**No-Go condition:** If the self-check node passes an adversarial ungrounded claim during testing, do not proceed to Phase 3 — the guardrail is the mission's defining engineering claim and must be proven, not assumed.

---

### Gate 4 — End of Phase 3 (MISSION SUCCESS GATE)
**Criteria to declare mission success:**
- [ ] Eval run completed across full frozen fact-set
- [ ] Factual accuracy ≥ 80% achieved (per Success Criteria in Problem Statement §8)
- [ ] 100% citation integrity on all passing outputs (zero tolerance, non-negotiable)
- [ ] Per-run logging (prompt version, chunks, latency, cost) operational and queryable
- [ ] At least one CI run demonstrates the eval gate catching a deliberately degraded prompt change

**No-Go condition:** If factual accuracy falls below 80%, mission proceeds to a **Remediation Sub-Phase** (see §7) rather than declaring success — do not lower the success bar to match the result.

---

### Gate 5 — Mission Closeout
**Criteria to close mission:**
- [ ] ADR authored covering LangGraph-over-chain decision and citation-guardrail-generalization decision
- [ ] README complete with architecture diagram, eval score, cost/latency figures, local run instructions
- [ ] Practitioner has verbally walked through the full architecture unaided (self-administered interview-readiness check)
- [ ] At least one manual integration test with AlignResume or Overture Outreach consuming a real `CompanyBrief`

---

## 5. Risk Register

| Risk ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-1 | Agent over-searches, inflating cost/latency beyond NFR-2/NFR-3 targets | Medium | Medium | Hard tool-call budget enforced per run | Practitioner |
| R-2 | Self-check node too lenient, passes ungrounded claims | Medium | High | Adversarial test cases built into eval set before trusting the guardrail | Practitioner |
| R-3 | Thin source coverage for small/obscure companies | High | Low | Brief explicitly marks low-confidence sections rather than fabricating | Practitioner |
| R-4 | Eval fact-set unintentionally tuned to be "passable" rather than rigorous | Low | High | Freeze fact-set at Gate 1, before any agent code exists | Practitioner |
| R-5 | Scope creep — attempting multi-company batch or live integration before single-agent correctness proven | Medium | Medium | Out-of-scope items explicitly fenced in Problem Statement §4; enforced at each Go/No-Go gate | Practitioner |
| R-6 | Time slippage due to IIT Roorkee coursework competing for available hours | Medium | Medium | 4-week timeline includes implicit slack; phases are sequential but not hour-locked | Practitioner |
| R-7 | Vector store choice (Chroma) creates migration cost if production-parity later needed | Low | Low | Documented as a deliberate, reversible trade-off in the ADR, not a permanent commitment | Practitioner |

---

## 6. Resource Allocation

| Resource | Allocation |
|---|---|
| Primary compute | Local development machine + free-tier cloud VM (per existing Linux/DevOps roadmap) |
| LLM backend | Groq API (LLaMA 3.3 70B) — existing account, no new cost commitment |
| Search/scrape | Firecrawl API — existing account, reused from Gleaner |
| Vector store | Chroma (local, zero marginal cost) |
| Logging/observability | SQLite (zero cost) or Langfuse self-hosted via Docker (per DevOps roadmap Phase 5) |
| Time budget | ~4 weeks part-time, run in parallel with ongoing coursework |

---

## 7. Remediation Sub-Phase (Contingency Plan)

Triggered only if Gate 4 fails (accuracy < 80%).

| Step | Action |
|---|---|
| 1 | Diagnose failure mode: is it a retrieval problem (wrong/insufficient sources) or a synthesis problem (sources retrieved but misread)? |
| 2 | If retrieval: expand source diversity per company (increase tool-call budget temporarily for diagnosis only, not production) |
| 3 | If synthesis: revise the `synthesize` node prompt, re-run eval, compare against previous version's logged results |
| 4 | Re-run full eval set; do not declare success until 80% threshold met on an unmodified fact-set |
| 5 | Document the failure and fix as a dedicated ADR entry — root-cause-first, no silent patching, per standing engineering principle |

---

## 8. Mission Dependencies

| Dependency | Status | Blocking? |
|---|---|---|
| Candidate Profile JSON schema [10] | Assumed stable per existing architecture spec | No — can proceed with current schema |
| Gleaner output format [3] | Assumed stable, provides company name + JD | No — interface already informally established |
| Conductor [6] | Not yet built | No — Research Agent is designed to be Conductor-independent; integration deferred |
| AlignResume / Overture Outreach consumption | Required only for Gate 5 closeout, not earlier gates | No — manual integration test is the only hard requirement |

---

## 9. Post-Mission Transition

Upon successful Gate 5 closeout, this mission's outputs become inputs to the next mission: **Conductor — Orchestration Skeleton**, which will treat Research Agent as its first routable unit of work via the `AgentTask` contract established in Phase 0. No new mission plan is required to begin Conductor's Phase 0 — schemas already exist; Conductor's Mission Plan should be authored as a follow-on document at that time.

---

## 10. Mission Command Summary

| Parameter | Value |
|---|---|
| Mission name | Research Agent Build |
| Mission window | 4 weeks |
| Success threshold | ≥80% eval accuracy, 100% citation integrity |
| Failure response | Remediation Sub-Phase, not threshold reduction |
| Next mission | Conductor — Orchestration Skeleton |
| Governing specification | `Research_Agent_Problem_Statement.md` |

---

*Document status: Mission Plan complete. Execution begins at Phase 0 / Gate 1.*
