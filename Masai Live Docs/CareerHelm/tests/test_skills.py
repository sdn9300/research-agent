"""
Tests for EdgeDash Skill Canonicalisation & Opportunity Cost Gap Analyzer (Subsystem 6)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 2 Class 4
"""
import pytest
from edgedash.skills import canonical, analyze_skill_gaps


def test_canonical_skill_normalization():
    aliases = {"k8s": "kubernetes", "postgres": "postgresql"}

    assert canonical("  Python  ") == "python"
    assert canonical("Kubernetes (EKS)") == "kubernetes"
    assert canonical("k8s", aliases) == "kubernetes"
    assert canonical("Postgres", aliases) == "postgresql"
    assert canonical("C++ / CUDA") == "c++ / cuda"


def test_analyze_skill_gaps_opportunity_cost():
    scored_listings = [
        {
            "id": "job_1",
            "fit_score": 80,
            "components": '{"gaps": ["kubernetes", "spark"]}',
        },
        {
            "id": "job_2",
            "fit_score": 90,
            "components": '{"gaps": ["kubernetes", "aws"]}',
        },
        {
            "id": "job_3",
            "fit_score": 70,
            "components": '{"gaps": ["spark"]}',
        },
    ]

    candidate_skills = {"python", "pytorch", "fastapi"}
    gaps = analyze_skill_gaps(scored_listings, candidate_skills)

    # Opportunity costs:
    # kubernetes: (80 + 90) / 100 = 1.70 (blocked 2 jobs)
    # spark: (80 + 70) / 100 = 1.50 (blocked 2 jobs)
    # aws: 90 / 100 = 0.90 (blocked 1 job)

    assert len(gaps) == 3
    assert gaps[0]["skill"] == "kubernetes"
    assert gaps[0]["opportunity_cost"] == 1.7
    assert gaps[0]["listings_blocked"] == 2

    assert gaps[1]["skill"] == "spark"
    assert gaps[1]["opportunity_cost"] == 1.5

    assert gaps[2]["skill"] == "aws"
    assert gaps[2]["opportunity_cost"] == 0.9
