"""
LLM client wrapper for Tier-2 and Tier-3 field resolution.
Uses Groq API for low-latency and heavy-duty text synthesis.
"""

import json
import logging
import os
from typing import Optional, Tuple

import groq
from pydantic import BaseModel

from .config import config
from .schemas import CandidateProfile

logger = logging.getLogger(__name__)


class Tier2Resolution(BaseModel):
    resolved_value: Optional[str]
    confidence: float
    reasoning: str


class LLMClient:
    """Wrapper around Groq API for field resolution."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        self.client = groq.Groq(api_key=self.api_key) if self.api_key else None

    def is_configured(self) -> bool:
        return self.client is not None

    def resolve_field_tier2(
        self,
        field_label: str,
        profile: CandidateProfile
    ) -> Tier2Resolution:
        """
        Tier 2 (LLM Light): Maps an ambiguous field label to a value from the profile.
        Returns the resolved value, confidence [0.0-1.0], and reasoning.
        """
        if not self.is_configured():
            logger.warning("[LLMClient] GROQ_API_KEY not set. Skipping Tier-2.")
            return Tier2Resolution(resolved_value=None, confidence=0.0, reasoning="API key missing")

        prompt = (
            f"You are an AI assistant helping fill out a job application form.\n"
            f"Given the candidate profile below, what is the best value to put in the field labeled '{field_label}'?\n\n"
            f"Candidate Profile (JSON):\n{profile.model_dump_json(indent=2)}\n\n"
            f"Respond in JSON format with exactly these fields:\n"
            f" - \"resolved_value\": The string value to enter, or null if the profile doesn't contain a reasonable answer.\n"
            f" - \"confidence\": A float between 0.0 and 1.0 indicating how sure you are.\n"
            f" - \"reasoning\": A brief explanation."
        )

        try:
            # Type ignore because groq types might not be fully compliant
            chat_completion = self.client.chat.completions.create( # type: ignore
                messages=[{"role": "user", "content": prompt}],
                model=config.groq.light_model,
                temperature=config.groq.temperature,
                response_format={"type": "json_object"},
            )

            content = chat_completion.choices[0].message.content
            if not content:
                raise ValueError("Empty response from Groq API")
                
            data = json.loads(content)
            return Tier2Resolution(
                resolved_value=data.get("resolved_value"),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", "No reasoning provided"),
            )
        except Exception as e:
            logger.error("[LLMClient] Tier-2 resolution failed for '%s': %s", field_label, e)
            return Tier2Resolution(resolved_value=None, confidence=0.0, reasoning=f"Error: {e}")

    def resolve_field_tier3(
        self,
        field_label: str,
        profile: CandidateProfile,
        job_context: str = ""
    ) -> str:
        """
        Tier 3 (LLM Heavy): Generates a free-text response.
        Always returned with 0.0 confidence to force DRAFT_PENDING_REVIEW.
        """
        if not self.is_configured():
            return "GROQ_API_KEY missing - could not generate response."

        prompt = (
            f"You are writing a short, professional response for a job application on behalf of the candidate.\n"
            f"The application asks: '{field_label}'\n"
            f"Candidate Profile: {profile.model_dump_json()}\n"
            f"Job Context: {job_context}\n\n"
            f"Provide only the text to be entered into the text box, without quotes or preamble."
        )

        try:
            chat_completion = self.client.chat.completions.create( # type: ignore
                messages=[{"role": "user", "content": prompt}],
                model=config.groq.heavy_model,
                temperature=config.groq.temperature,
            )
            return chat_completion.choices[0].message.content.strip() # type: ignore
        except Exception as e:
            logger.error("[LLMClient] Tier-3 resolution failed: %s", e)
            return f"Error generating response: {e}"
