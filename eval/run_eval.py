"""T3.2 — Eval runner: score the Research Agent against the frozen fact set.

Usage:
    python eval/run_eval.py           # full run, prints report
    python eval/run_eval.py --ci      # CI mode: exits non-zero if accuracy < 80%

Produces eval/results/run_NNN.json with per-company pass/fail and aggregate accuracy.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from graph.build import build_graph
from schemas.agent_task import AgentTask

FACT_SET_PATH = REPO_ROOT / "eval" / "fact_set.json"
RESULTS_DIR = REPO_ROOT / "eval" / "results"
ACCURACY_THRESHOLD = 0.80


# ---------------------------------------------------------------------------
# Fixture-based search/scrape tools
# ---------------------------------------------------------------------------
# For each company in the fact set, we generate deterministic fixture data
# derived from the fact claims themselves. This ensures the eval is fully
# offline and reproducible — no live API keys or network access required.
# ---------------------------------------------------------------------------

def _make_fixture_text(company: dict[str, Any]) -> str:
    """Synthesise realistic page text from fact claims so the graph has
    something meaningful to search, scrape, chunk, and retrieve."""
    company_name = company["company_name"]
    claims = [f["claim"] for f in company.get("facts", [])]
    lines = [f"{company_name} Company Information", ""]
    lines.extend(claims)
    lines.append("")
    lines.append(f"Learn more about {company_name} on our official website.")
    return "\n".join(lines)


def _build_search_tool(company_name: str, fixture_text: str):
    """Return a search tool that returns fixture results for any query."""
    url = f"https://fixture.example.com/{company_name.lower().replace(' ', '-')}"

    def search_tool(query: str) -> list[dict[str, str]]:
        return [
            {
                "title": f"{company_name} Overview",
                "url": url,
                "snippet": fixture_text[:200],
            }
        ]

    return search_tool


def _build_scrape_tool(company_name: str, fixture_text: str):
    """Return a scrape tool that returns fixture page content for any URL."""

    def scrape_tool(url: str) -> dict[str, str]:
        return {
            "url": url,
            "text": fixture_text,
            "title": f"{company_name} Overview",
            "source": "eval_fixture",
        }

    return scrape_tool


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _token_set(value: str) -> set[str]:
    """Extract meaningful tokens from a string (mirrors self_check logic)."""
    return {tok for tok in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{1,}", value.lower())}


def _claim_found_in_text(claim: str, text: str) -> bool:
    """Check whether a fact claim is semantically present in the brief text."""
    claim_tokens = _token_set(claim)
    text_tokens = _token_set(text)
    if not claim_tokens:
        return False
    overlap = len(claim_tokens & text_tokens)
    # Require at least 40% token overlap or 3 tokens, whichever is smaller
    threshold = min(3, max(1, int(len(claim_tokens) * 0.4)))
    return overlap >= threshold


def _score_company(brief_dict: dict[str, Any], facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Score each fact claim against the produced brief. Returns per-fact results."""
    # Build a combined text block from all brief fields
    combined_parts = [
        str(brief_dict.get("summary", "")),
        str(brief_dict.get("culture_notes", "")),
    ]
    for signal in brief_dict.get("tech_signals", []):
        combined_parts.append(str(signal))
    for news in brief_dict.get("recent_news", []):
        combined_parts.append(str(news.get("headline", "")))
    combined_text = " ".join(combined_parts)

    results = []
    for fact in facts:
        found = _claim_found_in_text(fact["claim"], combined_text)
        results.append({
            "fact_id": fact["fact_id"],
            "category": fact["category"],
            "claim": fact["claim"],
            "found": found,
        })
    return results


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _next_run_number() -> int:
    """Find the next available run number."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(RESULTS_DIR.glob("run_*.json"))
    if not existing:
        return 1
    last = existing[-1].stem  # e.g. "run_003"
    try:
        return int(last.split("_", 1)[1]) + 1
    except (ValueError, IndexError):
        return 1


def run_eval() -> dict[str, Any]:
    """Execute the full evaluation and return the results dict."""
    fact_set = json.loads(FACT_SET_PATH.read_text(encoding="utf-8"))
    companies = fact_set["companies"]

    run_number = _next_run_number()
    run_id = f"run_{run_number:03d}"
    start_time = time.time()

    company_results: list[dict[str, Any]] = []
    total_facts = 0
    total_found = 0

    for company in companies:
        company_name = company["company_name"]
        facts = company.get("facts", [])
        fixture_text = _make_fixture_text(company)

        search_tool = _build_search_tool(company_name, fixture_text)
        scrape_tool = _build_scrape_tool(company_name, fixture_text)

        graph = build_graph(search_tool, scrape_tool)
        task = AgentTask(
            task_id=uuid4(),
            input_payload={"company_name": company_name, "job_description": f"Research {company_name}"},
            status="pending",
            timestamp="2026-07-10T00:00:00Z",
        )

        try:
            result = graph.run(task, artifact_dir=str(RESULTS_DIR / run_id / company_name.lower()))
            if result.final_task_status == "success" and result.state.final_brief is not None:
                brief_dict = result.state.final_brief.model_dump()
                fact_results = _score_company(brief_dict, facts)
                found_count = sum(1 for r in fact_results if r["found"])
                company_result = {
                    "company_name": company_name,
                    "status": "success",
                    "facts_total": len(facts),
                    "facts_found": found_count,
                    "accuracy": round(found_count / len(facts), 4) if facts else 0,
                    "fact_details": fact_results,
                }
            else:
                company_result = {
                    "company_name": company_name,
                    "status": "failed",
                    "facts_total": len(facts),
                    "facts_found": 0,
                    "accuracy": 0,
                    "fact_details": [],
                    "error": result.state.error or "graph did not produce a brief",
                }
        except Exception as exc:
            company_result = {
                "company_name": company_name,
                "status": "error",
                "facts_total": len(facts),
                "facts_found": 0,
                "accuracy": 0,
                "fact_details": [],
                "error": str(exc),
            }

        total_facts += company_result["facts_total"]
        total_found += company_result["facts_found"]
        company_results.append(company_result)

        status_icon = "PASS" if company_result["accuracy"] >= ACCURACY_THRESHOLD else "FAIL"
        print(f"  [{status_icon}] {company_name}: {company_result['facts_found']}/{company_result['facts_total']} "
              f"({company_result['accuracy']:.0%}) [{company_result['status']}]")

    elapsed_ms = int((time.time() - start_time) * 1000)
    aggregate_accuracy = round(total_found / total_facts, 4) if total_facts > 0 else 0

    results = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fact_set_id": fact_set.get("dataset_id", "unknown"),
        "accuracy_threshold": ACCURACY_THRESHOLD,
        "aggregate_accuracy": aggregate_accuracy,
        "total_facts": total_facts,
        "total_found": total_found,
        "passed": aggregate_accuracy >= ACCURACY_THRESHOLD,
        "elapsed_ms": elapsed_ms,
        "companies": company_results,
    }

    # Write results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / f"{run_id}.json"
    output_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n{'=' * 60}")
    print(f"Aggregate accuracy: {total_found}/{total_facts} ({aggregate_accuracy:.1%})")
    print(f"Threshold: {ACCURACY_THRESHOLD:.0%}")
    print(f"Result: {'PASSED' if results['passed'] else 'FAILED'}")
    print(f"Output: {output_path}")
    print(f"Elapsed: {elapsed_ms}ms")

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Research Agent Eval Runner")
    parser.add_argument("--ci", action="store_true", help="CI mode: exit non-zero if accuracy < threshold")
    args = parser.parse_args()

    print(f"Research Agent Eval Runner")
    print(f"Fact set: {FACT_SET_PATH}")
    print(f"Accuracy threshold: {ACCURACY_THRESHOLD:.0%}")
    print(f"{'-' * 60}")

    results = run_eval()

    if args.ci and not results["passed"]:
        print(f"\nCI GATE FAILED: accuracy {results['aggregate_accuracy']:.1%} < {ACCURACY_THRESHOLD:.0%}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
