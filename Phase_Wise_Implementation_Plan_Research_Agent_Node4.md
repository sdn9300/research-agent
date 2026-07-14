# Phase-Wise Implementation Plan: Research Agent [Node 4]

*Execution Document — `speckit.tasks` + `speckit.implement` phase*
*System: AI-Native Job Agent Architecture*
*Governing documents: Research_Agent_Problem_Statement.md, Research_Agent_Mission_Plan.md, Research_Agent_Architecture_Design_Plan.md*

---

## 1. Purpose of This Document

This decomposes the Architecture Design Plan into granular, sequential, testable execution blocks. Each task below has an explicit input, output, and verification step — no task is considered complete until its verification step passes. This is the document actually followed day-to-day during the build; the Mission Plan governs *when* phases happen, this governs *what exactly gets typed*.

---

## Phase 0 — Constitution & Specification (Week 1)

| Task ID | Task | Input | Output | Verification |
|---|---|---|---|---|
| T0.1 | Write `CompanyBrief` JSON schema | Architecture Design Plan §4.1 | `schemas/company_brief.py` (Pydantic model) | Schema validates a hand-written sample brief without error |
| T0.2 | Write `AgentTask` JSON schema | Architecture Design Plan §4.2 | `schemas/agent_task.py` (Pydantic model) | Schema validates a hand-written sample task without error |
| T0.3 | Write internal chunk record schema | Architecture Design Plan §4.3 | `schemas/chunk.py` (Pydantic model) | Schema validates a hand-written sample chunk |
| T0.4 | Draft and freeze eval fact-set | Problem Statement §8, §10 | `eval/fact_set.json` — 15–20 companies, 3–5 facts each | Manually cross-check every fact against an independent source before freezing; commit with a `FROZEN` tag/commit message |
| T0.5 | Confirm Candidate Profile JSON compatibility | Existing [10] schema | Written confirmation note in `/specs/notes/` | Research Agent's planned read fields exist in the current Candidate Profile JSON schema |

**Phase 0 Exit Check:** All five tasks closed, all schemas committed, fact-set frozen → **Gate 1 (Mission Plan)**.

---

## Phase 1 — RAG Retrieval Core (Week 2)

| Task ID | Task | Input | Output | Verification |
|---|---|---|---|---|
| T1.1 | Implement web search tool function | Search API of choice | `tools/web_search.py` | Returns ≥1 result for a known test query, standalone unit test passes |
| T1.2 | Implement Firecrawl scrape tool function | Firecrawl API (reused from Gleaner) | `tools/scrape.py` | Returns clean text for a known test URL, standalone unit test passes |
| T1.3 | Implement chunking logic | Raw scraped text | `pipeline/chunker.py` | Produces non-overlapping or controlled-overlap chunks of expected size on a sample document |
| T1.4 | Implement embedding + Chroma write | Chunked text | `pipeline/embed_store.py` | Chunks written to Chroma retrievable by similarity query in a manual test |
| T1.5 | Implement retriever function | Query string | `pipeline/retriever.py` | Given a test query, returns top-k chunks **with source_url and chunk_id intact** |

**Phase 1 Exit Check:** T1.5's output metadata is manually inspected and confirmed non-null for `source_url` and `chunk_id` on every returned chunk → **Gate 2 (Mission Plan)**. This is the hard no-go checkpoint — do not proceed if metadata is lossy.

---

## Phase 2 — Agentic Graph Construction (Week 3)

| Task ID | Task | Input | Output | Verification |
|---|---|---|---|---|
| T2.1 | Define LangGraph state object | Architecture Design Plan §5 | `graph/state.py` | State object holds company_name, JD, retrieved chunks, draft brief, claim list |
| T2.2 | Implement `plan` node | State (company_name, JD) | `graph/nodes/plan.py` | Given a test company, produces a non-empty search strategy |
| T2.3 | Implement `search/scrape` node with tool-call budget | Plan output, T1.1/T1.2 tools | `graph/nodes/search_scrape.py` | Budget cap enforced — test that exceeding the cap halts further calls |
| T2.4 | Implement `retrieve` node | Scraped/embedded content | `graph/nodes/retrieve.py` | Wraps T1.5, confirmed working inside the graph context (not just standalone) |
| T2.5 | Implement `synthesize` node | Retrieved chunks | `graph/nodes/synthesize.py` | Produces a `CompanyBrief` draft where every claim is annotated with a source chunk reference internally |
| T2.6 | Implement `self_check` node | Draft brief + chunk references | `graph/nodes/self_check.py` | Adversarial test: manually insert one fabricated claim into a draft, confirm node flags/strips it |
| T2.7 | Wire full graph with retry-once loop (`self_check → synthesize`, capped) | All nodes above | `graph/build.py` | Confirm a forced self-check failure triggers exactly one retry, then terminates with a flagged output — never loops indefinitely |
| T2.8 | End-to-end manual run, 3 companies | Full graph | 3 `CompanyBrief` outputs | Every claim in all 3 outputs manually traced to a real, correct source |

