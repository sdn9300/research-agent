from __future__ import annotations

from graph.state import ResearchAgentState
from pipeline.retriever import retrieve as retrieve_chunks


def retrieve(state: ResearchAgentState) -> ResearchAgentState:
    """Load the most relevant chunks for synthesis from the local vector store."""

    query_parts = [state.company_name]
    if state.job_description:
        query_parts.append(state.job_description)
    query_text = " ".join(query_parts)

    state.retrieved_chunks = retrieve_chunks(
        query_text,
        store_path=state.artifact_path / "retrieval.sqlite",
        top_k=5,
        company_name=state.company_name,
    )
    return state

