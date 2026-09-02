"""
EdgeDash CLI: Skill Gaps Terminal Viewer (Session 2.2)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 2 Class 4
"""
from __future__ import annotations

from .config import load_config
from .storage import Storage


def main():
    config = load_config()
    storage = Storage(config.db_path)
    gaps = storage.get_latest_skill_gaps(limit=15)

    print("=" * 85)
    print(f"TOP SKILL GAPS RANKED BY WEIGHTED OPPORTUNITY COST")
    print("=" * 85)

    if not gaps:
        print("No skill gap snapshots found. Run a cycle to compute gaps.")
        return

    print(f"{'SKILL':<22} | {'OPP COST':<10} | {'BLOCKED JOBS':<14} | {'AVG FIT':<10} | {'TOP FIT'}")
    print("-" * 85)
    for g in gaps:
        print(f"{g['skill'].title():<22} | {g['opportunity_cost']:<10.2f} | {g['listings_blocked']:<14} | {g['mean_score']:<10.1f} | {g['top_score']}")
    print("=" * 85)


if __name__ == "__main__":
    main()
