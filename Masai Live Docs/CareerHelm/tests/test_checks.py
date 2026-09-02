"""
Tests for EdgeDash Plausibility Checks & Verifier (Subsystem 8)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 3 Class 6
"""
import pytest
from edgedash.checks import (
    check_score_spread,
    check_unscored_residuals,
    check_volume_stability,
    check_gap_consistency,
)


def test_score_spread_check():
    # Passing spread >= 10
    scored_pass = [{"fit_score": 85}, {"fit_score": 50}, {"fit_score": 30}]
    v_pass = check_score_spread(scored_pass, min_spread=10.0)
    assert v_pass.passed
    assert v_pass.observed_value == 55.0

    # Failing spread < 10 (e.g. weights flattened)
    scored_fail = [{"fit_score": 50}, {"fit_score": 52}, {"fit_score": 51}]
    v_fail = check_score_spread(scored_fail, min_spread=10.0)
    assert not v_fail.passed
    assert v_fail.observed_value == 2.0


def test_unscored_residuals_check():
    assert check_unscored_residuals(20).passed
    assert not check_unscored_residuals(600).passed


def test_volume_stability_check():
    assert check_volume_stability(12, min_expected=1).passed
    assert not check_volume_stability(0, min_expected=1).passed


def test_gap_consistency_check():
    # Gap list containing candidate's known skill is an inconsistency
    candidate_skills = ["python", "fastapi", "docker"]
    clean_gaps = [{"skill": "kubernetes"}, {"skill": "spark"}]
    assert check_gap_consistency(clean_gaps, candidate_skills).passed

    inconsistent_gaps = [{"skill": "python"}, {"skill": "kubernetes"}]
    assert not check_gap_consistency(inconsistent_gaps, candidate_skills).passed
