# PDF Auto-Apply Agent — Evaluation Plan

| Field | Value |
|---|---|
| Document ID | `PAA-EP-1.0` |
| Component | CONDUCTOR Component 7 — PDF Auto-Apply Agent (proposed codename: **Usher**) |
| Layer | Application |
| Version | 1.0 |
| Status | Draft — Pending Review |
| Date | 27 August 2026 |
| Depends On | `PAA-AD-1.0`, `PAA-IP-1.0` |

---

## 1. Evaluation Philosophy

Tiered gates, hard-blocking versus monitoring, exactly as already applied to the Sentiment Classifier: a small number of criteria are absolute (a single violation fails the release regardless of every other number), while the rest are weighted and tracked as trends. Correctness is a hard gate here specifically because this component's failure mode — wrong data reaching a real recruiter under the candidate's real name — is qualitatively worse than a failure mode measured only in lost time.

## 2. Metrics Framework

| Metric | Definition | Class |
|---|---|---|
| **Zero-fabrication guarantee** | Any submitted field value not traceable to Candidate Profile JSON, AlignResume output, or explicit candidate confirmation. | **Hard gate.** A single confirmed instance is a P0 defect, full stop. |
| **False-confidence rate** | Attempts where the resolver reported high confidence but the value was actually wrong, discovered on audit. | **Hard gate, near-zero tolerance.** This is the single most safety-critical metric in the whole plan — it measures the exact failure mode the confidence threshold exists to prevent. |
| Field-mapping accuracy | % of standard fields correctly auto-filled vs. audited ground truth. | Weighted |
| Attachment success rate | % of attempts where the correct, checksum-verified resume PDF was uploaded. | Weighted |
| Submission funnel breakdown | % of attempts landing in each of `SUBMITTED` / `DRAFT_PENDING_REVIEW` / `MANUAL_REQUIRED` / `AMBIGUOUS_OUTCOME` / `FAILED` / `SKIPPED`. | Monitoring |
| Time-to-complete | Automated vs. manual baseline (Problem Statement §9). | Weighted |
| Human intervention rate | % of attempts requiring manual takeover, trending down across phases. | Monitoring |
| Cost per application | Groq token cost per attempt. | Weighted |
| **Platform Standing** | Any account flag/warning/lockout incident. | **Hard gate.** Zero-tolerance monitoring metric — any incident triggers the rollback defined in Mission Plan §6, independent of all other scores. |

## 3. Test Methodology

- **Unit tests** per adapter, run against saved fixture HTML/DOM snapshots — fast, deterministic, no live platform interaction.
- **Integration tests** run in `DRAFT` mode only, against real platforms but never auto-submitted during testing — a test batch is manually audited, never silently trusted, and is never used to spam real postings with throwaway or duplicate applications.
- **Manual review checklist**, required before any platform is first unlocked into `AUTO` mode — a human-run sign-off, not a metric threshold alone.
- **Adapter Health Check** (§6) as an ongoing, low-frequency smoke test distinct from both of the above.

## 4. Weighted Scoring Rubric

Applied at each phase gate, on top of the hard gates in §2:

| Criterion | Weight | What it measures |
|---|---|---|
| Field Coverage | 25% | % of fields resolved (any tier) without falling to `MANUAL_REQUIRED`. |
| Confidence Calibration | 20% | How well reported confidence scores predict actual correctness on audited samples. |
| Latency | 15% | Wall-clock time from target received to `DRAFT_PENDING_REVIEW` / `SUBMITTED`. |
| Cost | 15% | Groq token cost per attempt. |
| Auditability | 15% | % of attempts producing a complete, replayable audit record (screenshot + structured log). |
| Platform Standing (weighted component) | 10% | Trend, independent of the hard-gate treatment in §2. |

```
FinalScore = 0.25·Coverage + 0.20·Calibration + 0.15·Latency_norm
           + 0.15·Cost_norm + 0.15·Auditability + 0.10·PlatformStanding

subject to: ZeroFabrication = TRUE  AND  FalseConfidenceRate ≈ 0   (hard gates — override the score to FAIL if violated)
```

## 5. Acceptance Gates per Phase

| Phase | Gate |
|---|---|
| 1 (Naukri) | ≥95% field accuracy on standard fields (audited); 0 fabrication incidents; ≥90% of the 20-application batch reach `DRAFT_PENDING_REVIEW` cleanly. |
| 2 (Indeed, LinkedIn) | Each new adapter independently meets Phase 1's accuracy bar before AUTO-mode graduation is even considered for that platform. |
| **AUTO-mode graduation (any platform)** | A minimum run of consecutive, clean `DRAFT`-mode attempts on that specific platform with **zero** manual corrections required — the exact count is set per platform at Phase 2 kickoff and recorded here once fixed, mirroring the candidate's own Adaptive Coding Examiner's level-up logic (correct → advance, any failure → reset). |
| 3 (Generic ATS) | ≥70% posting-coverage metric; `GenericATSAdapter` fallback never exceeds `DRAFT_PENDING_REVIEW` — it is never eligible for AUTO mode, given its inherently higher uncertainty. |
| 4 (Integration) | One full end-to-end orchestrated run, `ApplicationAttemptResult` correctly consumed downstream. |

## 6. Regression Testing & Adapter Health Monitoring

Platform DOMs change without notice — this is the primary ongoing maintenance risk for the entire component. Mitigation:

- **Adapter Health Check**: a scheduled, low-volume smoke run per active adapter (detect + map_fields against a known fixture posting) that surfaces selector breakage *before* it silently degrades a real attempt.
- **Root-cause-first repair**: when a selector breaks, the fix targets the specific DOM element that changed — never a broadened selector that risks a new false-positive match elsewhere. This mirrors the root-cause debugging principle already applied across the Linux and MySQL learning logs.
- **Regression suite** re-run whenever an adapter's selector dictionary is modified, before that adapter is trusted again in `AUTO` mode.

## 7. Continuous Monitoring Post-Launch

Once Phase 4 exits, the following run continuously rather than as one-time gates: Platform Standing (§2), false-confidence rate on a rolling audit sample, cost-per-application trend, and Adapter Health Check results. Any Platform Standing incident, at any point, immediately and manually reverts that platform to `DRAFT`-only — this rollback is never automatic re-approved by the passage of time alone (Mission Plan §6).

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-08-27 | Initial draft. |
