# EDGEDASH CORE ENGINE: EXTENSIVE PROBLEM STATEMENT
## The Structural Limitations of Job Search and the Engineering Pitfalls of LLM-Driven Job Loops

**Document ID:** EDGEDASH-CORE-PROB-v1.0  
**Status:** Approved Core Engine Specification  
**Scope:** EdgeDash Autonomous Career Intelligence Agent & Scheduled Loop Engineering

---

## 1. Executive Summary

Technical professionals navigating modern software and data career markets face a dual challenge:
1. **The Single-Listing Cognitive Bottleneck:** Every job board displays opportunities one item at a time. A single posting only answers *"Am I a fit for this single role?"* It cannot answer *"Across 200 relevant postings in my city and role, what specific skill is disqualifying me most frequently, and what is it costing my interview pipeline?"*
2. **The Fragility of Naive LLM Agent Pipelines:** Developers who build AI agents to solve this problem routinely build rigid sequential scripts that query LLMs for arbitrary fit scores, execute unchecked database mutations, fail silently on web scraping changes, and exhaust API quotas on redundant runs.

**EdgeDash** solves this by engineering an autonomous, self-verifying, state-driven loop grounded in deterministic arithmetic, fact-based extraction, weighted opportunity cost aggregation, and strict plausibility verification.

---

## 2. Core Problem Dimensions

```
+---------------------------------------------------------------------------------------------------------+
|                                    THE EDGEDASH CORE PROBLEM LANDSCAPE                                  |
|                                                                                                         |
|  [Dimension 1: The Agreeable LLM Trap]       [Dimension 2: The Raw Frequency Myth]                      |
|  - Asking LLMs for scores gives 85-92        - Sorting gaps by raw count is misleading                  |
|  - Non-deterministic (same job = 72 then 88) - Low-fit roles skew learning priorities                   |
|  - Untestable & unexplainable "vibes"        - Misses the mathematical leverage of Opportunity Cost     |
|                       |                                              |                                  |
|                       +----------------------+-----------------------+                                  |
|                                              |                                                          |
|                                              v                                                          |
|  [Dimension 3: Pipeline vs. Orchestrator]    [Dimension 4: The Silent Corrupted Run]                    |
|  - Rigid loops run fetch->score->analyse     - Loop exits 0 while extraction missed key skills          |
|  - Burns quota at 7 AM when nothing changed  - Dashboard displays confidently wrong data                |
|  - "Nothing to do" treated as an error       - Lack of self-verification & plausibility checks          |
+---------------------------------------------------------------------------------------------------------+
```

### Dimension 1: The Agreeable LLM Trap (Score Inflation & Non-Determinism)
* **Score Inflation:** Language models are fine-tuned to be helpful and encouraging. When prompted to score a candidate against a job description from 0–100, models assign scores in the 80s to almost every listing. A ranking where everything ranks in the top tier is not a ranking.
* **Non-Determinism:** Stochastic token generation means the same job description evaluated twice produces two different numbers (e.g., 72 vs 88). You cannot write automated unit tests against a stochastic number.
* **Unexplainability:** When a model outputs "88", the only available explanation is "because the model said so." It cannot provide a verifiable breakdown of skill match, seniority fit, location fit, and recency.

### Dimension 2: The Raw Frequency Myth in Skill Gap Analysis
Traditional job market reports rank skill gaps by **Raw Count** ($N_{\text{mentions}}$). This leads to flawed career decisions:
* If Skill A (Terraform) is required in 15 listings where candidate fit is 25% (wrong seniority, wrong city, wrong stack), Terraform is not what is blocking the candidate—*everything* is.
* If Skill B (Kubernetes) is required in 15 listings where candidate fit is 85% (exact role match, target city), Kubernetes is the single high-leverage barrier preventing interview qualification.
* **The Opportunity Cost Solution:** A weighted sum of fit scores ($\sum \frac{\text{score}}{100}$) for blocked listings separates noise from genuine career roadblocks.

### Dimension 3: Rigid Pipeline Loops vs. State-Driven Orchestration
Naive loops execute a fixed sequence: $\text{Fetch} \rightarrow \text{Score} \rightarrow \text{Analyze}$ unconditionally.
* At 7 AM, if the system fetched two hours ago, everything is scored, and gaps are fresh, a rigid script still re-fetches, re-prompts the model, and rescans the database—wasting API quotas and compute.
* A true Orchestrator must inspect system state (timestamps, counts) and dynamically decide what tasks to run. Skipping work because state is fresh must be a first-class success (`nothing_to_do`, exit 0), not an error.

### Dimension 4: The Clean Run Hallucination & Need for Self-Verification
* A pipeline can execute with exit code 0 while producing completely bogus data. If an extraction prompt silently fails to capture "Kubernetes" across 40 listings, the downstream gap report will confidently claim that Kubernetes is not required in the candidate's market.
* Without a dedicated **Verifier** that subjects score distributions (spread $\ge 10$), volumes, and gaps to plausibility checks before publishing, users make life-altering career decisions based on corrupted intelligence.

### Dimension 5: The Prompt Injection & Text-to-SQL Vulnerability
* Exposing a natural language interface by letting an LLM generate arbitrary SQL (`SELECT`, `JOIN`, `DROP`) against a live database creates severe security vulnerabilities.
* Scraped job postings from the public web can contain embedded prompt injection payloads. An agent must never compose queries at runtime; it must route user questions exclusively to pre-written, parameterized, and clamped tools.

---

## 3. Scope of the Core Engine Blueprint

The **EdgeDash Core Engine Blueprint** resolves every one of these dimensions through:
1. **Constitutional Steering (46 Rules):** Enforcing architectural isolation, standard interfaces, and determinism in writing before code is authored.
2. **Fact-Only LLM Extraction & Deterministic Scoring Math:** Pure Python 4-part scoring arithmetic with 100% test coverage.
3. **Canonicalisation & Weighted Opportunity Cost Gaps:** Transparent $\sum \frac{\text{score}}{100}$ calculation with drillable listing IDs and timestamped snapshots.
4. **State-Driven Orchestration:** Pure `build_plan(state, config)` with caller-enforced stop conditions.
5. **Trust Nothing Plausibility Verification:** Multi-check Verifier with 1-retry healing and *"Stale beats wrong"* degradation.
6. **Safe NLP Query Interface:** 2-call Route-and-Phrase architecture with zero model-generated SQL.
