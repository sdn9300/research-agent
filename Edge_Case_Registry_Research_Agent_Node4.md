# Edge Case Registry: Research Agent [Node 4]

*Quality Assurance Document — supplements `speckit.validate` phase*
*System: AI-Native Job Agent Architecture*
*Governing documents: Research_Agent_Problem_Statement.md, Research_Agent_Architecture_Design_Plan.md, Research_Agent_Evaluation_Plan.md*

---

## 1. Purpose of This Document

The Evaluation Plan measures aggregate correctness against ground truth. This document catalogs the *specific failure modes* that aggregate scoring can hide — individual scenarios where the agent could behave incorrectly in a way a high accuracy percentage would not surface. Each edge case is categorized, given an expected (correct) behavior, and assigned a detection method. This follows the same registry discipline already established for the Altitude & Heat Adaptation project's 37-scenario edge case catalog.

---

## 2. Categories Overview

| Category | Concern | Count |
|---|---|---|
| A — Input Malformation | Bad data arriving from Gleaner | 6 |
| B — Source Coverage Failures | Web has insufficient/conflicting information | 7 |
| C — Retrieval/Embedding Failures | RAG pipeline mechanics break | 6 |
| D — Synthesis & Hallucination | LLM generates ungrounded or distorted claims | 8 |
| E — Self-Check Guardrail Failures | The guardrail itself fails its job | 5 |
| F — Cost/Latency/Resource Boundaries | Agent behaves correctly but inefficiently | 5 |
| **Total** | | **37** |

---

## Category A — Input Malformation

| ID | Scenario | Expected Behavior | Detection Method |
|---|---|---|---|
| A-1 | Company name has inconsistent casing/spacing (e.g., "google" vs "Google LLC") | Agent normalizes for search but preserves original in output for traceability | Manual test with 3 casing variants of the same company |
| A-2 | Company name is ambiguous (e.g., "Apex," matching multiple real companies) | Agent uses JD context to disambiguate; if still ambiguous, flags low confidence rather than guessing | Adversarial eval case with a deliberately ambiguous name |
| A-3 | Job description field is empty or null | Agent proceeds on company name alone; does not crash | Unit test with null JD field |
| A-4 | Company name contains special characters or non-Latin script | Search/scrape tools handle encoding correctly; no silent truncation | Unit test with a non-English company name |
| A-5 | `AgentTask` payload is malformed (missing required field) | Agent rejects the task at the contract boundary with a clear error, not a downstream crash | Unit test feeding an invalid `AgentTask` |
| A-6 | Duplicate task submitted twice (same company, same task_id collision) | Idempotent handling — second submission either returns cached result or is rejected, not silently reprocessed at full cost | Unit test submitting the same `task_id` twice |

---

## Category B — Source Coverage Failures

| ID | Scenario | Expected Behavior | Detection Method |
|---|---|---|---|
| B-1 | Company has near-zero public web presence (very early-stage startup) | Agent returns a brief with explicit low-confidence flags rather than fabricating | Adversarial eval subset (per Evaluation Plan §4) |
| B-2 | Company name collides with a much more famous unrelated entity (search results dominated by the wrong company) | Agent uses JD/industry context to filter results; flags uncertainty if filtering fails | Adversarial test case with a deliberately generic/colliding name |
| B-3 | All retrieved sources are outdated (>2 years old, no recent news) | Brief reflects this explicitly ("no recent developments found") rather than presenting stale info as current | Manual review of a company with known low recent coverage |
| B-4 | Sources directly contradict each other (e.g., two articles cite different funding amounts) | Agent surfaces the conflict explicitly rather than picking one arbitrarily | Constructed test case with two deliberately conflicting source snippets |
| B-5 | Company website is the only available source (no independent third-party coverage) | Brief flags that information is self-reported/unverified by independent sources | Manual review case |
| B-6 | Scrape returns a paywall/login wall instead of content | Tool layer detects non-content response and does not pass it to embedding as if it were real text | Unit test against a known paywalled URL |
| B-7 | Company has rebranded/changed names recently | Agent may retrieve information under both old and new names; output should reconcile rather than presenting as two separate entities | Manual test with a known recently-renamed company |

