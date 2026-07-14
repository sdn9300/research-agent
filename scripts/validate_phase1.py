from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.chunker import chunk_text
from pipeline.embed_store import LocalVectorStore
from pipeline.retriever import retrieve
from tools.scrape import scrape_url
from tools.web_search import web_search


SEARCH_FIXTURE = """
<html>
  <body>
    <div class="result">
      <a class="result__a" href="https://example.com/about">ExampleCo About</a>
      <a class="result__snippet">ExampleCo builds workflow software for engineering teams.</a>
    </div>
    <div class="result">
      <a class="result__a" href="https://example.com/news">ExampleCo News</a>
      <a class="result__snippet">Recent product updates and company news.</a>
    </div>
  </body>
</html>
"""


HTML_FIXTURE = """
<html>
  <head><title>ExampleCo</title></head>
  <body>
    <main>
      <h1>ExampleCo</h1>
      <p>ExampleCo builds workflow software for engineering teams.</p>
      <p>Its platform helps teams ship products faster with APIs, automation, and analytics.</p>
    </main>
  </body>
</html>
"""


CANONICAL_SOURCE_URL = "https://example.com/exampleco"


def main() -> int:
    results = web_search("ExampleCo", html=SEARCH_FIXTURE, max_results=2)
    if len(results) != 2:
        raise SystemExit(f"Expected 2 parsed search results, got {len(results)}")

    with TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        html_file = temp_dir_path / "exampleco.html"
        html_file.write_text(HTML_FIXTURE, encoding="utf-8")

        scrape_result = scrape_url(html_file.as_uri())
        if "ExampleCo builds workflow software" not in scrape_result["text"]:
            raise SystemExit("Scrape step did not return expected text.")

        chunks = chunk_text(
            scrape_result["text"],
            company_name="ExampleCo",
            source_url=CANONICAL_SOURCE_URL,
            scraped_at=datetime.now(timezone.utc),
            chunk_size_words=20,
            overlap_words=5,
        )
        if not chunks:
            raise SystemExit("Chunking step returned no chunks.")

        store = LocalVectorStore(temp_dir_path / "phase1.sqlite")
        store.add_chunks(chunks)

        retrieved = retrieve(
            "workflow software engineering teams APIs",
            store_path=store.path,
            top_k=3,
            company_name="ExampleCo",
        )
        if not retrieved:
            raise SystemExit("Retriever returned no chunks.")

        best = retrieved[0]
        if not best.get("chunk_id") or not best.get("source_url"):
            raise SystemExit("Retriever lost chunk metadata.")
        if best.get("company_name") != "ExampleCo":
            raise SystemExit("Retriever returned the wrong company context.")
        if best.get("source_url") != CANONICAL_SOURCE_URL:
            raise SystemExit("Retriever returned the wrong canonical source URL.")

    print("Phase 1 validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
