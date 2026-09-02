"""
EdgeDash Subsystem 7: Pure Decision Planning Engine
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 7 (Rule 29: Pure planning logic)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .config import Config
from .state import SystemState


class Task(BaseModel):
    agent_name: str
    action: str  # run | skip
    reason: str
    params: Dict[str, Any] = Field(default_factory=dict)


class Plan(BaseModel):
    tasks: List[Task]
    is_noop: bool = False
    summary: str = ""


def build_plan(
    state: SystemState,
    config: Config,
    force_agent: Optional[str] = None,
) -> Plan:
    """Pure decision logic determining which agents need to execute.
    Evaluates fetch interval, unscored queue, and gap freshness.
    """
    tasks: List[Task] = []

    # 1. Task: Fetcher
    should_fetch = (
        force_agent == "fetcher"
        or state.hours_since_fetch is None
        or state.hours_since_fetch >= config.fetch_interval_hours
        or state.total_listings == 0
    )
    if should_fetch:
        tasks.append(Task(
            agent_name="fetcher",
            action="run",
            reason=f"Fetch interval elapsed ({state.hours_since_fetch:.1f}h >= {config.fetch_interval_hours}h)" if state.hours_since_fetch else "Initial fetch required",
        ))
    else:
        tasks.append(Task(
            agent_name="fetcher",
            action="skip",
            reason=f"Fresh ({state.hours_since_fetch:.1f}h < {config.fetch_interval_hours}h)",
        ))

    # 2. Task: Extractor & Scorer
    should_score = (
        force_agent in ("extractor", "scorer")
        or should_fetch
        or state.unscored_count > 0
    )
    if should_score:
        tasks.append(Task(
            agent_name="extractor",
            action="run",
            reason=f"{state.unscored_count} unscored listings in queue",
            params={"batch_size": config.score_batch_size},
        ))
        tasks.append(Task(
            agent_name="scorer",
            action="run",
            reason=f"Score up to {config.score_batch_size} listings",
            params={"batch_size": config.score_batch_size},
        ))
    else:
        tasks.append(Task(
            agent_name="extractor",
            action="skip",
            reason="0 unscored listings",
        ))
        tasks.append(Task(
            agent_name="scorer",
            action="skip",
            reason="0 unscored listings",
        ))

    # 3. Task: Gap Analyzer
    should_analyze_gaps = (
        force_agent == "gap_analyzer"
        or should_score
        or state.gaps_stale
    )
    if should_analyze_gaps:
        tasks.append(Task(
            agent_name="gap_analyzer",
            action="run",
            reason="Gaps stale or new scored listings available",
        ))
    else:
        tasks.append(Task(
            agent_name="gap_analyzer",
            action="skip",
            reason="Gaps fresh (< 24h old)",
        ))

    # 4. Task: Verifier
    if any(t.action == "run" for t in tasks):
        tasks.append(Task(
            agent_name="verifier",
            action="run",
            reason="Verify cycle plausibility across updated data",
        ))
    else:
        tasks.append(Task(
            agent_name="verifier",
            action="skip",
            reason="No data modified in this cycle",
        ))

    is_noop = all(t.action == "skip" for t in tasks)
    summary = "Nothing to do (All tasks skipped)" if is_noop else f"{sum(1 for t in tasks if t.action == 'run')} tasks scheduled to run"

    return Plan(tasks=tasks, is_noop=is_noop, summary=summary)
