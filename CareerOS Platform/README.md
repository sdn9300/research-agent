# CareerOS Platform

CareerOS Platform is the integration blueprint for a unified, human-supervised job-search ecosystem. It connects the existing AI Native Job Agent components with the knowledge, inbox, and market-intelligence systems in Masai Live Docs without absorbing or rewriting those projects.

## Documentation suite

1. [Problem statement](00_PROBLEM_STATEMENT.md)
2. [Mission plan](01_MISSION_PLAN.md)
3. [Architecture design](02_ARCHITECTURE_DESIGN.md)
4. [Phase-wise implementation plan](03_PHASE_WISE_IMPLEMENTATION_PLAN.md)
5. [Evaluation plan](04_EVALUATION_PLAN.md)
6. [Edge-cases plan](05_EDGE_CASES_PLAN.md)

## Design decision in one sentence

Use Conductor as the only lifecycle coordinator; use the Candidate Profile and Memory Module as the canonical data layer; connect Second Brain, EdgeDash, and Chief of Staff through versioned contracts, events, and governed adapters.

## Scope

This folder contains planning and design material only. It does not move, modify, or replace any existing component project.
