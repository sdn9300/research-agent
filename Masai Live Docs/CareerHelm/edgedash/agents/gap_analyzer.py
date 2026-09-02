"""
EdgeDash Subsystem 6: Gap Analyzer Agent
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 6
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from ..skills import analyze_skill_gaps


class GapAnalyzerAgent(BaseAgent):
    name: str = "gap_analyzer"

    def execute(self, config: Any, storage: Any, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        started = datetime.now(timezone.utc)
        scored_listings = storage.get_all_scored_listings()

        if not scored_listings:
            return AgentResult(
                agent_name=self.name,
                status="nothing_to_do",
                records_touched=0,
                started_at=started,
                finished_at=datetime.now(timezone.utc),
                notes="No scored listings available to analyze gaps.",
            )

        candidate_skills = set(config.my_skills)
        aliases = config.skill_aliases

        gaps = analyze_skill_gaps(
            scored_listings=scored_listings,
            candidate_skills=candidate_skills,
            aliases=aliases,
            min_score_threshold=30,
        )

        snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
        storage.save_skill_gap_snapshot(snapshot_id=snapshot_id, gaps=gaps)

        finished = datetime.now(timezone.utc)
        return AgentResult(
            agent_name=self.name,
            status="ok",
            records_touched=len(gaps),
            started_at=started,
            finished_at=finished,
            notes=f"Computed {len(gaps)} skill gaps across {len(scored_listings)} scored listings (Snapshot: {snapshot_id}).",
            data={"snapshot_id": snapshot_id, "gaps_count": len(gaps)},
        )
