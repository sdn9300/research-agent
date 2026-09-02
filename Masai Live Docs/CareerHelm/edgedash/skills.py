"""
EdgeDash Subsystem 6: Skill Canonicalisation & Opportunity Cost Gap Analyzer
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 6 (Rules 22-27)
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


def canonical(raw_skill: str, aliases: Optional[Dict[str, str]] = None) -> str:
    """Normalize a raw skill string:
    1. Lowercase and strip whitespace
    2. Remove parenthetical qualifiers, e.g. 'Kubernetes (EKS)' -> 'kubernetes'
    3. Strip punctuation / special symbols
    4. Collapse internal multiple spaces
    5. Map user-owned aliases from skill_aliases
    """
    if not raw_skill:
        return ""

    cleaned = raw_skill.lower().strip()

    # Remove parenthetical expressions: 'kubernetes (eks)' -> 'kubernetes'
    cleaned = re.sub(r"\(.*?\)", "", cleaned).strip()

    # Remove trailing/leading special characters
    cleaned = re.sub(r"[^\w\s\.\+\#\-\/]", "", cleaned)

    # Collapse internal spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Apply aliases
    if aliases and cleaned in aliases:
        cleaned = aliases[cleaned].lower().strip()

    return cleaned


def analyze_skill_gaps(
    scored_listings: List[Dict[str, Any]],
    candidate_skills: Set[str],
    aliases: Optional[Dict[str, str]] = None,
    min_score_threshold: int = 40,
) -> List[Dict[str, Any]]:
    """Compute weighted Opportunity Cost across blocked listings.
    Formula: Opportunity Cost(k) = sum( FitScore(j) / 100 ) for all j where skill k is missing.
    """
    canon_cand_skills = {canonical(s, aliases) for s in candidate_skills if s}

    # Skill -> list of (listing_id, fit_score, is_required)
    skill_blocks: Dict[str, List[Tuple[str, int, bool]]] = {}

    for listing in scored_listings:
        fit_score = listing.get("fit_score")
        if fit_score is None or fit_score < min_score_threshold:
            continue

        listing_id = listing.get("id", "")
        components_raw = listing.get("components")

        if isinstance(components_raw, str):
            import json
            try:
                comp = json.loads(components_raw)
            except Exception:
                comp = {}
        elif isinstance(components_raw, dict):
            comp = components_raw
        else:
            comp = {}

        gaps = comp.get("gaps", [])
        for raw_gap in gaps:
            c_gap = canonical(raw_gap, aliases)
            if not c_gap or c_gap in canon_cand_skills:
                continue

            if c_gap not in skill_blocks:
                skill_blocks[c_gap] = []
            skill_blocks[c_gap].append((listing_id, fit_score, True))

    # Aggregate opportunity cost per skill
    gap_records: List[Dict[str, Any]] = []
    for skill, occurrences in skill_blocks.items():
        blocked_count = len(occurrences)
        opp_cost = sum(score / 100.0 for _, score, _ in occurrences)
        scores = [score for _, score, _ in occurrences]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        top_score = max(scores) if scores else 0
        example_ids = [lid for lid, _, _ in occurrences[:5]]

        gap_records.append({
            "skill": skill,
            "listings_blocked": blocked_count,
            "opportunity_cost": round(opp_cost, 2),
            "mean_score": round(mean_score, 1),
            "top_score": top_score,
            "example_ids": example_ids,
            "also_nice_to_have": False,
        })

    # Sort descending by Opportunity Cost
    gap_records.sort(key=lambda g: g["opportunity_cost"], reverse=True)
    return gap_records
