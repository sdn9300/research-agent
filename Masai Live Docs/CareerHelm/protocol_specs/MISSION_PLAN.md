# EDGEDASH ↔ MCP CHIEF OF STAFF: PROTOCOL MISSION PLAN
## Strategic Directives, Protocol Invariants, Target Service Level Objectives, and Governance

**Document ID:** PROTOCOL-MSN-v1.0  
**Status:** Approved Strategic Directive  
**Scope:** Model Context Protocol (FastMCP) Integration Contract & System Governance

---

## 1. Protocol Mission Statement

To establish a zero-trust, low-latency, bidirectional **Model Context Protocol (FastMCP)** bridge between **EdgeDash** (Market Intelligence) and **MCP Chief of Staff** (Executive Action), enabling seamless context injection, automated interview coordination, and closed-loop market feedback while maintaining total repository decoupling, strict parameter clamping, and absolute human approval control.

---

## 2. The Five Protocol Invariants

```
+---------------------------------------------------------------------------------------------------------+
|                                    THE 5 PROTOCOL INVARIANTS                                            |
|                                                                                                         |
|  [Invariant 1] Read-Only Tool Boundary      --> EdgeDash MCP server exposes ZERO write tools            |
|  [Invariant 2] Mandatory Approval Barrier   --> Chief of Staff sends zero emails without user click     |
|  [Invariant 3] Strict Parameter Clamping    --> All numeric/string inputs validated before query         |
|  [Invariant 4] Stale-Beats-Wrong Sync       --> Only read from verified passing EdgeDash cycles         |
|  [Invariant 5] Circuit Breaker Fallback     --> Local persona fallback if MCP server is offline         |
+---------------------------------------------------------------------------------------------------------+
```

### Invariant 1: Pure Read-Only Tool Boundary
* The EdgeDash FastMCP server exposes strictly read-only query capabilities.
* Under no circumstances may an MCP tool permit data modification, raw SQL execution, table schema alteration, or deletion.
* All data writes in EdgeDash remain exclusively inside its internal scheduled loop.

### Invariant 2: Mandatory Physical Approval Barrier
* The protocol prohibits autonomous external side effects.
* While the protocol facilitates automated draft generation and calendar slot conflict checking, the final execution token is generated exclusively by a physical human button click in `approval_gate.py`.

### Invariant 3: Strict Parameter Clamping & Type Validation
* Model-supplied tool arguments are treated as untrusted input.
* Numerical parameters are strictly clamped to operational boundaries (e.g., `limit` clamped between $1 \dots 25$, `days` clamped between $1 \dots 90$).
* Skill strings are normalized via `canonical()` before reaching query engines; unrecognized skills safely return empty datasets rather than raising exceptions.

### Invariant 4: "Stale Beats Wrong" State Synchronization
* When Chief of Staff queries EdgeDash via MCP, the query engine resolves records exclusively from the last **verified passing cycle**.
* If EdgeDash's Verifier agent flagged the most recent cycle as `Degraded`, the MCP tools automatically serve the prior verified snapshot, preventing corrupt data from informing recruiter communications.

### Invariant 5: Circuit Breaker & Graceful Local Fallback
* If the EdgeDash FastMCP server is unreachable, unresponsive (timeout $> 500$ms), or returns an error, Chief of Staff's `context_builder.py` trips a local circuit breaker.
* The system logs a warning and seamlessly falls back to static persona files (`past_replies.json`, `tone_profile.json`), ensuring zero downtime for inbox operations.

---

## 3. Service Level Objectives (SLOs) & Quality Attributes

```
+------------------------------------+------------------------------------+---------------------+
| Metric / Attribute                 | Service Level Objective (SLO)      | Measurement Method  |
+------------------------------------+------------------------------------+---------------------+
| Protocol Latency (p95)             | < 200 ms                           | Client-side timer   |
| Schema Conformance                 | 100% compliant with JSON-RPC 2.0   | Automated fuzz tests|
| Availability / Uptime              | 99.9% local availability           | Process supervisor  |
| Circuit Breaker Recovery           | Resumes normal flow < 1s on restore| Health check probe  |
| False Action Rate                  | 0.00% unapproved external sends    | Audit log audit     |
+------------------------------------+------------------------------------+---------------------+
```

---

## 4. Architectural Quality Attributes

1. **Decoupling:** Neither project imports code or Python packages from the other. All communication is decoupled via standard FastMCP JSON-RPC over STDIO or local SSE.
2. **Observability:** Every MCP tool call, argument payload, execution duration, and return status is immutably recorded in `action_log.json` and `query_log`.
3. **Auditability:** Every drafted email enriched with EdgeDash intelligence includes metadata citations linking back to specific `listing_id` records in the database.
