# CLASS 5 SCRIPT â€” "The Orchestrator"
### Week 3 Â· Session 3.1 Â· Async Â· Target runtime 20:00

> **How to use this file:** Open it side-by-side with your slide deck. Everything in
> **plain text** is spoken word-for-word. Everything in `[SQUARE BRACKETS + BOLD]` is a
> stage direction â€” do it, don't say it. Prompts to paste into Kiro are in fenced code
> blocks marked `PROMPT C5-Px`. Never read a prompt aloud in full.
>
> **Fill these in before you record:** two `[FILL IN:]` placeholders â€” help channel and
> submission destination. Search for `[FILL IN`.
>
> **This class is 20 minutes, and that is a hard budget.** ~1,900 spoken words. Same three
> rules as session 3.2: prompt walkthroughs are two or three sentences, the full commentary
> lives in `prompts.md`, and only one segment slows down. Don't re-inflate it while recording.
>
> **The one idea this class exists to deliver:** *a pipeline runs the same steps every time;
> an orchestrator decides what needs doing.* Since Class 1 the learner has had an Orchestrator
> in name only â€” it calls fetch, score, analyse, in order, unconditionally. Today it reads the
> state of the system and delegates only the work that's actually needed, with a goal and a stop
> condition per sub-agent.
>
> **The honesty beat this class needs:** you have to admit that what you called an Orchestrator
> for four sessions was a to-do list. Say it plainly in Segment 1 â€” it's true, it's the reason
> today exists, and pretending otherwise makes the upgrade look like busywork.
>
> **Careful not to over-claim.** Nothing today makes the system smarter or the output better.
> It makes the system *cheaper and legible*. Say that out loud; slide 7 depends on it.

---

## PRE-FLIGHT CHECKLIST

- [ ] Slide deck open, presenter view, **8 slides**
- [ ] **Both `[FILL IN:]` placeholders replaced**
- [ ] **Class 4 repo working** â€” `run_cycle.py` runs fetcher, scorer, gap analyzer clean. Verify off camera.
- [ ] **A database in a "nothing to do" state** â€” everything fetched recently, everything scored, gaps fresh. Segment 4's best moment is a cycle that correctly decides to do almost nothing, and you need that state to exist. Run a full cycle right before recording.
- [ ] `python -m edgedash.llm --check` passes
- [ ] Terminal ~18pt, Kiro chat cleared
- [ ] Excalidraw open on the Class 4 diagram â€” you're annotating the Orchestrator box
- [ ] `.env` not visible, scrollback scrubbed
- [ ] Phone silent, mic tested

**Screen layout:** Slides 2:30, Excalidraw 2:30, Kiro + terminal 12:00, slides 2:30. **Three** switches.

---

# SEGMENT 1 â€” YOU DON'T ACTUALLY HAVE AN ORCHESTRATOR
### 00:00 â€“ 02:30 Â· Slides 1â€“3

**[SLIDE 1 â€” Title: "The Orchestrator"]**

**[Straight to camera. Brisk.]**

Hey everyone, welcome back. Week three â€” the Automator.

Twenty minutes again, same as Thursday will be. One idea per session and you build it the same day.

**[SLIDE 2 â€” "What you've actually been calling an Orchestrator"]**

I want to start by admitting something.

Since session one there's been a file in your project called `orchestrator.py`, and I've been calling it an Orchestrator for four sessions. Let's look at what it actually does.

**[Beat.]**

It calls the Fetcher. Then it calls the Scorer. Then it calls the Gap Analyzer. In that order. Every single time. Regardless of anything.

**[Direct to camera.]**

That's not an orchestrator. That's a to-do list with a `for` loop around it. And I want to be honest that I built it that way deliberately â€” it was the right thing for week one, because you can't orchestrate agents that don't exist yet.

But now they exist. All three of them. And a fixed sequence is now actively costing you.

**[SLIDE 3 â€” "Pipeline vs. orchestrator"]**

Here's the distinction, and it's the whole class.

**[Slow down.]**

A **pipeline** runs the same steps every time. An **orchestrator** looks at the state of the system and decides what needs doing.

**[Beat.]**

Concretely: it's seven in the morning, your cycle wakes up. You fetched two hours ago and got nothing new. Everything in your database is already scored. Your gap report was computed twenty minutes ago.

Your current code will now fetch again, score nothing, and recompute an identical gap report. That's three API calls and a full table scan to change nothing at all.

**[Direct to camera.]**

And when you put this on a schedule on Thursday â€” running every morning, unattended â€” that waste stops being theoretical. It's your free tier, every day, forever.

So today: state in, decisions out. Let's design it.

