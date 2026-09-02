# EDGEDASH CORE ENGINE: COMPREHENSIVE EVALUATION PLAN
## Automated Verification Harnesses, Mathematical Proofs, and Quality Benchmarks

**Document ID:** EDGEDASH-CORE-EVAL-v1.0  
**Status:** Approved Quality Assurance Standard  
**Scope:** EdgeDash Core Engine Test Suites, Plausibility Tripwires, and CLI Proofs

---

## 1. Multi-Tiered Testing Pyramid

```
+---------------------------------------------------------------------------------------------------------+
|                                    EDGEDASH 4-TIER EVALUATION PYRAMID                                   |
|                                                                                                         |
|                     / \                                                                                 |
|                    /   \     TIER 4: Full Autonomous Scheduled Loop & Cloud Deploy Verification        |
|                   /=====\                                                                               |
|                  /       \   TIER 3: Verifier Rejection Simulation & "Stale Beats Wrong" Proofs         |
|                 /=========\                                                                             |
|                /           \ TIER 2: Determinism, Hash Caching, and Idempotence Verification            |
|               /=============\                                                                           |
|              /               \TIER 1: Pure Function Unit Tests (Scoring, Canonical, Planning) (100%)   |
|             +-----------------+                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Test Suite Specifications & Verification Harnesses

### 2.1 Tier 1: Pure Function Unit Tests

#### A. Scorer Pure Arithmetic Tests (`tests/test_scoring.py`)
Validates that `score_listing(listing, facts, config)` is a pure mathematical function of its inputs with zero side effects.

```python
import pytest
from edgedash.scoring import score_listing
from edgedash.config import Config

@pytest.fixture
def base_config():
    return Config(
        target_role="Data Analyst",
        target_city="Bengaluru",
        my_skills=["python", "sql", "tableau", "pandas"],
        weights={"skill_match": 0.45, "seniority_fit": 0.25, "location_fit": 0.15, "recency": 0.15}
    )

def test_perfect_match(base_config):
    facts = {
        "required_skills": ["python", "sql"],
        "nice_to_have": ["tableau"],
        "seniority": "mid",
        "years_required": 2,
        "remote_ok": True
    }
    result = score_listing({"posted_at": "2026-08-27"}, facts, base_config)
    assert result["score"] >= 90
    assert "seniority fits" in result["reason"]

def test_empty_required_skills(base_config):
    facts = {"required_skills": [], "nice_to_have": [], "seniority": "unknown", "years_required": None, "remote_ok": None}
    result = score_listing({"posted_at": None}, facts, base_config)
    assert 0 <= result["score"] <= 100

def test_null_posted_at(base_config):
    facts = {"required_skills": ["python"], "nice_to_have": [], "seniority": "mid", "years_required": None, "remote_ok": True}
    result = score_listing({"posted_at": None}, facts, base_config)
    assert result["components"]["recency"] == 0.5

def test_extreme_seniority_mismatch(base_config):
    facts = {"required_skills": ["python"], "nice_to_have": [], "seniority": "lead", "years_required": 10, "remote_ok": True}
    result = score_listing({"posted_at": "2026-08-27"}, facts, base_config)
    assert result["components"]["seniority_fit"] == 0.0
```

#### B. Planning Pure Logic Tests (`tests/test_planning.py`)
Validates that `build_plan(state, config)` generates exact tasks and stop conditions purely from inputs.

```python
from edgedash.planning import build_plan
from edgedash.state import SystemState

def test_nothing_to_do(base_config):
    state = SystemState(hours_since_fetch=1.0, unscored_count=0, gaps_stale=False, last_cycle_verdict="pass")
    plan = build_plan(state, base_config)
    assert plan.is_empty_or_all_skips() is True

def test_unscored_listings_only(base_config):
    state = SystemState(hours_since_fetch=1.0, unscored_count=45, gaps_stale=False, last_cycle_verdict="pass")
    plan = build_plan(state, base_config)
    assert len(plan.active_tasks) == 2  # score + analyse
    assert plan.get_task("score").stop_conditions["max_items"] == base_config.score_batch_size
