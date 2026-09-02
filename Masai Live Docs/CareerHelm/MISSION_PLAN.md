# UNIFIED CAREEROS: MISSION PLAN & GOVERNANCE CONSTITUTION
## Strategic Directives, Governance Principles, Target Personas, and Operational KPIs

**Document ID:** CAREEROS-MSN-v2.2  
**Status:** Approved Strategic Directive  
**Scope:** Master System Governance across all 10 Ecosystem Subsystems

---

## 1. Core Mission Statement

To build the world's most resilient, autonomous, and cost-disciplined **AI-Native Career Operating System (CareerOS)**.

CareerOS liberates technical professionals from application churn and market opacity by executing an autonomous, self-verifying loop that:
1. Anchors all sub-agent operations to a single, verified **Candidate Profile JSON [10]** with strict `SourceProvenance` anti-fabrication gates.
2. Gathers live job opportunities via **The Gleaner [1]** and **EdgeDash Core** and deterministically computes profile alignment.
3. Identifies high-leverage skill gaps ranked by empirical **Opportunity Cost** and historical trends via **Future-Fit [5]**.
4. Conducts automated pre-application company intelligence research via **Research Agent [4]**.
5. Generates truthfulness-guarded tailored resumes via **AlignResume [2]** and high-signal outreach via **Overture Outreach [3]**.
6. Automates the final-mile application submission across ATS platforms via **PDF Auto-Apply Agent [7] ("Usher")** with DRAFT-mode review safety.
7. Ingests, triages, and coordinates interview scheduling across calendar systems via **MCP Chief of Staff [6]** and **Sentiment Classifier [9]**.
8. Immutably records every lifecycle event in the event-sourced **Memory Module [8]**, computing derived application state while keeping core memory operations 100% deterministic (zero LLM/embedding calls).
9. Upholds an inviolable **Universal Human Approval Gate** before every external real-world action.

---

## 2. The Eight Non-Negotiable Governance Laws

```
+---------------------------------------------------------------------------------------------------------+
|                                    THE 8 GOVERNANCE LAWS OF CAREEROS                                    |
|                                                                                                         |
|  [Law 1] Universal Human Gate     --> Zero external action (send/apply/book) without user approval      |
|  [Law 2] Reading vs. Arithmetic   --> LLMs extract facts; pure Python computes deterministic scores     |
|  [Law 3] FastMCP Tool Mesh        --> Sibling agents communicate exclusively via typed MCP interfaces   |
|  [Law 4] Single Source of Truth   --> Candidate Profile JSON [10] anchors all facts; zero hallucinations|
|  [Law 5] DRAFT-Mode Auto-Apply    --> PDF Auto-Apply [7] defaults to DRAFT; AUTO mode is earned per ATS |
|  [Law 6] No-Silent-Drop & Degrade --> Failures persist status="error"; stale verified data beats wrong  |
|  [Law 7] Zero Model-Generated SQL --> Natural language routes to clamped, parameterised query tools     |
|  [Law 8] Memory Event Sourcing    --> Memory Module [8] is append-only; remembers and never decides    |
+---------------------------------------------------------------------------------------------------------+
```

### Law 1: The Universal Human Approval Gate
* No agent within CareerOS may dispatch an email, submit an ATS job application, or confirm a calendar event without explicit user confirmation through the `approval_gate.py` interface.
* Execution APIs require a single-use cryptographic token generated only by physical UI click.

### Law 2: Separation of Reading from Arithmetic
* Never ask an LLM for a fit score, rank, or percentage rating.
* Language models function strictly as structured document readers (extracting required skills, years, seniority, remote status).
* All scoring arithmetic is executed in pure, deterministic, 100% unit-tested Python functions. The model never sees scoring weights.

### Law 3: Standard Model Context Protocol (FastMCP) Mesh
* All inter-agent data exchange and tool invocations operate over standard **FastMCP** JSON-RPC / STDIO / SSE bindings.
* Eliminates monolithic cross-repository dependencies; any agent can be swapped or refactored independently as long as its FastMCP tool contract holds.

### Law 4: Canonical Candidate Profile Single Source of Truth ("One Schema; Many Projections")
* All sub-agents (`AlignResume`, `Overture Outreach`, `PDF Auto-Apply Agent`, `The Gleaner`, `Scorer`) read verified facts strictly from **Candidate Profile JSON [10]**.
* Claim-bearing fields (`skills`, `experience`) carry a mandatory `SourceProvenance` record (`verified: bool`, `source_type`, `source_ref`). Sub-agents are forbidden from inventing unverified employment dates, skills, or certifications.
* **Disjoint Field Ownership:** Every top-level section of the profile has exactly one authoritative writer (`identity`/`education`/`skills`/`experience` $\rightarrow$ human-gated bootstrap; `tailoring_history` $\rightarrow$ AlignResume; `outreach_history` $\rightarrow$ Overture; `application_history` $\rightarrow$ Usher; `interaction_signals` $\rightarrow$ Sentiment Classifier; `profile_metadata` $\rightarrow$ Conductor). Cross-section write attempts raise `OwnershipViolationError`.
* **Projections over Duplicates:** Sibling components never maintain private duplicate models; they consume mechanically derived adapter projections (`to_resume_profile`, `to_search_criteria`, `to_outreach_context`, `to_application_view`).

### Law 5: DRAFT-Mode Auto-Apply & Tiered Field Resolution
* **PDF Auto-Apply Agent [7] ("Usher")** operates in **DRAFT** mode by default, pausing before the final submit button to allow human inspection of filled fields.
* Field resolution follows a strict cost-aware ladder: Tier 0 (Exact DOM Selectors) $\rightarrow$ Tier 1 (Fuzzy Label Match) $\rightarrow$ Tier 2 (Lightweight LLM) $\rightarrow$ Tier 3 (Heavy LLM). Unresolved fields trigger `MANUAL_REQUIRED` rather than guessing.
* Autonomous **AUTO** mode is opt-in and earned per platform only after achieving a $100\%$ accuracy record over 20+ verified submissions.

