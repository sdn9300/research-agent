# EDGEDASH ↔ MCP CHIEF OF STAFF: PROTOCOL SPECIFICATION
## Comprehensive Problem Statement & Inter-System Friction Analysis

**Document ID:** PROTOCOL-PROB-v1.0  
**Status:** Approved Technical Specification  
**Scope:** Model Context Protocol (FastMCP) Integration between `EdgeDash` (Market Intelligence Engine) and `MCP Chief of Staff` (Executive Action & Communication Hub)

---

## 1. Executive Summary

Modern AI-driven career automation requires a tight symbiosis between **Market Intelligence** (what jobs exist, how well a candidate fits, and what skills are missing) and **Executive Communication** (managing recruiter emails, drafting responses, and scheduling interviews).

Currently, these two subsystems operate in complete isolation:
* **EdgeDash** executes an autonomous scheduled loop that scrapes, scores, and aggregates skill gaps, yet remains a passive diagnostic tool unable to act on inbound recruiter interest.
* **MCP Chief of Staff** ingests Gmail threads, triages priorities, and drafts replies using static prompt templates, completely blind to real-time job fit scores, matched skills, or company intelligence.

Bridging these systems through ad-hoc scripts or direct database sharing introduces severe architectural hazards, including database lock contention, monolithic coupling, stochastic parameter hallucinations, and security vulnerabilities. A formal, standardized, typed protocol—implemented via **Model Context Protocol (FastMCP)**—is required.

---

## 2. Core Inter-System Friction Points

```
+---------------------------------------------------------------------------------------------------------+
|                                    INTER-SYSTEM FRICTION SURFACES                                       |
|                                                                                                         |
|  [Friction 1: Intelligence Void]     [Friction 2: Telemetry Loss]    [Friction 3: Unsafe Direct Coupling] |
|  - Static few-shot persona drafts    - Recruiter demand keywords     - Shared SQLite database locks     |
|  - No company match data             - Interview outcomes trapped    - Monolithic cross-repo imports    |
|  - Generic replies to recruiters     - No feedback to gap analyzer   - Single point of failure          |
|                 |                                    |                               |                  |
|                 +------------------------------------+-------------------------------+                  |
|                                                      |                                                  |
|                                                      v                                                  |
|  [Friction 4: Protocol & Parsing Failures]           [Friction 5: The Unchecked Autonomy Hazard]         |
|  - Stochastic un-clamped arguments                   - Accidental auto-send from authentic Gmail        |
|  - Schema drift across asynchronous updates          - Calendar double-booking with no human review     |
+---------------------------------------------------------------------------------------------------------+
```

### Friction Point 1: Context Void in Outbound/Inbound Communications
When a recruiter reaches out regarding an active posting (e.g., from Stripe or Google), Chief of Staff's `context_builder.py` only has access to static few-shot examples (`past_replies.json`) and a fixed tone profile. It lacks access to:
1. The exact fit score calculated for that role.
2. The specific required skills matched against the candidate's master profile.
3. The reason string detailing specific alignment (e.g., *"5/5 required skills · remote · senior band exact"*).
4. Any identified missing skills that need to be addressed or positioned strategically in the reply.

**Consequence:** Drafted responses sound generic, failing to reference specific technical synergies, project repositories, or architectural proficiencies relevant to the target role.

### Friction Point 2: Lost Recruiter Telemetry & Unidirectional Flow
Recruiter emails contain high-signal, real-time demand data. A recruiter stating: *"We love your profile, but this role requires heavy production experience in FastMCP and distributed Ray clusters"* represents ground-truth market demand.
* In an unintegrated system, this feedback is read once by the user and permanently lost.
* It never feeds into EdgeDash's **Gap Analyzer** or **Future-Fit's** predictive models.

**Consequence:** The market intelligence engine remains dependent solely on public scraped job postings, missing the hyper-recent nuances communicated directly in recruiter screening notes.

### Friction Point 3: The Danger of Monolithic Coupling & Shared Storage
Attempting to connect EdgeDash and Chief of Staff by having Chief of Staff import `edgedash/storage.py` directly or read EdgeDash's SQLite database introduces critical architectural flaws:
1. **SQLite Concurrency & Locking:** EdgeDash runs on a scheduled background loop performing batch writes; concurrent reads/writes from Chief of Staff cause `sqlite3.OperationalError: database is locked`.
2. **Repository Entanglement:** Direct code imports destroy repository independence, preventing independent CI/CD, testing, and deployment.
3. **Schema Rigidity:** Any internal schema update in EdgeDash's `listings` or `skill_gaps` table instantly breaks Chief of Staff.

### Friction Point 4: Protocol Parameter Hallucinations & Boundary Hazards
When an LLM inside Chief of Staff is tasked with querying market data, open-ended parameter generation introduces failure modes:
* **Unbounded Quantities:** The model requests `limit: 50000`, triggering massive memory allocations.
* **Typo & Normalization Drift:** The model passes raw unnormalized strings (`"K8s (EKS)"`), resulting in zero query matches.
* **SQL Injection via Text-to-SQL:** Generating arbitrary SQL queries to bridge the gap exposes the database to prompt injection vectors embedded in scraped job text.

### Friction Point 5: The Unchecked Autonomy & Silent Action Hazard
Allowing an integrated pipeline to automatically send email confirmations or book calendar slots without a dedicated Human Approval Gate creates catastrophic operational risk. If the model misinterprets a rejection as an interview invite or parses a timezone incorrectly, it can dispatch unauthorized emails from the candidate's authentic Gmail account.

---

## 3. Scope of Protocol Resolution

The **EdgeDash ↔ MCP Chief of Staff Protocol Specification** establishes:
1. **A Strict FastMCP Gateway (`FastMCP`):** Isolates database access behind typed, read-only JSON-RPC tools with enforced parameter clamping.
2. **A Bidirectional Telemetry Loop:** Feeds live recruiter skill mentions from Chief of Staff back into EdgeDash's Gap Analyzer.
3. **An Inviolable Human Approval Gate:** Enforces physical UI confirmation for all external actions (email sends, calendar bookings).
4. **Resilient Circuit Breakers:** Ensures Chief of Staff gracefully falls back to local persona defaults if the EdgeDash protocol server is offline.
