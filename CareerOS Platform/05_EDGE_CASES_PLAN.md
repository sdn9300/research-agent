# CareerOS Platform — Edge Cases Plan

## 1. Purpose

This plan defines how CareerOS detects, contains, explains, and recovers from edge cases. The central rule is:

> When confidence, identity, policy, or external-system state is uncertain, preserve evidence, avoid irreversible action, and route the decision to the candidate.

## 2. Severity model

| Severity | Meaning | Default response |
|---|---|---|
| P0 | Could cause unauthorized external action, data loss, or secret exposure. | Block action, quarantine event, alert operator. |
| P1 | Could corrupt lifecycle state, duplicate action, or materially misrepresent candidate/company facts. | Stop affected run, preserve evidence, require review. |
| P2 | Degrades quality or completeness but has a safe fallback. | Use fallback, create visible task/retry. |
| P3 | Cosmetic or non-critical observability issue. | Log and schedule repair. |

## 3. Identity and deduplication edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-01 | Same job has multiple board URLs with tracking parameters. | Duplicate outreach/application. | Normalize URL, compare source-independent fields, preserve source aliases, emit one canonical opportunity. |
| EC-02 | Same company/title but different location, level, requisition, or employment type. | False duplicate suppression. | Keep separate when a material discriminator differs; record resolution rationale. |
| EC-03 | Reposted role appears after expiry. | Permanent suppression of a legitimate new role. | Treat as a new observation; require explicit policy on repost-window and requisition match. |
| EC-04 | Recruiter email matches several historical applications. | Wrong lifecycle mutation. | Do not auto-link below confidence threshold; create a correlation-review task. |
| EC-05 | Company name changes after acquisition or uses staffing agency domain. | Cooldown/dedup bypass or false block. | Maintain aliases and recruiter/company-domain evidence; require candidate review for ambiguous company mapping. |
| EC-06 | Event is delivered more than once. | Duplicate state change/action. | Dedupe by event ID and idempotency key; record duplicate delivery without a second transition. |
| EC-07 | Event arrives out of order. | Invalid state progression. | Preserve raw event; apply only valid transitions or enqueue reconciliation; never discard silently. |

## 4. Candidate data, provenance, and RAG edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-08 | LLM adds a skill not in verified candidate evidence. | Resume fabrication. | Block claim or mark it as an explicit candidate-edit request; never export as verified. |
| EC-09 | Candidate Profile data is incomplete. | Bad form fill or wrong outreach. | Validate mandatory projection fields; stage a profile-completion task. |
| EC-10 | Candidate profile patch conflicts with another component's update. | Lost update/ownership violation. | Enforce section ownership and optimistic versioning; reject conflicting write with structured error. |
| EC-11 | Second Brain returns stale, irrelevant, or contradictory context. | Misleading draft or decision. | Return sources/relevance/timestamps; do not use for deterministic policy; flag low-confidence context. |
| EC-12 | Second Brain query or ingestion fails. | Context/projection gap. | Continue core lifecycle without optional RAG; queue idempotent projection retry and show reduced-context status. |
| EC-13 | Artifact hash matches but metadata differs. | Wrong resume or JD attached. | Treat content identity and metadata integrity separately; require both checks before action. |
| EC-14 | Raw artifact contains secrets or sensitive personal data. | Privacy breach. | Classify restricted, redact derivative projections, block telemetry export, and apply retention policy. |

## 5. Research and market-intelligence edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-15 | Research source is unavailable or rate-limited. | Incomplete company brief. | Return partial brief with explicit missing-source flag; never invent replacement facts. |
| EC-16 | Research claims lack source citations. | Hallucinated personalization. | Strip unsupported claims and mark research incomplete. |
| EC-17 | Job board returns anti-bot page, CAPTCHA, or malformed HTML. | False job data or scraping loop. | Capture diagnostic metadata, stop bounded retries, mark source degraded, use alternate source/manual import. |
| EC-18 | Job posting is suspicious, stale, or from an unverified company. | Scam exposure. | Fail qualification/policy check; prohibit auto-apply; require explicit candidate override with reason. |
| EC-19 | EdgeDash score is high but candidate preference conflicts. | Misleading ranking. | Candidate Profile preference policy wins; retain score as explanation only. |
| EC-20 | Skill trend signal comes from a private recruiter email. | Sensitive-data overcollection. | Emit only approved extracted keywords after redaction; never send raw body to Future Fit. |

## 6. Inbound email and calendar edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-21 | Auto-reply or mailing-list message is classified as recruiter intent. | Unwanted action. | Require sender/trust checks and auto-reply detection; stage no reply by default. |
| EC-22 | Email contains prompt injection or malicious instructions. | Unsafe tool/action invocation. | Treat message as untrusted content; never execute embedded instructions; classify only within a constrained schema. |
| EC-23 | Interview invitation has conflicting or missing timezone. | Incorrect booking. | Show timezone assumptions and require candidate confirmation. |
| EC-24 | Calendar time is already occupied or travel-infeasible. | Double booking. | Create a conflict proposal, not a calendar event; offer candidate-approved alternatives. |
| EC-25 | Recruiter uses a personal or agency email domain. | Wrong company association. | Do not infer company solely from sender domain; combine thread history, content, and candidate review. |
| EC-26 | A thread contains multiple roles or companies. | Wrong application linkage. | Split into separate reviewable interaction records; prohibit automatic single-application binding. |
| EC-27 | Message is a hard rejection after an offer/interview. | Invalid terminal transition. | Preserve raw event, apply allowed transition if policy permits, and surface conflict for review. |

