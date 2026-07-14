# T4.3 Walkthrough: Self-Administered Interview Readiness

This checklist serves as a walkthrough guideline to explain the Research Agent architecture from first principles.

## Interview Readiness Verification

1. **How is the control flow managed?**
   - Managed via `graph/build.py` utilizing the `ResearchAgentGraph` class containing LangGraph state variables.
   - It transitions from `plan` -> `search_scrape` -> `retrieve` -> `synthesize` -> `self_check` -> `END`.

2. **How are hallucination guardrails enforced?**
   - The `self_check` node runs grounding checks against the retrieved chunks matching token sets. Any unsupported claims are discarded, and warning flags are raised under `confidence_flags`.

3. **How does the system ensure finite execution?**
   - A `retry_count` limit is capped at 1. If self-check fails, it cycles back to synthesize exactly once; on a secondary failure, it exits with the partial brief flagged rather than looping indefinitely.

4. **What are the data interface contracts?**
   - The primary input/output boundary uses `schemas/agent_task.py` and `schemas/company_brief.py` models, preventing leakage of graph state internals to Conductor.
