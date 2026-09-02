"""
Tests for EdgeDash Configuration Module (Subsystem 1)
"""
import pytest
from edgedash.config import Config, ScoringWeights, load_config


def test_config_defaults():
    cfg = Config()
    assert cfg.target_role == "Machine Learning Engineer"
    assert cfg.weights.skill == 0.45
    assert cfg.weights.seniority == 0.25
    assert cfg.experience_years == 2


def test_invalid_weights_raise_validation_error():
    with pytest.raises(ValueError):
        ScoringWeights(skill=1.5)


def test_load_config_fallback_nonexistent(tmp_path):
    non_existent = tmp_path / "non_existent.yaml"
    cfg = load_config(non_existent)
    assert cfg is not None
    assert cfg.target_role == "Machine Learning Engineer"
