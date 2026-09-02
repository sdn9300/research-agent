# PDF Auto-Apply Agent — Edge Case Plan

| Field | Value |
|---|---|
| Document ID | `PAA-EC-1.0` |
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent (proposed codename: **Usher**) |
| Layer | Application |
| Version | 1.0 |
| Status | Draft — Pending Review |
| Date | 27 August 2026 |
| Registry size | 28 scenarios across 7 categories |

---

## 1. Registry Structure & Conventions

Each entry follows the same convention already used for the Sentiment Classifier's `EC-AMBIG-010` and the FIFA project's edge case registry: `EC-PAA-[CATEGORY]-[NN]`. Every entry names the trigger, how it's detected, what the system does, and its severity. Per the fallback-artifact principle carried through every other document in this suite, **no edge case below ever results in silence** — every one of them terminates in a specific, structured `ApplicationAttemptResult` status.

| Category code | Domain |
|---|---|
| `DOM` | Platform & DOM variability |
| `MAP` | Field mapping ambiguity |
| `DAT` | Data integrity & Candidate Profile sync |
| `SEC` | Anti-automation & security |
| `ATT` | Attachment & document handling |
| `SUB` | Submission & post-submission |
| `ETH` | Ethical / compliance boundaries |

## 2. Category DOM — Platform & DOM Variability

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-DOM-01` | Platform A/B-tests a redesigned apply-flow layout mid-operation | `fill()` raises element-not-found after timeout | Abort attempt → `FAILED`, `error_code=SELECTOR_MISS`; adapter flagged for health-check review | Medium — monitoring |
| `EC-PAA-DOM-02` | Multi-step wizard inserts an unexpected intermediate step not in the adapter's known sequence | Expected next-step marker absent | → `MANUAL_REQUIRED`, screenshot of the unrecognized step captured | Medium |
| `EC-PAA-DOM-03` | Submit control present but disabled pending an unrelated platform nag (e.g., "complete your profile first") | Submit element has a `disabled` attribute | → `MANUAL_REQUIRED`, reason recorded | Low |
| `EC-PAA-DOM-04` | Job posting already expired/closed by the time the agent visits (Gleaner's snapshot is stale) | Platform renders a "no longer accepting applications" banner | → `SKIPPED`, `error_code=POSTING_EXPIRED`; staleness signal fed back toward Gleaner's freshness window | Low |

## 3. Category MAP — Field Mapping Ambiguity

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-MAP-01` | Free-text "Expected CTC / Salary Expectation" field | Field label matches a maintained ambiguous-field dictionary | Never auto-filled from a guess; `MANUAL_REQUIRED` unless Candidate Profile JSON has an explicit `salary_expectation` set by the candidate | High — financial/negotiation sensitivity |
| `EC-PAA-MAP-02` | "Notice period" field, no employment history to compute one from (fresher case) | Source field absent in profile | Use an explicit fresher-default only if the candidate has set one; otherwise `MANUAL_REQUIRED` | Medium |
| `EC-PAA-MAP-03` | Open-ended "Why do you want to work here?" box | Field type = long free text, no structured equivalent exists | Tier-3 LLM draft, grounded only in Candidate Profile JSON + Research Agent brief + AlignResume rationale; **always** routed to `DRAFT_PENDING_REVIEW`, even in `AUTO` mode | High — voice/authenticity risk |
| `EC-PAA-MAP-04` | Field label ambiguous or CSS-truncated (e.g., "Curr…" could mean current CTC or current company) | Resolution confidence < 0.85 | Forced `MANUAL_REQUIRED`, regardless of which tier produced the guess | Medium |

## 4. Category DAT — Data Integrity & Candidate Profile Sync

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-DAT-01` | Candidate Profile JSON missing a field the target form marks required | Pre-fill schema validation against the form's required-field set fails | Abort *before* touching the browser → `SKIPPED`, `error_code=PROFILE_INCOMPLETE`, missing fields listed | High |
| `EC-PAA-DAT-02` | Candidate Profile JSON is stale relative to reality (e.g., education status changed) | `last_verified_at` timestamp exceeds a 30-day staleness threshold | Non-blocking warning surfaced at session start and logged into every attempt that session | Medium |
| `EC-PAA-DAT-03` | AlignResume's tailored PDF was generated against an older Candidate Profile JSON version than the one currently in use | `TailoringRun.profile_version` hash mismatch | `MANUAL_REQUIRED`, flagged for AlignResume re-tailoring | Medium |
| `EC-PAA-DAT-04` | Two near-duplicate postings from Gleaner (same role, same company, different URLs) | Fuzzy match on `{company, title, location}` before attempting | Second occurrence → `SKIPPED` as `DUPLICATE_TARGET`, cross-referenced against Memory Module history | Low |

## 5. Category SEC — Anti-Automation & Security

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-SEC-01` | CAPTCHA / challenge screen appears mid-flow | Known CAPTCHA DOM fingerprint or iframe pattern | Immediate `MANUAL_REQUIRED`, screenshot captured — **no solve or bypass attempt, ever** (ADR-PAA-004) | High — hard rule, non-negotiable |
| `EC-PAA-SEC-02` | Session cookie/token expires mid-application | Unexpected redirect to a login page | Abort → `FAILED`, `error_code=SESSION_EXPIRED`; remaining queue for that platform halts until re-authentication | Medium |
| `EC-PAA-SEC-03` | Platform rate limit or soft block triggered after N attempts in a session | Repeated `FAILED` results in a short window, or an explicit "unusual activity" banner | Circuit breaker halts all further attempts on that platform for a cool-down period; candidate notified | High |
| `EC-PAA-SEC-04` | Platform explicitly flags/warns the account for automated behavior | Account-level warning banner or notice (human-reported, not machine-detected) | Immediate, manual, permanent rollback of that platform to `DRAFT`-only — never automatically restored to `AUTO`; logged as a Platform Standing incident (Evaluation Plan §2) | Critical |

