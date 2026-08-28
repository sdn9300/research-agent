"""
Observability, Prometheus telemetry hooks, drift detection, and taxonomy metrics.
Reference: CONDUCTOR-CP-AD-v1.0 (Architecture Design §11, Evaluation Plan Monitored Gates MG-1 to MG-5)
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from prometheus_client import Counter, Gauge, Histogram, REGISTRY

from candidate_profile.models import CandidateProfile
from candidate_profile.migrations import CURRENT_SCHEMA_VERSION

# ============================================================================
# Prometheus Telemetry Instruments (§11)
# ============================================================================

def _get_or_create_counter(name: str, documentation: str, labelnames: List[str]) -> Counter:
    try:
        return Counter(name, documentation, labelnames)
    except ValueError:
        # Already registered in default registry
        for collector in REGISTRY._names_to_collectors.values():
            if collector._name == name:
                return collector
        raise


def _get_or_create_gauge(name: str, documentation: str, labelnames: List[str]) -> Gauge:
    try:
        return Gauge(name, documentation, labelnames)
    except ValueError:
        for collector in REGISTRY._names_to_collectors.values():
            if collector._name == name:
                return collector
        raise


def _get_or_create_histogram(name: str, documentation: str, labelnames: List[str]) -> Histogram:
    try:
        return Histogram(name, documentation, labelnames)
    except ValueError:
        for collector in REGISTRY._names_to_collectors.values():
            if collector._name == name:
                return collector
        raise


CANDIDATE_PROFILE_WRITES_TOTAL = _get_or_create_counter(
    "candidate_profile_writes_total",
    "Total number of candidate profile write attempts",
    ["component", "status"],
)

CANDIDATE_PROFILE_VALIDATION_FAILURES_TOTAL = _get_or_create_counter(
    "candidate_profile_validation_failures_total",
    "Total number of schema validation failures partitioned by offending field",
    ["field"],
)

CANDIDATE_PROFILE_SCHEMA_VERSION_GAUGE = _get_or_create_gauge(
    "candidate_profile_schema_version_gauge",
    "Tracks current schema version of candidate profiles",
    ["candidate_id", "schema_version"],
)

CANDIDATE_PROFILE_WRITE_LATENCY_SECONDS = _get_or_create_histogram(
    "candidate_profile_write_latency_seconds",
    "Latency of candidate profile atomic write operations in seconds",
    ["component"],
)

CANDIDATE_PROFILE_OWNERSHIP_VIOLATIONS_TOTAL = _get_or_create_counter(
    "candidate_profile_ownership_violations_total",
    "Total number of unauthorized write attempts by component",
    ["component"],
)


# ============================================================================
# Telemetry Recording Helpers
# ============================================================================

def record_profile_write(component: str, success: bool, latency_sec: float) -> None:
    """Record a profile write attempt and its latency."""
    status = "success" if success else "error"
    CANDIDATE_PROFILE_WRITES_TOTAL.labels(component=component, status=status).inc()
    CANDIDATE_PROFILE_WRITE_LATENCY_SECONDS.labels(component=component).observe(latency_sec)


def record_validation_failure(field: str) -> None:
    """Record a schema validation failure (MG-1)."""
    CANDIDATE_PROFILE_VALIDATION_FAILURES_TOTAL.labels(field=field).inc()


def record_ownership_violation(component: str) -> None:
    """Record an unauthorized field mutation attempt (MG-4)."""
    CANDIDATE_PROFILE_OWNERSHIP_VIOLATIONS_TOTAL.labels(component=component).inc()


def record_schema_version(candidate_id: str, schema_version: str) -> None:
    """Update gauge tracking profile schema version (MG-2)."""
    CANDIDATE_PROFILE_SCHEMA_VERSION_GAUGE.labels(
        candidate_id=candidate_id, schema_version=schema_version
    ).set(1)


# ============================================================================
# Monitored Gate Evaluators (MG-2 & MG-5)
# ============================================================================

def check_schema_version_drift(
    profile: CandidateProfile, expected_version: str = CURRENT_SCHEMA_VERSION
) -> Dict[str, Any]:
    """Evaluates whether a loaded profile suffers from schema version drift (MG-2)."""
    actual_version = profile.profile_metadata.schema_version
    is_drifted = actual_version != expected_version
    return {
        "candidate_id": profile.profile_metadata.candidate_id,
        "actual_version": actual_version,
        "expected_version": expected_version,
        "is_drifted": is_drifted,
        "action_required": "run_migration" if is_drifted else "none",
    }


def compute_taxonomy_coverage(profile: CandidateProfile) -> Dict[str, Any]:
    """Computes Future Fit taxonomy coverage and null-rate across candidate skills (MG-5)."""
    total_skills = len(profile.skills)
    if total_skills == 0:
        return {
            "total_skills": 0,
            "mapped_skills": 0,
            "unmapped_skills": 0,
            "null_rate": 0.0,
            "unmapped_names": [],
        }

    unmapped = [s.name for s in profile.skills if s.taxonomy_ref is None]
    mapped_count = total_skills - len(unmapped)
    null_rate = len(unmapped) / total_skills

    return {
        "total_skills": total_skills,
        "mapped_skills": mapped_count,
        "unmapped_skills": len(unmapped),
        "null_rate": round(null_rate, 4),
        "unmapped_names": unmapped,
    }
