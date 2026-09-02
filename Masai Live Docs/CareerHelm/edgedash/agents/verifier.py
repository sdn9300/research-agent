"""
EdgeDash Subsystem 8: Verifier Agent
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 8 (Rules 34-39: Stale beats wrong)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from ..checks import (
    check_score_spread,
    check_unscored_residuals,
    check_gap_consistency,
)


class VerifierAgent(BaseAgent):
    name: str = "verifier"

    def execute(self, config: Any, storage: Any, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        started = datetime.now(timezone.utc)
        cycle_id = (context or {}).get("cycle_id", "manual_run")

        scored = storage.get_all_scored_listings()
        unscored = storage.get_unscored_listings(limit=1000)
        latest_gaps = storage.get_latest_skill_gaps(limit=20)

        # 1. Score Spread Check
        v_spread = check_score_spread(scored, min_spread=10.0)
        # 2. Unscored Residual Check
        v_resid = check_unscored_residuals(len(unscored), batch_size=config.score_batch_size)
        # 3. Gap Consistency Check
        v_gap = check_gap_consistency(latest_gaps, config.my_skills)

        all_checks = [v_spread, v_resid, v_gap]
        all_passed = all(c.passed for c in all_checks)
        overall_verdict = "pass" if all_passed else "fail"

        # Record verdicts in storage
        failed_names = [c.name for c in all_checks if not c.passed]
        storage.record_verdict(
            cycle_id=cycle_id,
            verdict=overall_verdict,
            failed_check="; ".join(failed_names) if failed_names else None,
            observed_value=v_spread.observed_value,
            threshold=v_spread.threshold,
            action_taken="Cycle marked verified" if all_passed else "Cycle marked Degraded",
        )

        finished = datetime.now(timezone.utc)
        notes = f"Verdict: {overall_verdict.upper()} ({len(failed_names)} failed checks: {failed_names})"

        return AgentResult(
            agent_name=self.name,
            status="ok" if all_passed else "degraded",
            records_touched=len(all_checks),
            started_at=started,
            finished_at=finished,
            notes=notes,
            data={"verdict": overall_verdict, "checks": [c.model_dump() for c in all_checks]},
        )
