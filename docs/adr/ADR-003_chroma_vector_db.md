# Architecture Decision Record 003: Chroma Vector Database for Retrieval Core

## Status
Accepted

## Context
Scraped web pages must be indexed, chunked, and queried efficiently using embedding vectors. The project requires a lightweight, locally embeddable, and fast vector database that can run locally without complex setup, and run within CI environments.

## Decision
We selected Chroma as the vector store for local development and offline validation, deferring distributed/hosted databases (such as Qdrant) to a later stage.

## Rationale
1. **Low Friction**: Chroma runs inside the Python process using duckdb/parquet or simple in-memory storage, requiring zero external server setup.
2. **CI Friendly**: Ideal for automated evaluation suites running in GitHub Actions runners.
3. **Speed**: Enables fast read/write cycles matching our 4-week implementation timeline.

## Trade-offs
- **Scale and Durability**: Chroma is not designed for multi-tenant, high-concurrency production deployments or distributed horizontal scaling.
- **Mitigation**: We isolated the vector database connection and query patterns within a clean boundary (`pipeline/retriever.py`, `pipeline/embed_store.py`). This guarantees a minimal migration cost if we later transition to a production-grade database like Qdrant.
