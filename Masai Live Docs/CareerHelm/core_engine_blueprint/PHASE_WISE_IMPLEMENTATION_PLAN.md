# EDGEDASH CORE ENGINE: PHASE-WISE IMPLEMENTATION PLAN
## Master Roadmap, 8 Session Deliverables, CLI Commands, and Milestone Verification Gates

**Document ID:** EDGEDASH-CORE-IMPL-v1.0  
**Status:** Approved Implementation Schedule  
**Timeline:** 4-Week Phased Curriculum (8 Core Sessions)

---

## 1. Master Implementation Roadmap

```mermaid
gantt
    title EdgeDash Core Engine Phased Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Week 1: The Radar
    Session 1.1: Steering, Config & Storage Skeleton :w1_1, 2026-09-01, 2d
    Session 1.2: Source Layer, Real Fetcher & Secrets :w1_2, 2026-09-03, 3d
    section Week 2: The Decoder
    Session 2.1: LLM Gateway, Fact Extractor & Scorer :w2_1, 2026-09-06, 3d
    Session 2.2: Skill Canonicalisation & Gap Analyzer :w2_2, 2026-09-09, 3d
    section Week 3: The Automator
    Session 3.1: State Reader, Pure Planner & Loop    :w3_1, 2026-09-12, 3d
    Session 3.2: Verifier Agent, Checks & Dashboard   :w3_2, 2026-09-15, 3d
    section Week 4: The Edge
    Session 4.1: Natural Language Query Tools & Router :w4_1, 2026-09-18, 3d
    Session 4.2: Automated Actions & Cloud Deployment :w4_2, 2026-09-21, 3d
```

---

## 2. Session-by-Session Implementation Specifications

### Week 1: Foundation & The Radar (Classes 1 & 2)

#### Session 1.1 (Class 1) — Steering File, Config & Storage Skeleton
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 1–8), `edgedash/config.py`, `edgedash/storage.py`, `edgedash/agents/base.py`, `edgedash/agents/mock_fetcher.py`, `edgedash/orchestrator.py`, `run_cycle.py`.
* **Key Tasks:**
  1. Initialize SQLite database creating `listings`, `skill_gaps`, and `cycle_log` tables.
  2. Implement `upsert_listings()` returning genuinely new row count via `INSERT OR IGNORE` on `SHA256(source + url)`.
  3. Implement `MockFetcher` generating 12 listings (4 identical across runs).
* **Verification:** Run `python run_cycle.py` twice; run 1 returns 12 new, run 2 returns 4 new (dedup proven).

#### Session 1.2 (Class 2) — Source Plugin Layer & Real Fetcher
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 9–14), `edgedash/sources/base.py`, `edgedash/sources/http.py`, `edgedash/sources/arbeitnow.py`, `edgedash/sources/apify.py`, `edgedash/agents/fetcher.py`, `edgedash/diagnose.py`, `.env.example`, `.gitignore`.
* **Key Tasks:**
  1. Build `http.py` with 10s timeout, exponential backoff (2 retries), User-Agent header, and 1 req/sec rate limit.
  2. Build `ArbeitnowSource` (no key) and `ApifySource` (token-guarded).
  3. Implement per-source `try/except` in `fetcher.py` ensuring failing sources log `failed` without crashing cycle.
* **Verification:** Accumulate 50+ live listings; simulate broken source URL; verify other sources complete cleanly.
* **Badge Unlocked: The Tracker.**

---

### Week 2: Intelligence & The Decoder (Classes 3 & 4)

#### Session 2.1 (Class 3) — Fact Extractor & Deterministic Scorer
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 15–21), `edgedash/llm.py`, `edgedash/agents/extractor.py`, `edgedash/scoring.py`, `edgedash/agents/scorer.py`, `edgedash/rescore.py`, `tests/test_scoring.py`.
* **Key Tasks:**
  1. Build `llm.py` with code-fence stripping, schema validation, rate-limiting (15 RPM), and smart error-feedback retry.
  2. Implement `extractor.py` reading JDs without candidate details; cache results against `hash(description)`.
  3. Implement pure arithmetic `score_listing()` combining 4 weighted components; build formula reason strings.
  4. Write `rescore.py` CLI allowing manual score invalidation without clearing extraction cache.
* **Verification:** `python -m edgedash.llm --check` passes; `pytest tests/test_scoring.py` passes 6 edge cases; determinism proven (`rescore --id` returns identical score); score spread $\ge 15$.