---

## Category C — Retrieval/Embedding Failures

| ID | Scenario | Expected Behavior | Detection Method |
|---|---|---|---|
| C-1 | Scraped page is mostly boilerplate/navigation text, minimal actual content | Chunking/filtering removes low-signal boilerplate before embedding | Manual inspection of chunks generated from a content-sparse page |
| C-2 | Chunk size splits a fact across two chunks (e.g., "founded in" / "2019" separated) | Chunking strategy uses sufficient overlap to avoid splitting atomic facts | Constructed test with a known fact near a chunk boundary |
| C-3 | Vector similarity search returns chunks that are topically similar but factually irrelevant | Retriever node's top-k results are spot-checked for relevance, not just vector distance | Manual review of retrieved chunks vs. query intent |
| C-4 | Embedding fails silently (API timeout, malformed input) | Pipeline raises a visible error/log entry, does not proceed with an empty embedding as if it succeeded | Unit test forcing an embedding API failure |
| C-5 | Vector store grows stale (same company researched twice, weeks apart, old chunks still present) | Either re-scrape policy or explicit staleness flag — old chunks should not silently override fresher ones | Manual test re-running the same company after modifying source content |
| C-6 | Two different companies have textually similar names, causing cross-contamination in retrieval | Chunk metadata's `company_name` field is enforced as a hard filter, not just a soft signal, during retrieval | Constructed test with two similarly-named companies in the store simultaneously |

---

## Category D — Synthesis & Hallucination

| ID | Scenario | Expected Behavior | Detection Method |
|---|---|---|---|
| D-1 | Model fills a schema field (e.g., `funding_stage`) with a plausible-sounding guess when no source supports it | Field is left null/flagged rather than populated with an unsupported guess | Adversarial eval — deliberately omit funding info from sources, check output |
| D-2 | Model paraphrases a source so loosely that the "citation" no longer actually supports the claim | Self-check must verify semantic alignment between claim and cited chunk, not just that a citation ID exists | Adversarial test: insert a chunk and a claim that cites it but distorts its meaning |
| D-3 | Model combines two unrelated facts from different chunks into one fabricated composite claim | Self-check rejects claims that require synthesis across chunks unless explicitly designed to allow it | Constructed test combining two real but unrelated chunks |
| D-4 | Model states a number with false precision (e.g., "exactly 1,243 employees" when source says "over 1,000") | Self-check or synthesis prompt enforces that stated precision cannot exceed source precision | Manual review of numeric claims against source wording |
| D-5 | Model produces a confident tone on a low-confidence finding | Confidence flags are tied to source coverage programmatically, not left to the model's tone alone | Manual review of language/hedging vs. actual source strength |
| D-6 | Model includes outdated information without temporal framing (e.g., reporting a past CEO as current) | Synthesis prompt requires temporal qualifiers when source dates are not current | Test case with a source containing outdated leadership info |
| D-7 | Model invents a citation ID that doesn't exist in the retrieved set | Self-check validates every citation ID against the actual retrieved chunk set, not just checks "is a citation present" | Adversarial test forcing a malformed/invented citation ID |
| D-8 | Model produces a brief with internally inconsistent claims (e.g., two different founding years in different sections) | Self-check includes an internal consistency pass across the full brief, not just per-claim citation checks | Constructed test with conflicting claims injected into a draft |

---

## Category E — Self-Check Guardrail Failures

| ID | Scenario | Expected Behavior | Detection Method |
|---|---|---|---|
| E-1 | Self-check is too lenient, passes an ungrounded claim | Caught via adversarial eval subset before trusting the node in production | Mission Plan Gate 3 adversarial test (already specified) |
| E-2 | Self-check is too strict, rejects a correctly-cited claim due to a parsing bug | Manual review of rejected claims periodically, not just accepted ones | Spot-check a sample of stripped/rejected claims for false positives |
| E-3 | Self-check retry loop (capped at one retry per Architecture Plan §5) produces a worse second draft than the first | Compare pre- and post-retry drafts in logs; if retry consistently degrades quality, the retry mechanism itself needs revision | Logged comparison across multiple eval runs |
| E-4 | Self-check passes a brief with zero citations because there were zero claims to check (empty brief edge case) | An empty/near-empty brief should be flagged as a failure mode, not pass by vacuous truth | Unit test with a deliberately near-empty draft |
| E-5 | Self-check node itself times out or errors, and the system defaults to passing the unchecked draft | Fail-closed, not fail-open — a self-check error must block output, never silently bypass the guardrail | Unit test forcing a self-check node exception |

