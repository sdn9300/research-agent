# Class 8 Prompts â€” "Ship to the World"
### Week 4 Â· Session 4.2 Â· EdgeDash Â· Proof of Ship, August Cohort

These are every prompt used in Class 8, in order. Paste them into **Kiro** one at a time.

**This is the last session.** After this you have a live public URL, a scheduled job, and the
final assignment. **C8-P4 was not covered on camera** â€” it's self-study and it's the one that tells
you when your deployed system breaks.

## Before you start â€” two free accounts

Neither needs a card. Create both **before** you start building, because both involve email
confirmation and you don't want to be waiting on an inbox mid-deploy.

**1. Supabase** (hosted Postgres, free tier) â€” `https://supabase.com`

- New project. Pick a region near you. Set a database password and **save it somewhere**.
- Project Settings â†’ Database â†’ Connection string â†’ URI. Copy it.
- Put it in `.env` as `DATABASE_URL=postgresql://...`
- If connections fail later, append `?sslmode=require`.

Free tier is 500MB and pauses after a week of inactivity â€” fine for this, and your daily cycle
keeps it awake.

**2. Streamlit Community Cloud** (hosting, free) â€” `https://share.streamlit.io`

- Sign in with GitHub and authorise it to read your repositories. That's all for now; you point it
  at the repo during the class.
- It deploys straight from GitHub and **redeploys itself on every push to your branch** â€” no second
  git remote, nothing to upload.

**If you hit a free-tier limit**, Hugging Face Spaces is a drop-in alternative: same code, add the
Spaces YAML front matter to your README, `git remote add space ...` and push. Ask in the channel.

**Also needed:** your repo pushed to GitHub and current. Today's deploy assumes it.

---

## The one idea this class is built on

> **The deploy is easy because you designed for it in week one.**

The first prompt of the month contained this:

```
2. ALL storage access goes through a single storage module with a thin interface.
   No other module may import sqlite3 directly. We will swap SQLite for hosted
   Postgres in week 4 and it must be a one-file change.
```

Today that promise comes due. If the swap really is one file, that's four weeks of return on
twenty minutes of architecture. If it isn't, you'll find out exactly which file reached past the
storage module â€” **and that's the more instructive outcome**, so don't paper over it.

### The trap that eats your database

Do this in the obvious order â€” deploy the app, sort the database later â€” and here's what happens:

1. You deploy with your SQLite file. It works. Listings are there. Perfect.
2. The Space restarts: you pushed a change, or it slept, or Tuesday.
3. **Your database is gone.** Four weeks of listings, scores, snapshots, cycle history.

Because the filesystem on free hosting is **ephemeral** â€” it exists while the container runs and
not afterwards.

**Why this one is nasty rather than annoying:** it's invisible for three weeks. On your laptop a
SQLite file is the most reliable thing in the project. It works perfectly, every time, right up
until the night you deploy â€” which is the night you have least patience for it.

That's why Postgres comes **before** the deploy today, and it's why rule 2 was written in session
one.

---

## PROMPT C8-P1 â€” Deployment rules + the storage swap

**What it does:** Five deployment rules, then the swap rule 2 was written for.

```text
Update .kiro/steering/edgedash.md â€” add a DEPLOYMENT section. Do not
rewrite the rest of the file.

DEPLOYMENT:
47. Never rely on the local filesystem for anything that must survive a
    restart. Hosting filesystems are ephemeral. All persistent state is in
    the hosted database.
48. Every secret comes from an environment variable read in one place.
    No secret is ever committed, printed, logged, or shown in an error
    message or traceback.
49. The scheduled job and the dashboard are separate processes that share
    only the database. The dashboard never runs a cycle; the scheduler
    never serves a page.
50. The deployed app must start and render even when the database is
    empty, unreachable, or mid-migration. It shows a clear status message
    instead of a stack trace. A stranger must never see a traceback.
51. The scheduled job is idempotent and safe to run twice. It must have a
    hard timeout and stay inside free-tier limits.

Then, per rule 2: swap SQLite for hosted Postgres.

edgedash/storage.py is the ONLY file that may change. If you find
yourself needing to edit any other file, STOP and tell me which file and
why â€” that means rule 2 was violated somewhere and I want to know before
we go further.

- Read DATABASE_URL from the environment. If it is absent, fall back to
  local SQLite so I can still develop offline â€” log which backend is
  active at startup, every time.
- Keep every existing function signature identical.
- Handle the SQL dialect differences (autoincrement, upsert/ON CONFLICT,
  timestamp types, boolean handling) inside this module only.
- Add `python -m edgedash.storage --migrate` that creates every table on
  an empty Postgres database, and is safe to run repeatedly.
- Add `python -m edgedash.storage --check` that prints which backend is
  active, whether it connected, and the row count per table.

Then tell me plainly: did you need to touch any file other than
storage.py?
```

