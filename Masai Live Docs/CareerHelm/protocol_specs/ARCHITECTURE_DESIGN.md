# EDGEDASH ↔ MCP CHIEF OF STAFF: DETAILED PROTOCOL ARCHITECTURE
## FastMCP Tool Server Specifications, Client Bindings, Canonical Data Contracts, and Security Architecture

**Document ID:** PROTOCOL-ARCH-v1.0  
**Status:** Approved Technical Architecture  
**Scope:** FastMCP Protocol Bindings & Integration Specification

---

## 1. Protocol Architecture & Topology

The communication bridge between **EdgeDash** and **MCP Chief of Staff** is powered by the **Model Context Protocol (FastMCP)** running over standard JSON-RPC 2.0 transport (STDIO or local Server-Sent Events / SSE).

```mermaid
flowchart LR
    subgraph EdgeDash_Server ["EdgeDash FastMCP Server (Provider)"]
        ED_DB[("EdgeDash Storage\n[Listings, Gaps, Verdicts]")] --> FastMCPServer["FastMCP Server\n(edgedash/mcp/server.py)"]
        FastMCPServer --> ToolReg["Tool Registry:\n- get_best_job_matches\n- get_skill_gap_analysis\n- get_skill_drilldown\n- check_company_hiring\n- get_market_skill_demand\n- get_system_status"]
    end

    subgraph FastMCP_Transport ["FastMCP Protocol Bridge (JSON-RPC 2.0 / STDIO / SSE)"]
        ToolReg <===="mcp.tool() calls & responses"====> MCPClient["Chief of Staff MCP Client\n(FastMCP Client Adapter)"]
    end

    subgraph ChiefOfStaff_Client ["MCP Chief of Staff (Consumer & Action Hub)"]
        MCPClient --> CB["context_builder.py\n(RAG Context Enrichment)"]
        CB --> DM["draft_machine.py\n(Tone-Aligned Reply Gen)"]
        DM --> AG["approval_gate.py\n(Human Approval Gate)"]
        
        Gmail["Inbound Recruiter Email"] --> Triage["triage.py\n(4-Tier Classification)"]
        Triage --> CB
        Triage -->|"Extracted Skill Keywords"| TelemetryStream[("Live Skill Stream\n(recruiter_mentions.json)")]
        
        Triage -->|"interview_invite"| CalEngine["calendar_engine.py\n(Conflict Checking)"]
        CalEngine --> AG
    end

    TelemetryStream -.->|"Periodic Batch Ingest"| ED_DB
```

---

## 2. FastMCP Tool Server Specifications (`edgedash/mcp/server.py`)

The EdgeDash FastMCP server registers 6 core tools:

### Tool 1: `get_best_job_matches`
* **Description:** Retrieves top-scoring job listings matching candidate profile with explainable reasons.
* **Input Parameters:**
  * `limit` (`int`, optional, default: 5): Maximum number of listings to return. Clamped to $[1, 25]$.
  * `min_score` (`int`, optional, default: 70): Minimum fit score threshold. Clamped to $[0, 100]$.
  * `company` (`str`, optional): Filter by target company name.
* **Return Schema (`list[dict]`):**
  ```json
  [
    {
      "listing_id": "3a8f9c1b",
      "company": "Stripe",
      "title": "Senior AI Infrastructure Engineer",
      "fit_score": 89,
      "fit_reason": "5/5 required skills · seniority exact · remote · posted 1d ago",
      "matched_skills": ["python", "fastapi", "langgraph", "kubernetes", "sql"],
      "missing_skills": ["kafka", "go"],
      "posted_at": "2026-08-26"
    }
  ]
  ```

### Tool 2: `get_skill_gap_analysis`
* **Description:** Retrieves top skill gaps ranked deterministically by weighted Opportunity Cost ($\sum \frac{\text{score}}{100}$).
* **Input Parameters:**
  * `limit` (`int`, optional, default: 5): Maximum gaps to return. Clamped to $[1, 15]$.
* **Return Schema (`list[dict]`):**
  ```json
  [
    {
      "skill": "kubernetes",
      "opportunity_cost": 24.1,
      "listings_blocked": 31,
      "mean_score": 79.2,
      "confidence": "high",
      "example_listing_ids": ["3a8f9c1b", "7e2a9f4c", "1b5d8e9a"]
    }
  ]
  ```

