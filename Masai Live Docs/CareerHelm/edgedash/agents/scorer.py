"""
EdgeDash Subsystem 5: Deterministic Scorer Agent
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 5
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from ..scoring import score_listing
from ..storage import compute_desc_hash
from ..llm import complete_json


class ScorerAgent(BaseAgent):
    name: str = "scorer"

    def execute(self, config: Any, storage: Any, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        started = datetime.now(timezone.utc)
        batch_size = config.score_batch_size
        unscored = storage.get_unscored_listings(limit=batch_size)

        if not unscored:
            return AgentResult(
                agent_name=self.name,
                status="nothing_to_do",
                records_touched=0,
                started_at=started,
                finished_at=datetime.now(timezone.utc),
                notes="No unscored listings pending.",
            )

        scored_count = 0
        now = datetime.now(timezone.utc)

        for listing in unscored:
            desc = listing.get("description", "")
            desc_hash = compute_desc_hash(desc) if desc else ""
            extracted_facts = storage.get_cached_extraction(desc_hash) if desc_hash else None

            if not extracted_facts:
                extracted_facts = complete_json(desc)
                if desc_hash:
                    storage.set_cached_extraction(desc_hash, extracted_facts)

            fit_score, fit_reason, components = score_listing(
                extracted_facts=extracted_facts,
                listing_meta=listing,
                config=config,
                now=now,
            )

            storage.update_listing_score(
                listing_id=listing["id"],
                fit_score=fit_score,
                fit_reason=fit_reason,
                components=components,
            )
            scored_count += 1

        finished = datetime.now(timezone.utc)
        return AgentResult(
            agent_name=self.name,
            status="ok",
            records_touched=scored_count,
            started_at=started,
            finished_at=finished,
            notes=f"Deterministically scored {scored_count} listings.",
        )
