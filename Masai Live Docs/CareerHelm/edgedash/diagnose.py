"""
EdgeDash CLI: Diagnostics & Storage Health Check
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 1 Class 2
"""
from __future__ import annotations

from .config import load_config
from .storage import Storage


def main():
    config = load_config()
    storage = Storage(config.db_path)

    with storage.get_connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) as total, COUNT(fit_score) as scored FROM listings")
        r_list = cursor.fetchone()

        cursor = conn.execute("SELECT COUNT(*) as cnt FROM extraction_cache")
        r_cache = cursor.fetchone()

        cursor = conn.execute("SELECT COUNT(*) as cnt FROM skill_gaps")
        r_gaps = cursor.fetchone()

        cursor = conn.execute("SELECT COUNT(*) as cnt FROM cycle_log")
        r_cycles = cursor.fetchone()

        cursor = conn.execute("SELECT COUNT(*) as cnt FROM verdicts")
        r_verdicts = cursor.fetchone()

    print("=" * 60)
    print("EDGEDASH STORAGE DIAGNOSTICS")
    print("=" * 60)
    print(f"Database File:          {config.db_path}")
    print(f"Total Listings:         {r_list['total']} ({r_list['scored']} scored)")
    print(f"Extraction Cache Size:  {r_cache['cnt']} cached JDs")
    print(f"Skill Gap Snapshots:    {r_gaps['cnt']} records")
    print(f"Cycles Logged:          {r_cycles['cnt']}")
    print(f"Verdicts Recorded:      {r_verdicts['cnt']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
