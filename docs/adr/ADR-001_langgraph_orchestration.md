# Architecture Decision Record 001: LangGraph over linear chain orchestration

## Status
Accepted

## Context
The Research Agent must autonomously plan, search, scrape, retrieve, synthesize, and self-check company information. This agentic loop requires conditional branching (e.g. deciding whether to perform additional web searches based on source availability and tool-call budgets) and self-correction (e.g. retrying synthesis if the self-check node identifies ungrounded claims).

## Decision
We chose LangGraph's explicit state-machine model to coordinate execution nodes rather than a linear, single-pass pipeline (such as a sequential LangChain run).

## Rationale
A simple linear chain cannot easily model conditional logic or retry feedback loops as first-class, inspectable constructs. By modeling the control flow as a state machine where nodes represent distinct operations (`plan`, `search_scrape`, `retrieve`, `synthesize`, `self_check`) and edges dictate execution conditions, we achieve:
1. First-class observability of state transitions.
2. The ability to unit-test and validate individual nodes in isolation.
3. Decoupling of state and business logic, simplifying concurrency and execution control.

## Trade-offs
- **Complexity**: Higher initial overhead to define state schemas, schemas configuration, and execution boundaries.
- **Dependency**: Locks the orchestration layer to LangGraph/LangChain ecosystem constructs.
- **Mitigation**: The API surface exposed to the consumer (the Conductor) is hidden behind a simple standard schema class `AgentTask`.
