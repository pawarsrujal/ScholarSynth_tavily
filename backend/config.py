"""Central configuration for ScholarSynth V2."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openrouter_api_key: str | None = None
    openrouter_model: str = "openrouter/free"
    openrouter_planner_model: str | None = None
    openrouter_executor_model: str | None = None
    openrouter_publisher_model: str | None = None
    openrouter_verifier_model: str | None = None

    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash"

    tavily_api_key: str | None = None

    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:3000,https://scholar-synth-tavily.vercel.app/"

    max_subquestions: int = 4
    max_search_queries_per_subquestion: int = 3
    max_results_per_query: int = 5
    max_sources_per_subquestion: int = 5
    min_total_sources: int = 10
    max_concurrent_research: int = 3

    provider_retries: int = 4
    provider_timeout_seconds: float = 45.0
    tavily_timeout_seconds: float = 30.0

    def origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
