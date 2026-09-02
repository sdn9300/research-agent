"""
EdgeDash Subsystem 7: State-Driven Autonomous Orchestrator
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 7
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import Config, load_config
from .storage import Storage
from .state import read_state, SystemState
from .planning import build_plan, Plan
from .agents import (
    BaseAgent,
    AgentResult,
    MockFetcherAgent,
    FetcherAgent,
    ExtractorAgent,
    ScorerAgent,
    GapAnalyzerAgent,
    VerifierAgent,
)


class Orchestrator:
    """Master loop coordinating state inspection, task planning, and agent execution."""

    def __init__(self, config: Optional[Config] = None, storage: Optional[Storage] = None, use_mock_fetcher: bool = False):
        self.config = config or load_config()
        self.storage = storage or Storage(self.config.db_path)
        self.use_mock_fetcher = use_mock_fetcher

        # Registry of agent instances
        fetcher = MockFetcherAgent() if use_mock_fetcher else FetcherAgent()
        self.agents: Dict[str, BaseAgent] = {
            "fetcher": fetcher,
            "mock_fetcher": MockFetcherAgent(),
            "extractor": ExtractorAgent(),
            "scorer": ScorerAgent(),
            "gap_analyzer": GapAnalyzerAgent(),
            "verifier": VerifierAgent(),
        }

    def run_cycle(
        self,
        dry_run: bool = False,
        force_agent: Optional[str] = None,
        explain: bool = False,
    ) -> Dict[str, Any]:
        """Execute a full autonomous cycle."""
        cycle_id = f"cycle_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 1. Read State
        state = read_state(self.config, self.storage, now=now)

        # 2. Build Plan
        plan = build_plan(state, self.config, force_agent=force_agent)

        if explain:
            print("=" * 60)
            print(f"EDGEDASH PLAN EXPLANATION (Cycle: {cycle_id})")
            print("=" * 60)
            print(f"Total Listings:    {state.total_listings}")
            print(f"Unscored Queue:    {state.unscored_count}")
            print(f"Hours Since Fetch: {state.hours_since_fetch if state.hours_since_fetch is not None else 'N/A'}")
            print(f"Gaps Stale:        {state.gaps_stale}")
            print("-" * 60)
            for t in plan.tasks:
                status_icon = "[RUN]" if t.action == "run" else "[SKIP]"
                print(f"  {status_icon:<6} {t.agent_name:<15} Reason: {t.reason}")
            print("=" * 60)

        if dry_run:
            return {"cycle_id": cycle_id, "status": "dry_run", "plan": plan.model_dump()}

        if plan.is_noop and not force_agent:
            # Fast clean exit 0 per Rule 28
            self.storage.log_cycle_task(
                cycle_id=cycle_id,
                agent="orchestrator",
                started_at=now,
                finished_at=datetime.now(timezone.utc),
                records_touched=0,
                status="nothing_to_do",
                notes="All tasks skipped based on fresh state.",
            )
            return {"cycle_id": cycle_id, "status": "nothing_to_do", "plan": plan.model_dump()}

        # 3. Execute Scheduled Tasks
        results: List[AgentResult] = []
        context = {"cycle_id": cycle_id}

        for task in plan.tasks:
            if task.action != "run" and force_agent != task.agent_name:
                continue

            agent = self.agents.get(task.agent_name)
            if not agent:
                continue

            # Execute agent
            res = agent.execute(self.config, self.storage, context=context)
            results.append(res)

            # Log to cycle_log
            self.storage.log_cycle_task(
                cycle_id=cycle_id,
                agent=res.agent_name,
                started_at=res.started_at,
                finished_at=res.finished_at,
                records_touched=res.records_touched,
                status=res.status,
                notes=res.notes,
            )

        return {
            "cycle_id": cycle_id,
            "status": "completed",
            "tasks_executed": len(results),
            "results": [r.model_dump() for r in results],
        }
