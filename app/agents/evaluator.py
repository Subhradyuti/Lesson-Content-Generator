"""
Lesson evaluator agent.
Applies the binary rubric independently of the generator — separate system
prompt, lower temperature to encourage more critical assessment.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from langchain_groq import ChatGroq
from pydantic import SecretStr

from app.agents._retry import make_retry_decorator
from app.core.config import get_settings
from app.core.logging import get_logger
from app.observability.metrics import record_provider_error
from app.quality.rubric import load_rubric
from app.quality.schemas import EvaluationOutput

logger = get_logger(__name__)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "evaluator_v1.md"

EVALUATOR_VERSION = "v1"


def _load_prompt_template() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _format_rubric_checkpoints(rubric_version: str) -> tuple[str, int]:
    """Return a formatted string of rubric checkpoints for the evaluator prompt."""
    rubric = load_rubric(rubric_version)
    lines = []
    for cp in rubric.checkpoints:
        lines.append(
            f"- ID: {cp.id}\n"
            f"  Dimension: {cp.dimension}\n"
            f"  Pass condition: {cp.pass_condition.strip()}"
        )
    return "\n\n".join(lines), len(rubric.checkpoints)


def _build_reference_material_section(reference_material: str | None) -> str:
    """Build the reference material block to inject into the evaluator prompt."""
    if reference_material:
        return (
            "REFERENCE MATERIAL (compare ACC-02 claims against these sources):\n"
            "---\n"
            f"{reference_material}\n"
            "---\n"
            "When evaluating ACC-02, check each factual claim in the lesson against the\n"
            "reference material above. Mark evidence as [reference-supported] or\n"
            "[not found in references]."
        )
    return (
        "No reference material supplied.\n"
        "For ACC-02, base your assessment on widely accepted understanding of RAG.\n"
        "Mark your ACC-02 evidence as '[model-based assessment — no external references supplied]'.\n"
        "Do not claim the lesson was independently verified against external sources."
    )


def _parse_and_validate(raw_text: str, rubric_version: str) -> EvaluationOutput:
    """
    Parse and validate a raw JSON string into an EvaluationOutput.

    Raises ValueError on any of:
    - invalid / truncated JSON
    - schema validation failure
    - wrong number of checkpoints
    """
    _, checkpoint_count = _format_rubric_checkpoints(rubric_version)

    # Strip markdown fences if present
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
        text = text.strip()

    try:
        eval_dict: dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Evaluator returned invalid JSON: {exc}") from exc

    try:
        evaluation = EvaluationOutput.model_validate(eval_dict)
    except Exception as exc:
        raise ValueError(f"Evaluator output failed schema validation: {exc}") from exc

    actual_count = len(evaluation.checks)
    if actual_count != checkpoint_count:
        raise ValueError(
            f"Evaluator returned {actual_count} checkpoint results but rubric "
            f"'{rubric_version}' requires exactly {checkpoint_count}. "
            "Missing or extra checkpoints are not allowed."
        )

    return evaluation


def evaluate_lesson(
    lesson_content: str,
    topic: str,
    learner_profile: str,
    rubric_version: str,
    reference_material: str | None = None,
) -> EvaluationOutput:
    """
    Evaluate a lesson against the rubric using the Groq LLM.

    Returns a validated EvaluationOutput. Raises ValueError if the evaluator
    output is malformed or missing checkpoints after all repair attempts.

    When reference_material is supplied, ACC-02 is evaluated against those
    sources. Without it, ACC-02 uses model-based assessment and the evidence
    field is labelled accordingly.

    JSON robustness strategy:
    - The LLM is invoked with response_format={"type": "json_object"} so the
      provider enforces valid JSON at the token level.
    - evaluator_max_tokens is set higher than model_max_tokens (default 8192)
      so 14 detailed checkpoint results fit without truncation.
    - If JSON parsing still fails (e.g. the model does not honour response_format),
      one bounded repair call is made: a short prompt asking the model to fix the
      broken JSON, capped at 512 tokens. This does NOT count as a lesson revision.
    - If the repair also fails, ValueError is raised and the caller records
      evaluation_error — never silently approving the lesson.
    """
    settings = get_settings()

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    llm = ChatGroq(
        api_key=SecretStr(settings.groq_api_key),
        model=settings.evaluator_model,
        temperature=settings.evaluator_temperature,
        max_tokens=settings.evaluator_max_tokens,
        timeout=settings.provider_timeout_seconds,
        max_retries=settings.provider_sdk_retries,
        stop_sequences=None,
    )

    template = _load_prompt_template()
    rubric_checkpoints_text, checkpoint_count = _format_rubric_checkpoints(rubric_version)
    reference_material_section = _build_reference_material_section(reference_material)

    prompt = template.format(
        topic=topic,
        learner_profile=learner_profile,
        rubric_version=rubric_version,
        lesson_content=lesson_content,
        rubric_checkpoints=rubric_checkpoints_text,
        checkpoint_count=checkpoint_count,
        reference_material_section=reference_material_section,
    )

    logger.info(
        "Calling evaluator LLM",
        extra={
            "topic": topic,
            "rubric_version": rubric_version,
            "model": settings.evaluator_model,
            "lesson_length_chars": len(lesson_content),
            "has_reference_material": reference_material is not None,
        },
    )

    start_time = time.perf_counter()
    try:
        # Pass response_format so the provider enforces valid JSON at the output level.
        # This is the primary defence against truncated / malformed JSON.
        response = _invoke_with_retry(llm, prompt, response_format={"type": "json_object"})
    except Exception as exc:
        elapsed = time.perf_counter() - start_time
        error_category = _classify_provider_error(exc)
        record_provider_error(error_category)
        logger.error(
            "Evaluator LLM call failed",
            extra={
                "error_category": error_category,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(exc)[:200],
            },
        )
        raise

    elapsed = time.perf_counter() - start_time
    logger.info(
        "Evaluator LLM responded",
        extra={"elapsed_seconds": round(elapsed, 3)},
    )

    raw_text = response.content if isinstance(response.content, str) else str(response.content)

    # Attempt to parse the primary response.
    parse_error: ValueError | None = None
    try:
        evaluation = _parse_and_validate(raw_text, rubric_version)
    except ValueError as exc:
        parse_error = exc
        logger.warning(
            "Evaluator primary response failed validation — attempting one repair call",
            extra={"error": str(exc), "raw_preview": raw_text[:300]},
        )

    original_error: ValueError | None = parse_error
    if parse_error is not None:
        # One bounded repair attempt: ask the model to fix the broken JSON.
        # Cap at 512 tokens so the cost is minimal and the budget is explicit.
        repaired_text = _attempt_json_repair(
            llm=llm,
            broken_text=raw_text,
            rubric_version=rubric_version,
            checkpoint_count=checkpoint_count,
        )
        if repaired_text is not None:
            try:
                evaluation = _parse_and_validate(repaired_text, rubric_version)
                logger.info("Evaluator JSON repair succeeded")
                parse_error = None
            except ValueError as repair_exc:
                logger.error(
                    "Evaluator JSON repair also failed",
                    extra={"error": str(repair_exc)},
                )
                # Keep original_error so callers see the right failure message
        else:
            logger.error("Evaluator JSON repair call returned no usable content")

    if parse_error is not None:
        logger.error(
            "Evaluator returned invalid JSON",
            extra={"error": str(original_error), "raw_preview": raw_text[:500]},
        )
        raise original_error  # type: ignore[misc]

    passed_count = sum(1 for c in evaluation.checks if c.status == "PASS")
    failed_count = sum(1 for c in evaluation.checks if c.status == "FAIL")

    logger.info(
        "Evaluation complete",
        extra={
            "llm_overall_pass": evaluation.overall_pass,
            "checks_total": len(evaluation.checks),
            "checks_passed": passed_count,
            "checks_failed": failed_count,
        },
    )

    return evaluation


def _attempt_json_repair(
    llm: ChatGroq,
    broken_text: str,
    rubric_version: str,
    checkpoint_count: int,
) -> str | None:
    """
    Make one short LLM call to repair a broken JSON string.

    Uses a low token cap (512) so this is clearly bounded in cost.
    Returns the repaired text, or None if the call fails.
    Does NOT count as a lesson revision attempt.
    """
    # Trim the broken text to avoid spending tokens sending the whole thing back.
    # 2000 chars is enough to give the model meaningful context.
    excerpt = broken_text[:2000] if len(broken_text) > 2000 else broken_text

    repair_prompt = (
        f"The following JSON was returned by an evaluation model but is malformed "
        f"(truncated, unterminated string, or missing fields). "
        f"Fix it so it is valid JSON matching this structure exactly:\n\n"
        f'{{"rubric_version": string, "overall_pass": bool, "checks": [array of {checkpoint_count} objects]}}\n\n'
        f"Each check object must have: id (string), status (\"PASS\" or \"FAIL\"), "
        f"evidence (string), reason (string), required_fix (string or null).\n\n"
        f"Return ONLY the corrected JSON — no explanation, no markdown fences.\n\n"
        f"BROKEN JSON (first 2000 chars):\n{excerpt}"
    )

    # Use a tight token limit and low temperature for this mechanical repair task.
    repair_llm = llm.bind(max_tokens=512, temperature=0)  # type: ignore[arg-type]
    try:
        repair_response = repair_llm.invoke(
            repair_prompt, response_format={"type": "json_object"}
        )
        content = (
            repair_response.content
            if isinstance(repair_response.content, str)
            else str(repair_response.content)
        )
        return content.strip() or None
    except Exception as exc:
        logger.warning(
            "Evaluator repair call failed",
            extra={"error": str(exc)[:200]},
        )
        return None


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
def _invoke_with_retry(llm: ChatGroq, prompt: str, **kwargs: Any):  # type: ignore[return]
    """Invoke the evaluator LLM with automatic retries for transient provider errors."""
    return llm.invoke(prompt, **kwargs)
