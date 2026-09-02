"""
EdgeDash CLI: Verifier History & Verdicts Viewer (Session 3.2)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 3 Class 6
"""
from __future__ import annotations

from .config import load_config
from .storage import Storage


def main():
    config = load_config()
    storage = Storage(config.db_path)

    query = "SELECT * FROM verdicts ORDER BY checked_at DESC LIMIT 15"
    with storage.get_connection() as conn:
        cursor = conn.execute(query)
        rows = [dict(r) for r in cursor.fetchall()]

    print("=" * 95)
    print("HISTORICAL VERIFIER VERDICTS & PLAUSIBILITY CHECKS")
    print("=" * 95)

    if not rows:
        print("No verdicts logged yet.")
        return

    print(f"{'CHECKED AT':<24} | {'VERDICT':<10} | {'CYCLE ID':<20} | {'FAILED CHECKS':<20} | {'ACTION'}")
    print("-" * 95)
    for r in rows:
        verdict_str = f"[{r['verdict'].upper()}]"
        failed = r.get("failed_check") or "None (Clean)"
        action = r.get("action_taken") or ""
        print(f"{r['checked_at'][:19]:<24} | {verdict_str:<10} | {r['cycle_id']:<20} | {failed:<20} | {action}")
    print("=" * 95)


if __name__ == "__main__":
    main()
