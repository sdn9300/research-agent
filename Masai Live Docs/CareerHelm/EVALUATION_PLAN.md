# UNIFIED CAREEROS: COMPREHENSIVE EVALUATION PLAN
## Multi-Tiered Verification Suites, Automated Test Harnesses, and Quality Benchmarks

**Document ID:** CAREEROS-EVAL-v2.2  
**Status:** Approved Quality Assurance Standard  
**Scope:** Complete 10-Component Testing & Validation Framework

---

## 1. Multi-Tiered Testing Pyramid

```
+---------------------------------------------------------------------------------------------------------+
|                                    CAREEROS 4-TIER EVALUATION PYRAMID                                   |
|                                                                                                         |
|                     / \                                                                                 |
|                    /   \     TIER 4: Full Multi-Agent DAG Simulations (100 Opps)                         |
|                   /=====\                                                                               |
|                  /       \   TIER 3: FastMCP Protocol, Auto-Apply & Memory Ingest Integration Tests     |
|                 /=========\                                                                             |
|                /           \ TIER 2: Component Determinism, Plausibility Tripwires & Replay Rebuilds    |
|               /=============\                                                                           |
|              /               \TIER 1: Pure Function Unit Tests (Scoring, Profile, State Machine) (100%) |
|             +-----------------+                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Component Verification & Test Harness Specifications

### 2.1 Tier 1: Pure Mathematical & Schema Unit Tests

#### A. Scorer Arithmetic Pure Tests (`tests/test_scoring.py`)
Validates that `score_listing(listing, facts, config)` is a pure function of its inputs with zero side effects.

```python
import pytest
from edgedash.scoring import score_listing
from edgedash.config import Config

@pytest.fixture
def base_config():
    return Config(
        target_role="AI Engineer",
        target_city="Bengaluru",
        my_skills=["python", "fastapi", "langgraph", "pytorch", "sql"],
        weights={"skill_match": 0.45, "seniority_fit": 0.25, "location_fit": 0.15, "recency": 0.15}
    )

def test_perfect_match(base_config):
    facts = {
        "required_skills": ["python", "fastapi", "pytorch"],
        "nice_to_have": ["sql"],
        "seniority": "mid",
        "years_required": 3,
        "remote_ok": True
    }
    result = score_listing({"posted_at": "2026-08-27"}, facts, base_config)
    assert result["score"] >= 90
    assert "seniority fits" in result["reason"]

def test_empty_required_skills(base_config):
    facts = {"required_skills": [], "nice_to_have": [], "seniority": "unknown", "years_required": None, "remote_ok": None}
    result = score_listing({"posted_at": None}, facts, base_config)
    assert 0 <= result["score"] <= 100
```

#### B. Candidate Profile Pydantic v2 Canonical Validation (`tests/test_candidate_profile.py`)
Validates the canonical `CandidateProfile` Pydantic v2 model, field-level constraints, and `extra="forbid"`.

```python
import pytest
from datetime import datetime
from pydantic import ValidationError
from candidate_profile.schemas import (
    CandidateProfile, ProfileMetadata, Identity, ContactInfo,
    EducationRecord, SkillRecord, ExperienceRecord, ApplicationPreferences,
    SourceProvenance, ProficiencyLevel
)

def test_valid_canonical_profile():
    profile = CandidateProfile(
        profile_metadata=ProfileMetadata(
            candidate_id="sdn9300",
            schema_version="1.0.0",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            last_writer_component="bootstrap"
        ),
        identity=Identity(
            legal_name="Soumyadeep Nath",
            location="Bengaluru",
            contact=ContactInfo(email="sdn@example.com", github="https://github.com/sdn9300")
        ),
        education=[EducationRecord(institution="IIT Roorkee", program="B.Tech", status="completed", start_date="2022-08")],
        skills=[SkillRecord(
            name="Python",
            taxonomy_ref="python",
            proficiency_self_assessed=ProficiencyLevel.ADVANCED,
            source=SourceProvenance(source_type="resume_v12", verified=True, recorded_at=datetime.utcnow())
        )],
        experience=[ExperienceRecord(
            title="AI Systems Engineer",
            kind="project",
            stack=["Python", "FastAPI", "LangGraph"],
            bullets=["Engineered multi-agent loop with 100% deterministic replay"],
            source=SourceProvenance(source_type="manual_entry", verified=True, recorded_at=datetime.utcnow())
        )],
        preferences=ApplicationPreferences(target_roles=["AI Engineer", "Backend Engineer"], locations=["Bengaluru", "Remote"])
    )
    assert profile.identity.legal_name == "Soumyadeep Nath"
    assert profile.skills[0].source.verified is True

