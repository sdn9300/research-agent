from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from graph.nodes.plan import plan
from graph.nodes.retrieve import retrieve
from graph.nodes.search_scrape import search_scrape
from graph.nodes.self_check import self_check
from graph.nodes.synthesize import synthesize
from schemas.agent_task import AgentTask
from graph.state import ResearchAgentState, ResearchGraphResult
from observability.logger import RunLogger
import uuid


@dataclass(slots=True)
class ResearchAgentGraph:
    search_tool: Callable[[str], list[dict[str, str]]]
    scrape_tool: Callable[[str], dict[str, str]]

    def run(self, task: AgentTask, *, artifact_dir: str | None = None, tool_call_budget: int = 6) -> ResearchGraphResult:
        import time
        start_time = time.time()
        state = ResearchAgentState(
            task_id=str(task.task_id),
            company_name=task.input_payload.company_name,
            job_description=task.input_payload.job_description,
            artifact_dir=artifact_dir or "artifacts/research_agent",
            tool_call_budget=tool_call_budget,
            status="running",
        )

        state = plan(state)
        state = search_scrape(state, search_tool=self.search_tool, scrape_tool=self.scrape_tool)
        state = retrieve(state)
        state = synthesize(state)
        state = self_check(state)

        if not state.self_check_passed and state.retry_count < 1:
            state.retry_count += 1
            state.status = "retrying"
            state = synthesize(state)
            state = self_check(state)

        if state.final_brief is None:
            state.status = "failed"
            state.error = "Research agent failed to produce a valid CompanyBrief."
            return ResearchGraphResult(state=state, final_task_status="failed")

        if state.self_check_passed:
            state.status = "success"
            final_task_status = "success"
        else:
            state.status = "success"
            state.final_brief.confidence_flags.append("self_check_partial")
            final_task_status = "success"

        # Log run metadata after successful execution
        if state.final_brief is not None:
            run_id = str(uuid.uuid4())
            latency_ms = int((time.time() - start_time) * 1000)
            chunk_ids = [
                str(c.get("chunk_id", ""))
                for c in state.retrieved_chunks
                if c.get("chunk_id")
            ]
            citation_dicts = [
                {"citation_id": c.citation_id, "chunk_id": c.chunk_id, "source_url": str(c.source_url)}
                for c in state.final_brief.citations
            ]
            logger = RunLogger()
            logger.log_run(
                run_id=run_id,
                company_name=state.company_name,
                prompt_version=state.prompt_version,
                tool_calls_used=state.tool_calls_used,
                latency_ms=latency_ms,
                token_cost_usd=0.0,
                chunk_ids=chunk_ids,
                citations=citation_dicts,
            )
        state.final_brief.run_metadata.tool_calls_used = state.tool_calls_used
        return ResearchGraphResult(state=state, final_task_status=final_task_status)


def build_graph(
    search_tool: Callable[[str], list[dict[str, str]]],
    scrape_tool: Callable[[str], dict[str, str]],
) -> ResearchAgentGraph:
    return ResearchAgentGraph(search_tool=search_tool, scrape_tool=scrape_tool)