#### Session 2.2 (Class 4) — Skill Canonicalisation & Opportunity Cost Gap Analyzer
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 22–27), `edgedash/skills.py`, `edgedash/agents/gap_analyzer.py`, `edgedash/gaps.py`, `tests/test_skills.py`.
* **Key Tasks:**
  1. Build `canonical()` normalizing skills and mapping aliases from user-owned `skill_aliases` in `config.yaml`.
  2. Implement `python -m edgedash.skills --audit` identifying top 40 raw skills and singleton outliers.
  3. Implement `gap_analyzer.py` computing weighted Opportunity Cost ($\sum \frac{\text{score}}{100}$) with drillable listing IDs and timestamped snapshot history.
  4. Build `python -m edgedash.skills --suggest-aliases` (read-only LLM helper outputting YAML suggestions).
* **Verification:** `python -m edgedash.gaps` prints readable terminal table; snapshot appends without overwriting; Opportunity Cost ranking demonstrates divergence from raw counts.
* **Badge Unlocked: The Decoder.**

---

### Week 3: Autonomy & The Automator (Classes 5 & 6)

#### Session 3.1 (Class 5) — State-Driven Planning & Orchestration
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 28–33), `edgedash/state.py`, `edgedash/planning.py`, `edgedash/orchestrator.py`, `tests/test_planning.py`.
* **Key Tasks:**
  1. Implement `read_state(config, now)` taking `now` as parameter with cheap queries only.
  2. Implement pure `build_plan(state, config)` generating tasks with caller-enforced stop conditions (`max_items`, `max_seconds`).
  3. Render plan before execution; exit 0 cleanly on `nothing_to_do`.
  4. Add operational CLI flags: `--dry-run`, `--force <agent>`, `--explain`.
* **Verification:** Consecutive run reports all tasks skipped (`nothing_to_do`, 0 API calls, 40ms); `pytest tests/test_planning.py` passes 4 cases.

#### Session 3.2 (Class 6) — Verifier Agent & Streamlit Dashboard
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 34–39), `edgedash/checks.py`, `edgedash/agents/verifier.py`, `edgedash/verdicts.py`, `app.py`, `tests/test_checks.py`.
* **Key Tasks:**
  1. Implement 4 plausibility checks as pure functions (score spread, residuals, volume stability, gap consistency).
  2. Implement Verifier agent with 1 capped retry using stricter rubric; mark cycle `Degraded` on persistent failure.
  3. Build Streamlit dashboard (`app.py`) displaying 3 panels (Matches, Gaps, Activity Log) reading exclusively from the last passing cycle (*"Stale beats wrong"*).
* **Verification:** Simulated failure (flattening weights) triggers retry and marks cycle `Degraded`; dashboard preserves prior valid snapshot; `python -m edgedash.verdicts` displays historical checks.
* **Badge Unlocked: The Automator.**

---

### Week 4: Voice & The Edge (Classes 7 & 8)

#### Session 4.1 (Class 7) — Safe Natural Language Query Interface
* **Files Built:** `.kiro/steering/edgedash.md` (Rules 40–46), `edgedash/query/tools.py`, `edgedash/query/ask.py`, `tests/test_tools.py`, `tests/test_ask.py`.
* **Key Tasks:**
  1. Register 7 parameterized query tools with input validation and clamping (`companies_hiring`, `best_matches`, `top_gaps`, `gap_detail`, `trend`, `listing_count`, `skill_demand`).
  2. Implement two-call LLM pipeline (Route $\rightarrow$ Execute $\rightarrow$ Phrase); forbid model-generated SQL.
  3. Implement explicit refusal handling for out-of-scope questions.
  4. Add "Ask your data" section to `app.py` with 3 example buttons, session rate limiting (10 queries / 10 min), and daily cap (200/day).
* **Verification:** Out-of-scope prompt ("Should I take a pay cut?") returns static refusal listing capabilities; parameters clamped; underlying rows displayed with prose.

#### Session 4.2 (Class 8) — Production Automation & Cloud Deployment
* **Files Built:** `.github/workflows/daily_cycle.yml`, `Dockerfile`, `README.md`.
* **Key Tasks:**
  1. Configure GitHub Actions scheduled workflow executing headless cycles daily at 06:00 UTC.
  2. Migrate SQLite schema to hosted PostgreSQL (one-file change in `storage.py`).
  3. Deploy read-only Streamlit dashboard to Hugging Face Spaces.
* **Verification:** Daily workflow executes unattended; public URL accessible and updates autonomously.
* **Badge Unlocked: The Edge (Complete 4-Badge Certification).**
