# Class 7 Prompts â€” "Give It a Voice"
### Week 4 Â· Session 4.1 Â· EdgeDash Â· Proof of Ship, August Cohort

These are every prompt used in Class 7, in order. Paste them into **Kiro** one at a time.

**This session was 21 minutes, so the video moves fast and this file carries the commentary.**
**C7-P4 was not covered on camera** â€” it's self-study, about ten minutes, and it's the one that
makes your public URL safe to share.

## Before you start

1. Your Class 6 repo open in Kiro, with `.kiro/steering/edgedash.md` containing rules 1â€“39.
2. `run_cycle.py` runs and passes verification; `streamlit run app.py` shows your dashboard.
3. **50+ scored listings and a current gap report.** Every answer today is computed from your real
   data â€” thin data gives boring answers.
4. A terminal open in the repo.

---

## The one idea this class is built on

> **Don't let the model touch your database. Let it pick from a menu of questions you already
> wrote.**

You have real listings, deterministic scores, a ranked gap report and a dashboard. But there's a
category of question your dashboard can't answer, and it's the category you actually have:

- *Which companies are hiring for my role this week?*
- *What three skills would unlock the most listings?*
- *Have things gotten better or worse this month?*

All answerable from data you already hold. None of them a panel â€” and you can't add a panel for
every question you might ever think of.

### Why not just let the model write SQL

Because it works, it's fifteen lines, a lot of tutorials teach it, and it is a genuine security
hole.

The model generates arbitrary SQL and you execute it against your live database. It's `SELECT`
today. Nothing in that design *prevents* a `DROP TABLE` â€” you are relying on the model choosing
not to. And your inputs aren't entirely yours: some of the text in your prompts came off the
internet, out of job descriptions you scraped. That's the shape of a prompt injection, and it
doesn't require anyone to be targeting you.

### The inversion