### Law 6: No-Silent-Drop & "Stale Beats Wrong"
* Every agent invocation produces a persisted `AgentResult` record, even on failure.
* The Verifier agent validates scoring spreads, volumes, and gap consistency. If checks fail after 1 capped retry, the cycle is marked *Degraded* and the public dashboard preserves the last verified passing state (*"Stale beats wrong"*).

### Law 7: Zero Model-Generated SQL
* Prohibit Text-to-SQL in all forms.
* Natural language queries route through a two-stage LLM pipeline (Route $\rightarrow$ Execute $\rightarrow$ Phrase) utilizing 7 pre-written, parameterized tools.
* All model-supplied parameters are validated and clamped to strict bounds (e.g., `days` $1 \dots 90$).

### Law 8: Memory Event Sourcing & Immutability ("Remember; Do Not Decide")
* **Memory Module [8]** is a pure sink-and-source operating on an event-sourcing hybrid pattern: `memory_events` is the immutable append-only ledger; `application_records` and `status_transitions` are materialized derived views, 100% rebuildable via `rebuild_derived_state()`.
* Core ingestion and queries are fully deterministic—zero LLM calls, zero embedding calls.
* Memory Module computes derived *state* (what happened, what is true now) but never derived *action* (what should happen next). Action judgment belongs exclusively to **Conductor [0]**.
* Hard/soft rejections automatically enforce a 30-day domain cooldown in the Memory Module.

---

## 3. The 10-Component Ecosystem Topology & Dependency Matrix

```
DATA & ANCHOR LAYER      [10] Candidate Profile JSON Engine (Master Anchor)
                                         │
DISCOVERY LAYER          [1] The Gleaner (Gleaner) ─── [EdgeDash Loop & Deterministic Scorer]
                                         │
INTELLIGENCE LAYER       [4] Research Agent (Dossiers) ─ [5] Future-Fit (Skill Forecasts)
                                         │
APPLICATION LAYER        [2] AlignResume (PDF) ───────── [7] PDF Auto-Apply Agent (Usher)
                                         │
OUTREACH & INBOUND       [3] Overture Outreach ───────── [6] MCP Chief of Staff Hub
                                         │
TRIAGE & SCHEDULING      [9] Sentiment Classifier ────── [Google Calendar Engine]
                                         │
LEARNING & MEMORY LAYER  [8] Memory Module (Event-Sourced Append-Only Ledger)
                                         │
COORDINATION ENGINE      [0] Conductor Agent (LangGraph Master DAG Coordinator)
```

### 3.1 Cross-Component Data Contract Matrix

| Subsystem # | Component Name | Reads from Profile [10] | Writes to Profile [10] | Relationship to Memory Module [8] |
|---|---|---|---|---|
| **[10]** | **Candidate Profile JSON** | Master Store | Self (Atomic `put`) | Persisted via Memory Module Storage Adapter |
| **[1]** | **The Gleaner** | `preferences` (via `to_search_criteria`) | None | Emits `JOB_DISCOVERED` |
| **[2]** | **AlignResume** | `identity`, `education`, `skills`, `experience` | `tailoring_history` (refs only) | Emits `RESUME_TAILORED` |
| **[3]** | **Overture Outreach** | `identity.contact`, `preferences` | `outreach_history` (refs only) | Emits `OUTREACH_SENT` |
| **[4]** | **Research Agent** | `preferences` (industry/role scope) | None | Emits `DOSSIER_COMPILED` |
| **[5]** | **Future-Fit** | (None directly) | Supplies `skills.taxonomy_ref` export | Emits `SKILL_GAP_EVALUATED` |
| **[6]** | **MCP Chief of Staff** | `identity.contact` | None | Emits `INTERVIEW_SCHEDULED`, queries state |
| **[7]** | **PDF Auto-Apply (Usher)** | `identity`, `education`, `experience`, `tailoring_history` | `application_history` (refs only) | Emits `APPLICATION_SUBMITTED`, checks cooldown |
| **[8]** | **Memory Module** | `candidate_id` foreign key | None (owns lifecycle ledger) | Immutably persists all ecosystem events |
| **[9]** | **Sentiment Classifier** | None | `interaction_signals` (refs only) | Emits `RESPONSE_CLASSIFIED` |
| **[0]** | **Conductor Orchestrator**| All (threads as LangGraph state) | `profile_metadata` (system-managed) | Master DAG Router querying Memory Module & Profile |

---

## 4. Milestone & Certification Badge Hierarchy

```
+---------------------------------------------------------------------------------------------------------+
|                                    CAREEROS BADGE MILESTONES                                            |
|                                                                                                         |
|  [Badge 1: The Tracker]   --> 50+ real live listings ingested, dedup proven, error-isolated             |
|  [Badge 2: The Decoder]   --> Deterministic scorer active, Opportunity Cost gap ranking & audit         |
|  [Badge 3: The Automator] --> State-driven Orchestrator, Verifier plausibility checks, Streamlit UI     |
|  [Badge 4: The Usher]     --> PDF Auto-Apply Agent active with DRAFT mode & multi-ATS adapters          |
|  [Badge 5: The Edge]      --> Safe NLP query tools, session rate guards, public cloud deployment        |
|  [Badge 6: The Conductor] --> Full 10-agent FastMCP mesh integration, Memory Module & Profile sync     |
+---------------------------------------------------------------------------------------------------------+
```
