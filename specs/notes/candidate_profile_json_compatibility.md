# Candidate Profile JSON Compatibility Note

Date: 2026-07-01
Phase: 0
Task: T0.5

## Purpose

This note records the Phase 0 compatibility check between the planned Research Agent read requirements and the existing Candidate Profile JSON contract referenced by the architecture documents.

## Result

Compatibility is **provisionally confirmed at the interface level**, but the source Candidate Profile schema is **not present in this repository** for direct validation.

## Research Agent Read Requirements

The current Research Agent design may reasonably need access to the following candidate-side fields:

- `target_roles`
- `target_industries`
- `preferred_locations`
- `seniority_level`
- `skills`
- `work_authorization`

These fields are not required for the minimum `{company_name, job_description}` execution path, but they are consistent with the prioritization behavior described in the problem statement and mission plan.

## Compatibility Assessment

- No blocking mismatch is visible in the current local repository because no conflicting schema is defined here.
- The Research Agent Phase 0 contracts do not hard-depend on Candidate Profile JSON for schema validation.
- Conductor-side integration should treat Candidate Profile JSON as an optional enrichment source until the canonical schema is checked into a shared repo or linked into this workspace.

## Follow-Up Required

- Add the canonical Candidate Profile JSON schema to the workspace when available.
- Validate that the eventual field names match the assumptions listed above.
- If field names differ, update only the adapter layer, not the Research Agent's core `CompanyBrief` contract.