```

---

### 2.2 Tier 2: Determinism & Hash Caching Verification

#### A. Scorer Determinism CLI Proof
Proves that scoring the exact same listing twice produces the identical score without model drift.

```bash
# Clear score for a specific listing
python -m edgedash.rescore --id 41ac9e
# Run scoring cycle
python run_cycle.py
# Assert score before == score after
```

#### B. Fact Extraction Hash Caching Proof
Proves that re-extracting an existing description text hits the cache at 0 API cost.

```bash
python -c "from edgedash.agents.extractor import extract; from edgedash.storage import get_listings; import time; l = get_listings(limit=1)[0]; t0 = time.time(); extract(l); t1 = time.time(); extract(l); t2 = time.time(); print(f'Run 1: {t1-t0:.4f}s | Run 2 (Cache): {t2-t1:.4f}s')"
# Run 2 duration must be < 0.005s (pure SQLite cache lookup)
```

---

### 2.3 Tier 3: Verifier Plausibility & Degradation Simulations

#### A. Verifier Plausibility Checks (`tests/test_checks.py`)
Validates that score spread and residual checks catch corrupted data batches.

```python
from edgedash.checks import check_score_spread, check_unscored_residuals

def test_spread_failure():
    clustered_scores = [82, 84, 85, 83, 85]
    verdict, spread = check_score_spread(clustered_scores, min_spread=10)
    assert verdict == "fail"
    assert spread == 3

def test_valid_spread():
    good_scores = [34, 52, 67, 78, 89]
    verdict, spread = check_score_spread(good_scores, min_spread=10)
    assert verdict == "pass"
    assert spread == 55
```

#### B. Simulated Failure & Degradation Proof
Simulate a scoring failure by temporarily setting scoring weights to zero, running a cycle, and verifying that the Verifier logs a failure and marks the cycle `Degraded` without updating the dashboard.

```bash
# Run cycle with flattened weights
python run_cycle.py
# Check verdicts history
python -m edgedash.verdicts
# Expected output: VERDICT: fail — score_spread observed < 10 -> cycle DEGRADED
```

---

### 2.4 Tier 4: NLP Query Safety & Clamping Tests

#### A. Query Parameter Clamping (`tests/test_tools.py`)
Validates that model-supplied query parameters are clamped to safe ranges.

```python
from edgedash.query.tools import companies_hiring, best_matches

def test_tool_parameter_clamping():
    # Pass out-of-bounds parameters
    res_companies = companies_hiring(days=5000)   # Clamped to days=90
    res_matches = best_matches(n=1000)           # Clamped to n=25
    assert len(res_matches) <= 25
```

#### B. Explicit Refusal for Out-of-Scope Prompts (`tests/test_ask.py`)
Validates that unhandled questions trigger a static refusal and execute zero SQL.

```python
from edgedash.query.ask import ask

def test_out_of_scope_prompt():
    res = ask("Should I ask for a salary increase during my review?")
    assert res.tool_used is None
    assert "I cannot answer that question from your data" in res.text
    assert len(res.rows) == 0
```

---

## 3. Master Verification Matrix

```
+------------------------------------+------------------------------------+---------------------+
| Verification Harness               | Execution Command                  | Acceptance Criteria |
+------------------------------------+------------------------------------+---------------------+
| Deduplication Engine               | python run_cycle.py (twice)        | Run 2: <= 2 new rows|
| Source Fault Isolation             | Point source to invalid URL        | Cycle completes ok  |
| LLM Gateway & JSON Repair          | python -m edgedash.llm --check     | Provider/Model OK   |
| Scorer Arithmetic Suite            | pytest tests/test_scoring.py       | 6/6 tests pass      |
| Determinism Proof                  | rescore --id <id> -> run_cycle.py  | Identical score out |
| Skill Normalization Audit          | python -m edgedash.skills --audit  | Top 40 clean        |
| Gap Analysis Opportunity Cost      | python -m edgedash.gaps            | Top 10 by opp cost  |
| State Planning Pure Logic          | pytest tests/test_planning.py      | 4/4 tests pass      |
| Orchestrator Idempotence           | python run_cycle.py (immediate)    | nothing_to_do, 0 API|
| Verifier Plausibility Checks       | pytest tests/test_checks.py        | Spread >= 10 checked|
| Verifier Simulated Failure         | Flatten weights -> run_cycle.py    | Verdict: fail, retry|
| NLP Parameter Clamping             | pytest tests/test_tools.py         | Bounds clamped      |
| NLP Explicit Refusal               | Ask "Should I take a pay cut?"     | Static refusal msg  |
| Headless Daily Action Run          | pytest tests/test_e2e_cycle.py     | Full loop completes |
+------------------------------------+------------------------------------+---------------------+
```
