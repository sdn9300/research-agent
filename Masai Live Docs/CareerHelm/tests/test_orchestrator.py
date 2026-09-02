"""
Tests for EdgeDash Orchestrator & End-to-End Autonomous Loop (Subsystem 7)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 1 Class 1 & Week 3 Class 5
"""
import pytest
from edgedash.config import Config
from edgedash.storage import Storage
from edgedash.orchestrator import Orchestrator


def test_end_to_end_orchestration_cycle(tmp_path):
    db_file = tmp_path / "test_loop.db"
    cfg = Config(
        target_role="Machine Learning Engineer",
        target_city="Bengaluru",
        my_skills=["python", "pytorch", "fastapi", "docker"],
        experience_years=2,
        score_batch_size=20,
        fetch_interval_hours=6,
        db_path=str(db_file),
    )
    storage = Storage(db_path=str(db_file))
    orchestrator = Orchestrator(config=cfg, storage=storage, use_mock_fetcher=True)

    # 1. First cycle: full execution
    res1 = orchestrator.run_cycle()
    assert res1["status"] == "completed"
    assert res1["tasks_executed"] >= 4

    # Verify listings were inserted and scored
    scored = storage.get_all_scored_listings()
    assert len(scored) == 12
    assert all(s["fit_score"] is not None for s in scored)

    # Verify skill gaps computed
    gaps = storage.get_latest_skill_gaps()
    assert len(gaps) > 0

    # Verify verdict recorded
    verdict = storage.get_latest_verdict()
    assert verdict is not None
    assert verdict["verdict"] in ("pass", "fail")

    # 2. Second immediate cycle: should be a clean no-op
    res2 = orchestrator.run_cycle()
    assert res2["status"] == "nothing_to_do"
    assert res2["plan"]["is_noop"] is True
