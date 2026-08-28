"""
Metrics & Cost Observability Tracker for Usher (Phase 5).
Tracks LLM token spend, computes cost estimates in USD, and aggregates performance metrics.
"""

import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from .config import config
from .memory import MemoryModuleAdapter
from .schemas import ApplicationAttemptResult

logger = logging.getLogger(__name__)

# Official Groq pricing (USD per 1M tokens)
PRICE_PER_1M_LIGHT = 0.05   # llama-3.1-8b-instant
PRICE_PER_1M_HEAVY = 0.59   # llama-3.3-70b-versatile


class PlatformCostSummary(BaseModel):
    channel: str
    total_attempts: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    successful_attempts: int = 0
    avg_cost_per_attempt_usd: float = 0.0


class MetricsDashboardReport(BaseModel):
    total_attempts: int = 0
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    avg_cost_per_attempt_usd: float = 0.0
    cost_by_platform: Dict[str, PlatformCostSummary] = Field(default_factory=dict)
    tier_counts: Dict[str, int] = Field(default_factory=lambda: {
        "tier0_selector": 0,
        "tier1_fuzzy": 0,
        "tier2_llm_light": 0,
        "tier3_llm_heavy": 0,
        "unresolved": 0,
    })


class MetricsTracker:
    """Calculates and aggregates cost and efficiency metrics across attempts."""

    @staticmethod
    def calculate_token_cost(tokens: int, is_heavy_model: bool = False) -> float:
        """Calculates estimated cost in USD for a given token count."""
        rate = PRICE_PER_1M_HEAVY if is_heavy_model else PRICE_PER_1M_LIGHT
        return (tokens / 1_000_000.0) * rate

    @staticmethod
    def generate_report(memory_adapter: Optional[MemoryModuleAdapter] = None) -> MetricsDashboardReport:
        """Assembles metrics and cost summary across all stored application attempts."""
        memory = memory_adapter or MemoryModuleAdapter()
        attempts: List[ApplicationAttemptResult] = memory.attempts

        report = MetricsDashboardReport()
        report.total_attempts = len(attempts)

        for att in attempts:
            channel_name = att.job.detected_channel.value if att.job.detected_channel else att.job.source_platform

            if channel_name not in report.cost_by_platform:
                report.cost_by_platform[channel_name] = PlatformCostSummary(channel=channel_name)

            p_summary = report.cost_by_platform[channel_name]
            p_summary.total_attempts += 1
            p_summary.total_tokens += att.groq_tokens_used
            p_summary.total_cost_usd += att.groq_cost_estimate_usd

            if att.status in ["SUBMITTED", "DRAFT_PENDING_REVIEW"]:
                p_summary.successful_attempts += 1

            report.total_tokens_used += att.groq_tokens_used
            report.total_cost_usd += att.groq_cost_estimate_usd

            # Count resolution tiers
            for res in att.field_resolutions:
                t = res.resolution_tier
                report.tier_counts[t] = report.tier_counts.get(t, 0) + 1

        # Compute averages
        if report.total_attempts > 0:
            report.avg_cost_per_attempt_usd = report.total_cost_usd / report.total_attempts

        for p_summary in report.cost_by_platform.values():
            if p_summary.total_attempts > 0:
                p_summary.avg_cost_per_attempt_usd = p_summary.total_cost_usd / p_summary.total_attempts

        return report
