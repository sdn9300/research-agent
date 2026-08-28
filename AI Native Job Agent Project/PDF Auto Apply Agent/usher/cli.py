"""
Command-Line Interface (CLI) for Usher (PDF Auto-Apply Agent).
Supports manual trigger, batch status queries, trust graduation inspection,
health check smoke tests, cost dashboards, and artifact retention pruning.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import config
from .graduation import PlatformGraduationTracker
from .health import AdapterHealthMonitor
from .memory import MemoryModuleAdapter
from .metrics import MetricsTracker
from .pipeline import AutoApplyPipeline
from .retention import RetentionManager
from .schemas import CandidateProfile, JobApplicationTarget, ResumeArtifact, SubmissionMode

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def handle_status(_args):
    """Displays application outcomes stored in Memory Module."""
    memory = MemoryModuleAdapter()
    stats = memory.get_stats()
    print("\n" + "=" * 50)
    print("  USHER — APPLICATION OUTCOME SUMMARY (MEMORY MODULE)")
    print("=" * 50)
    print(f" Total Attempted:        {stats['total']}")
    print(f" SUBMITTED:              {stats['SUBMITTED']}")
    print(f" DRAFT_PENDING_REVIEW:   {stats['DRAFT_PENDING_REVIEW']}")
    print(f" MANUAL_REQUIRED:        {stats['MANUAL_REQUIRED']}")
    print(f" AMBIGUOUS_OUTCOME:      {stats['AMBIGUOUS_OUTCOME']}")
    print(f" FAILED:                 {stats['FAILED']}")
    print(f" SKIPPED:                {stats['SKIPPED']}")
    print("=" * 50 + "\n")


def handle_graduation(_args):
    """Displays platform trust graduation standings."""
    tracker = PlatformGraduationTracker()
    print("\n" + "=" * 65)
    print("  USHER — PLATFORM TRUST GRADUATION STANDINGS")
    print("=" * 65)
    print(f"{'Platform':<22} {'Clean Streak':<14} {'AUTO Unlocked':<15} {'Locked Out'}")
    print("-" * 65)
    for channel, record in tracker.records.items():
        thresh = tracker._get_threshold(channel)
        streak_str = f"{record.consecutive_clean_runs}/{thresh}"
        unlocked_str = "YES (Active)" if record.is_auto_unlocked else "NO (Draft only)"
        locked_str = f"YES ({record.lockout_reason})" if record.is_locked_out else "NO"
        print(f"{channel.value:<22} {streak_str:<14} {unlocked_str:<15} {locked_str}")
    print("=" * 65 + "\n")


def handle_health(_args):
    """Executes standalone adapter health checks and selector regression tests."""
    monitor = AdapterHealthMonitor()
    report = monitor.run_all_checks()
    print("\n" + "=" * 70)
    print("  USHER — ADAPTER HEALTH & SELECTOR REGRESSION REPORT")
    print("=" * 70)
    print(f"{'Adapter':<26} {'URL Detect':<12} {'Fields OK':<12} {'Status'}")
    print("-" * 70)
    for name, status in report.adapters.items():
        url_str = "PASS" if status.url_detection_passed else "FAIL"
        fields_str = "PASS" if status.critical_fields_covered else "FAIL"
        status_str = "HEALTHY" if status.is_healthy else f"BROKEN ({status.error_message})"
        print(f"{name:<26} {url_str:<12} {fields_str:<12} {status_str}")
    print("=" * 70)
    print(f" Overall System Health: {'ALL HEALTHY' if report.all_healthy else 'REGRESSIONS DETECTED'}\n")


def handle_metrics(_args):
    """Displays cost dashboard and LLM token usage breakdown."""
    report = MetricsTracker.generate_report()
    print("\n" + "=" * 65)
    print("  USHER — LLM COST & OBSERVABILITY DASHBOARD")
    print("=" * 65)
    print(f" Total Applications Tracked: {report.total_attempts}")
    print(f" Total Groq Tokens Used:     {report.total_tokens_used:,}")
    print(f" Total Estimated Spend:      ${report.total_cost_usd:.5f} USD")
    print(f" Avg Cost Per Attempt:       ${report.avg_cost_per_attempt_usd:.5f} USD")
    print("-" * 65)
    print(" Spend Breakdown by Platform:")
    for channel, p_summary in report.cost_by_platform.items():
        print(f"   • {channel:<22} : {p_summary.total_attempts} attempts | {p_summary.total_tokens:,} tokens | ${p_summary.total_cost_usd:.5f}")
    print("-" * 65)
    print(" Field Resolution Ladder Usage:")
    for tier, count in report.tier_counts.items():
        print(f"   • {tier:<22} : {count} fields")
    print("=" * 65 + "\n")


def handle_clean(args):
    """Prunes old screenshots and attempt JSON logs based on age."""
    manager = RetentionManager(
        max_screenshot_age_days=args.max_screenshot_age,
        max_attempt_age_days=args.max_attempt_age,
    )
    report = manager.run_retention_policy()
    print("\n" + "=" * 50)
    print("  USHER — RETENTION CLEANUP REPORT")
    print("=" * 50)
    print(f" Screenshots Purged:    {report.screenshots_deleted}")
    print(f" Attempt Files Purged:  {report.attempt_files_deleted}")
    print(f" Total Disk Reclaimed:  {report.bytes_reclaimed / 1024:.2f} KB")
    print("=" * 50 + "\n")


def handle_apply(args):
    """Executes an auto-apply run from JSON fixture files."""
    try:
        with open(args.job, "r", encoding="utf-8") as f:
            job_data = json.load(f)
        with open(args.profile, "r", encoding="utf-8") as f:
            profile_data = json.load(f)
        with open(args.resume, "r", encoding="utf-8") as f:
            resume_data = json.load(f)

        job = JobApplicationTarget(**job_data)
        profile = CandidateProfile(**profile_data)
        resume = ResumeArtifact(**resume_data)

        mode = SubmissionMode(args.mode) if args.mode else None

        pipeline = AutoApplyPipeline()
        result = pipeline.execute(job=job, profile=profile, resume=resume, mode=mode)

        print("\n" + "=" * 50)
        print("  APPLICATION ATTEMPT RESULT")
        print("=" * 50)
        print(f" Attempt ID:   {result.attempt_id}")
        print(f" Job Title:    {result.job.title} at {result.job.company}")
        print(f" Final Status: {result.status}")
        if result.error_code:
            print(f" Error Code:   {result.error_code} - {result.error_message}")
        print("=" * 50 + "\n")

    except Exception as e:
        logger.error("Failed to execute application: %s", e)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Usher — PDF Auto-Apply Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status command
    subparsers.add_parser("status", help="Show Memory Module application stats")

    # graduation command
    subparsers.add_parser("graduation", help="Show platform trust graduation status")

    # health command
    subparsers.add_parser("health", help="Run standalone adapter health checks")

    # metrics command
    subparsers.add_parser("metrics", help="Show LLM cost and token dashboard")

    # clean command
    clean_parser = subparsers.add_parser("clean", help="Prune old screenshots and attempt logs")
    clean_parser.add_argument("--max-screenshot-age", type=int, help="Max screenshot age in days")
    clean_parser.add_argument("--max-attempt-age", type=int, help="Max attempt log age in days")

    # apply command
    apply_parser = subparsers.add_parser("apply", help="Execute an application attempt")
    apply_parser.add_argument("--job", required=True, help="Path to JobApplicationTarget JSON")
    apply_parser.add_argument("--profile", required=True, help="Path to CandidateProfile JSON")
    apply_parser.add_argument("--resume", required=True, help="Path to ResumeArtifact JSON")
    apply_parser.add_argument("--mode", choices=["draft", "auto", "skip"], help="Override submission mode")

    args = parser.parse_args()
    if args.command == "status":
        handle_status(args)
    elif args.command == "graduation":
        handle_graduation(args)
    elif args.command == "health":
        handle_health(args)
    elif args.command == "metrics":
        handle_metrics(args)
    elif args.command == "clean":
        handle_clean(args)
    elif args.command == "apply":
        handle_apply(args)


if __name__ == "__main__":
    main()
