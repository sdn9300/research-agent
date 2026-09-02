"""
EdgeDash Source Plugin: Arbeitnow (Free Public Job Board API)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 3
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .base import BaseSource, register
from .http import get_json


@register("arbeitnow")
class ArbeitnowSource(BaseSource):
    """Fetches real tech and ML listings from the free Arbeitnow API."""
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def fetch(self, role: str, city: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        listings: List[Dict[str, Any]] = []
        try:
            data = get_json(self.API_URL, timeout=10.0)
            raw_jobs = data.get("data", [])

            role_tokens = [t.lower() for t in role.split() if len(t) > 2]

            for job in raw_jobs:
                title = job.get("title", "")
                description = job.get("description", "")
                location = job.get("location", "")
                remote = job.get("remote", False)

                # Filter lightly by role keywords
                combined_text = f"{title} {description}".lower()
                if role_tokens and not any(t in combined_text for t in role_tokens):
                    continue

                posted_at = job.get("created_at")
                if posted_at:
                    try:
                        # Convert unix timestamp or iso string
                        if isinstance(posted_at, (int, float)):
                            dt = datetime.fromtimestamp(posted_at, tz=timezone.utc)
                            posted_at = dt.isoformat()
                    except Exception:
                        pass

                loc_str = location
                if remote:
                    loc_str = f"Remote ({location})" if location else "Remote"

                listings.append({
                    "title": title,
                    "company": job.get("company_name", "Unknown Company"),
                    "location": loc_str,
                    "url": job.get("url", ""),
                    "description": description,
                    "source": "arbeitnow",
                    "posted_at": posted_at,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })

                if len(listings) >= limit:
                    break

        except Exception as e:
            # Propagate error to fetcher try/except boundary
            raise RuntimeError(f"Arbeitnow fetch failed: {e}") from e

        return listings
