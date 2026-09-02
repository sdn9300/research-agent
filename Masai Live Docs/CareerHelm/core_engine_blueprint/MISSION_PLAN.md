# EDGEDASH CORE ENGINE: MISSION PLAN & CONSTITUTIONAL STEERING
## Strategic Directives, 46 Constitutional Rules, Core Maxims, and Certification Milestones

**Document ID:** EDGEDASH-CORE-MSN-v1.0  
**Status:** Approved Architectural Constitution  
**Scope:** EdgeDash Core Engine Governance, Steering File, and Milestone Hierarchy

---

## 1. Core Mission Statement

To build **EdgeDash**: an autonomous, cost-disciplined, self-verifying AI career intelligence agent that runs on a continuous scheduled loop, scrapes live job listings across the web, deterministically calculates candidate fit, surfaces actionable skill gaps ranked by **Opportunity Cost**, verifies its own output before publishing, and serves intelligence through a clean Streamlit dashboard and a safe, natural-language query interface.

---

## 2. The 46 Constitutional Steering Rules

These rules are loaded into the agent's steering constitution (`.kiro/steering/edgedash.md`) and govern every design and code decision.

```
+---------------------------------------------------------------------------------------------------------+
|                                  THE 46 CONSTITUTIONAL RULES OF EDGEDASH                                |
|                                                                                                         |
|  [Chapter 1: Rules 1-8]   --> Foundation, Isolated Storage, Config Dataclass, Fail Loudly               |
|  [Chapter 2: Rules 9-14]  --> Source Plugin Pattern, 10s Timeouts, Rate Limits, Error Isolation         |
|  [Chapter 3: Rules 15-21] --> Fact Extraction Only, Deterministic Math Scorer, Hash Caching             |
|  [Chapter 4: Rules 22-27] --> Skill Canonicalisation, Opportunity Cost Math, Drillable IDs              |
|  [Chapter 5: Rules 28-33] --> Pure Decision Planner, Caller Stop Conditions, Skipped is Success        |
|  [Chapter 6: Rules 34-46] --> Plausibility Verifier, Stale Beats Wrong, Zero Text-to-SQL, Clamped Tools |
+---------------------------------------------------------------------------------------------------------+
```

### Chapter 1: Foundation & Storage (Rules 1–8)
1. **Python 3.11+ & Standard Library First:** Add dependencies only when they genuinely save real work.
2. **Single Storage Boundary:** ALL database access goes through `edgedash/storage.py`. No other module may import `sqlite3` or database drivers directly.
3. **No Hardcoded User Profiles:** Target role, city, keywords, and skill lists reside strictly in `config.yaml`.
4. **Zero Secrets in Code:** Environment variables only, loaded in one place from `.env` (gitignored, `.env.example` committed).
5. **Cycle Telemetry Logging:** Every agent run writes a row to `cycle_log`: agent, timestamp, records touched, pass/fail status, notes.
6. **Fail Loudly:** No bare `except: pass`. Errors must be visible and actionable.
7. **Type Hints Throughout:** Enforce strict type hints on every function signature.
8. **File Size Discipline:** Keep files under $\sim 150$ lines. Refactor before size becomes unmanageable.

### Chapter 2: Network & Sources (Rules 9–14)
9. **Source Plugin Pattern:** Every external source implements an abstract `Source` interface. The `Fetcher` never contains source-specific parsing.
10. **Normalized Output Dictionaries:** Every source returns dicts with exact keys: `source`, `external_id`, `title`, `company`, `location`, `url`, `description`, `posted_at`, `raw`. Missing values are `None`, never empty strings or "N/A".
11. **Unified HTTP Helper:** All network calls route through `edgedash/sources/http.py` with 10s timeout, exponential backoff (2 retries), custom User-Agent, and custom `SourceError`.
12. **Per-Source Error Isolation:** A failing source must NEVER crash the cycle. Catch per-source, log status "failed", and continue to the next source.
13. **Secret Isolation:** Missing API keys cause a source to skip itself cleanly with a log line without raising an exception.
14. **Respectful Scraping:** Rate limit to at most 1 request per second per source, honor page limits, and back off on HTTP 429.

