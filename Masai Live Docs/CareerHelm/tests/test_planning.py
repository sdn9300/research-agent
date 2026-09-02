"""
Tests for EdgeDash State Reader & Pure Planning Engine (Subsystem 7)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 3 Class 5
"""
import pytest
from datetime import datetime, timezone
from edgedash.config import Config
from edgedash.state import SystemState
from edgedash.planning import build_plan


def test_initial_state_plans_full_cycle():
    cfg = Config()
    initial_state = SystemState(
        now=datetime.now(timezone.utc),
        hours_since_fetch=None,
        unscored_count=0,
        gaps_stale=True,
        total_listings=0,
    )

    plan = build_plan(initial_state, cfg)
    assert not plan.is_noop

    task_map = {t.agent_name: t.action for t in plan.tasks}
    assert task_map["fetcher"] == "run"
    assert task_map["extractor"] == "run"
    assert task_map["scorer"] == "run"
    assert task_map["gap_analyzer"] == "run"
    assert task_map["verifier"] == "run"


def test_fresh_state_plans_noop_clean_exit():
    cfg = Config(fetch_interval_hours=6)
    fresh_state = SystemState(
        now=datetime.now(timezone.utc),
        hours_since_fetch=1.5,  # Fresh!
        unscored_count=0,       # Empty queue!
        gaps_stale=False,       # Fresh gaps!
        total_listings=50,
    )

    plan = build_plan(fresh_state, cfg)
    assert plan.is_noop
    assert all(t.action == "skip" for t in plan.tasks)


def test_unscored_queue_triggers_scorer_without_fetcher():
    cfg = Config(fetch_interval_hours=6)
    unscored_state = SystemState(
        now=datetime.now(timezone.utc),
        hours_since_fetch=2.0,  # Fresh fetch
        unscored_count=15,      # Unscored items pending
        gaps_stale=False,
        total_listings=50,
    )

    plan = build_plan(unscored_state, cfg)
    assert not plan.is_noop
    task_map = {t.agent_name: t.action for t in plan.tasks}
    assert task_map["fetcher"] == "skip"
    assert task_map["extractor"] == "run"
    assert task_map["scorer"] == "run"
