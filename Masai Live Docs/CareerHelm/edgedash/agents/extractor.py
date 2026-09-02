"""
EdgeDash Subsystem 4: Fact Extractor Agent
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 4
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from ..llm import complete_json
from ..storage import compute_desc_hash


class ExtractorAgent(BaseAgent):
    name: str = "extractor"

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
                notes="No unscored listings to extract.",
            )

        extracted_count = 0
        cache_hits = 0

        for listing in unscored:
            desc = listing.get("description", "")
            if not desc:
                continue

            desc_hash = compute_desc_hash(desc)
            cached = storage.get_cached_extraction(desc_hash)

            if cached:
                cache_hits += 1
            else:
                facts = complete_json(desc)
                storage.set_cached_extraction(desc_hash, facts)
                extracted_count += 1

        finished = datetime.now(timezone.utc)
        return AgentResult(
            agent_name=self.name,
            status="ok",
            records_touched=extracted_count + cache_hits,
            started_at=started,
            finished_at=finished,
            notes=f"Extracted {extracted_count} new JDs ({cache_hits} cache hits).",
        )
