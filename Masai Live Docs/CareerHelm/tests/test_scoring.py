"""
Tests for EdgeDash Deterministic Scoring Engine (Subsystem 5)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 2 Class 3
"""
import pytest
from datetime import datetime, timezone, timedelta
from edgedash.scoring import (
    score_listing,
    compute_skill_component,
    compute_seniority_component,
    compute_location_component,
    compute_recency_component,
)
from edgedash.config import Config, ScoringWeights


def test_skill_component_math():
    cand_skills = {"python", "pytorch", "fastapi"}
    # 2/3 required matched, 1/2 nice matched
    # s_skill = (2 + (1/3)*1) / (3 + (1/3)*2) = (2 + 0.333) / (3 + 0.666) = 2.333 / 3.666 = 0.636
    s_skill, matched, gaps = compute_skill_component(
        required_skills=["python", "pytorch", "kubernetes"],
        nice_to_have=["fastapi", "docker"],
        candidate_skills=cand_skills,
    )
    assert round(s_skill, 2) == 0.64
    assert set(matched) == {"python", "pytorch"}
    assert gaps == ["kubernetes"]


def test_recency_decay_math():
    now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # 0 days ago -> 1.0
    s_rec_0, d0 = compute_recency_component("2026-08-30T12:00:00Z", now=now)
    assert s_rec_0 == 1.0
    assert d0 == 0

    # 15 days ago -> 0.5
    s_rec_15, d15 = compute_recency_component("2026-08-15T12:00:00Z", now=now)
    assert round(s_rec_15, 2) == 0.5
    assert d15 == 15

    # 30+ days ago -> 0.0
    s_rec_30, d30 = compute_recency_component("2026-07-25T12:00:00Z", now=now)
    assert s_rec_30 == 0.0


def test_scoring_determinism_and_spread(sample_config):
    now = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Strong match
    strong_facts = {
        "required_skills": ["python", "pytorch", "fastapi"],
        "nice_to_have": ["docker", "sql"],
        "seniority": "mid",
        "years_required": 2,
        "remote_ok": True,
    }
    strong_meta = {"location": "Bengaluru", "posted_at": "2026-08-29T12:00:00Z"}
    score_1, reason_1, comp_1 = score_listing(strong_facts, strong_meta, sample_config, now=now)

    # Re-run on same inputs -> exact same score and reason (Determinism)
    score_1_repeat, reason_1_repeat, _ = score_listing(strong_facts, strong_meta, sample_config, now=now)
    assert score_1 == score_1_repeat
    assert reason_1 == reason_1_repeat
    assert score_1 >= 85

    # Weak match
    weak_facts = {
        "required_skills": ["c++", "rust", "cuda", "embedded"],
        "nice_to_have": ["assembly"],
        "seniority": "principal",
        "years_required": 10,
        "remote_ok": False,
    }
    weak_meta = {"location": "Frankfurt", "posted_at": "2026-07-01T12:00:00Z"}
    score_2, reason_2, comp_2 = score_listing(weak_facts, weak_meta, sample_config, now=now)

    assert score_2 <= 25

    # Assert score spread >= 15 (Plausibility criterion)
    spread = score_1 - score_2
    assert spread >= 50