**Then:**

```bash
python -m edgedash.storage --migrate
python -m edgedash.storage --check
python run_cycle.py
```

**Check before moving on:** `--check` says Postgres, connected, with tables. Then a full cycle
passes against it. Same code, different database, nothing above the storage module noticed.

**Read Kiro's answer to the last question carefully.** One file means rule 2 held. More than one
file means something reached past the storage module â€” go and look at it now rather than after
deployment, and add the fix to your README's known-issues if you don't want to refactor tonight.

**Why the SQLite fallback stays.** No `DATABASE_URL` means local SQLite, so you can still develop
on a plane. And the startup log line saying which backend is active is how you avoid the genuinely
confusing hour where you're writing to a database you didn't mean to.

**Rule 50 is the one that protects you in public.** Your app now has visitors who are not you. A
stranger seeing a Python traceback is the worst possible first impression of your work, and an
empty database is the *normal* state for the first few minutes after you deploy.

---

## PROMPT C8-P2 â€” Package it for Spaces

**What it does:** Makes the repo deployable and audits it for leaks before anything goes public.

```text
Prepare the repo for deployment to Streamlit Community Cloud (free tier),
deploying from GitHub.

1. Files it needs:
   - requirements.txt â€” pinned versions, nothing unused. Include the
     Postgres driver.
   - .python-version or a runtime pin if any dependency needs it
   - .streamlit/config.toml with the dark theme, so the deployed app looks
     like the local one
   - .gitignore confirmed to exclude .env, .streamlit/secrets.toml, and
     any local .db file

2. Per rule 50, make app.py robust to a hostile startup:
   - If DATABASE_URL is missing or unreachable, render the page with a
     clear "database not configured" status message. No traceback.
   - If tables are empty, show "no cycles yet â€” first run is scheduled for
     <time>" instead of empty charts or an exception.
   - Wrap every panel so one failing panel cannot take down the page.
   - A stranger must never see a stack trace. Log the detail server-side.

3. Per rule 48, audit for leaks before we deploy:
   - Confirm no secret is printed at startup, in any log line, or in any
     error path shown to a user.
   - Confirm the connection string is never rendered, even truncated.
   - List every environment variable the app needs, so I can set them in
     the Spaces UI.

4. Per rule 49, confirm app.py cannot run a cycle. It reads only. If any
   code path lets the dashboard trigger a write, show me and remove it.

5. Add a small footer to the dashboard: last successful cycle timestamp,
   and a link to the GitHub repo.

Do not deploy yet. Show me the file list and the secrets TOML block.
```

**Then deploy:**

```bash
git add -A && git commit -m "prepare for deploy" && git push
```

1. `share.streamlit.io` â†’ **Create app** â†’ from an existing repo.
2. Pick the repo, branch `main`, main file `app.py`.
3. **Advanced settings â†’ Secrets**, in TOML:

```toml
DATABASE_URL = "postgresql://..."
GEMINI_API_KEY = "..."
```

4. Deploy. From here on it redeploys itself whenever you push.

**Check before moving on:** open the URL **in an incognito window or a different browser profile.**
Logged in, you'll miss exactly the failures a visitor would hit.

**Note the last line of the prompt: don't push yet.** Read the leak audit first. Once something is
pushed it's in the history, and "I'll remove it in the next commit" doesn't remove it.

**On secrets and screen recordings.** If you record your own walkthrough, don't paste a secret on
camera. A value that appeared in a frame is a value you must treat as public forever â€” even if you
cut the frame, you'd never fully trust it, so you'd rotate it anyway. Set secrets before you start
recording. **Decide where your secrets are allowed to appear before you're mid-task**, not during.

**What isn't deployed: your database.** The platform holds your code. Data lives in Postgres
somewhere else. That separation is the whole reason C8-P1 came first.

---

## PROMPT C8-P3 â€” The scheduler

**What it does:** Makes "autonomous" honest. Your cycle runs on GitHub's machine every morning
whether your laptop is open or not.

