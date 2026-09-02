#!/usr/bin/env python3
"""
EdgeDash Autonomous Cycle Runner CLI
Reference: EDGEDASH-CORE-IMPL-v1.0
"""
from __future__ import annotations

import argparse
import sys
from edgedash.config import load_config
from edgedash.storage import Storage
from edgedash.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="EdgeDash Autonomous Loop Execution Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Render execution plan without running agents")
    parser.add_argument("--force", choices=["fetcher", "extractor", "scorer", "gap_analyzer", "verifier"], help="Force run a specific agent")
    parser.add_argument("--explain", action="store_true", help="Print detailed state and decision breakdown")
    parser.add_argument("--mock", action="store_true", help="Use MockFetcher for offline testing")

    args = parser.parse_args()

    config = load_config(args.config)
    storage = Storage(config.db_path)
    orchestrator = Orchestrator(config=config, storage=storage, use_mock_fetcher=args.mock)

    result = orchestrator.run_cycle(
        dry_run=args.dry_run,
        force_agent=args.force,
        explain=args.explain,
    )

    status = result.get("status")
    print(f"\nCycle Execution Status: {status.upper() if status else 'UNKNOWN'} (Cycle ID: {result.get('cycle_id')})")
    if result.get("tasks_executed"):
        print(f"Tasks Executed: {result['tasks_executed']}")
        for r in result.get("results", []):
            print(f"  - [{r['status'].upper()}] {r['agent_name']}: {r.get('notes', '')}")


if __name__ == "__main__":
    main()