---

## Category F — Cost/Latency/Resource Boundaries

| ID | Scenario | Expected Behavior | Detection Method |
|---|---|---|---|
| F-1 | `plan` node requests more tool calls than the budget allows | Hard cap enforced at the tool-layer level, not just a suggestion in the prompt | Unit test forcing an over-budget plan |
| F-2 | A single scrape call hangs (slow/unresponsive site) | Timeout enforced; agent proceeds with partial sources rather than hanging indefinitely | Unit test against a deliberately slow/mock endpoint |
| F-3 | Cost per run spikes anomalously on one company (e.g., unusually long scraped pages) | Anomaly flagged in observability logs for investigation, per Evaluation Plan §5.4 | Logged cost outlier review |
| F-4 | Concurrent task submissions from Conductor exceed available rate limits (Firecrawl/Groq) | Agent surfaces a rate-limit failure clearly via `AgentTask.status: failed`, not a generic crash | Load test with simulated concurrent task submission |
| F-5 | Eval suite itself becomes slow/expensive to run repeatedly in CI as the fact-set grows | A documented ceiling on eval-set size vs. CI time budget, revisited if exceeded | Time the full eval suite run, document against CI budget |

---

## 3. Severity Classification

| Severity | Definition | Examples |
|---|---|---|
| **Critical** | Could cause a fabricated claim to reach a downstream agent undetected | D-1, D-2, D-3, D-7, E-1, E-5 |
| **High** | Could cause incorrect or misleading output without necessarily being a fabrication | B-2, B-4, D-4, D-5, D-6, D-8 |
| **Medium** | Degrades quality or efficiency but is self-correcting or visibly flagged | A-2, B-1, B-3, C-3, C-5, F-3 |
| **Low** | Operational/robustness issues unlikely to affect output correctness | A-1, A-4, C-1, F-2 |

**Testing priority rule:** All **Critical** severity cases must have a passing adversarial test before Mission Plan Gate 4 is declared met — these are non-negotiable per the zero-tolerance citation integrity standard already established in the Evaluation Plan.

---

## 4. Coverage Mapping to Evaluation Plan

| Evaluation Plan dimension | Edge case categories covered |
|---|---|
| Factual Accuracy | B, C, D |
| Citation Integrity | D, E |
| Confidence Calibration | B, D-5 |
| Cost Efficiency | F |
| Latency | F |
| Regression Stability | All categories, via CI re-run on every change |

---

## 5. Living Document Note

This registry is not exhaustive at first writing — per the same discipline applied to the Altitude & Heat Adaptation project, new edge cases discovered during Phase 2/3 implementation or post-deployment use should be appended here with an incrementing ID within their category, not discarded informally. Any edge case that causes an actual failure during eval or manual testing must be added here retroactively if not already present, closing the gap between "what we anticipated" and "what actually broke."

---

## 6. Relationship to Other Documents

| Document | Role |
|---|---|
| Research_Agent_Problem_Statement.md | Defines the correctness bar these edge cases test against |
| Research_Agent_Architecture_Design_Plan.md | Identifies the component boundaries (tool layer, self-check, etc.) each edge case targets |
| Research_Agent_Evaluation_Plan.md | This registry supplies the adversarial/stress test cases referenced there |
| Research_Agent_Implementation_Plan.md | Critical-severity cases should map to explicit unit/adversarial tests within the relevant task (e.g., D-7 → T2.6) |

---

*Document status: Edge Case Registry complete — 37 scenarios across 6 categories. Living document, append-only for new discoveries.*