```text
Add scheduled execution with GitHub Actions, per rules 49 and 51.

.github/workflows/cycle.yml

1. Schedule: daily at 06:00 in my timezone â€” compute the correct UTC cron
   and put a comment showing both times, because I will forget.
   Also allow manual triggering (workflow_dispatch).

2. The job:
   - checkout, set up Python, install from requirements.txt with pip cache
   - run `python -m edgedash.storage --migrate` first (safe to repeat)
   - then `python run_cycle.py`
   - DATABASE_URL and GEMINI_API_KEY from GitHub repository secrets
   - a hard job timeout of 10 minutes per rule 51
   - upload the cycle log as an artifact so I can read what happened

3. Per rule 48: nothing may print a secret. Confirm no step echoes an
   environment variable, and that a failing step's output cannot contain
   one.

4. Failure handling: if the cycle fails, the job fails visibly so I get
   the GitHub notification. It must NOT retry automatically â€” rule 36
   caps retries inside the cycle, and a workflow-level retry would
   multiply that.

5. Tell me exactly which secrets to add in GitHub settings, and the
   command or UI path to trigger the workflow manually right now so I can
   test it without waiting until tomorrow morning.
```

**Then:** add the two secrets in GitHub â†’ Settings â†’ Secrets and variables â†’ Actions, and
**trigger the workflow manually.** Don't wait for tomorrow morning â€” "it'll probably work
overnight" is not something to discover at breakfast.

**Check before moving on:** the workflow completes green, and refreshing your public URL shows a
new timestamp. At that point a cycle ran on GitHub's machine, wrote to a database in a third
place, and updated a page you're reading in a fourth â€” with your laptop uninvolved.

**Why no workflow-level retry.** Rule 36 caps retries inside the cycle at one. If the workflow also
retried, you'd get that cap multiplied â€” which is how a bounded system quietly becomes an unbounded
one. One retry means one, at exactly one level.

**Why the scheduler and dashboard are separate processes (rule 49).** They share exactly one thing:
the database. The scheduler writes, the dashboard reads, and neither can break the other. That's
why a failed cycle doesn't take your public URL down â€” it just means the dashboard shows the last
verified cycle, which is rule 38 doing its job.

**The most common failure here is secrets naming.** The workflow expects the exact names in the
prompt; your `.env` may spell them differently. If the job fails on the first run, check that
before anything else.

---

## PROMPT C8-P4 â€” Know when it breaks (self-study â€” not in the video)

**What it does:** Tells you when your deployed system stops working. **Not covered on camera**, and
worth doing in the first week after you deploy.

```text
Add lightweight health reporting to the deployed system. No new services,
no paid monitoring.

1. `python -m edgedash.health` â€” read-only, exits non-zero if unhealthy:
   - newest listing older than 3 days
   - no successful cycle in 48 hours
   - last 3 cycles all failed verification
   - database unreachable
   Print a one-line summary per check with the observed value.

2. Add it as a final step in the GitHub Actions workflow, so an unhealthy
   system makes the job fail and I get the notification. It runs AFTER the
   cycle and never blocks it.

3. Add a small status line at the top of the dashboard: green if the last
   cycle passed within 24h, amber if stale, red if the last 3 failed.
   One line, not a panel. A visitor should be able to tell at a glance
   whether they're looking at live data.

4. Per rule 50, if the health check itself cannot run, the dashboard still
   renders. Health reporting must never be able to take the page down.
```

**Why this matters more than it sounds.** From now on your project runs unattended. The failure
mode of an unattended system is not a crash â€” it's **silence.** Your cycle stops running, your
dashboard keeps serving last week's numbers, and nothing tells you. A `#MyEdge` post with a live
URL is only as good as the URL still being live three weeks later.

**Note the constraint in point 4:** health reporting can never take the page down. A monitoring
feature that breaks the thing it monitors is worse than no monitoring â€” and it's a common enough
mistake to be worth stating as a rule.

---

## Your final assignment

**Due Sunday.** This is the one that goes in your portfolio.

- [ ] **Live public URL, working** â€” anyone can open it
- [ ] **Hosted Postgres, not SQLite** â€” `--check` confirms the backend
- [ ] **Scheduler proven** â€” at least one successful automated cycle you did **not** trigger by hand
- [ ] Dashboard renders honestly when data is empty or stale â€” no tracebacks
- [ ] Ask box working on the public URL
- [ ] `.env` never committed; secrets only in Spaces and GitHub settings
- [ ] **A README a stranger could follow** to run it themselves
- [ ] **60â€“90 second demo video** â€” see below
- [ ] Submit GitHub repo link + live URL + video

### The 60-second demo â€” four shots

