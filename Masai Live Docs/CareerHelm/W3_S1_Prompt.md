# Class 5 Prompts â€” "The Orchestrator"
### Week 3 Â· Session 3.1 Â· EdgeDash Â· Proof of Ship, August Cohort

These are every prompt used in Class 5, in order. Paste them into **Kiro** one at a time.

**This session was 20 minutes, so the video moves fast and this file carries the commentary.**
**C5-P4 was not covered on camera** â€” it's self-study, ten minutes, and it's the one that makes
Thursday easier.

## Before you start

1. Your Class 4 repo open in Kiro, with `.kiro/steering/edgedash.md` containing rules 1â€“27.
2. `python run_cycle.py` runs the fetcher, scorer and gap analyzer clean.
3. A terminal open in the repo.

---

## The one idea this class is built on

> **A pipeline runs the same steps every time. An orchestrator reads state and decides what
> needs doing.**

Since session one there has been a file called `orchestrator.py` in your project, and it has
been lying to you. Here's what it does:

```
fetch()  â†’  score()  â†’  analyse()      # every time. regardless of anything.
```

That's a to-do list with a `for` loop around it. It was the right thing for week one â€” you
can't orchestrate agents that don't exist yet â€” but now all three exist and the fixed sequence
is costing you.

**Concretely.** It's 7 AM. You fetched two hours ago and got nothing new. Everything is scored.
Your gap report was computed twenty minutes ago. Your current code will fetch again, score
nothing, and recompute an identical report: **three API calls and a full table scan to change
nothing.**

Once that's on a schedule (Thursday), the waste isn't theoretical â€” it's your free tier, every
morning, forever.

### What "orchestration" actually means here

Two capabilities, and neither is exotic:

| | Pipeline (what you have) | Orchestrator (today) |
|---|---|---|
| **What runs** | All three, always | Only what state says is needed |
| **How much** | Whatever the agent decides internally | A stop condition set by the caller |
| **Skipping** | Not expressible | A first-class successful outcome |
| **Visibility** | You see what happened | You see what it *decided*, before it acts |

---

## PROMPT C5-P1 â€” Amend the steering file

**What it does:** Six rules for orchestration. Rules before code, fifth time.

```text
Update .kiro/steering/edgedash.md â€” add an ORCHESTRATION section to the
existing rules. Do not rewrite the rest of the file.

ORCHESTRATION:
28. The Orchestrator reads system state and decides which agents to run.
    It never runs a fixed sequence. Skipping an agent because there is no
    work for it is a SUCCESSFUL outcome, not a failure.
29. Every delegation carries an explicit goal and an explicit stop
    condition (max items, max duration). A sub-agent never decides its own
    limits â€” the Orchestrator sets them.
30. The Orchestrator never does an agent's work. It reads state,
    delegates, collects results, logs. No fetching, scoring, or analysis
    logic in the Orchestrator.
31. The Orchestrator prints and logs its PLAN before executing it â€”
    which agents will run, which are skipped, and the state value that
    caused each decision.
32. One sub-agent failing does not stop the cycle. Log the failure,
    continue with the remaining plan, and mark the cycle partial.
33. Every cycle writes exactly one summary row: what ran, what was
    skipped, why, duration per agent, and the outcome.

Then show me the diff.
```

**Check before moving on:** rules 1â€“27 intact, new section appended.

**Rule 28 is the class.** "Skipping is a success" sounds like a technicality and it isn't â€” if
your system can't express *"there was nothing to do and that's fine,"* then every quiet morning
looks like a malfunction and you'll stop reading your own logs.

**Rule 30 is the boundary that keeps this honest.** The Orchestrator coordinates and never does
the work. Without that rule it slowly accretes "just one quick check" logic and turns back into
a script over about three weeks. This is the same instinct as rule 2 (all DB access behind one
module) and rule 15 (all LLM calls behind one module): **one job per component, enforced in
writing.**

**Rule 29 is what makes unattended operation survivable.** An agent without a stop condition
runs until something else stops it â€” your quota, your bill, or the platform. Note the direction
of control: the *caller* sets the limit, not the agent. That's what puts every limit in one file
you can read instead of scattered across three.

---

## PROMPT C5-P2 â€” State and the plan

**What it does:** Two pure modules â€” read four numbers, then decide. No I/O in the decision, so
the decision logic of your whole system becomes unit-testable.

