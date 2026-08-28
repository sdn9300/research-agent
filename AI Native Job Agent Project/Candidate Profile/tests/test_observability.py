"""
Unit and benchmark tests for observability, Prometheus metrics, and 500+ history load performance (Phase 4).
Validates Monitored Gates MG-1 through MG-5 and the 100ms read latency budget.
"""
import time
from datetime import datetime, timezone
from pathlib import Path
import pytest

from candidate_profile.models import CandidateProfile, HistoryRef
from candidate_profile.storage import CandidateProfileStore
from candidate_profile.concurrency import CandidateProfilePatch, merge_candidate_profile, OwnershipViolationError
from candidate_profile.observability import (
    CANDIDATE_PROFILE_OWNERSHIP_VIOLATIONS_TOTAL,
    CANDIDATE_PROFILE_SCHEMA_VERSION_GAUGE,
    CANDIDATE_PROFILE_VALIDATION_FAILURES_TOTAL,
    CANDIDATE_PROFILE_WRITES_TOTAL,
    check_schema_version_drift,
    compute_taxonomy_coverage,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def real_profile() -> CandidateProfile:
    fixture_path = FIXTURES_DIR / "real_candidate_profile.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        return CandidateProfile.model_validate_json(f.read())


def test_prometheus_telemetry_recording(real_profile: CandidateProfile, tmp_path: Path):
    """Verifies that storage operations and violations increment Prometheus metrics."""
    store = CandidateProfileStore(base_dir=tmp_path)
    cand_id = real_profile.profile_metadata.candidate_id

    # Initial write
    store.put(real_profile)

    # 1. Verify writes metric
    write_metric = CANDIDATE_PROFILE_WRITES_TOTAL.labels(
        component=real_profile.profile_metadata.last_writer_component, status="success"
    )._value.get()
    assert write_metric >= 1

    # 2. Verify schema version gauge
    gauge_val = CANDIDATE_PROFILE_SCHEMA_VERSION_GAUGE.labels(
        candidate_id=cand_id, schema_version="1.0.0"
    )._value.get()
    assert gauge_val == 1

    # 3. Verify ownership violation metric increment
    patch = CandidateProfilePatch(
        writer_component="gleaner",
        section="identity",
        value={"legal_name": "Bad Actor"},
    )
    with pytest.raises(OwnershipViolationError):
        merge_candidate_profile(real_profile, patch)

    viol_metric = CANDIDATE_PROFILE_OWNERSHIP_VIOLATIONS_TOTAL.labels(component="gleaner")._value.get()
    assert viol_metric >= 1


def test_mg2_check_schema_version_drift(real_profile: CandidateProfile):
    """MG-2: Evaluates schema version drift detection."""
    # Matched version
    drift_ok = check_schema_version_drift(real_profile, expected_version="1.0.0")
    assert drift_ok["is_drifted"] is False
    assert drift_ok["action_required"] == "none"

    # Drifted version
    drift_lag = check_schema_version_drift(real_profile, expected_version="2.0.0")
    assert drift_lag["is_drifted"] is True
    assert drift_lag["action_required"] == "run_migration"
    assert drift_lag["actual_version"] == "1.0.0"


def test_mg5_compute_taxonomy_coverage(real_profile: CandidateProfile):
    """MG-5: Evaluates taxonomy coverage calculation."""
    cov = compute_taxonomy_coverage(real_profile)
    assert cov["total_skills"] >= 5
    assert cov["mapped_skills"] >= 5
    assert cov["null_rate"] == 0.0

    # Test with unmapped skills
    profile_with_unmapped = real_profile.model_copy(deep=True)
    profile_with_unmapped.skills[0].taxonomy_ref = None

    cov_unmapped = compute_taxonomy_coverage(profile_with_unmapped)
    assert cov_unmapped["unmapped_skills"] == 1
    assert cov_unmapped["null_rate"] > 0.0


def test_load_and_read_latency_budget_500_entries(real_profile: CandidateProfile, tmp_path: Path):
    """Load test: Synthesizes 500+ history entries and asserts read latency < 100ms budget."""
    store = CandidateProfileStore(base_dir=tmp_path)
    now = datetime.now(timezone.utc)

    # 1. Synthesize 200 tailoring runs, 200 outreach records, 50 application attempts, 50 interaction signals
    tailoring_runs = [
        HistoryRef(
            run_id=f"tailor-{i}",
            component="align_resume",
            timestamp=now,
            outcome="success",
            score=0.85 + (i % 15) * 0.01,
            detail_ref=f"align_resume/runs/tailor-{i}.json",
        )
        for i in range(200)
    ]

    outreach_records = [
        HistoryRef(
            run_id=f"outreach-{i}",
            component="overture",
            timestamp=now,
            outcome="email_sent",
            score=0.9,
            detail_ref=f"overture/campaigns/outreach-{i}.json",
        )
        for i in range(200)
    ]

    application_attempts = [
        HistoryRef(
            run_id=f"app-{i}",
            component="usher",
            timestamp=now,
            outcome="submitted_pdf",
            score=1.0,
            detail_ref=f"usher/attempts/app-{i}.json",
        )
        for i in range(50)
    ]

    interaction_signals = [
        HistoryRef(
            run_id=f"signal-{i}",
            component="sentiment_classifier",
            timestamp=now,
            outcome="positive_response" if i % 2 == 0 else "neutral",
            score=0.75 + (i % 25) * 0.01,
            detail_ref=f"sentiment/signals/signal-{i}.json",
        )
        for i in range(50)
    ]

    loaded_profile = real_profile.model_copy(
        update={
            "tailoring_history": tailoring_runs,
            "outreach_history": outreach_records,
            "application_history": application_attempts,
            "interaction_signals": interaction_signals,
        }
    )

    total_history_count = (
        len(loaded_profile.tailoring_history)
        + len(loaded_profile.outreach_history)
        + len(loaded_profile.application_history)
        + len(loaded_profile.interaction_signals)
    )
    assert total_history_count == 500

    # 2. Persist 500-entry profile to disk
    store.put(loaded_profile)
    cand_id = loaded_profile.profile_metadata.candidate_id

    # 3. Benchmark read latency across multiple iterations
    iterations = 50
    latencies_ms = []

    for _ in range(iterations):
        t0 = time.perf_counter()
        retrieved = store.get(cand_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        assert retrieved is not None
        assert len(retrieved.tailoring_history) == 200

    avg_latency_ms = sum(latencies_ms) / len(latencies_ms)
    max_latency_ms = max(latencies_ms)
    p95_latency_ms = sorted(latencies_ms)[int(0.95 * len(latencies_ms))]

    print(f"\n[500-Entry Load Benchmark] Avg: {avg_latency_ms:.2f}ms | P95: {p95_latency_ms:.2f}ms | Max: {max_latency_ms:.2f}ms")

    # Budget assertion: average read latency must be strictly < 100ms
    assert avg_latency_ms < 100.0, f"Average latency {avg_latency_ms:.2f}ms exceeded 100ms budget"
    assert p95_latency_ms < 100.0, f"P95 latency {p95_latency_ms:.2f}ms exceeded 100ms budget"
