# Architecture Design Plan: Research Agent [Node 4]

*Technical Design Document — `speckit.plan` phase*
*System: AI-Native Job Agent Architecture*
*Governing Specification: Research_Agent_Problem_Statement.md*
*Governing Mission Plan: Research_Agent_Mission_Plan.md*

---

## 1. Purpose of This Document

This document translates the functional/non-functional requirements established in the Problem Statement into a concrete technical architecture: component boundaries, data schemas, control flow, and the Architecture Decision Records (ADRs) justifying each major choice. Per Spec-Driven Development discipline, no implementation code is written until this plan is finalized.

---

## 2. System Context Diagram

```
                         ┌─────────────────────────┐
                         │   Gleaner [3]            │
                         │   (company_name, JD)     │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │     RESEARCH AGENT [4]                │
                    │                                        │
                    │  ┌──────────┐                          │
                    │  │  plan    │                          │
                    │  └────┬─────┘                          │
                    │       ▼                                │
                    │  ┌──────────────┐    ┌────────────┐    │
                    │  │ search/scrape│───▶│  Tool Layer │    │
                    │  └────┬─────────┘    │ (web search,│    │
                    │       ▼               │  Firecrawl) │    │
                    │  ┌──────────┐         └────────────┘    │
                    │  │ retrieve │◀────┐                     │
                    │  └────┬─────┘     │                     │
                    │       ▼           │   ┌──────────────┐  │
                    │  ┌───────────┐     └───│ Vector Store │  │
                    │  │ synthesize│         │   (Chroma)   │  │
                    │  └────┬──────┘         └──────────────┘  │
                    │       ▼                                  │
                    │  ┌────────────┐                          │
                    │  │ self_check │                          │
                    │  └────┬───────┘                          │
                    │       ▼                                  │
                    └───────┼──────────────────────────────────┘
                             │
                             ▼
                   ┌──────────────────────┐
                   │   CompanyBrief JSON   │
                   └──────┬───────┬────────┘
                          │       │
              ┌───────────┘       └────────────┐
              ▼                                 ▼
     ┌──────────────────┐              ┌──────────────────┐
     │  AlignResume [1]  │              │ Overture Outreach │
     │  (tailoring input)│              │  [2] (personaliz.) │
     └──────────────────┘              └──────────────────┘

     [Observability sidecar: every node emits to SQLite/Langfoge log]
     [Conductor [6]: invokes this entire subsystem via AgentTask contract]
```

---

## 3. Component Breakdown

| Component | Responsibility | Technology |
|---|---|---|
| Planner node | Decides search strategy given company name + JD context | LangGraph node, LLM-driven |
| Tool layer | Executes web search and Firecrawl scrape calls | Python functions wrapped as LangGraph tools |
| Chunking/embedding pipeline | Splits scraped text, generates embeddings, writes to vector store | LangChain text splitters + embedding model |
| Vector store | Persists embedded chunks with source metadata | Chroma (local) |
| Retriever node | Queries vector store for relevant chunks given the current research need | LangGraph node |
| Synthesizer node | Generates `CompanyBrief` fields from retrieved chunks only | LangGraph node, LLM-driven |
| Self-check node | Validates every claim traces to a cited chunk; strips/rejects unsupported claims | LangGraph node, rule-based + LLM-assisted verification |
| Observability sidecar | Logs prompt version, chunk IDs, latency, cost, eval status per run | SQLite or Langfuse |
| Eval runner | Executes the frozen fact-set against the full graph, scores accuracy | Standalone Python script, independent of the agent itself |

---

## 4. Data Schemas

### 4.1 `CompanyBrief` (Output Contract)

```json
{
  "company_name": "string",
  "summary": "string",
  "tech_signals": ["string"],
  "recent_news": [
    {
      "headline": "string",
      "citation_id": "string"
    }
  ],
  "culture_notes": "string",
  "confidence_flags": ["string"],
  "citations": [
    {
      "citation_id": "string",
      "chunk_id": "string",
      "source_url": "string"
    }
  ],
  "run_metadata": {
    "prompt_version": "string",
    "latency_ms": "integer",
    "token_cost_usd": "float",
    "tool_calls_used": "integer"
  }
}
```

### 4.2 `AgentTask` (Conductor Interface Contract)

```json
{
  "task_id": "string (uuid)",
  "agent_name": "research_agent",
  "input_payload": {
    "company_name": "string",
    "job_description": "string"
  },
  "status": "enum [pending, running, success, failed, retrying]",
  "result": "CompanyBrief | null",
  "retry_count": "integer",
  "timestamp": "ISO8601"
}
```

### 4.3 Internal Chunk Record (Vector Store Entry)

```json
{
  "chunk_id": "string",
  "text": "string",
  "embedding": "vector",
  "source_url": "string",
  "scraped_at": "ISO8601",
  "company_name": "string"
}
```

---

## 5. Control Flow (LangGraph State Machine)