| | Text-to-SQL (don't) | Tool registry (today) |
|---|---|---|
| **Who writes the query** | The model, at runtime | You, in advance, tested |
| **Model's job** | Compose arbitrary SQL | Pick one of ~7 functions + fill params |
| **Task difficulty** | Open-ended generation | Classification with 7 options |
| **Worst case** | Arbitrary code execution on your data | Right answer to the wrong question |
| **Auditable** | Only after the fact, if you log it | Every possible query is in your repo |

Same user experience â€” ask in English, get an answer from your data. Completely different blast
radius.

**The model appears exactly twice and touches the database zero times:** once to **route** (pick a
tool), once to **phrase** (turn rows into a sentence). The arithmetic in between is yours.

---

## PROMPT C7-P1 â€” Amend the steering file

**What it does:** Seven rules for natural language queries. Rules before code, seventh time.

```text
Update .kiro/steering/edgedash.md â€” add a NATURAL LANGUAGE QUERIES section
to the existing rules. Do not rewrite the rest of the file.

NATURAL LANGUAGE QUERIES:
40. NEVER generate SQL from a model. No text-to-SQL, ever, in any form.
    The model selects from a fixed registry of parameterised query
    functions that I wrote. It never composes a query.
41. Every query tool is read-only, parameterised, and takes typed
    parameters that are validated and clamped to a safe range before
    execution. A model-supplied parameter is untrusted input.
42. The model appears exactly twice per question: once to ROUTE (pick a
    tool and its parameters) and once to PHRASE (turn returned rows into
    prose). It never touches the database in either call.
43. The phrasing call may use ONLY the numbers present in the rows it was
    given. It must not estimate, extrapolate, add outside context, or
    infer a value that is not in the data. If the rows are empty it must
    say so plainly.
44. Every answer displays the underlying rows alongside it. No prose
    answer appears without the data that produced it.
45. If no tool matches the question, say so and list what CAN be asked.
    Never guess at the closest tool and never answer from general
    knowledge.
46. Query tools read from the last passing cycle only, per rule 38.

Then show me the diff.
```

**Check before moving on:** rules 1â€“39 intact, new section appended.

**Rule 40 is phrased as an absolute deliberately.** "Never, ever, in any form" leaves Kiro no room
to helpfully suggest text-to-SQL in week 6 when you ask for "a quick way to query this." Absolutes
are appropriate for the small number of things that are genuinely never a good idea.

**Rule 43 is what keeps the answers honest.** A model handed five rows and asked to write a summary
will happily add context that sounds plausible â€” a comparison to the market, a rough percentage,
an encouraging aside. Every one of those is fabricated. Restricting it to numbers present in the
rows is the difference between a summary and a story.

**Rule 44 matters more here than anywhere else in the project.** A fluent English sentence is the
most trustworthy-*looking* output your system can produce, and looking trustworthy is not the same
as being right. So every answer ships with its rows. This is rule 26 (every number drillable) from
Class 4, applied where it's most needed.

---

## PROMPT C7-P2 â€” The query tools

**What it does:** Seven parameterised read-only functions. You own all of them. This is the file
that makes rule 40 possible.

```text
Build the query tool registry. Deterministic. No LLM anywhere in this
file â€” these are parameterised queries I own.

edgedash/query/tools.py

1. A `@tool` decorator registering each function in a TOOLS dict with its
   name, description, and a JSON-schema-style parameter spec. The
   description is what the router model sees, so make each one specific
   and unambiguous about when it applies.

2. These seven tools, all read-only, all reading from the last passing
   cycle per rule 46:

   companies_hiring(days: int = 7)
     Companies with listings posted in the last N days, with counts.
   best_matches(n: int = 10)
     Highest-scoring listings with score, title, company, reason.
   top_gaps(n: int = 5)
     Top skill gaps by opportunity cost, with listings_blocked.
   gap_detail(skill: str)
     The listings blocked by one named skill â€” this is rule 26's
     drill-down, exposed as a question.
   trend(weeks: int = 3)
     Gap opportunity_cost change over N weeks from the snapshots.
   listing_count()
     Totals: listings, scored, unscored, newest listing date.
   skill_demand(skill: str)
     How often one skill appears in required vs nice_to_have.

3. Per rule 41, every parameter is validated and CLAMPED before use:
   - ints clamped to a sane range (days 1-90, n 1-25, weeks 1-12)
   - `skill` canonicalised through edgedash.skills.canonical and matched
     against skills actually present in the database â€” never interpolated
     into a query string
   Treat every parameter as untrusted input from a model, because it is.

4. Each tool returns a plain list of dicts plus a short `summary` string
   of what it looked at ("47 listings from the last 7 days").

5. All reads through the storage module per rule 2. No direct sqlite3.

6. Tests: each tool returns the right shape, clamping works at both
   bounds, an unknown skill returns empty rather than raising.

Show me the @tool decorator and companies_hiring first.
```

**Check before moving on:** `python -m pytest tests/test_tools.py -q` green, including both
clamping bounds.

**Why clamping isn't paranoia.** The model supplies those parameters. It is not adversarial, but it
is unreliable â€” ask for "all the companies" and you may get `days: 3650`. Clamping turns an
unbounded query into a bounded one, and it costs one line per parameter.

**The `skill` parameter is the one to watch.** It's the only free-text parameter here, and free
text is where injection lives. It never gets interpolated into a query string: it's canonicalised
through the Class 4 function and matched against skills that actually exist in your database. An
unrecognised skill returns empty rather than reaching the database at all.

**Note how much of this is exposing what you already built.** `gap_detail` is rule 26's drill-down
from Class 4. `trend` reads the Class 4 snapshots. `best_matches` reads Class 3's scores. Most of
this feature's value is making three weeks of work *askable* â€” the new code is thin because the
data layer was done properly.

**Tool descriptions are the actual prompt engineering here.** The router model sees only names,
descriptions and parameter specs. If two descriptions overlap, routing gets unreliable â€” and the
fix is editing a description, not the model call.

---

## PROMPT C7-P3 â€” Route, then phrase

**What it does:** The two model calls, and the Streamlit section that surfaces them.

```text
Build the two-call query pipeline per rules 42-45.

edgedash/query/ask.py â€” `ask(question: str) -> Answer` where Answer has
.text, .rows, .tool_used, .params.

1. ROUTE â€” one llm.complete_json call:
   - Prompt contains the question and the TOOLS registry: each name,
     description and parameter spec. Nothing else. No schema, no SQL, no
     table names.
   - Schema: {"tool": str|null, "params": {...}, "confidence":
     "high"|"low"}
   - tool must be null if nothing matches. Per rule 45, instruct it
     explicitly: do not pick the closest tool, return null.
   - Validate the returned name is in TOOLS. Anything else is a hard
     error, not a fallback.

2. EXECUTE â€” call the tool with validated, clamped params. Never eval,
   never getattr on a model-supplied string outside the registry lookup.

3. PHRASE â€” one llm.complete_json call:
   - Given the question and the returned rows ONLY, write 2-3 sentences.
   - Per rule 43, the prompt must state: use only numbers present in
     these rows; do not estimate or add outside context; if the rows are
     empty say the data does not contain an answer.
   - Include the tool's `summary` so the answer can state what it looked
     at ("across 47 listings from the last 7 days").

4. If tool is null, return an Answer whose text says the question can't be
   answered and LISTS the available tool descriptions in plain English.
   No model call for phrasing in this case â€” it's a fixed message.

5. Log every question to a query_log table: question, tool chosen, params,
   whether it was answerable, duration.

6. Add an "Ask your data" section to app.py: a text input, the answer,
   and the rows underneath in a table per rule 44. Three example
   questions as clickable buttons so the first thing a visitor does
   works.

Show me the routing prompt text first â€” that's the part I want to read.
```

**Check before moving on:** ask it something genuinely outside the registry â€” *"should I take a pay
cut for a remote role?"* â€” and confirm it **refuses and lists what it can answer.** If it picks a
tool anyway and answers something adjacent, rule 45 isn't working, and that's the most important
thing in this class to get right.

**What the routing prompt does NOT contain:** no schema, no table names, no column names, no SQL.
It sees function descriptions and nothing else. Even if someone injected instructions into a job
description you scraped, there's nothing in that context to attack â€” the model has no capability to
misuse.

**Point 4 is the one people skip.** A system that always produces *something* trains you to verify
every answer, which costs more time than the feature saves. Saying "I can't answer that, here's
what I can" is a feature, not an admission of incompleteness.

**Point 5 gives you a roadmap written by your users.** In a week, `query_log` tells you which
questions people ask that you don't have a tool for. That's a better feature list than guessing.

**Point 6, the example buttons:** the first thing a stranger does on your public URL has to work. A
blank text box is not a prompt â€” it's an invitation to type something you didn't anticipate and
conclude your project is broken.

---

## PROMPT C7-P4 â€” Rate limiting and abuse guards (self-study â€” not in the video)

**What it does:** Makes the ask box safe to expose publicly. **Not covered on camera**, and you
want it before Thursday's deploy.

```text
Add abuse guards to the ask endpoint. This runs on a public URL from
Thursday, so assume strangers and bots will find the text box.

1. Rate limit per session: max 10 questions per 10 minutes. On exceed,
   show a clear friendly message with the wait time. No model call is made
   when rate limited â€” the limit must be checked BEFORE routing.

2. Input guards before any model call:
   - reject questions over 300 characters
   - reject empty or whitespace-only input
   - strip control characters
   - if the input contains obvious instruction-injection patterns
     ("ignore previous", "system prompt", "you are now"), skip the model
     entirely and return the standard can't-answer message. Log it as
     "rejected: suspicious input". Do not explain the filter in the
     response.

3. A global daily cap on total questions, from config (default 200), so a
   traffic spike cannot exhaust my free tier. On exceed, show the
   dashboard normally with the ask box disabled and a short note â€” the
   dashboard must never go down because the ask box hit its cap.

4. Log every rejection to query_log with its reason, so I can see what
   people actually send.

The dashboard's data panels must keep working under every one of these
conditions. Only the ask box degrades.
```

**Why this is genuinely necessary rather than defensive theatre.** From Thursday there's a text box
on a public URL wired to an API key you pay nothing for but *can* exhaust. The daily cap is the
important one: it means the worst outcome of unexpected traffic is a disabled ask box, not a broken
dashboard and a dead quota.

**Note point 3's constraint.** The dashboard degrades in exactly one place. Everything computed
from your data keeps working, because none of it depends on the model. That separation was free â€”
you get it because the query layer sits *beside* the dashboard rather than inside it.

**On the injection filter:** it's a cheap layer, not a defence. Your actual defence is rules 40â€“42
â€” there's no SQL to inject into and no capability to hijack. The filter just avoids paying for a
model call on obvious junk. Don't mistake it for the thing keeping you safe.

---

## Your assignment

**Due Sunday** â€” this is the first half of week 4; Thursday's deployment completes it and the
month:

- [ ] Query layer working with **at least 5 tools** (7 if you use them all)
- [ ] **No model-generated SQL anywhere** â€” rule 40
- [ ] Every parameter validated and **clamped**; `skill` matched, never interpolated
- [ ] **Rows displayed with every answer** â€” rule 44
- [ ] **Out-of-scope questions refused**, with a list of what can be asked â€” rule 45
- [ ] Ask section live in `app.py` with three working example buttons
- [ ] `query_log` recording questions, tools chosen and refusals
- [ ] **One tool of your own** that I didn't write â€” see below
- [ ] **Film the refusal** â€” see below
- [ ] 2â€“3 minute walkthrough video
- [ ] Submit GitHub repo link + video

### Film the refusal

Ask it something it genuinely can't answer and record the response: the refusal plus the list of
what *can* be asked.

Fourth week running I've asked you to film a failure. The working state is easy. What proves your
system is trustworthy is watching it decline.

### Add one tool of your own

Seven is what I needed. Write an eighth for a question about *your* career that I didn't think of â€”
*"which companies have posted more than once?"*, *"what's my score distribution by seniority?"*,
*"which listings mention a skill I just learned?"*

Adding a tool should take ten minutes: one decorated function, one description, one test. **If it
takes longer than that, your registry isn't as clean as it looks** â€” and that's worth knowing
before Thursday.

### What this is not

Don't oversell it. **This is not a chatbot.** No memory, no follow-ups, no conversation. It answers
a fixed set of questions in natural language.

That's the design, not a shortcut. A system that answers seven questions reliably, with receipts,
and refuses the rest, is worth more than one that answers anything and can't be trusted on any of
it. If someone asks whether you built a chatbot: you built a query interface with a language model
at the edges. That's the better answer to anyone who knows the difference.

**Badge progress:** The Edge â€” Thursday's public deployment completes it, and the month.

---

## Fixing common problems

Paste these as follow-ups. Describe the symptom, not your guess at the cause.

**It answers out-of-scope questions instead of refusing (violates rule 45):**
```text
I asked a question no tool covers and it picked the closest tool and
answered anyway. Rule 45 says return null and list what CAN be asked. Show
me the routing prompt and the null-handling branch. The prompt must
explicitly instruct: do not pick the closest tool, return null if nothing
matches. Then confirm with three questions that are clearly outside the
registry.
```

**Routing picks the wrong tool:**
```text
The question "<question>" routed to <tool> when it should have gone to
<other tool>. Print the exact tool descriptions the router was given for
both. I suspect the descriptions overlap or are too vague about when each
applies â€” rewrite both so the boundary between them is explicit. Do not
add routing logic in code; fix the descriptions, since that's what the
model sees.
```

**The answer contains numbers that aren't in the rows (violates rule 43):**
```text
The prose answer includes a figure that does not appear in the rows it was
given. Rule 43 says the phrasing call may use ONLY numbers present in the
rows. Show me the phrasing prompt and make that constraint explicit and
unambiguous. Then add a post-check: extract every number from the generated
text and verify each one appears in the rows, and log a warning when it
doesn't.
```

**Kiro generated SQL from the model anyway (violates rule 40):**
```text
Check every file in edgedash/query/ for model-generated SQL, query strings
built from model output, or any prompt containing table or column names.
Rule 40 says the model selects from a fixed registry and never composes a
query. Show me every place model output reaches the database layer and
remove it. The router's only valid output is a tool name from TOOLS plus
typed parameters.
```

**A parameter came back out of range or the wrong type:**
```text
The router returned a parameter my tool didn't expect (<detail>). Rule 41
says model-supplied parameters are untrusted input, validated and clamped
before execution. Show me the validation layer between routing and
execution, and confirm every parameter is type-checked and clamped there
rather than inside each tool. Then test with a deliberately absurd value.
```

**The ask box is slow:**
```text
A question takes several seconds. Print the duration of each stage: routing
call, tool execution, phrasing call. Two model calls have a floor I can't
avoid, but tell me which stage dominates. If it's tool execution, show me
the query â€” it should be counts and indexed lookups, not table scans.
```

**Empty rows produce a confident-sounding answer:**
```text
When a tool returns no rows, the answer still reads as though it found
something. Rule 43 says an empty result must be stated plainly. Show me the
phrasing prompt's empty-rows branch â€” ideally we skip the model call
entirely for an empty result and return a fixed message, since there is
nothing to phrase.
```

**Adding an eighth tool required changes outside tools.py:**
```text
I added a tool and had to edit files other than tools.py. Adding a tool
should be one decorated function plus a test â€” the registry should pick it
up and the router should see it automatically. Show me everything I had to
touch and refactor so the registry is the only place a tool is declared.
```