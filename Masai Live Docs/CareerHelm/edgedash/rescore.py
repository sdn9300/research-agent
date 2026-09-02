"""
EdgeDash CLI: Manual Rescore Tool (Session 2.1)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 2 Class 3
Invalidates listing scores and re-evaluates them using deterministic math without clearing extraction cache.
"""
from __future__ import annotations

import argparse
import sys
from .config import load_config
from .storage import Storage
from .agents.scorer import ScorerAgent


def main():
    parser = argparse.ArgumentParser(description="EdgeDash Rescoring Tool")
    parser.add_argument("--id", dest="listing_id", help="Rescore a specific listing ID")
    parser.add_argument("--all", action="store_true", help="Clear all scores and re-evaluate entire database")
    args = parser.parse_args()

    config = load_config()
    storage = Storage(config.db_path)

    if args.all:
        with storage.get_connection() as conn:
            conn.execute("UPDATE listings SET fit_score = NULL, fit_reason = NULL, components = NULL, scored_at = NULL")
            conn.commit()
        print("Invalidated all listing scores.")

    elif args.listing_id:
        with storage.get_connection() as conn:
            conn.execute("UPDATE listings SET fit_score = NULL WHERE id = ?", (args.listing_id,))
            conn.commit()
        print(f"Invalidated score for listing {args.listing_id}.")

    # Run scorer agent
    scorer = ScorerAgent()
    res = scorer.execute(config, storage)
    print(f"Rescoring complete: {res.records_touched} listings rescored ({res.notes}).")


if __name__ == "__main__":
    main()
