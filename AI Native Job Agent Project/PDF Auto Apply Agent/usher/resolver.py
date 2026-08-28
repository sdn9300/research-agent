"""
Four-tier field resolution ladder for Usher.
Implements the cost-aware, tiered mapping strategy (PAA-AD-1.0 §5).
"""

import logging
from typing import Dict, Literal, Optional, Callable

from .llm import LLMClient
from .schemas import CandidateProfile, FieldResolution

logger = logging.getLogger(__name__)


class FieldResolver:
    """Runs the tiered resolution ladder for form fields."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()
        self.tier0_dictionary: Dict[str, Callable[[CandidateProfile], str]] = {}
        self.tier1_synonyms: Dict[str, Callable[[CandidateProfile], str]] = {}

    def register_tier0(self, exact_label: str, extractor: Callable[[CandidateProfile], str]) -> None:
        """Registers a Tier 0 exact string match for a field label."""
        self.tier0_dictionary[exact_label.strip().lower()] = extractor

    def register_tier1(self, synonym: str, extractor: Callable[[CandidateProfile], str]) -> None:
        """Registers a Tier 1 substring/fuzzy match for a field label."""
        self.tier1_synonyms[synonym.strip().lower()] = extractor

    def resolve(
        self,
        field_label: str,
        profile: CandidateProfile,
        is_free_text: bool = False,
        job_context: str = ""
    ) -> FieldResolution:
        """
        Executes the resolution ladder:
        Tier 0: Exact match
        Tier 1: Fuzzy match
        Tier 2: LLM Light (standard fields)
        Tier 3: LLM Heavy (free-text, forces review)
        """
        normalized_label = field_label.strip().lower()

        # Tier 3 (Force-routed for open-ended free text)
        if is_free_text:
            logger.info("[Resolver] Routing '%s' directly to Tier 3 (Free Text)", field_label)
            generated = self.llm.resolve_field_tier3(field_label, profile, job_context)
            return FieldResolution(
                field_label=field_label,
                resolution_tier="tier3_llm_heavy",
                resolved_value=generated,
                confidence=0.0,  # Always 0.0 to force DRAFT_PENDING_REVIEW per PAA-EC-MAP-03
                source="generated",
                reasoning="Tier 3 open-ended generation."
            )

        # Tier 0 (Exact Match)
        if normalized_label in self.tier0_dictionary:
            value = self.tier0_dictionary[normalized_label](profile)
            if value:
                return FieldResolution(
                    field_label=field_label,
                    resolution_tier="tier0_selector",
                    resolved_value=value,
                    confidence=1.0,
                    source="candidate_profile",
                    reasoning="Tier 0 exact label match."
                )

        # Tier 1 (Fuzzy/Synonym Match)
        for syn, extractor in self.tier1_synonyms.items():
            if syn in normalized_label:
                value = extractor(profile)
                if value:
                    return FieldResolution(
                        field_label=field_label,
                        resolution_tier="tier1_fuzzy",
                        resolved_value=value,
                        confidence=0.95,
                        source="candidate_profile",
                        reasoning=f"Tier 1 fuzzy match on '{syn}'."
                    )

        # Tier 2 (LLM Light Classification)
        logger.info("[Resolver] Escalating '%s' to Tier 2 (LLM Light)", field_label)
        t2_res = self.llm.resolve_field_tier2(field_label, profile)
        
        if t2_res.resolved_value and t2_res.confidence > 0.0:
            return FieldResolution(
                field_label=field_label,
                resolution_tier="tier2_llm_light",
                resolved_value=t2_res.resolved_value,
                confidence=t2_res.confidence,
                source="candidate_profile",
                reasoning=t2_res.reasoning
            )

        # Fallback (Unresolved / Manual Required)
        return FieldResolution(
            field_label=field_label,
            resolution_tier="unresolved",
            resolved_value=None,
            confidence=0.0,
            source="manual_required",
            reasoning="Resolution ladder exhausted. No confident mapping found."
        )