| Step | Node | Transition Condition |
|---|---|---|
| 1 | `plan` | Always runs first; outputs a search strategy |
| 2 | `search/scrape` | Runs while plan indicates insufficient sources, bounded by tool-call budget |
| 3 | `retrieve` | Runs after at least one successful scrape |
| 4 | `synthesize` | Runs once retrieval returns a non-empty chunk set |
| 5 | `self_check` | Always runs after synthesis; can loop back to `synthesize` once if claims fail validation, then forces a flagged/partial output rather than looping indefinitely |
| 6 | END | Emits final `CompanyBrief` + logs run metadata |

**Loop termination guarantee:** the `self_check → synthesize` retry path is capped at one retry to prevent infinite loops — this directly satisfies NFR-2 (bounded cost) and is a deliberate, documented constraint rather than an oversight.

---

## 6. Architecture Decision Records

### ADR-001: LangGraph over linear chain orchestration

**Decision:** Use LangGraph's explicit state-machine model rather than a fixed linear chain (e.g., a simple sequential LangChain pipeline).

**Rationale:** The agent's defining requirement (per Problem Statement §3) is that it exercises judgment about what to search for and when evidence is sufficient. A linear chain cannot express conditional branching or bounded retry loops as first-class constructs; LangGraph's graph-based model makes the agentic behavior — not just the LLM call — the architecturally visible unit.

**Trade-off accepted:** Higher initial setup complexity than a simple chain, in exchange for control-flow transparency and testability of individual nodes in isolation.

---

### ADR-002: Citation-grounded guardrail as a generalized pattern

**Decision:** Apply the same anchoring philosophy used in AlignResume's hallucination guardrail (validate LLM output against verified source data, block on violation) to research claims instead of resume credentials.

**Rationale:** This is not a new invention — it is a deliberate generalization of an already-proven design pattern in the existing portfolio, reinforcing architectural consistency across the AI-Native Job Agent system rather than introducing a one-off mechanism.

**Trade-off accepted:** Stricter guardrails reduce output completeness in low-source-coverage cases (small companies); accepted per NFR-1 (correctness over completeness).

---

### ADR-003: Chroma over Qdrant for the vector store

**Decision:** Use Chroma for local development; Qdrant deferred as a future option.

**Rationale:** Development velocity is prioritized over production-parity at this build stage — no current requirement (per Problem Statement §4, Out of Scope) demands the scale or persistence guarantees Qdrant provides. Chroma's lower setup friction matches the 4-week mission timeline.

**Trade-off accepted:** A future migration cost if production-grade hosting is later required; explicitly logged as a reversible decision, not a permanent architectural commitment.

---

### ADR-004: SQLite (or self-hosted Langfuse) over a managed observability SaaS

**Decision:** Log per-run observability data to a self-owned store rather than a third-party managed platform.

**Rationale:** Consistent with cost-bounded, reproducible system design (Problem Statement §4, Out of Scope: no proprietary/paid data dependencies); also keeps full data ownership, which matters for showing raw eval logs in an interview setting without a vendor dependency.

---

## 7. Interface Boundaries (for Conductor Integration)

Research Agent must be invokable by Conductor **without Conductor having any knowledge of LangGraph internals.** The only contract Conductor needs is:

- **Input:** `AgentTask` with `agent_name: "research_agent"`
- **Output:** Updated `AgentTask` with `status` and `result` populated
- **Failure mode:** `status: "failed"` with a human-readable error in place of `result`, never a silent null

This boundary is what allows Conductor's Mission Plan (Phase 4 onward) to treat Research Agent as a black-box routable unit, satisfying the system-level decoupling goal stated in the original Problem Statement (§4, Out of Scope: direct integration deferred to Conductor).

---

## 8. Testing & Validation Strategy

| Test type | Target | Method |
|---|---|---|
| Unit tests | Tool layer functions (search, scrape) | pytest, mocked network calls |
| Integration tests | Full graph run on 3 manually-verified companies | Manual inspection against Gate 3 criteria |
| Adversarial tests | Self-check node | Deliberately inject ungrounded claims, confirm rejection |
| Eval suite | Full 15–20 company fact-set | Automated scoring script, run in CI |
| Regression tests | Prompt/retrieval changes | Eval suite re-run on every PR, gated in CI per DevOps roadmap Phase 5 |

---

## 9. Known Limitations (Documented, Not Hidden)

- Fuzzy company name resolution is not handled — malformed input from Gleaner will degrade research quality without a clear error signal at this stage.
- Thin source coverage for very small/early-stage companies is expected and handled via confidence flags, not fabrication — but this means brief completeness will vary by company size.
- The self-check node's rejection logic is itself LLM-assisted in part, meaning it carries residual risk of being fooled by sufficiently subtle ungrounded claims — mitigated, not eliminated, by adversarial testing.

---

## 10. Relationship to Other Documents

| Document | Relationship |
|---|---|
| Research_Agent_Problem_Statement.md | This plan implements the requirements and constraints defined there |
| Research_Agent_Mission_Plan.md | This plan's components map directly to that document's phase deliverables and Go/No-Go gates |
| Future: Conductor Architecture Design Plan | Will consume the `AgentTask` contract defined here as a given, not redefine it |

---

*Document status: Architecture Design Plan complete. Next: `speckit.tasks` — decompose into granular, testable execution blocks.*