1. **Your live URL loading.** The real thing, in a browser, with the address bar visible.
2. **Ask it a question** â€” the answer and the rows underneath.
3. **The gap panel** with your real top gap.
4. **The activity log with a rejection in it.**

**Shot four is the one most people will leave out, and it's the one that makes the other three
credible.** Everyone's demo shows the thing working. Yours shows the thing catching itself being
wrong â€” which is the only evidence that anything else on the page can be trusted.

### The README matters more than you think

It's the first thing anyone who follows your link from LinkedIn will read after the dashboard. Cover:

- What it does, in two sentences, before any setup instructions
- The architecture in one diagram or list â€” Trigger â†’ Orchestrator â†’ sub-agents â†’ Verifier â†’ storage â†’ dashboard
- **Why** three or four decisions were made: storage behind one module, no model-generated SQL, the Verifier not being allowed to repair, deterministic scoring
- Known limitations, honestly â€” cross-source duplicates, extraction misses, thin trend data

That "why" section is what separates your repo from the hundred others that look similar. Anyone can
generate this project. Explaining the decisions is the part that doesn't come free.

**Badge unlocked: The Edge.** Four of four â€” The Tracker, The Decoder, The Automator, The Edge.

---

## Fixing common problems

Paste these as follow-ups. Describe the symptom, not your guess at the cause.

**The storage swap needed changes outside storage.py:**
```text
Swapping to Postgres required editing files other than storage.py, which
means rule 2 was violated somewhere. List every file that needed changing
and, for each, the exact line that reaches past the storage module. Then
refactor so those callers go through storage's interface and the backend is
invisible to them. I want to know which abstraction leaked before we
deploy.
```

**Postgres migration fails on upsert syntax:**
```text
--migrate or the first write fails on Postgres with a syntax error around
the upsert. SQLite's INSERT OR IGNORE has no direct Postgres equivalent â€”
show me where that statement is built and implement the dialect difference
INSIDE storage.py per rule 2, using ON CONFLICT DO NOTHING with the right
conflict target. Confirm the listing id is still the same stable hash so
existing dedup behaviour is unchanged.
```

**The app builds but crashes on startup:**
```text
The build succeeds but the app crashes when it starts. Show me the
full startup error, then tell me which of these it is: a missing
environment variable, an unreachable database, a dependency version that
differs from my local one, or a path that assumes local files. Per rule 50
the app must render a status message rather than crash â€” fix the root cause
AND make that path non-fatal.
```

**"Database not configured" on the deployed app but it works locally:**
```text
The deployed app says the database isn't configured; it works locally. Print
which environment variables the app actually sees at startup (names only,
never values). I suspect the deployed secret name doesn't match what the code
reads, that secrets are in the wrong format, or DATABASE_URL needs
?sslmode=require. Tell me which, and confirm
no value is ever printed.
```

**The scheduled workflow fails:**
```text
My GitHub Actions cycle job is failing. Read the workflow file and tell me
which step fails and why. Check specifically: secret names matching between
the workflow and my repository secrets, whether --migrate runs before
run_cycle.py, and whether the job exceeded its timeout. Do not add a retry â€”
rule 36 caps retries inside the cycle and a workflow retry would multiply
it.
```

**The workflow runs but the dashboard doesn't update:**
```text
The scheduled job completes successfully but my public dashboard shows the
same old timestamp. Confirm the workflow and the dashboard are pointed at
the SAME database â€” print the host from each side (host only, never
credentials). I suspect one is using DATABASE_URL and the other fell back to
local SQLite, which would explain a green job and a stale page.
```

**A stranger saw a traceback:**
```text
Someone opened my public URL and got a Python error instead of a page. Rule
50 says the app renders a status message in every failure case and a
stranger never sees a stack trace. Show me every panel and startup path that
isn't wrapped, and make each one degrade to a message. Log the detail
server-side so I can still debug it.
```

**I think I committed a secret:**
```text
I may have committed a secret. Show me the command to search the entire git
history (all branches) for the pattern, not just the current working tree.
If it is in history, tell me plainly that rotating the credential is the
only real fix and give me the steps to rotate both the Supabase database
password and the Gemini API key. Do not suggest rewriting history as a
substitute for rotation.
```

**Supabase project paused / connections refused after a few days:**
```text
My database connections started failing after several days of no activity.
Free-tier Supabase pauses inactive projects. Confirm whether that's what
happened, tell me how to resume it, and then confirm my scheduled daily
cycle is enough to keep it awake going forward. Per rule 50, also confirm
the dashboard shows a status message rather than crashing while the database
is paused.
```