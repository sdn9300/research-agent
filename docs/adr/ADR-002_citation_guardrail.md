# Architecture Decision Record 002: Citation-Grounded Guardrail Pattern

## Status
Accepted

## Context
Hallucination is a primary failure mode in LLM synthesis. When creating corporate profiles (CompanyBriefs) for candidates to review prior to interviews, it is crucial that the details are completely factual and verifiable. 

## Decision
We generalized and applied the citation-grounded verification pattern (originally validated in the AlignResume component) to the research synthesis workflow. The system matches every claim made in the generated summary, tech signals, news, and culture notes against retrieved chunks using token overlap checks and strict string matching. Any ungrounded claim is flagged and stripped, returning a sanitized "partial_output" with warning flags rather than letting fabrication slip through.

## Rationale
Consistency across portfolio modules is prioritized. Generalizing a proven guardrail pattern decreases overall system complexity, simplifies debugging, and guarantees the security of generated content. In addition, prioritizing high precision over high recall directly satisfies NFR-1 (correctness over completeness).

## Trade-offs
- **Completeness**: Stricter guardrails reduce output length and coverage in low-source-coverage cases.
- **Verification Cost**: The self-check logic increases execution overhead, adding to total runtime latency.
- **Mitigation**: We allow a capped single-retry loop back to synthesis to give the model a chance to regenerate and auto-correct itself, mitigating complete failures.
