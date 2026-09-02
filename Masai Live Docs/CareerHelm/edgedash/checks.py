"""
EdgeDash Subsystem 8: Plausibility Checks (Pure Mathematical Functions)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 8
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel


class CheckVerdict(BaseModel):
    name: str
    passed: bool
    observed_value: float
    threshold: float
    details: str


def check_score_spread(
    scored_listings: List[Dict[str, Any]],
    min_spread: float = 10.0,
) -> CheckVerdict:
    """Asserts max(score) - min(score) >= min_spread (Rule 34)."""
    if len(scored_listings) < 2:
        return CheckVerdict(
            name="score_spread",
            passed=True,
            observed_value=0.0,
            threshold=min_spread,
            details="Fewer than 2 scored listings; spread check skipped.",
        )

    scores = [l["fit_score"] for l in scored_listings if l.get("fit_score") is not None]
    if not scores:
        return CheckVerdict(
            name="score_spread",
            passed=False,
            observed_value=0.0,
            threshold=min_spread,
            details="No valid fit_scores found.",
        )

    spread = float(max(scores) - min(scores))
    passed = spread >= min_spread

    return CheckVerdict(
        name="score_spread",
        passed=passed,
        observed_value=spread,
        threshold=min_spread,
        details=f"Score spread is {spread:.1f} (min: {min(scores)}, max: {max(scores)}). Threshold: {min_spread}",
    )


def check_unscored_residuals(
    unscored_remaining: int,
    batch_size: int = 20,
) -> CheckVerdict:
    """Verifies that remaining unscored listings do not exceed reasonable threshold."""
    # A passing check means unscored items are within manageable queue limits
    passed = unscored_remaining <= 500
    return CheckVerdict(
        name="unscored_residuals",
        passed=passed,
        observed_value=float(unscored_remaining),
        threshold=500.0,
        details=f"{unscored_remaining} unscored listings remaining in storage queue.",
    )


def check_volume_stability(
    new_listings_count: int,
    min_expected: int = 1,
) -> CheckVerdict:
    """Checks that scraper produced non-zero volume during active fetch."""
    passed = new_listings_count >= min_expected
    return CheckVerdict(
        name="volume_stability",
        passed=passed,
        observed_value=float(new_listings_count),
        threshold=float(min_expected),
        details=f"Fetched {new_listings_count} new listings (expected >= {min_expected}).",
    )


def check_gap_consistency(
    gaps: List[Dict[str, Any]],
    candidate_skills: List[str],
) -> CheckVerdict:
    """Verifies that none of candidate's registered skills appear in gap list."""
    cand_set = {s.lower().strip() for s in candidate_skills}
    overlap = []

    for g in gaps:
        skill = g.get("skill", "").lower().strip()
        if skill in cand_set:
            overlap.append(skill)

    passed = len(overlap) == 0
    return CheckVerdict(
        name="gap_consistency",
        passed=passed,
        observed_value=float(len(overlap)),
        threshold=0.0,
        details=f"Overlap with candidate skills: {overlap if overlap else 'None (Consistent)'}",
    )
