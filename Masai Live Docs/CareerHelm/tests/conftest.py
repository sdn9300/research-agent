import pytest
import tempfile
import os
from pathlib import Path
from edgedash.config import Config, ScoringWeights
from edgedash.storage import Storage


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_edgedash.db"
    return Storage(db_path=str(db_file))


@pytest.fixture
def sample_config(tmp_path):
    db_file = tmp_path / "test_config_edgedash.db"
    return Config(
        target_role="Machine Learning Engineer",
        target_city="Bengaluru",
        keywords=["python", "machine learning", "fastapi"],
        my_skills=["python", "pytorch", "fastapi", "sql", "docker"],
        experience_years=2,
        weights=ScoringWeights(skill=0.45, seniority=0.25, location=0.15, recency=0.15),
        score_batch_size=20,
        fetch_interval_hours=6,
        skill_aliases={"postgres": "postgresql", "k8s": "kubernetes"},
        db_path=str(db_file),
    )