```text
Build state inspection and planning. Deterministic. No LLM anywhere â€”
this is arithmetic on timestamps and counts.

1. edgedash/state.py â€” `read_state(config, now) -> SystemState` with:
   - last_fetch_at, hours_since_fetch
   - unscored_count
   - gaps_computed_at, gaps_stale (true if any score is newer than the
     gap snapshot)
   - last_cycle_verdict, last_cycle_at
   `now` is a PARAMETER, never datetime.now() inside â€” so this is
   testable. Read through the storage module only, per rule 2. These must
   be cheap queries: counts and max(timestamp), no full table loads.

2. edgedash/planning.py â€” `build_plan(state, config) -> Plan` where a Plan
   is an ordered list of Task(agent_name, goal, stop_conditions, reason).
   Pure function of (state, config). No I/O at all.

   Decision rules, thresholds from config:
   - fetch    if hours_since_fetch >= fetch_interval_hours (default 6)
   - score    if unscored_count > 0
   - analyse  if gaps_stale, or gaps_computed_at is null
   - each Task carries stop_conditions from config:
       fetch:   max_pages, max_listings
       score:   max_items (reuse score_batch_size), max_seconds
       analyse: max_seconds
   - `reason` is a human-readable string naming the state value that
     caused the decision: "unscored_count=41" or
     "skipped: unscored_count=0"

   Skipped agents appear in the Plan as skipped WITH a reason â€” they are
   not silently absent, per rule 31.

3. `Plan.render() -> str` â€” a compact printable plan, one line per agent,
   showing goal, stop conditions and reason. This is what gets printed
   before execution.

4. Tests for build_plan: everything stale (all three run), nothing to do
   (all three skipped), only unscored listings, gaps stale but nothing
   unscored.

Show me build_plan and one rendered Plan for a "nothing to do" state.
```

**Check before moving on:** `python -m pytest tests/test_planning.py -q` green, four cases.

**Why `build_plan` is a pure function.** It takes state and config and returns a plan â€” no
database, no clock, no network. That means **the decision logic of your entire system is
unit-testable**, which is unusual and worth appreciating. You can assert "given 41 unscored
listings and a fetch 2 hours ago, the plan is score-only" without touching a database.

This is the third time this month the same trick has appeared: `score_listing` (Class 3),
`canonical` (Class 4), and now `build_plan`. **Push the clock, the network and the database to
the edges; keep the logic pure in the middle.** It's the single most useful structural habit in
this whole curriculum.

**Why skipped agents stay in the plan.** An agent that's silently absent from the log looks
exactly like an agent that crashed. You will not enjoy telling those apart at 7 AM. A skip with
`"skipped: unscored_count=0"` attached is self-explaining.

**Why thresholds are in config.** Six hours between fetches is a guess â€” yours might be twelve,
or one. The point isn't the number, it's that it's a number you can change rather than a
condition buried in an `if`.

---

## PROMPT C5-P3 â€” The real Orchestrator

**What it does:** Replaces the fixed sequence. This is the file you've been pretending you had.

```text
Rewrite the Orchestrator to be state-driven, per rules 28-33.

edgedash/orchestrator.py â€” replace the fixed sequence:

1. Read state via state.read_state, build a plan via planning.build_plan.
2. PRINT the rendered plan before executing anything (rule 31).
3. Execute only the tasks in the plan, in order. Pass each Task's goal and
   stop_conditions to the agent â€” agents must now accept and RESPECT the
   stop conditions rather than using their own internal limits.
4. Per rule 32, wrap each task in try/except: log the failure, continue
   with the remaining tasks, mark the cycle "partial".
5. Per rule 33, write exactly one cycle summary row: plan, what ran, what
   was skipped with reasons, per-agent duration, outcome
   (complete | partial | nothing_to_do).
6. Cycle outcome "nothing_to_do" when the plan is entirely skips. This is
   a SUCCESS, not an error â€” exit code 0, no warnings.
7. Keep the agent registry exactly as it is. The Orchestrator resolves
   agents by name from the registry and knows nothing else about them.

Update the three agents minimally to accept stop_conditions. Do NOT
change their internal logic beyond respecting the limits they're given.

Then tell me: what would I change to add a fourth agent? It should be a
registry entry plus a decision rule in build_plan, and nothing else.
```

**Check before moving on:** read Kiro's answer to that final question. **If it says anything
more than "a registry entry plus a decision rule," the abstraction leaked** â€” say so and have it
fixed. That's a real finding, not a nitpick, and Thursday's Verifier is the fourth agent that
will test it.

**Point 6 matters more than it looks.** A cycle that does nothing exits 0 with no warnings. If
"nothing to do" prints a warning, you'll train yourself to ignore your own logs within about
four days â€” and then you'll miss the warning that mattered. **Reserve alarm for things that are
actually wrong.**

**Note what point 7 protects.** The registry from Class 1 is now on its fifth week of paying
off. The Orchestrator resolves agents by name and knows nothing else about them, which is why
adding the Verifier on Thursday is a one-line change.

---

## PROMPT C5-P4 â€” Dry run and force flags (self-study â€” not in the video)

**What it does:** Two operational flags you'll want the moment this runs on a schedule.
**Not covered on camera.**

```text
Add two operational flags to run_cycle.py.

1. `--dry-run`
   Read state, build the plan, print it, and EXIT WITHOUT EXECUTING
   anything. No writes, no API calls, exit code 0. This is how I check
   what a cycle would do before letting it do it.

2. `--force <agent>` (repeatable)
   Add the named agent to the plan even if state says it should be
   skipped, with reason "forced by operator". Everything else still
   follows normal planning rules.
   Print a clear warning that the plan was manually overridden, and record
   the override in the cycle summary row so it's visible in the log later.

3. `--explain`
   Print the full SystemState â€” every value read, with its timestamp â€”
   next to the decision each value drove. This is the debugging tool for
   "why did it skip that?"

None of these change planning logic. build_plan stays a pure function;
--force adds to its output, it does not alter its rules.
```