### Chapter 3: Intelligence & Scoring (Rules 15–21)
15. **Single LLM Gateway:** All LLM calls route through `edgedash/llm.py` exposing `complete_json()`. Provider and model come from config. Rate limited to 15 RPM.
16. **Fact-Only Extraction & Deterministic Arithmetic (The Core Rule):** NEVER ask an LLM for a final score, ranking, or rating. The model extracts facts (`required_skills`, `seniority`, `years_required`, `remote_ok`). Pure Python in `scoring.py` computes the score. The model never sees weights.
17. **Schema Validation & Feedback Retry:** Validate model JSON against explicit schemas. On error, retry ONCE providing the exact validation error. If still failing, drop that single row without killing the batch.
18. **Scoring Idempotence & Hash Caching:** Never re-score a scored listing (`WHERE fit_score IS NULL`). Cache extractions against `hash(description)`.
19. **Formula-Derived Reason Strings:** Generate human-readable reasons strictly from computed component values, never free text from an LLM.
20. **Score Distribution Logging:** Log score count, min, max, mean, and spread to `cycle_log`. A spread $< 10$ is suspect.
21. **Batch Capping:** Cap listings scored per cycle at a configurable `score_batch_size` (default: 25) to prevent quota blowups.

### Chapter 4: Aggregate Analysis & Skill Gaps (Rules 22–27)
22. **Deterministic SQL/Python Aggregation:** No LLM call may produce, adjust, or rank an aggregate number.
23. **Explicit Skill Alias Maps:** Canonicalize skill names via user-owned `skill_aliases` in `config.yaml`. Never auto-merge skills by model judgment alone.
24. **Weighted Opportunity Cost Ranking:** Rank skill gaps by the sum of fit scores of blocked listings ($\sum \frac{\text{score}}{100}$), not raw frequency.
25. **Timestamped Versioned Snapshots:** Append-only snapshots to `skill_gaps` table; never overwrite previous run history.
26. **Drillability to Listing IDs:** Every reported gap must list the specific listing IDs it was computed from.
27. **Sample Size Reporting:** Gaps computed from $< 3$ listings must be explicitly flagged as "low confidence".

### Chapter 5: Orchestration & State-Driven Decisions (Rules 28–33)
28. **State-Driven Planning:** The Orchestrator reads system state and decides which agents run. Skipping an agent when no work is needed is a SUCCESSFUL outcome (`nothing_to_do`, exit 0).
29. **Caller-Imposed Stop Conditions:** Every task delegation carries explicit goals and stop conditions (`max_items`, `max_seconds`, `max_pages`).
30. **Strict Orchestrator Boundary:** The Orchestrator coordinates and never executes fetching, scoring, or analysis directly.
31. **Print & Log Plan Before Execution:** Print rendered plan with state values and decision reasons before running tasks.
32. **Task Failure Containment:** One sub-agent failing marks cycle "partial" and continues remaining tasks.
33. **Single Summary Row Per Cycle:** Record exactly what ran, what was skipped, durations, and final verdict.

### Chapter 6: Verification & Natural Language Queries (Rules 34–46)
34. **Plausibility Over Correctness:** Four plausibility checks run as pure functions before publishing.
35. **Verifier Judges, Never Repairs:** The Verifier flags anomalies; the Orchestrator owns retry logic.
36. **Capped 1-Retry Healing:** If checks fail, retry once with adjusted extraction context; if still failing, mark cycle `Degraded`.
37. **"Stale Beats Wrong" Publishing:** A failed/degraded cycle never updates the public dashboard; existing verified data is preserved.
38. **Activity Log Transparency:** Publish agent activity logs and verdicts directly on the dashboard.
39. **Decoupled Streamlit Dashboard:** Dashboard is strictly read-only; no "run cycle" trigger buttons in UI.
40. **Zero Text-to-SQL:** NEVER generate SQL from an LLM. The model selects from a fixed registry of parameterized tools.
41. **Untrusted Parameter Clamping:** Validate and clamp all model-supplied arguments to safe numeric ranges.
42. **Two-Call NLP Architecture:** Model appears exactly twice: once to ROUTE (select tool + params) and once to PHRASE (summarize returned rows).
43. **Phrasing Numerical Integrity:** The phrasing call may ONLY use numbers present in returned rows; zero extrapolation.
44. **Display Underlying Rows:** Every NLP answer displays the raw database rows alongside the prose summary.
45. **Explicit Refusal on Out-of-Scope Prompts:** Return static refusal listing supported capabilities for unhandled questions.
46. **Read Only Last Passing Cycle:** Query tools resolve data exclusively from the latest verified passing cycle.

---

## 3. Four-Tier Certification Badge Hierarchy

```
+---------------------------------------------------------------------------------------------------------+
|                                    EDGEDASH CERTIFICATION BADGES                                        |
|                                                                                                         |
|  [Badge 1: The Tracker]   --> Live Fetcher, stable hash dedup, 50+ live listings, error isolation       |
|  [Badge 2: The Decoder]   --> Deterministic scorer, spread >= 15, opportunity cost gap analyzer         |
|  [Badge 3: The Automator] --> State-driven Orchestrator, Verifier plausibility checks, Streamlit UI     |
|  [Badge 4: The Edge]      --> Safe NLP query interface, abuse guards, public cloud deployment          |
+---------------------------------------------------------------------------------------------------------+
```
