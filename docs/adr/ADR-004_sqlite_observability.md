# Architecture Decision Record 004: Local SQLite Telemetry and Observability Store

## Status
Accepted

## Context
Each run of the Research Agent graph must log execution metadata (e.g. latency, company name, prompt version, tool usage, chunk IDs, and citations) to allow offline evaluations, performance debugging, and cost-auditing.

## Decision
We implemented a self-hosted, local SQLite logger (`observability/logger.py`) to record all telemetry metadata directly on disk, avoiding managed external SaaS products.

## Rationale
1. **Cost Bounded**: Zero operational cost, directly satisfying NFR-3.
2. **Offline Reproducibility**: Keeps all telemetry inside the workspace, allowing evaluation and checking scripts to run offline.
3. **Data Ownership**: Retains full metadata logs in a queryable database file (`logger.db`), which is ideal for showcasing results.

## Trade-offs
- **Analysis UI**: Lacks built-in dashboarding compared to specialized tools like Langfuse or Arize Phoenix.
- **Mitigation**: We serialize outputs into JSON and SQLite, making it trivial to build simple reporting scripts (such as `specs/notes/cost_latency_report.md`) or write a migration script to forward these logs to an external trace collector when needed.