**Why this is worth ten minutes.** From Thursday your cycle runs on a schedule, unattended.
`--dry-run` is how you check a config change without waiting for tomorrow morning, and
`--explain` is how you answer "why did it skip that?" without adding print statements to
production code.

**Note the constraint in the last paragraph:** `--force` adds to the plan's output rather than
changing `build_plan`'s rules. Keep the pure function pure â€” the moment operator flags start
mutating the decision logic, your tests stop describing what actually runs.

---

## Your assignment

**Due Sunday** â€” this is the first half of week 3; Thursday's Verifier completes it:

- [ ] State-driven Orchestrator running â€” no fixed sequence anywhere
- [ ] `read_state` taking `now` as a parameter, using cheap queries only
- [ ] `build_plan` a pure function, with **4+ tests** including the nothing-to-do case
- [ ] **Stop conditions on all three delegations**, set by the Orchestrator from config
- [ ] The plan **printed before execution**, every cycle
- [ ] Skipped agents in the plan **with reasons**, not silently absent
- [ ] `nothing_to_do` as a successful outcome â€” exit 0, no warnings
- [ ] One summary row per cycle
- [ ] **Two runs, one screenshot** â€” see below
- [ ] 2â€“3 minute walkthrough video
- [ ] Submit GitHub repo link + video

### Two runs, one screenshot

Run your cycle twice in a row and film both plans. First run does work. **Second run skips
everything and says why.**

```bash
python run_cycle.py     # does work
python run_cycle.py     # nothing to do â€” 0 API calls, ~40ms
```

That's the whole lesson in one screenshot, and the second run is the one that matters: a system
that knows there's nothing to do is reading its own state rather than following instructions.

### What today did *not* do

Worth being honest with yourself about. Nothing today made your system smarter â€” your scores are
identical, your gap report is identical. What changed is that it became **cheap and legible**: it
does the minimum work required and it explains its decisions.

Those are the two properties that make unattended operation survivable, which is Thursday and
then week 4. **Boring wins are the ones that let a system run for a month without you.**

**Badge progress:** The Automator â€” Thursday's Verifier completes it.

---

## Fixing common problems

Paste these as follow-ups. Describe the symptom, not your guess at the cause.

**Every agent runs every cycle, even with nothing to do:**
```text
My cycle runs all three agents even on a second consecutive run when there
should be nothing to do. Print the full SystemState that was read, then the
Plan that was built from it, showing the threshold each decision was
compared against. I need to see whether state is being read wrongly, or the
thresholds are wrong, or build_plan is ignoring state entirely.
```

**"Nothing to do" is being treated as an error:**
```text
A cycle with an empty plan exits non-zero or logs a warning. Rule 28 says
skipping because there is no work is a SUCCESSFUL outcome. Show me the exit
code and log-level logic at the end of the cycle and fix it so nothing_to_do
is exit 0 at info level, with no warnings.
```

**Agents ignore their stop conditions:**
```text
I passed max_items to the Scorer but it processed more than that. Rule 29
says the Orchestrator sets the limits and the sub-agent respects them. Show
me where the Task's stop_conditions are passed in and where the agent reads
them, and confirm the agent is not falling back to its own internal default.
Then prove it with a stop condition of 3.
```

**`build_plan` isn't testable / reads the database:**
```text
build_plan appears to touch the database or the clock. It must be a pure
function of (state, config) with no I/O â€” that's what makes the decision
logic testable. Show me every import and call in planning.py and move any
I/O into state.py where it belongs.
```

**gaps_stale is always true (or always false):**
```text
My gaps_stale flag never changes. Print gaps_computed_at and the max
scored_at timestamp side by side, with their types. I suspect a timezone
mismatch, a null being compared, or string-vs-datetime comparison. Tell me
which it was rather than adding a workaround.
```

**One agent failing kills the cycle (violates rule 32):**
```text
When one agent raises, the remaining tasks in the plan don't run. Rule 32
says log the failure, continue the plan, and mark the cycle partial. Show me
the try/except boundary around task execution and fix it so a failing task
costs only that task. Then prove it by failing the middle task of a
three-task plan.
```

**The Orchestrator is doing agent work (violates rule 30):**
```text
Check orchestrator.py for any fetching, scoring, or analysis logic. Rule 30
says it only reads state, delegates, collects results and logs. Show me
every operation it performs and move anything that belongs to an agent into
that agent.
```

**Adding a fourth agent required editing the Orchestrator:**
```text
Adding a new agent required changes to the Orchestrator, which means the
registry isn't decoupling agents from the loop. Show me how the Orchestrator
resolves and invokes an agent, and refactor so a new agent needs only a
registry entry plus a decision rule in build_plan. Thursday's Verifier is
that fourth agent, so this needs to be right now.
```