---

# SEGMENT 3 â€” BUILD
### 05:00 â€“ 14:30 Â· Kiro

**[SWITCH â†’ Kiro, chat clear]**

**[PACE: three prompts, nine and a half minutes. Paste, two sentences on the one idea, enter.]**

Fast again. Every prompt is fully explained in `prompts.md` â€” I'm pointing at the one thing that matters in each.

---

## 05:00 â€” PROMPT C5-P1 Â· The rules

**[PASTE. DON'T HIT ENTER.]**

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

**[Walk it â€” TWO sentences.]**

Rule twenty-eight is the class: skipping is a success, not a failure. And rule thirty is the boundary that keeps this honest â€” the Orchestrator coordinates and never does the work itself, which is what stops it slowly turning back into a script.

**[HIT ENTER.]**

Twenty-seven rules to thirty-three.

---

## 07:00 â€” PROMPT C5-P2 Â· State and the plan

**[PASTE. DON'T HIT ENTER.]**

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

**[Walk it â€” THREE sentences.]**

Two things. `build_plan` is a pure function of state and config â€” no database, no clock, no network â€” which means the decision logic of your entire system is unit-testable, and that's unusual and worth having.

And skipped agents stay *in* the plan with a reason attached. An agent that's silently absent looks identical to an agent that crashed, and you will not enjoy telling those apart at seven in the morning.

**[HIT ENTER. While it generates:]**

Notice every threshold is in config. Six hours between fetches is a guess â€” yours might be twelve. The point is it's a number you can change, not a condition buried in an `if`.

**[When it lands, run the tests. Confirm green, don't narrate.]**

```bash
python -m pytest tests/test_planning.py -q
```

---

## 10:00 â€” PROMPT C5-P3 Â· The real Orchestrator

**[PASTE. DON'T HIT ENTER.]**

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

**[Walk it â€” TWO sentences.]**

Point six is the one to read carefully: a cycle that does nothing exits zero with no warnings. If "nothing to do" looks like an error, you'll train yourself to ignore your own logs within about four days.

And that last question is the real test of the design â€” adding an agent should be a registry line and a decision rule. If Kiro's answer involves editing the Orchestrator, the abstraction leaked.

**[HIT ENTER. While it generates:]**

This is the fifth week the registry from Class 1 has paid off. That's the return on twenty minutes of design in session one.

**[When it lands, read Kiro's answer to the final question aloud. If it says anything more than "registry + decision rule", say so and have it fixed â€” that's a real finding, not a nitpick.]**

**[Then run a cycle.]**

```bash
python run_cycle.py
```

**[Read the printed plan aloud, then the outcome. Move quickly â€” the interesting run is next.]**

---

# SEGMENT 4 â€” WATCH IT DECIDE
### 14:30 â€“ 17:30 Â· Terminal

**[The only slow segment. Three minutes. Two runs, and the second one is the point.]**

Now the run I actually care about. Let's do it again immediately.

```bash
python run_cycle.py
```

**[Read the plan off the screen â€” everything should be skipped.]**

Look at this plan.

Fetch â€” skipped, fetched eleven minutes ago. Score â€” skipped, unscored count zero. Analyse â€” skipped, gaps newer than the newest score.

Outcome: **nothing to do.** Exit zero.

**[Beat. Direct to camera â€” this is the line of the class.]**

Zero API calls. Zero writes. About forty milliseconds. And it told me exactly why it made every one of those three decisions.

Run that same cycle on your old code and it fetches, calls the model, and recomputes an identical report â€” to change nothing.

**[Now create work and show it react. Fastest reliable method: clear a few scores.]**

Now let's give it something to do.

**[Run `python -m edgedash.rescore --id <one or two ids>` â€” or clear a handful of scores â€” then run the cycle.]**

```bash
python -m edgedash.rescore --all
python run_cycle.py
```

**[Read the new plan.]**

Different plan. Fetch still skipped â€” nothing's changed upstream. But score is in, because unscored count is fifty now, and it's carrying a stop condition of twenty-five items.

**[Point at the stop condition.]**

Twenty-five, not fifty. It'll do half tonight and half on the next cycle, because that's the boundary I set in config. Nobody has to remember to be careful â€” the limit is structural.

**[Let it run. Then read the summary row.]**

And then analyse ran, because the scores it just wrote are newer than the gap snapshot. It figured that out from timestamps; I didn't tell it to.

**[Beat.]**

That's the difference. Same three agents as last week. Same code inside them. The system just stopped doing work it didn't need to do, and started telling me what it decided.

**[One more â€” the failure isolation, quickly.]**

Last thing, and it's rule thirty-two. If the Fetcher dies mid-plan, the rest of the plan still runs.

**[Either break a source URL briefly, or say plainly that you're taking this on trust from Class 2 if you're tight on time.]**

Same shape as week two: one dead thing doesn't take the rest with it. Third time you've seen that pattern, and it will not be the last.

---

# SEGMENT 5 â€” ASSIGNMENT & CLOSE
### 17:30 â€“ 20:00 Â· Slides 4â€“8

**[SWITCH â†’ slides]**

**[SLIDE 4 â€” "What you built today"]**

Today: a state reader â€” four cheap queries, no API calls. A pure planning function that decides what needs doing and is fully unit-tested. Goals and stop conditions on every delegation, set by the Orchestrator. A plan printed before execution. And "nothing to do" as a first-class successful outcome.

**[SLIDE 5 â€” The assignment]**

Week three's assignment is due **Sunday**, and this is the first half â€” Thursday's Verifier completes it.

Your state-driven Orchestrator running. Stop conditions on all three delegations. The plan printed every cycle. Tests on `build_plan` â€” four cases minimum.

**[SLIDE 6 â€” "Two runs, one screenshot"]**

And this week's ten seconds.

**Run your cycle twice in a row and film both plans.** First run does work. Second run skips everything and says why.

**[Beat.]**

That's the whole lesson in one screenshot. And the second run is the one that matters, because a system that knows there's nothing to do is a system that's actually reading its own state rather than following instructions.

**[SLIDE 7 â€” "What today did not do"]**

One honest note before we finish, because I don't want to oversell this.

**[Direct to camera.]**

Nothing today made your system smarter. Your scores are identical. Your gap report is identical. If you were hoping the output would get better, it didn't.

**[Beat.]**

What changed is that it became **cheap and legible.** It does the minimum work required, and it explains its decisions. Those are the two properties that make unattended operation survivable â€” which is Thursday, and then week four.

Boring wins are the ones that let a system run for a month without you.

**[SLIDE 8 â€” Close]**

**[Slow down.]**

Thursday: the **Verifier.** Your system can decide what to do â€” next it learns to check whether what it did was any good, and refuse to publish when it wasn't. That completes the Automator badge.

**[Beat.]**

But today you got the thing that makes an agent an agent rather than a script. It looks at the world and decides. Everything else is detail.

Two runs, one screenshot. See you Thursday.

---

## POST-RECORDING CHECKLIST

- [ ] Is the printed plan legible? Those three "skipped, because" lines are the payoff â€” re-record at a larger font if there's any doubt
- [ ] **Confirm you restored your scores** after `rescore --all` in Segment 4, and that a final cycle ran clean
- [ ] No API key in any frame
- [ ] **Check the runtime.** Over 22:00, use the cut list below
- [ ] Export the Excalidraw diagram (state â†’ plan â†’ tasks) as PNG â†’ resources
- [ ] Share `prompts.md` â€” mention that C5-P4 is self-study and wasn't on camera
- [ ] Post the recording + diagram

## HOLDING THE 20-MINUTE BUDGET

~1,900 spoken words. The cuts are already made; the risk is re-inflating while recording.

Running long? Cut in this order:
1. The rule 32 failure demo at the end of Segment 4 â€” you've taught that pattern twice already, so saying "same shape as week two" is enough
2. The `pytest` run at 09:30 â€” the prompt asks for tests, you don't have to watch them pass
3. The goal/stop-condition explanation in Segment 2 â€” draw the task envelope and give it one sentence instead of three
4. Slide 7's honesty note â€” it's valuable and it is cuttable if you're badly over

**Never cut the second run in Segment 4.** The all-skipped plan is the entire proof of the class.

Running short? Read Kiro's answer to "what would I change to add a fourth agent?" properly, and walk `build_plan`'s decision rules line by line. **Don't** add a fourth prompt.

## GETTING THE "NOTHING TO DO" STATE

Segment 4's best moment needs a database with genuinely nothing to do. Set this up before recording:

1. Run a full cycle 10â€“15 minutes before you start recording. That leaves `last_fetch_at` recent, everything scored, and gaps fresh.
2. Confirm it: run the cycle a second time and check that the plan is all skips. **If anything still runs, your `fetch_interval_hours` is shorter than the gap since your last fetch** â€” either wait, or raise the interval in config before recording.
3. Don't fetch again between that check and hitting record.

If you arrive at Segment 4 and something unexpectedly runs, don't fight it â€” read the plan you actually got, explain the state value that caused it, and *then* run again to get the all-skipped version. An orchestrator explaining a decision you didn't expect is a perfectly good demo of the same point.