def test_extra_field_raises_validation_error():
    with pytest.raises(ValidationError):
        Identity(legal_name="Soumyadeep Nath", location="Bengaluru", contact=ContactInfo(email="sdn@example.com"), unapproved_field="malicious")
```

---

### 2.2 Tier 2: Candidate Profile & Memory Module Hard Gates (HG-1 to HG-6 & G1 to G6)

```
+---------------------------------------------------------------------------------------------------------------+
|                                    CANDIDATE PROFILE HARD-BLOCKING GATES (HG-1 to HG-6)                       |
+--------+-------------------------------+----------------------------------------------------------------------+
| Gate   | Gate Name                     | Acceptance Procedure & Verification Condition                        |
+--------+-------------------------------+----------------------------------------------------------------------+
| HG-1   | Real-Data Ingestion Fidelity  | 100% Pydantic validation pass rate on real resume.pdf; 0 patches.   |
| HG-2   | Round-Trip Serialization      | Pydantic -> JSON -> Pydantic lossless fidelity excluding updated_at. |
| HG-3   | Atomic-Write Crash Safety     | Kill mid-write; verify prior valid file is untouched and loadable.   |
| HG-4   | Ownership-Violation Rejection | Adversarial suite: illegal section writes raise OwnershipViolation.  |
| HG-5   | Schema Version Migration      | Explicit migration chain executes round-trip test across semver hops.|
| HG-6   | Strict Extra Forbid           | Injected unknown fields on any model raise immediate ValidationError.|
+--------+-------------------------------+----------------------------------------------------------------------+
```

```
+---------------------------------------------------------------------------------------------------------------+
|                                      MEMORY MODULE HARD-BLOCKING GATES (G1 to G6)                             |
+--------+-------------------------------+----------------------------------------------------------------------+
| Gate   | Gate Name                     | Acceptance Procedure & Verification Condition                        |
+--------+-------------------------------+----------------------------------------------------------------------+
| G1     | Zero Data Loss & Durability   | Ingested events retrievable via get_history() after process restart. |
| G2     | Deterministic Idempotency     | 1,000 duplicate event bursts produce 0 duplicate rows.               |
| G3     | Fallback & UNKNOWN Catch-all  | Malformed/unrecognized event types logged as UNKNOWN; 0 drops.       |
| G4     | State Machine & Sub-50ms Lat  | 100% state machine coverage; get_application() executes in < 50ms.   |
| G5     | Full Event Replay Parity      | rebuild_derived_state() produces 100% byte-for-byte state parity.    |
| G6     | SQLite WAL Concurrency Stress | 10 concurrent threads (5R/5W, 60s) produce 0 lock errors in WAL mode.|
+--------+-------------------------------+----------------------------------------------------------------------+
```

#### A. Ownership-Violation Adversarial Test (`tests/test_profile_ownership.py` — Gate HG-4)
```python
import pytest
from candidate_profile.reducer import merge_candidate_profile, OwnershipViolationError
from candidate_profile.schemas import CandidateProfilePatch

def test_illegal_section_write_raises(base_profile):
    # Gleaner attempts to overwrite skills (illegal — only bootstrap/extractor owns skills)
    illegal_patch = CandidateProfilePatch(
        writer_component="gleaner",
        section="skills",
        value=[]
    )
    with pytest.raises(OwnershipViolationError):
        merge_candidate_profile(base_profile, illegal_patch)
