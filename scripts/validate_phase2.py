from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from graph.build import build_graph
from schemas.agent_task import AgentTask


COMPANY_FIXTURES = {
    "ExampleCo": {
        "search": {
            "ExampleCo company overview": [
                {"title": "ExampleCo Overview", "url": "https://example.com/overview", "snippet": "ExampleCo builds workflow software for engineering teams."},
            ],
            "ExampleCo recent news": [
                {"title": "ExampleCo News", "url": "https://example.com/news", "snippet": "ExampleCo announced new APIs, automation, and analytics tools."},
            ],
        },
        "pages": {
            "https://example.com/overview": "ExampleCo builds workflow software for engineering teams. Its platform helps teams ship products faster with APIs, automation, and analytics.",
            "https://example.com/news": "ExampleCo announced new APIs, automation, and analytics tools for engineering teams.",
        },
    },
    "VectorWorks": {
        "search": {
            "VectorWorks company overview": [
                {"title": "VectorWorks Overview", "url": "https://vectorworks.example/overview", "snippet": "VectorWorks builds design tooling and collaborative planning software."},
            ],
            "VectorWorks recent news": [
                {"title": "VectorWorks News", "url": "https://vectorworks.example/news", "snippet": "VectorWorks released collaboration updates and workflow improvements."},
            ],
        },
        "pages": {
            "https://vectorworks.example/overview": "VectorWorks builds design tooling and collaborative planning software. It focuses on workflow, product design, and team collaboration.",
            "https://vectorworks.example/news": "VectorWorks released collaboration updates and workflow improvements.",
        },
    },
    "CloudForge": {
        "search": {
            "CloudForge company overview": [
                {"title": "CloudForge Overview", "url": "https://cloudforge.example/overview", "snippet": "CloudForge provides cloud platform software for developer teams."},
            ],
            "CloudForge recent news": [
                {"title": "CloudForge News", "url": "https://cloudforge.example/news", "snippet": "CloudForge highlighted AI, cloud, and developer platform updates."},
            ],
        },
        "pages": {
            "https://cloudforge.example/overview": "CloudForge provides cloud platform software for developer teams. Its platform emphasizes AI, cloud, and developer productivity.",
            "https://cloudforge.example/news": "CloudForge highlighted AI, cloud, and developer platform updates.",
        },
    },
}


def make_search_tool(company_name: str):
    fixtures = COMPANY_FIXTURES[company_name]["search"]

    def search_tool(query: str) -> list[dict[str, str]]:
        return list(fixtures.get(query, []))

    return search_tool


def make_scrape_tool(company_name: str):
    pages = COMPANY_FIXTURES[company_name]["pages"]

    def scrape_tool(url: str) -> dict[str, str]:
        return {"url": url, "text": pages[url], "title": url.rsplit("/", 1)[-1], "source": "fixture"}

    return scrape_tool


def assert_invalid_claim_is_removed() -> None:
    graph = build_graph(make_search_tool("ExampleCo"), make_scrape_tool("ExampleCo"))
    task = AgentTask(
        task_id=uuid4(),
        input_payload={"company_name": "ExampleCo", "job_description": "Build APIs for engineering teams"},
        status="pending",
        timestamp="2026-07-02T00:00:00Z",
    )
    result = graph.run(task, artifact_dir=str(REPO_ROOT / "artifacts" / "phase2_example"))
    assert result.final_task_status == "success"
    assert result.state.final_brief is not None
    assert result.state.final_brief.company_name == "ExampleCo"
    assert result.state.final_brief.citations

    state = result.state
    state.draft_brief = dict(state.draft_brief or {})
    state.draft_brief["tech_signals"] = list(state.draft_brief.get("tech_signals", [])) + ["unrelated fabrication"]
    state.self_check_issues = []
    from graph.nodes.self_check import self_check

    checked = self_check(state)
    assert "unsupported tech signal: unrelated fabrication" in checked.self_check_issues


def main() -> int:
    with TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        for company_name in COMPANY_FIXTURES:
            graph = build_graph(make_search_tool(company_name), make_scrape_tool(company_name))
            task = AgentTask(
                task_id=uuid4(),
                input_payload={"company_name": company_name, "job_description": f"Research {company_name} engineering, APIs, and platform work"},
                status="pending",
                timestamp="2026-07-02T00:00:00Z",
            )
            result = graph.run(task, artifact_dir=str(temp_dir_path / company_name.lower()))
            if result.final_task_status != "success":
                raise SystemExit(f"{company_name}: graph failed")
            if result.state.final_brief is None:
                raise SystemExit(f"{company_name}: missing CompanyBrief")
            if not result.state.final_brief.citations:
                raise SystemExit(f"{company_name}: missing citations")
            if not result.state.final_brief.summary.strip():
                raise SystemExit(f"{company_name}: empty summary")
            if result.state.final_brief.run_metadata.tool_calls_used <= 0:
                raise SystemExit(f"{company_name}: missing tool usage metadata")

        assert_invalid_claim_is_removed()

    print("Phase 2 validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