## 6. Category ATT — Attachment & Document Handling

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-ATT-01` | Resume PDF upload silently fails (network hiccup, file-picker timing) | Post-upload DOM check for filename confirmation is absent | Retry once with backoff; else `FAILED`, `error_code=UPLOAD_FAILED` | Medium |
| `EC-PAA-ATT-02` | Platform enforces a file type AlignResume's output doesn't produce (e.g., DOCX-only field) | Platform validation error text detected | `MANUAL_REQUIRED`; backlog item raised for AlignResume to add a DOCX export path | Low |
| `EC-PAA-ATT-03` | Wrong resume version attached — a stale cached file from a prior run | Checksum mismatch between the attached file and AlignResume's latest `TailoringRun` for this job | `FAILED`, submission blocked entirely — this is treated as a correctness failure, not a retriable glitch | High |
| `EC-PAA-ATT-04` | Platform requires a separate cover-letter file distinct from the resume | A second, distinctly labeled upload field detected | `MANUAL_REQUIRED` unless a cover-letter artifact contract is added in a later phase | Low |

## 7. Category SUB — Submission & Post-Submission

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-SUB-01` | Confirmation page/toast is ambiguous — no clear "application submitted" signal | No match against the adapter's known confirmation-pattern signatures | **Never assume success.** → `AMBIGUOUS_OUTCOME` for human verification | High — a false-positive success is the single worst outcome class in this whole system |
| `EC-PAA-SUB-02` | Already applied to this exact job previously | Pre-flight check against Memory Module history before attempting | `SKIPPED` as `ALREADY_APPLIED` | Low |
| `EC-PAA-SUB-03` | Platform requires account creation before the apply flow even begins | Apply link routes to a signup wall | `MANUAL_REQUIRED` — explicitly out of scope through Phase 3 | Low |
| `EC-PAA-SUB-04` | Multi-page redirect chain lands on a third-party ATS not yet supported | Final landing domain not in the adapter registry | Routed through `GenericATSAdapter`'s Tier-3 fallback if Phase ≥3; otherwise `MANUAL_REQUIRED` | Medium |

## 8. Category ETH — Ethical / Compliance Boundaries

| ID | Trigger | Detection | System Response | Severity |
|---|---|---|---|---|
| `EC-PAA-ETH-01` | Platform's Terms of Service explicitly and unambiguously prohibit automated submission | Manually curated per-platform compliance flag, set at adapter-registration time — never runtime-detected | That platform is excluded from Auto-Apply entirely at the config level; its Gleaner-sourced postings route straight to `MANUAL_REQUIRED` | Critical — policy, not a bug |
| `EC-PAA-ETH-02` | Job posting later identified as fraudulent or a scam listing | Research Agent's company-verification flag on the `JobApplicationTarget` | `SKIPPED`, never attempted | High |
| `EC-PAA-ETH-03` | A screening question solicits information not legitimately required for the role (e.g., religion, marital status) | Field label matched against a maintained sensitive-question dictionary | `MANUAL_REQUIRED`, never auto-answered under any circumstance | High |
| `EC-PAA-ETH-04` | Same posting reachable via two different Gleaner channels, risking a recruiter seeing duplicate submissions | Cross-referenced at Candidate Profile / Memory Module level (cross-platform version of `EC-PAA-DAT-04`) | Only the higher-priority channel is attempted | Medium |

## 9. Summary

| Category | Count | Highest severity present |
|---|---|---|
| DOM | 4 | Medium |
| MAP | 4 | High |
| DAT | 4 | High |
| SEC | 4 | **Critical** |
| ATT | 4 | High |
| SUB | 4 | High |
| ETH | 4 | **Critical** |
| **Total** | **28** | — |

The two `Critical` entries (`EC-PAA-SEC-04`, `EC-PAA-ETH-01`) are the only cases in this registry that produce a *permanent, manually-gated* state change rather than a per-attempt outcome — by design, since both represent the system learning something true about a platform's posture toward it, not a one-off glitch to retry past.

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial draft — 28 scenarios across 7 categories. |
