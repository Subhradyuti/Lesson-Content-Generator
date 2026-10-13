"""
Lesson planner agent.
Converts the request into a structured lesson plan before drafting begins.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field, SecretStr

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "planner_v1.md"


class LessonPlan(BaseModel):
    """Validated lesson plan produced by the planner."""

    learning_objectives: list[str] = Field(..., min_length=1)
    prerequisites: list[str]
    key_concepts: list[str] = Field(..., min_length=1)
    teaching_order: list[str] = Field(..., min_length=1)
    worked_example: str = Field(..., min_length=20)
    misconceptions: list[str] = Field(..., min_length=1)


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _build_objectives_section(objectives: list[str] | None) -> str:
    if not objectives:
        return ""
    joined = "\n".join(f"- {o}" for o in objectives)
    return f"Requested learning objectives:\n{joined}"


def create_lesson_plan(
    topic: str,
    learner_profile: str,
    language: str,
    learning_objectives: list[str] | None = None,
) -> LessonPlan:
    """
    Call the planner LLM and return a validated LessonPlan.
    Raises ValueError if the plan cannot be parsed or validated.
    """
    settings = get_settings()

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    llm = ChatGroq(
        api_key=SecretStr(settings.groq_api_key),
        model=settings.generator_model,
        temperature=0.4,
        max_tokens=1024,
        timeout=settings.provider_timeout_seconds,
        max_retries=settings.provider_sdk_retries,
        stop_sequences=None,
    )

    template = _load_prompt_template()
    prompt = template.format(
        topic=topic,
        learner_profile=learner_profile,
        language=language,
        objectives_section=_build_objectives_section(learning_objectives),
    )

    logger.info("Calling planner LLM", extra={"topic": topic, "model": settings.generator_model})

    response = llm.invoke(prompt)
    raw_text = response.content if isinstance(response.content, str) else str(response.content)

    # Strip markdown code fences if present
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        plan_dict: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Planner returned invalid JSON", extra={"error": str(exc)})
        raise ValueError(f"Planner returned invalid JSON: {exc}") from exc

    try:
        plan = LessonPlan.model_validate(plan_dict)
    except Exception as exc:
        logger.error("Lesson plan failed validation", extra={"error": str(exc)})
        raise ValueError(f"Lesson plan failed validation: {exc}") from exc

    logger.info(
        "Lesson plan created",
        extra={
            "objectives_count": len(plan.learning_objectives),
            "concepts_count": len(plan.key_concepts),
        },
    )
    return plan
