"""T3.1 verification — confirm that RunLogger writes a queryable row with all expected fields."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from graph.build import build_graph
from schemas.agent_task import AgentTask

# ---- Fixtures (reuse the ExampleCo pattern from validate_phase2) ----

FIXTURE_SEARCH = {
    "ExampleCo company overview": [
        {"title": "ExampleCo Overview", "url": "https://example.com/overview",
         "snippet": "ExampleCo builds workflow software for engineering teams."},
    ],
    "ExampleCo recent news": [
        {"title": "ExampleCo News", "url": "https://example.com/news",
         "snippet": "ExampleCo announced new APIs, automation, and analytics tools."},
    ],
}

FIXTURE_PAGES = {
    "https://example.com/overview": (
        "ExampleCo builds workflow software for engineering teams. "
        "Its platform helps teams ship products faster with APIs, automation, and analytics."
    ),
    "https://example.com/news": (
        "ExampleCo announced new APIs, automation, and analytics tools for engineering teams."
    ),
}


def _search_tool(query: str) -> list[dict[str, str]]:
    return list(FIXTURE_SEARCH.get(query, []))


def _scrape_tool(url: str) -> dict[str, str]:
    return {"url": url, "text": FIXTURE_PAGES.get(url, ""), "title": url.rsplit("/", 1)[-1], "source": "fixture"}


def main() -> int:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "test_logger.db"

        # Monkey-patch the default db_path so the run writes here instead of the repo db
        import observability.logger as logger_mod
        _orig_init = logger_mod.RunLogger.__init__

        def _patched_init(self, db_path_arg=db_path):
            _orig_init(self, db_path=db_path_arg)

        logger_mod.RunLogger.__init__ = _patched_init

        graph = build_graph(_search_tool, _scrape_tool)
        task = AgentTask(
            task_id=uuid4(),
            input_payload={"company_name": "ExampleCo", "job_description": "Build APIs"},
            status="pending",
            timestamp="2026-07-10T00:00:00Z",
        )
        result = graph.run(task, artifact_dir=str(Path(tmp) / "artifacts"))

        # Restore original init
        logger_mod.RunLogger.__init__ = _orig_init

        if result.final_task_status != "success":
            print(f"FAIL: graph returned {result.final_task_status}")
            return 1

        # Query the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM runs").fetchall()
        conn.close()

        if len(rows) != 1:
            print(f"FAIL: expected 1 row, found {len(rows)}")
            return 1

        row = dict(rows[0])
        checks = {
            "run_id": row.get("run_id") is not None,
            "timestamp": row.get("timestamp") is not None,
            "company_name": row.get("company_name") == "ExampleCo",
            "prompt_version": row.get("prompt_version") is not None and len(row["prompt_version"]) > 0,
            "tool_calls_used": row.get("tool_calls_used") is not None and row["tool_calls_used"] > 0,
            "latency_ms": row.get("latency_ms") is not None and row["latency_ms"] >= 0,
            "token_cost_usd": row.get("token_cost_usd") is not None,
            "chunk_ids": row.get("chunk_ids") is not None and len(json.loads(row["chunk_ids"])) > 0,
            "citations": row.get("citations") is not None and len(json.loads(row["citations"])) > 0,
        }

        all_passed = True
        for field, passed in checks.items():
            status = "OK" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"  [{status}] {field}: {row.get(field)!r}")

        if all_passed:
            print("\nT3.1 verification passed — all logger fields populated correctly.")
            return 0
        else:
            print("\nT3.1 verification FAILED — see failures above.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
