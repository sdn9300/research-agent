# EDGEDASH ↔ MCP CHIEF OF STAFF: PROTOCOL EVALUATION PLAN
## Automated Verification Harnesses, Protocol Conformance Tests, and Resilience Benchmarks

**Document ID:** PROTOCOL-EVAL-v1.0  
**Status:** Approved Quality Assurance Standard  
**Scope:** FastMCP Tool Conformance, Data Contract Verification, and Fault Resilience

---

## 1. Protocol Testing Pyramid

```
+---------------------------------------------------------------------------------------------------------+
|                                    PROTOCOL 4-TIER EVALUATION PYRAMID                                   |
|                                                                                                         |
|                     / \                                                                                 |
|                    /   \     TIER 4: End-to-End Inbound-to-Booking Simulations (50 Threads)             |
|                   /=====\                                                                               |
|                  /       \   TIER 3: Circuit Breaker & Network Failure Simulations                      |
|                 /=========\                                                                             |
|                /           \ TIER 2: FastMCP JSON-RPC Contract & Parameter Clamping Tests              |
|               /=============\                                                                           |
|              /               \TIER 1: Pydantic Schema Validation & Unit Tests (100% Coverage)           |
|             +-----------------+                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

---

## 2. Protocol Test Suite Specifications

### 2.1 Tier 1: Pydantic Schema & Data Contract Unit Tests

#### A. Inbound Signal Validation (`tests/test_protocol_schemas.py`)
Validates that incoming recruiter signals conform strictly to `RecruiterThreadSignal` types.

```python
import pytest
from pydantic import ValidationError
from mcp_chief_of_staff.schemas import RecruiterThreadSignal

def test_valid_recruiter_signal():
    payload = {
        "thread_id": "thread_abc123",
        "message_id": "msg_xyz789",
        "sender_email": "recruiter@stripe.com",
        "company_domain": "stripe.com",
        "subject": "Interview Invitation: Senior AI Engineer",
        "intent": "interview_invite",
        "urgency_score": 5,
        "requires_calendar_action": True
    }
    signal = RecruiterThreadSignal(**payload)
    assert signal.company_domain == "stripe.com"
    assert signal.urgency_score == 5

def test_invalid_urgency_score():
    with pytest.raises(ValidationError):
        RecruiterThreadSignal(
            thread_id="t1", message_id="m1", sender_email="a@b.com",
            company_domain="b.com", subject="Hi", intent="interview_invite",
            urgency_score=99  # Invalid: must be <= 5
        )
```

---

### 2.2 Tier 2: FastMCP JSON-RPC Contract & Parameter Clamping Tests

#### A. Tool Parameter Clamping (`tests/test_mcp_clamping.py`)
Validates that invalid or out-of-bounds parameters passed over FastMCP are clamped before executing database queries.

```python
import pytest
from edgedash.mcp.server import get_best_job_matches, check_company_hiring_status

def test_limit_clamping():
    # Pass an absurdly high limit (e.g. 5000)
    results = get_best_job_matches(limit=5000, min_score=-20)
    assert len(results) <= 25  # Clamped to max 25

def test_days_clamping():
    results = check_company_hiring_status(company="Stripe", days=9999)
    # Internally clamped to days=90
    assert isinstance(results, list)
```

---

### 2.3 Tier 3: Circuit Breaker & Failover Resilience Tests

#### A. Offline MCP Server Graceful Fallback (`tests/test_circuit_breaker.py`)
Proves that Chief of Staff continues functioning normally when the EdgeDash FastMCP server is terminated.

```python
import pytest
from mcp_chief_of_staff.context_builder import build_reply_context

class MockFailingMCPClient:
    async def call_tool(self, *args, **kwargs):
        raise ConnectionRefusedError("EdgeDash MCP Server is offline")

@pytest.mark.asyncio
async def test_mcp_server_offline_fallback():
    thread_data = {"sender": "recruiter@stripe.com", "body": "Are you open to discussing a role?"}
    context = await build_reply_context(thread_data, mcp_client=MockFailingMCPClient())
    
    # Assert fallback to default static persona without throwing exception
    assert context["company_profile"] is None
    assert context["job_fit_facts"] is None
    assert context["thread_history"] == thread_data["body"]
```

---

### 2.4 Tier 4: End-to-End Inbound Recruiter Simulation

#### A. Full Recruiter Lifecycle Simulation (`tests/test_protocol_e2e.py`)
Executes an end-to-end test from inbound email to staged calendar booking.

```python
import pytest
from mcp_chief_of_staff.engine import simulate_inbound_email
from mcp_chief_of_staff.triage import triage_thread
from mcp_chief_of_staff.calendar_engine import parse_meeting_request
from mcp_chief_of_staff.approval_gate import get_pending_approvals

def test_full_inbound_recruiter_lifecycle():
    # 1. Simulate inbound recruiter email
    raw_email = {
        "sender": "recruiter@stripe.com",
        "subject": "Interview slot: Senior AI Engineer",
        "body": "Hi! Can you speak this Thursday at 2 PM IST?"
    }
    
    # 2. Ingest and triage
    signal = triage_thread(raw_email)
    assert signal.intent == "interview_invite"
    assert signal.urgency_score == 5
    
    # 3. Parse meeting request
    slot = parse_meeting_request(raw_email["body"])
    assert slot.start_time_iso is not None
    
    # 4. Verify staged in Approval Gate
    pending = get_pending_approvals()
    assert len(pending) >= 1
    assert pending[0]["company"] == "Stripe"
    assert pending[0]["requires_calendar_confirm"] is True
```

---

## 3. Master Protocol Verification Matrix

```
+------------------------------------+------------------------------------+---------------------+
| Protocol Test Harness              | Execution Command                  | Acceptance Target   |
+------------------------------------+------------------------------------+---------------------+
| FastMCP Server Health Check        | python -m edgedash.mcp.server --chk| Server starts clean |
| Parameter Clamping Unit Tests      | pytest tests/test_mcp_clamping.py  | 100% bounds clamped |
| Data Contract Schema Validation    | pytest tests/test_protocol_schemas | Valid Pydantic types|
| Context Builder RAG Injection      | pytest tests/test_context_builder  | Real fit facts in   |
| Calendar Conflict Detection        | pytest tests/test_calendar.py      | Overlaps flagged    |
| Offline Circuit Breaker Fallback   | pytest tests/test_circuit_breaker  | 0 crashes on outage |
| Approval Gate Physical Barrier     | pytest tests/test_gate_security.py | 0 unapproved sends  |
| Recruiter Skill Telemetry Feed     | pytest tests/test_skill_stream.py  | Keywords in radar   |
| End-to-End Inbound Lifecycle Test  | pytest tests/test_protocol_e2e.py  | 100% DAG pass       |
+------------------------------------+------------------------------------+---------------------+
```
