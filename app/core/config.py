"""
Application configuration using pydantic-settings.
All secrets come from environment variables or .env file — never hardcoded.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    app_secret_key: str = Field(default="change-me", min_length=8)
    api_key: str = Field(default="", description="X-API-Key for protected endpoints")

    # ── Groq / LLM ───────────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key")
    generator_model: str = "llama-3.3-70b-versatile"
    evaluator_model: str = "llama-3.3-70b-versatile"
    generator_temperature: float = 0.7
    evaluator_temperature: float = 0.1
    model_max_tokens: int = 4096
    # Evaluator needs more tokens than the generator: 14 checkpoints × evidence + reason
    # fields easily exceeds 4096 tokens. Kept separate so generator cost is unchanged.
    evaluator_max_tokens: int = 8192
    provider_timeout_seconds: int = 60
    # SDK-level retries per individual LLM call.
    # Set to 0 to surface provider errors immediately — the workflow loop handles content retries.
    provider_sdk_retries: int = 0
    provider_max_retries: int = 3  # kept for backward compat; use provider_sdk_retries for SDK

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite:///./lesson_generator.db"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Rate limiting ─────────────────────────────────────────────────────────
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60

    # ── Input limits ──────────────────────────────────────────────────────────
    max_topic_length: int = 500
    max_learner_profile_length: int = 1000
    max_reference_material_length: int = 50000
    max_learning_objectives: int = 10

    # ── Workflow ──────────────────────────────────────────────────────────────
    default_max_retries: int = 2
    rubric_version: str = "rag-beginner-v1"
    prompt_version: str = "v1"

    # ── Observability ─────────────────────────────────────────────────────────
    log_level: str = "INFO"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = "lesson-content-generator"
    metrics_bearer_token: str = ""

    @field_validator("groq_api_key")
    @classmethod
    def groq_key_must_exist(cls, v: str) -> str:
        # Allow empty key in testing (mocked), but warn at runtime
        return v

    @field_validator("default_max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        if v not in (0, 1, 2):
            raise ValueError("default_max_retries must be 0, 1, or 2")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton settings instance."""
    return Settings()
