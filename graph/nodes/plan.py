from __future__ import annotations

import re

from graph.state import ResearchAgentState


STOPWORDS = {
    "and",
    "for",
    "the",
    "with",
    "from",
    "into",
    "that",
    "this",
    "your",
    "role",
    "team",
    "teams",
    "work",
    "will",
    "are",
    "you",
    "our",
    "their",
    "about",
    "job",
    "description",
}


def _extract_terms(job_description: str | None) -> list[str]:
    if not job_description:
        return []

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", job_description.lower())
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token in STOPWORDS or len(token) < 3:
            continue
        if token not in seen:
            seen.add(token)
            terms.append(token)
    return terms[:5]


def plan(state: ResearchAgentState) -> ResearchAgentState:
    """Create a concise search strategy from company name and job description."""

    terms = _extract_terms(state.job_description)
    strategy = [
        f"{state.company_name} company overview",
        f"{state.company_name} recent news",
        f"{state.company_name} about engineering",
    ]

    if terms:
        strategy.append(f"{state.company_name} {' '.join(terms[:3])}")
        strategy.append(f"{state.company_name} hiring {' '.join(terms[:2])}")

    state.search_strategy = strategy[:5]
    return state
