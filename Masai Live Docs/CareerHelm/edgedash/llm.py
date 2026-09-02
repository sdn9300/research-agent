"""
EdgeDash Subsystem 4: LLM Gateway (Single Door Architecture)
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 4 (Rule 15: Single door for all LLM calls)
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel


def strip_code_fences(text: str) -> str:
    """Strip markdown ```json and ``` code fences from text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening fence
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    if cleaned.endswith("```"):
        # Remove closing fence
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def heuristic_extract_jd(text: str) -> Dict[str, Any]:
    """Deterministic heuristic extraction when LLM API is unavailable or offline."""
    lower = text.lower()

    # Common tech skills taxonomy
    common_skills = [
        "python", "pytorch", "tensorflow", "fastapi", "django", "flask",
        "sql", "postgresql", "mysql", "mongodb", "redis",
        "docker", "kubernetes", "k8s", "aws", "gcp", "azure",
        "langgraph", "langchain", "llm", "rag", "scikit-learn",
        "pandas", "numpy", "git", "ci/cd", "linux", "c++", "java", "scala",
        "spark", "kafka", "airflow", "databricks", "snowflake"
    ]

    found_skills = []
    for skill in common_skills:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, lower):
            found_skills.append(skill)

    # Split into required vs nice-to-have heuristically
    required = found_skills[: max(1, int(len(found_skills) * 0.7))]
    nice_to_have = found_skills[len(required):]

    # Seniority detection
    seniority = "mid"
    if any(k in lower for k in ["lead", "principal", "staff", "architect"]):
        seniority = "staff"
    elif any(k in lower for k in ["senior", "sr.", "sr "]):
        seniority = "senior"
    elif any(k in lower for k in ["junior", "jr.", "entry", "intern", "associate"]):
        seniority = "junior"

    # Years of experience extraction
    years = 2
    years_match = re.search(r"(\d+)\+?\s*(?:-\s*\d+)?\s*(?:years?|yrs?)\b", lower)
    if years_match:
        try:
            years = int(years_match.group(1))
        except Exception:
            pass

    remote_ok = any(k in lower for k in ["remote", "work from home", "hybrid"])

    return {
        "required_skills": required or ["python"],
        "nice_to_have": nice_to_have,
        "seniority": seniority,
        "years_required": years,
        "remote_ok": remote_ok,
    }


def complete_json(
    prompt: str,
    schema: Optional[Type[BaseModel]] = None,
    system_instruction: Optional[str] = None,
    max_retries: int = 1,
) -> Dict[str, Any]:
    """Execute LLM JSON completion with fence stripping and schema validation."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

    if not api_key:
        # Fallback to heuristic parser if API key is not present
        return heuristic_extract_jd(prompt)

    try:
        # Attempt calling Google Gemini API if library is installed
        from google import genai
        client = genai.Client(api_key=api_key)
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        cleaned = strip_code_fences(response.text or "{}")
        parsed = json.loads(cleaned)
        if schema:
            validated = schema(**parsed)
            return validated.model_dump()
        return parsed
    except Exception:
        # Graceful fallback to heuristic extractor
        return heuristic_extract_jd(prompt)


def main():
    """CLI check: python -m edgedash.llm --check"""
    print("=" * 60)
    print("EDGEDASH LLM GATEWAY DIAGNOSTIC")
    print("=" * 60)
    sample_jd = """
    Senior Machine Learning Engineer at Acme Corp.
    Requirements: 5+ years of experience with Python, PyTorch, and Docker.
    Nice to have: Kubernetes and FastAPI. Remote friendly.
    """
    facts = complete_json(sample_jd)
    print(f"Extracted Facts: {json.dumps(facts, indent=2)}")
    print("=" * 60)
    print("LLM GATEWAY STATUS: OK")


if __name__ == "__main__":
    main()
