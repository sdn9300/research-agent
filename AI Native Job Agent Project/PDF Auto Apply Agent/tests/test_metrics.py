from usher.memory import MemoryModuleAdapter
from usher.metrics import MetricsTracker
from usher.schemas import (
    ApplicationAttemptResult,
    ApplicationChannel,
    FieldResolution,
    JobApplicationTarget,
)

def test_metrics_token_cost_calculation():
    # 1,000,000 light tokens should be $0.05
    cost_light = MetricsTracker.calculate_token_cost(1_000_000, is_heavy_model=False)
    assert abs(cost_light - 0.05) < 1e-6

    # 1,000,000 heavy tokens should be $0.59
    cost_heavy = MetricsTracker.calculate_token_cost(1_000_000, is_heavy_model=True)
    assert abs(cost_heavy - 0.59) < 1e-6

def test_metrics_report_aggregation(tmp_path):
    storage_file = tmp_path / "memory_records.json"
    memory = MemoryModuleAdapter(storage_file_path=storage_file)

    job1 = JobApplicationTarget(
        job_id="m1",
        title="ML Engineer",
        company="Stripe",
        apply_url="https://boards.greenhouse.io/stripe/1",
        source_platform="greenhouse",
        detected_channel=ApplicationChannel.GENERIC_ATS_GREENHOUSE
    )
    att1 = ApplicationAttemptResult(
        attempt_id="att_m1",
        job=job1,
        status="SUBMITTED",
        groq_tokens_used=1000,
        groq_cost_estimate_usd=0.00005,
        field_resolutions=[
            FieldResolution(field_label="Email", resolution_tier="tier0_selector", confidence=1.0, source="candidate_profile")
        ]
    )

    job2 = JobApplicationTarget(
        job_id="m2",
        title="AI Engineer",
        company="Naukri Hiring",
        apply_url="https://www.naukri.com/job/2",
        source_platform="naukri",
        detected_channel=ApplicationChannel.NAUKRI
    )
    att2 = ApplicationAttemptResult(
        attempt_id="att_m2",
        job=job2,
        status="DRAFT_PENDING_REVIEW",
        groq_tokens_used=2000,
        groq_cost_estimate_usd=0.00010,
        field_resolutions=[
            FieldResolution(field_label="Notice Period", resolution_tier="tier1_fuzzy", confidence=0.95, source="candidate_profile")
        ]
    )

    memory.persist_attempt(att1)
    memory.persist_attempt(att2)

    report = MetricsTracker.generate_report(memory)
    assert report.total_attempts == 2
    assert report.total_tokens_used == 3000
    assert abs(report.total_cost_usd - 0.00015) < 1e-6
    assert abs(report.avg_cost_per_attempt_usd - 0.000075) < 1e-6
    assert "generic_ats_greenhouse" in report.cost_by_platform
    assert "naukri" in report.cost_by_platform
    assert report.tier_counts["tier0_selector"] == 1
    assert report.tier_counts["tier1_fuzzy"] == 1