## 7. Approval and action-execution edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-28 | Executor receives no approval ID. | Unauthorized action. | P0: reject before side effect and log policy denial. |
| EC-29 | Approval has expired, is consumed, or is for another payload. | Replay or payload substitution. | P0: reject; require new approval. |
| EC-30 | Candidate edits email, recipient, resume, form response, URL, or meeting time after approval. | Approval no longer represents action. | Invalidate old approval and create a replacement request. |
| EC-31 | Network timeout happens after an external send/submit may have completed. | Duplicate external action on retry. | Query external provider idempotency/status where possible; otherwise hold for review and record uncertain outcome. |
| EC-32 | Gmail, calendar, or ATS credentials are absent/expired. | Failed action or accidental fallback. | Never simulate a confirmed live success; return retryable failure or draft/manual packet. |
| EC-33 | ATS requires CAPTCHA, MFA, unsupported widget, or browser download. | Unsafe/unreliable automation. | Stop at a reviewable session artifact; do not bypass anti-automation controls. |
| EC-34 | Form contains free-text diversity, legal, compensation, or work-authorization questions. | Harmful or incorrect answer. | Require candidate review and a freshly approved response; never auto-submit LLM text. |
| EC-35 | Company is in active rejection cooldown. | Spam/reputation damage. | Suppress action by default; only candidate-approved policy override can reopen it. |
| EC-36 | Outreach rate limit is reached. | Spam or account suspension. | Defer action and expose earliest eligible execution time. |

## 8. Event, storage, and recovery edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-37 | Process crashes after event commit but before publication. | Missing projection/notification. | Transactional outbox dispatcher republishes committed event after restart. |
| EC-38 | Consumer crashes after side effect but before acknowledgement. | Duplicate work. | Use idempotent consumer record and external idempotency token; reconcile uncertain actions. |
| EC-39 | Schema version is unsupported. | Unsafe misinterpretation. | Quarantine event, retain raw envelope, alert operator, and do not process. |
| EC-40 | Materialized application table diverges from event replay. | State corruption. | Stop automatic action for affected record, rebuild, compare, and preserve discrepancy evidence. |
| EC-41 | Disk/database is full or locked. | Lost/corrupt writes. | Fail closed before action; emit operational alert; recover from backups/outbox. |
| EC-42 | Clock skew or daylight-saving transition alters event ordering. | Incorrect cooldown/expiry. | Store UTC timestamps, retain received time, and use server-side monotonic ordering where available. |
| EC-43 | Event payload contains invalid PII classification. | Privacy-policy violation. | Reject or quarantine before fan-out; do not write to broad telemetry. |

## 9. Observability and security edge cases

| ID | Scenario | Risk | Required behavior |
|---|---|---|---|
| EC-44 | Log entry includes email body, token, cookie, or resume content. | Sensitive-data leak. | Redaction test fails release; rotate exposed credential and remediate retained logs. |
| EC-45 | Correlation ID is missing across an adapter boundary. | Untraceable workflow. | Mark run degraded; emit instrumentation error; prevent graduation if systemic. |
| EC-46 | Model/provider changes output shape or availability. | Silent quality regression. | Pin contract/output parser, run canaries, apply fallback, and record model/version metadata. |
| EC-47 | Malicious job page or email attempts prompt injection. | Tool misuse/data exposure. | Separate instructions from untrusted content, constrain tools, and treat content only as data. |
| EC-48 | Secrets are copied between projects or committed. | Account compromise. | Enforce secret scanning, per-component credentials, and documented rotation/revocation procedure. |

## 10. Fallback matrix

| Dependency failure | Safe fallback | Never do |
|---|---|---|
| Job board / EdgeDash | Use last known observations or manual import. | Invent job details. |
| Research Agent | Proceed with a flagged incomplete brief. | Present uncited company claims as facts. |
| Second Brain | Continue core lifecycle; retry projection. | Block or mutate lifecycle from missing RAG. |
| Sentiment Classifier | Use deterministic low-confidence triage and review. | Auto-send based on guessed intent. |
| Candidate Profile | Halt action preparation and request profile completion. | Substitute invented candidate data. |
| Memory Module | Halt new action creation and preserve local pending evidence. | Perform an unlogged external action. |
| Gmail / Calendar / ATS | Produce draft/manual packet and retry guidance. | Claim external success after a failed call. |
| Approval service | Keep all executors dry-run/blocked. | Trust a stale local UI approval flag. |

## 11. Incident procedure

For P0 or P1 incidents:

1. Immediately disable affected live executor capability by configuration/credential isolation.
2. Preserve event, artifact, correlation, and approval evidence without altering history.
3. Determine whether an external side effect actually occurred.
4. Reconcile application state through event replay and provider status checks.
5. Notify the candidate of the impact and required human decision.
6. Fix the contract, policy, or idempotency gap; add a deterministic regression fixture.
7. Re-enable only after the new negative test passes and the incident record is complete.

## 12. Edge-case exit criteria

The platform is ready for governed live use only when every P0/P1 scenario has an automated test or documented manual drill, all action-executor bypass tests pass, every fallback produces a visible candidate-facing state, and incident recovery can reproduce the lifecycle from the durable event ledger.
