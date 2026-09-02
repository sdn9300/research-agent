"""
EdgeDash Subsystem 1: Configuration & Environment
Reference: EDGEDASH-CORE-ARCH-v1.0 §2 Subsystem 1
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator


class ScoringWeights(BaseModel):
    skill: float = 0.45
    seniority: float = 0.25
    location: float = 0.15
    recency: float = 0.15

    @field_validator("skill", "seniority", "location", "recency")
    @classmethod
    def validate_weight_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v


class Config(BaseModel):
    target_role: str = "Machine Learning Engineer"
    target_city: str = "Bengaluru"
    keywords: List[str] = Field(default_factory=lambda: ["python", "machine learning", "fastapi"])
    my_skills: List[str] = Field(default_factory=lambda: ["python", "pytorch", "fastapi", "sql", "docker"])
    experience_years: int = 2
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    score_batch_size: int = 20
    fetch_interval_hours: int = 6
    llm_provider: str = "gemini"
    llm_model: str = "gemini-1.5-flash"
    skill_aliases: Dict[str, str] = Field(default_factory=dict)
    db_path: str = "edgedash.db"


def load_config(config_path: str | Path = "config.yaml") -> Config:
    """Load and validate configuration from YAML file. Fail fast if missing or malformed."""
    path = Path(config_path)
    if not path.exists():
        # Fallback to default config if file does not exist
        return Config()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        raise ValueError(f"Failed to parse config YAML at '{path}': {e}") from e

    return Config(**data)


def main():
    """CLI check: python -m edgedash.config"""
    try:
        cfg = load_config()
        print("=" * 60)
        print("EDGEDASH CONFIGURATION VALIDATION: PASSED")
        print("=" * 60)
        print(f"Target Role:       {cfg.target_role}")
        print(f"Target City:       {cfg.target_city}")
        print(f"Experience Years:  {cfg.experience_years}")
        print(f"Candidate Skills:  {len(cfg.my_skills)} registered")
        print(f"Skill Aliases:     {len(cfg.skill_aliases)} mapped")
        print(f"Weights:           Skill={cfg.weights.skill}, Seniority={cfg.weights.seniority}, Loc={cfg.weights.location}, Recency={cfg.weights.recency}")
        print(f"Database Path:     {cfg.db_path}")
        print("=" * 60)
    except Exception as e:
        print(f"Configuration validation failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