**Phase 2 Exit Check:** T2.6's adversarial test passes AND T2.8's 3 manual companies are fully citation-clean → **Gate 3 (Mission Plan)**.

---

## Phase 3 — Eval & Observability (Week 4)

| Task ID | Task | Input | Output | Verification |
|---|---|---|---|---|
| T3.1 | Implement observability logger | Per-run graph execution | `observability/logger.py` (SQLite) or Langfuse wiring | A test run produces a queryable log row with prompt version, chunk IDs, latency, cost |
| T3.2 | Implement eval runner script | Frozen fact-set (T0.4) + full graph | `eval/run_eval.py` | Runs all companies, outputs a per-company pass/fail + aggregate accuracy |
| T3.3 | Execute full eval run | T3.2 | `eval/results/run_001.json` | Aggregate accuracy ≥80% — if not, trigger Mission Plan §7 Remediation Sub-Phase before continuing |
| T3.4 | Implement CI eval gate | T3.2, existing GitHub Actions setup | `.github/workflows/eval_gate.yml` | A deliberately degraded prompt change is pushed to a test branch and confirmed to fail the CI check |
| T3.5 | Cost/latency sanity check | Logged data from T3.1 | Summary stats in `/specs/notes/` | Average cost-per-run and latency documented and within NFR-2/NFR-3 targets |

**Phase 3 Exit Check:** T3.3 accuracy threshold met (or remediation completed and re-verified), T3.4 CI gate proven functional → **Gate 4 — Mission Success Gate (Mission Plan)**.

---

## Phase 4 — Documentation & Packaging (Week 4, overlapping)

| Task ID | Task | Input | Output | Verification |
|---|---|---|---|---|
| T4.1 | Author ADR-001 through ADR-004 | Architecture Design Plan §6 | `docs/adr/` (4 files or 1 consolidated) | Each ADR has decision, rationale, and trade-off sections — no bare assertions |
| T4.2 | Write README | All prior artifacts | `README.md` | Includes architecture diagram, eval score, cost/latency figures, local run instructions |
| T4.3 | Self-administered interview-readiness walkthrough | Full system | Notes/checklist | Practitioner explains the full architecture aloud, unaided, without referring to documents |
| T4.4 | Manual integration test with one downstream consumer | A real `CompanyBrief` output | Before/after comparison | AlignResume or Overture Outreach output visibly improves when given the brief vs. JD-only baseline |

**Phase 4 Exit Check:** All four tasks closed → **Gate 5 — Mission Closeout (Mission Plan)**.

---

## 2. Task Dependency Graph (Critical Path)

```
T0.1–T0.5 (parallel-safe within Phase 0)
        │
        ▼
T1.1, T1.2 (parallel) ──▶ T1.3 ──▶ T1.4 ──▶ T1.5
        │
        ▼
T2.1 ──▶ T2.2 ──▶ T2.3 ──▶ T2.4 ──▶ T2.5 ──▶ T2.6 ──▶ T2.7 ──▶ T2.8
        │
        ▼
T3.1 (parallel with T3.2) ──▶ T3.3 ──▶ T3.4 ──▶ T3.5
        │
        ▼
T4.1, T4.2 (parallel) ──▶ T4.3 ──▶ T4.4
```

**Critical path note:** T1.5's metadata integrity (source_url, chunk_id) is the single highest-leverage checkpoint in the entire plan — every downstream task (T2.5 synthesis, T2.6 self-check, T3.2 eval) depends on it being correct. Treat any ambiguity here as a hard blocker, not a "fix later" item.

---

## 3. Daily/Weekly Execution Rhythm

| Week | Primary focus | End-of-week deliverable |
|---|---|---|
| 1 | Schemas + frozen eval set | Gate 1 passed |
| 2 | Tools + retrieval pipeline | Gate 2 passed |
| 3 | Full agentic graph | Gate 3 passed |
| 4 | Eval, CI, docs (overlapping) | Gates 4 and 5 passed |

Given coursework competing for time (per Mission Plan R-6), tasks within a phase are sequential by dependency, not by calendar day — a phase that slips a few days does not require re-planning, only a later Gate check.

---

## 4. Definition of "Implementation Complete"

The Research Agent build is implementation-complete when:
- All 5 Go/No-Go gates from the Mission Plan have passed
- The eval accuracy threshold is met on the frozen, unmodified fact-set
- The self-check guardrail has been adversarially tested and proven, not assumed
- Documentation exists sufficient for the practitioner to explain the system unaided in a live interview

---

## 5. Relationship to Other Documents

| Document | Role |
|---|---|
| Research_Agent_Problem_Statement.md | Defines *what* and *why* |
| Research_Agent_Mission_Plan.md | Defines *when*, with Go/No-Go gates and risk register |
| Research_Agent_Architecture_Design_Plan.md | Defines *how*, structurally |
| **This document** | Defines *exactly what gets built, in what order, with what verification* — the day-to-day execution reference |

---

*Document status: Phase-Wise Implementation Plan complete. Execution begins at T0.1.*
