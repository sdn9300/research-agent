"""
EdgeDash Subsystem 7: State Reader
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 7
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel

from .config import Config
from .storage import Storage


class SystemState(BaseModel):
    now: datetime
    hours_since_fetch: Optional[float]
    unscored_count: int
    gaps_stale: bool
    total_listings: int
    last_verdict: Optional[str] = None


def read_state(config: Config, storage: Storage, now: Optional[datetime] = None) -> SystemState:
    """Read current system state from storage using cheap queries only."""
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    with storage.get_connection() as conn:
        # Total listings
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM listings")
        total_listings = cursor.fetchone()["cnt"]

        # Unscored count
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM listings WHERE fit_score IS NULL")
        unscored_count = cursor.fetchone()["cnt"]

        # Last fetch timestamp
        cursor = conn.execute("SELECT MAX(fetched_at) as last_fetch FROM listings")
        row = cursor.fetchone()
        last_fetch_str = row["last_fetch"] if row else None

        hours_since_fetch: Optional[float] = None
        if last_fetch_str:
            try:
                dt_fetch = datetime.fromisoformat(last_fetch_str)
                if dt_fetch.tzinfo is None:
                    dt_fetch = dt_fetch.replace(tzinfo=timezone.utc)
                hours_since_fetch = max(0.0, (now - dt_fetch).total_seconds() / 3600.0)
            except Exception:
                pass

        # Gaps stale check (stale if no snapshot or last snapshot older than 24h)
        cursor = conn.execute("SELECT MAX(computed_at) as last_snap FROM skill_gaps")
        row = cursor.fetchone()
        last_snap_str = row["last_snap"] if row else None

        gaps_stale = True
        if last_snap_str:
            try:
                dt_snap = datetime.fromisoformat(last_snap_str)
                if dt_snap.tzinfo is None:
                    dt_snap = dt_snap.replace(tzinfo=timezone.utc)
                hours_since_snap = (now - dt_snap).total_seconds() / 3600.0
                gaps_stale = hours_since_snap >= 24.0
            except Exception:
                gaps_stale = True

    # Last verdict
    verdict_row = storage.get_latest_verdict()
    last_verdict = verdict_row["verdict"] if verdict_row else None

    return SystemState(
        now=now,
        hours_since_fetch=hours_since_fetch,
        unscored_count=unscored_count,
        gaps_stale=gaps_stale,
        total_listings=total_listings,
        last_verdict=last_verdict,
    )
