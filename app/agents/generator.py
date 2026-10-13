"""
Lesson generator agent.
Produces a beginner lesson from a validated lesson plan, with support for
targeted revisions when earlier drafts fail the quality gate.
"""

from __future__ import annotations

import time
from pathlib import Path

from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.agents._retry import make_retry_decorator
from app.agents.planner import LessonPlan
from app.core.config import get_settings
from app.core.logging import get_logger
from app.observability.metrics import record_provider_error

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "generator_v1.md"

PROMPT_VERSION = "v1"


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _build_revision_section(
    previous_draft: str | None,
    failed_checkpoint_ids: list[str],
    revision_instructions: list[str],
    passing_checkpoint_ids: list[str],
) -> str:
    """Build the revision instructions block injected into the prompt."""
    if not previous_draft:
        return ""

    failed_str = ", ".join(failed_checkpoint_ids) if failed_checkpoint_ids else "none"
    passing_str = ", ".join(passing_checkpoint_ids) if passing_checkpoint_ids else "none"

    instructions_block = "\n".join(
        f"{i + 1}. {instr}" for i, instr in enumerate(revision_instructions)
    )

    return f"""
THIS IS A REVISION. The previous draft failed evaluation.

Failed checkpoints: {failed_str}
Checkpoints that already passed (preserve their content): {passing_str}

Specific revision instructions:
{instructions_block}

PREVIOUS DRAFT:
---
{previous_draft[:8000]}
---

Fix ONLY the problems listed above. Do not remove or weaken content that already passed.
"""


def generate_lesson(
    topic: str,
    learner_profile: str,
    language: str,
    plan: LessonPlan,
    previous_draft: str | None = None,
    failed_checkpoint_ids: list[str] | None = None,
    revision_instructions: list[str] | None = None,
    passing_checkpoint_ids: list[str] | None = None,
) -> str:
    """
    Generate or revise a lesson using the Groq LLM.
    Returns the lesson text as a string.
    """
    settings = get_settings()

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    llm = ChatGroq(
        api_key=SecretStr(settings.groq_api_key),
        model=settings.generator_model,
        temperature=settings.generator_temperature,
        max_tokens=settings.model_max_tokens,
        timeout=settings.provider_timeout_seconds,
        max_retries=settings.provider_sdk_retries,
        stop_sequences=None,
    )

    template = _load_prompt_template()

    revision_section = _build_revision_section(
        previous_draft=previous_draft,
        failed_checkpoint_ids=failed_checkpoint_ids or [],
        revision_instructions=revision_instructions or [],
        passing_checkpoint_ids=passing_checkpoint_ids or [],
    )

    prompt = template.format(
        topic=topic,
        learner_profile=learner_profile,
        language=language,
        learning_objectives=", ".join(plan.learning_objectives),
        key_concepts=", ".join(plan.key_concepts),
        teaching_order=", ".join(plan.teaching_order),
        worked_example=plan.worked_example,
        misconceptions=", ".join(plan.misconceptions),
        revision_section=revision_section,
    )

    is_revision = bool(previous_draft)
    logger.info(
        "Calling generator LLM",
        extra={
            "topic": topic,
            "model": settings.generator_model,
            "is_revision": is_revision,
            "failed_checkpoints": failed_checkpoint_ids or [],
        },
    )

    start_time = time.perf_counter()
    try:
        response = _invoke_with_retry(llm, prompt)
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        error_category = _classify_provider_error(exc)
        record_provider_error(error_category)
        logger.error(
            "Generator LLM call failed",
            extra={
                "error_category": error_category,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(exc)[:200],
            },
        )
        raise

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Generator LLM responded",
        extra={"elapsed_seconds": round(elapsed, 3), "is_revision": is_revision},
    )

    lesson_text = response.content if isinstance(response.content, str) else str(response.content)

    if not lesson_text or len(lesson_text.strip()) < 100:
        raise ValueError("Generator returned an empty or very short response")

    logger.info(
        "Lesson generated",
        extra={"length_chars": len(lesson_text), "is_revision": is_revision},
    )
    return lesson_text.strip()


def build_revision_instructions(
    failed_checkpoints: list[dict],
) -> list[str]:
    """
    Build concrete revision instructions from the failed checkpoint results.
    Each instruction corresponds to one failed checkpoint.
    """
    instructions = []
    for check in failed_checkpoints:
        cid = check.get("id", "UNKNOWN")
        fix = check.get("required_fix", "Please review and fix this section")
        evidence = check.get("evidence", "")

        instr = f"[{cid}] {fix}"
        if evidence:
            instr += f" (Evidence of failure: {evidence[:200]})"
        instructions.append(instr)

    return instructions


def _classify_provider_error(exc: Exception) -> str:
    """Classify a provider exception into a standard error category for metrics/logging."""
    exc_type = type(exc).__name__
    exc_str = str(exc).lower()

    if "timeout" in exc_type.lower() or "timeout" in exc_str:
        return "provider_timeout"
    if "ratelimit" in exc_type.lower() or "rate limit" in exc_str or "429" in exc_str:
        return "provider_rate_limit"
    if any(code in exc_str for code in ("500", "502", "503", "504")):
        return "provider_server_error"
    return "provider_unknown_error"


@make_retry_decorator()
def _invoke_with_retry(llm: ChatGroq, prompt: str):  # type: ignore[return]
    """Invoke the LLM with automatic retries for transient provider errors."""
    return llm.invoke(prompt)
