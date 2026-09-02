"""
EdgeDash Subsystem 8.1: System Health Reporter (Self-Study W4-S2)
Reference: W4_S2_Prompt.md C8-P4 (Rules 47-51)

Checks:
1. Newest listing older than 3 days
2. No successful cycle in 48 hours
3. Last 3 cycles all failed verification
4. Database unreachable
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from .config import load_config
from .storage import Storage


class HealthStatus(BaseModel):
    is_healthy: bool
    status_label: str  # green | amber | red
    message: str
    checks: List[Dict[str, Any]]


def check_health(storage: Optional[Storage] = None) -> HealthStatus:
    """Evaluate 4 core health checks against active storage backend."""
    storage = storage or Storage()
    checks = []
    now = datetime.now(timezone.utc)

    # 1. Database Reachability Check
    db_ok = False
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            db_ok = True
        checks.append({
            "name": "database_reachability",
            "passed": True,
            "observed": f"Connected ({storage.backend})",
            "message": "Database is reachable and responding.",
        })
    except Exception as e:
        checks.append({
            "name": "database_reachability",
            "passed": False,
            "observed": "Unreachable",
            "message": f"Database connection failed: {e}",
        })
        return HealthStatus(
            is_healthy=False,
            status_label="red",
            message="Database unreachable",
            checks=checks,
        )

    # 2. Newest Listing Age Check (< 3 days)
    newest_listing_age_days: Optional[float] = None
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(fetched_at) as latest FROM listings")
            row = cursor.fetchone()
            latest_str = row["latest"] if row else None

        if latest_str:
            dt = datetime.fromisoformat(latest_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            newest_listing_age_days = (now - dt).total_seconds() / 86400.0
            passed = newest_listing_age_days <= 3.0
            checks.append({
                "name": "listing_freshness",
                "passed": passed,
                "observed": f"{newest_listing_age_days:.1f} days ago",
                "message": f"Newest listing fetched {newest_listing_age_days:.1f} days ago (Threshold: <= 3.0d)",
            })
        else:
            checks.append({
                "name": "listing_freshness",
                "passed": True,
                "observed": "No listings",
                "message": "No listings recorded yet (initial state).",
            })
    except Exception as e:
        checks.append({
            "name": "listing_freshness",
            "passed": False,
            "observed": f"Error ({e})",
            "message": "Failed to inspect listing freshness.",
        })

    # 3. Successful Cycle in 48 Hours
    hours_since_success: Optional[float] = None
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(finished_at) as last_success FROM cycle_log WHERE status IN ('ok', 'completed', 'nothing_to_do')")
            row = cursor.fetchone()
            success_str = row["last_success"] if row else None

        if success_str:
            dt_s = datetime.fromisoformat(success_str)
            if dt_s.tzinfo is None:
                dt_s = dt_s.replace(tzinfo=timezone.utc)
            hours_since_success = (now - dt_s).total_seconds() / 3600.0
            passed = hours_since_success <= 48.0
            checks.append({
                "name": "cycle_cadence",
                "passed": passed,
                "observed": f"{hours_since_success:.1f}h ago",
                "message": f"Last successful cycle ran {hours_since_success:.1f}h ago (Threshold: <= 48.0h)",
            })
        else:
            checks.append({
                "name": "cycle_cadence",
                "passed": True,
                "observed": "No cycles logged",
                "message": "No cycle logs recorded yet (initial state).",
            })
    except Exception as e:
        checks.append({
            "name": "cycle_cadence",
            "passed": False,
            "observed": f"Error ({e})",
            "message": "Failed to query cycle logs.",
        })

    # 4. Last 3 Cycles Verification Failure Check
    try:
        with storage.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT verdict FROM verdicts ORDER BY checked_at DESC LIMIT 3")
            rows = cursor.fetchall()
            verdicts = [r["verdict"] for r in rows] if rows else []

        all_failed = len(verdicts) >= 3 and all(v == "fail" for v in verdicts)
        checks.append({
            "name": "verification_stability",
            "passed": not all_failed,
            "observed": f"{verdicts}" if verdicts else "No verdicts",
            "message": "Verification stable." if not all_failed else "Last 3 consecutive cycles failed plausibility verification!",
        })
    except Exception as e:
        checks.append({
            "name": "verification_stability",
            "passed": False,
            "observed": f"Error ({e})",
            "message": "Failed to check verifier history.",
        })

    # Overall Health Determination
    all_passed = all(c["passed"] for c in checks)
    if all_passed:
        # Green if cycle ran within 24h, amber if 24-48h
        status_label = "green" if (hours_since_success is None or hours_since_success <= 24.0) else "amber"
        message = "System is healthy and operational."
    else:
        status_label = "red"
        failed_checks = [c["name"] for c in checks if not c["passed"]]
        message = f"System unhealthy: failed checks {failed_checks}"

    return HealthStatus(
        is_healthy=all_passed,
        status_label=status_label,
        message=message,
        checks=checks,
    )


def cli_main():
    health = check_health()

    print("=" * 60)
    print("EDGEDASH SYSTEM HEALTH REPORT")
    print("=" * 60)
    status_text = {"green": "[HEALTHY]", "amber": "[STALE]", "red": "[UNHEALTHY]"}.get(health.status_label, "[UNKNOWN]")
    print(f"Overall Status: {status_text} - {health.message}\n")

    for c in health.checks:
        icon = "[PASS]" if c["passed"] else "[FAIL]"
        print(f"  {icon:<7} {c['name']:<25}: {c['observed']:<15} ({c['message']})")

    print("=" * 60)
    sys.exit(0 if health.is_healthy else 1)


if __name__ == "__main__":
    cli_main()
