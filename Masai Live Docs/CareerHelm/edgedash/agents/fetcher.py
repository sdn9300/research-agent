"""
EdgeDash Subsystem 3: Real Fetcher Agent (Session 1.2)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 3 (Rule 12: Per-source fault isolation)
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult
from ..sources import SOURCES, ArbeitnowSource, ApifySource


class FetcherAgent(BaseAgent):
    name: str = "fetcher"

    def execute(self, config: Any, storage: Any, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        started = datetime.now(timezone.utc)
        total_inserted = 0
        source_summaries = []

        # Default to Arbeitnow and any other registered plugins
        sources_to_run = list(SOURCES.values())
        if not sources_to_run:
            sources_to_run = [ArbeitnowSource, ApifySource]

        for source_cls in sources_to_run:
            src_instance = source_cls()
            src_name = getattr(src_instance, "source_name", source_cls.__name__)
            try:
                raw_listings = src_instance.fetch(
                    role=config.target_role,
                    city=config.target_city,
                    limit=50,
                )
                new_rows = storage.upsert_listings(raw_listings)
                total_inserted += new_rows
                source_summaries.append(f"{src_name}: {len(raw_listings)} fetched ({new_rows} new)")
            except Exception as e:
                # Fault isolation: log failure and continue with other sources
                source_summaries.append(f"{src_name}: failed ({e})")

        finished = datetime.now(timezone.utc)
        status = "ok" if total_inserted > 0 else "nothing_to_do"

        return AgentResult(
            agent_name=self.name,
            status=status,
            records_touched=total_inserted,
            started_at=started,
            finished_at=finished,
            notes="; ".join(source_summaries),
        )
