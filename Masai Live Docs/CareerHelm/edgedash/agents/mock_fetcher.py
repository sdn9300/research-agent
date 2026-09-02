"""
EdgeDash Subsystem 3: Mock Fetcher Agent (Session 1.1)
Reference: EDGEDASH-CORE-IMPL-v1.0 Week 1 Class 1
Generates 12 listings with 4 identical across runs for deduplication proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentResult


class MockFetcherAgent(BaseAgent):
    name: str = "mock_fetcher"

    def execute(self, config: Any, storage: Any, context: Optional[Dict[str, Any]] = None) -> AgentResult:
        started = datetime.now(timezone.utc)
        mock_jobs = [
            # 4 Fixed / Identical Across Runs
            {
                "title": "Machine Learning Engineer",
                "company": "DeepTech AI",
                "location": "Bengaluru",
                "url": "https://deeptech.example.com/jobs/mle-01",
                "description": "Looking for MLE with Python, PyTorch, FastAPI, and Docker experience. 2+ years required.",
                "source": "mock",
                "posted_at": "2026-08-25T10:00:00Z",
            },
            {
                "title": "Senior AI Systems Architect",
                "company": "ScaleAI Labs",
                "location": "Remote",
                "url": "https://scaleai.example.com/jobs/arch-99",
                "description": "Senior architect with Kubernetes, LangGraph, Python, and C++ distributed systems.",
                "source": "mock",
                "posted_at": "2026-08-26T12:00:00Z",
            },
            {
                "title": "Backend Python Developer",
                "company": "FinFlow",
                "location": "Bengaluru",
                "url": "https://finflow.example.com/careers/py-dev",
                "description": "Backend engineer with Python, FastAPI, PostgreSQL, and Redis.",
                "source": "mock",
                "posted_at": "2026-08-27T08:00:00Z",
            },
            {
                "title": "Data Scientist - NLP",
                "company": "Cognitive Cloud",
                "location": "Remote",
                "url": "https://cognitive.example.com/jobs/nlp-02",
                "description": "NLP Data Scientist with Python, PyTorch, Transformers, and Databricks.",
                "source": "mock",
                "posted_at": "2026-08-27T15:00:00Z",
            },
            # 8 Additional Opportunities
            {
                "title": "Junior MLOps Engineer",
                "company": "ModelOps",
                "location": "Bengaluru",
                "url": f"https://modelops.example.com/jobs/mlops-{started.microsecond % 1000}",
                "description": "MLOps engineer with Docker, Kubernetes, CI/CD, and Python.",
                "source": "mock",
                "posted_at": "2026-08-28T09:00:00Z",
            },
            {
                "title": "AI Research Scientist",
                "company": "NeuralFrontier",
                "location": "Remote",
                "url": f"https://neuralfrontier.example.com/jobs/rs-{started.microsecond % 1000}",
                "description": "Research scientist working on LLM fine-tuning, PyTorch, and CUDA.",
                "source": "mock",
                "posted_at": "2026-08-28T11:00:00Z",
            },
            {
                "title": "Full Stack AI Engineer",
                "company": "Agentic Co",
                "location": "Remote",
                "url": f"https://agentic.example.com/jobs/fs-{started.microsecond % 1000}",
                "description": "Full stack engineer building Next.js apps with FastAPI and LangGraph backends.",
                "source": "mock",
                "posted_at": "2026-08-28T14:00:00Z",
            },
            {
                "title": "Lead Data Platform Engineer",
                "company": "DataScale",
                "location": "Hyderabad",
                "url": f"https://datascale.example.com/jobs/lead-{started.microsecond % 1000}",
                "description": "Lead engineer with Spark, Kafka, Snowflake, and Python.",
                "source": "mock",
                "posted_at": "2026-08-20T10:00:00Z",
            },
            {
                "title": "Computer Vision Engineer",
                "company": "VisionCore",
                "location": "Bengaluru",
                "url": f"https://visioncore.example.com/jobs/cv-{started.microsecond % 1000}",
                "description": "Computer vision engineer with OpenCV, PyTorch, C++, and TensorRT.",
                "source": "mock",
                "posted_at": "2026-08-24T16:00:00Z",
            },
            {
                "title": "GenAI Solutions Developer",
                "company": "EnterpriseAI",
                "location": "Remote",
                "url": f"https://enterpriseai.example.com/jobs/genai-{started.microsecond % 1000}",
                "description": "GenAI developer with Python, LangChain, RAG, and Azure.",
                "source": "mock",
                "posted_at": "2026-08-27T18:00:00Z",
            },
            {
                "title": "Analytics Engineer",
                "company": "MetricFlow",
                "location": "Bengaluru",
                "url": f"https://metricflow.example.com/jobs/ae-{started.microsecond % 1000}",
                "description": "Analytics engineer with dbt, SQL, PostgreSQL, and Python.",
                "source": "mock",
                "posted_at": "2026-08-28T07:00:00Z",
            },
            {
                "title": "Platform Infrastructure Engineer",
                "company": "CloudNative",
                "location": "Remote",
                "url": f"https://cloudnative.example.com/jobs/infra-{started.microsecond % 1000}",
                "description": "Platform engineer with Kubernetes, Terraform, AWS, and Golang.",
                "source": "mock",
                "posted_at": "2026-08-28T08:30:00Z",
            },
        ]

        new_count = storage.upsert_listings(mock_jobs)
        finished = datetime.now(timezone.utc)

        return AgentResult(
            agent_name=self.name,
            status="ok" if new_count > 0 else "nothing_to_do",
            records_touched=new_count,
            started_at=started,
            finished_at=finished,
            notes=f"Fetched {len(mock_jobs)} mock listings ({new_count} newly inserted).",
        )