### Tool 3: `get_skill_drilldown`
* **Description:** Drills into a specific skill gap to retrieve the exact listings and companies blocked by it.
* **Input Parameters:**
  * `skill` (`str`, required): Name of the skill to investigate (canonicalized automatically).
* **Return Schema (`dict`):**
  ```json
  {
    "canonical_skill": "kubernetes",
    "opportunity_cost": 24.1,
    "total_listings_blocked": 31,
    "top_companies_requiring": ["Stripe", "Datadog", "OpenAI", "Anthropic"],
    "example_listings": [
      { "id": "3a8f9c1b", "company": "Stripe", "title": "Senior AI Infrastructure Engineer", "score": 89 }
    ]
  }
  ```

### Tool 4: `check_company_hiring_status`
* **Description:** Checks if a specific company has active postings in the market radar.
* **Input Parameters:**
  * `company` (`str`, required): Company name to search.
  * `days` (`int`, optional, default: 30): Max age of postings in days. Clamped to $[1, 90]$.
* **Return Schema (`list[dict]`):** List of active postings from that company.

### Tool 5: `get_market_skill_demand`
* **Description:** Returns frequency of a skill across required vs. nice-to-have specifications.
* **Input Parameters:**
  * `skill` (`str`, required): Target skill name.
* **Return Schema (`dict`):** `{"skill": "fastapi", "required_count": 42, "nice_to_have_count": 18}`

### Tool 6: `get_system_status`
* **Description:** Returns current EdgeDash loop health, last passing cycle timestamp, and total listings.
* **Return Schema (`dict`):** `{"last_cycle_status": "pass", "last_fetch_at": "...", "total_listings": 142}`

---

## 3. Chief of Staff Client Integration Layer

### 3.1 Context Builder RAG Hook (`mcp_chief_of_staff/context_builder.py`)

When an inbound email is triaged, `context_builder.py` invokes EdgeDash tools to enrich draft prompts:

```python
async def build_reply_context(thread_data: dict, mcp_client) -> dict:
    sender_domain = extract_domain(thread_data["sender"])
    company_name = resolve_company_name(sender_domain)
    
    # 1. Query EdgeDash for company-specific postings
    company_matches = await mcp_client.call_tool(
        "EdgeDash-Career-Intelligence", 
        "check_company_hiring_status", 
        {"company": company_name, "days": 30}
    )
    
    # 2. Query top skill profile
    top_matches = await mcp_client.call_tool(
        "EdgeDash-Career-Intelligence", 
        "get_best_job_matches", 
        {"limit": 1, "company": company_name}
    )
    
    context = {
        "company_profile": company_matches,
        "job_fit_facts": top_matches[0] if top_matches else None,
        "thread_history": thread_data["body"]
    }
    return context
```

---

## 4. Canonical Data Contracts

### 4.1 Inbound Recruiter Thread Contract (`RecruiterThreadSignal`)

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional, List

class RecruiterThreadSignal(BaseModel):
    thread_id: str
    message_id: str
    sender_email: str
    company_domain: str
    subject: str
    intent: Literal[
        "interview_invite", "scheduling_link", "offer_extended",
        "technical_question", "soft_rejection", "hard_rejection", "general_inquiry"
    ]
    extracted_skills: List[str] = Field(default_factory=list)
    proposed_slot_iso: Optional[str] = None
    urgency_score: int = Field(ge=1, le=5)
    requires_calendar_action: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 4.2 Calendar Booking Event Contract (`MeetingBookingEvent`)

```python
class MeetingBookingEvent(BaseModel):
    event_id: str
    thread_id: str
    company_name: str
    role_title: str
    start_time_iso: str
    duration_minutes: int = 30
    attendees: List[str]
    calendar_html_link: str
    status: Literal["CONFIRMED", "CONFLICT_DETECTED", "SIMULATED"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 4.3 Live Recruiter Skill Telemetry Contract (`SkillTelemetryFeed`)

```python
class SkillTelemetryEntry(BaseModel):
    timestamp: str
    source_company: str
    thread_id: str
    skill_keywords: List[str]
    intent_context: str
```

---

## 5. Security & Authentication Architecture

1. **Local Transport Security:** FastMCP operates over local STDIO / localhost SSE. No public open ports are exposed.
2. **Untrusted Parameter Clamping:** The MCP server rejects raw string interpolation into queries; all integers are clamped, and strings are canonicalized against whitelist indices.
3. **Approval Gate Token Barrier:** The execution endpoints in `approval_gate.py` enforce a cryptographic one-time action token (`approval_token`) generated exclusively upon user physical button press.