```

#### B. Memory Module State Replay & Rebuildability Test (`tests/test_memory_rebuild.py` — Gate G5)
```python
from memory_module.store import MemoryStore
from memory_module.schemas import MemoryEvent, EventType
from datetime import datetime

def test_memory_replay_rebuildability():
    store = MemoryStore(":memory:")
    store.record_event(MemoryEvent(event_type=EventType.JOB_DISCOVERED, source_component="gleaner", job_id="j1", application_id="app_1", occurred_at=datetime.utcnow(), payload={"company": "Stripe", "title": "AI Engineer"}))
    store.record_event(MemoryEvent(event_type=EventType.RESUME_TAILORED, source_component="align_resume", application_id="app_1", occurred_at=datetime.utcnow(), payload={"tailoring_run_id": "tr_1"}))
    store.record_event(MemoryEvent(event_type=EventType.APPLICATION_SUBMITTED, source_component="auto_apply", application_id="app_1", occurred_at=datetime.utcnow(), payload={"channel": "greenhouse"}))
    
    app_before = store.get_application("app_1")
    assert app_before.status == "applied"
    
    store.rebuild_derived_state()
    app_after = store.get_application("app_1")
    assert app_before == app_after
```

---

### 2.3 Tier 3: Auto-Apply & FastMCP Protocol Integration Tests

#### A. PDF Auto-Apply Field Resolution & DRAFT Mode (`tests/test_auto_apply.py`)
Validates that the Auto-Apply agent accurately fills form fields and pauses in DRAFT mode.

```python
import pytest
from pdf_auto_apply.engine import AutoApplyEngine
from pdf_auto_apply.schemas import ApplicationDraft

def test_greenhouse_draft_mode_pause(mock_greenhouse_page, sample_resume_pdf):
    engine = AutoApplyEngine(mode="DRAFT")
    draft = engine.stage_application(
        ats_url="https://boards.greenhouse.io/sample/jobs/123",
        resume_artifact=sample_resume_pdf,
        candidate_facts={"first_name": "Soumyadeep", "last_name": "Nath", "email": "sdn@example.com"}
    )
    assert draft.status == "STAGED_FOR_REVIEW"
    assert draft.filled_field_count >= 10
    assert draft.is_submitted is False
```

---

## 3. Monitored Gates (Production Telemetry)

```
+---------------------------------------------------------------------------------------------------------------+
|                                           MONITORED GATES (MG-1 to MG-5)                                      |
+--------+---------------------------------------+----------------------------------+---------------------------+
| ID     | Metric                                | What it Signals                  | Expected Steady-State     |
+--------+---------------------------------------+----------------------------------+---------------------------+
| MG-1   | Profile Validation Failure Rate       | Real-world writes hitting edges  | Trend toward 0%           |
| MG-2   | Schema Version Drift Rate             | Components on older semver       | 0 pinned to legacy        |
| MG-3   | Accumulated Profile Read Latency      | History array growth impact      | Flat < 100ms              |
| MG-4   | Ownership Violation Attempt Rate      | Sub-agent coding bugs            | Exactly 0                 |
| MG-5   | Taxonomy Ref Null Rate                | Future-Fit vocabulary coverage   | Decreasing over time      |
+--------+---------------------------------------+----------------------------------+---------------------------+
```

---

## 4. End-to-End Verification Commands

```bash
# 1. Tier 1 Pure Unit Tests (100% pass required)
pytest tests/test_scoring.py tests/test_candidate_profile.py -v

# 2. Candidate Profile Hard Gates (HG-1 to HG-6)
pytest tests/test_profile_*.py -v

# 3. Memory Module Hard Gates (G1 to G6 + Concurrency)
pytest tests/test_memory_*.py -v

# 4. Auto-Apply & FastMCP Protocol Integration
pytest tests/test_auto_apply.py tests/test_mcp_mesh.py -v

# 5. Full 10-Agent Simulation Suite (100 Opportunities)
python -m conductor.simulate --num-opportunities 100 --seed 42
```
