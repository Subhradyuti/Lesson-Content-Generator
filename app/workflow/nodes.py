"""
LangGraph workflow nodes.
Each node receives the current state and returns a partial state update.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from app.agents import evaluator as evaluator_agent
from app.agents import generator as generator_agent
from app.agents import planner as planner_agent
from app.agents.generator import build_revision_instructions
from app.agents.planner import LessonPlan
from app.core.config import get_settings
from app.core.logging import get_logger, set_run_id
from app.quality.decision import compute_quality_gate
from app.quality.schemas import EvaluationOutput
from app.workflow.state import WorkflowState

logger = get_logger(__name__)


# ── Node 1: validate_request ──────────────────────────────────────────────────


def node_validate_request(state: WorkflowState) -> dict[str, Any]:
    """Validate request parameters and initialise per-run tracking fields."""
    settings = get_settings()

    run_id = state.get("run_id") or str(uuid.uuid4())
    set_run_id(run_id)

    max_retries = state.get("max_retries", settings.default_max_retries)

    # Enforce hard maximum — API validation normally catches this, but the
    # workflow clamps it defensively so the loop is always bounded.
    if max_retries not in (0, 1, 2):
        logger.warning(
            "Invalid max_retries value; clamping to default",
            extra={"requested": max_retries},
        )
        max_retries = min(max(max_retries, 0), 2)

    topic = state.get("topic", "").strip()
    if not topic:
        return {
            "final_status": "generation_error",
            "error_detail": "topic is required and must not be empty",
            "run_id": run_id,
        }

    if len(topic) > settings.max_topic_length:
        return {
            "final_status": "generation_error",
            "error_detail": f"topic exceeds maximum length of {settings.max_topic_length} characters",
            "run_id": run_id,
        }

    learner_profile = state.get("learner_profile", "")
    if learner_profile and len(learner_profile) > settings.max_learner_profile_length:
        return {
            "final_status": "generation_error",
            "error_detail": (
                f"learner_profile exceeds maximum length of "
                f"{settings.max_learner_profile_length} characters"
            ),
            "run_id": run_id,
        }

    logger.info(
        "Request validated",
        extra={"run_id": run_id, "topic": topic, "max_retries": max_retries},
    )

    return {
        "run_id": run_id,
        "max_retries": max_retries,
        "current_attempt": 0,
        "all_drafts": [],
        "all_evaluations": [],
        "rejection_log": [],
        "draft_db_ids": [],
        "revision_instructions": [],
        "rubric_version": state.get("rubric_version", settings.rubric_version),
        "prompt_version": state.get("prompt_version", settings.prompt_version),
        "model_provider": "groq",
        "model_name": settings.generator_model,
        "final_status": None,
        "final_lesson": None,
        "error_detail": None,
        "lesson_plan": None,
        "current_draft": None,
        "current_evaluation": None,
        "quality_gate_result": None,
    }


# ── Node 2: create_lesson_plan ────────────────────────────────────────────────


def node_create_lesson_plan(state: WorkflowState) -> dict[str, Any]:
    """Call the planner LLM and return a validated lesson plan."""
    topic = state["topic"]
    learner_profile = state.get("learner_profile", "")
    language = state.get("language", "simple English")
    objectives = state.get("learning_objectives", [])

    try:
        plan = planner_agent.create_lesson_plan(
            topic=topic,
            learner_profile=learner_profile,
            language=language,
            learning_objectives=objectives if objectives else None,
        )
        logger.info("Lesson plan created successfully")
        return {"lesson_plan": plan}
    except Exception as exc:
        logger.error("Lesson planning failed", extra={"error": str(exc)})
        return {
            "final_status": "generation_error",
            "error_detail": f"Lesson planning failed: {_sanitize_error(exc)}",
        }


# ── Node 3: generate_lesson ───────────────────────────────────────────────────


def node_generate_lesson(state: WorkflowState) -> dict[str, Any]:
    """Generate the initial draft or a targeted revision of the lesson."""
    topic = state["topic"]
    learner_profile = state.get("learner_profile", "")
    language = state.get("language", "simple English")
    plan: LessonPlan | None = state.get("lesson_plan")
    attempt = state.get("current_attempt", 0)
    all_drafts: list[str] = list(state.get("all_drafts", []))

    # Guard: plan must exist before generation
    if plan is None:
        return {
            "final_status": "generation_error",
            "error_detail": "Cannot generate lesson: no lesson plan available",
        }

    # Build revision context if this is not the first attempt
    previous_draft: str | None = None
    failed_ids: list[str] = []
    revision_instructions: list[str] = []
    passing_ids: list[str] = []

    if attempt > 0 and all_drafts:
        previous_draft = all_drafts[-1]
        gate_result = state.get("quality_gate_result")
        if gate_result:
            failed_ids = gate_result.failed_checkpoint_ids
            passing_ids = [c.id for c in gate_result.checks if c.status == "PASS"]
        revision_instructions = state.get("revision_instructions", [])

    logger.info(
        "Generating lesson",
        extra={"attempt": attempt, "is_revision": attempt > 0},
    )

    try:
        lesson_text = generator_agent.generate_lesson(
            topic=topic,
            learner_profile=learner_profile,
            language=language,
            plan=plan,
            previous_draft=previous_draft,
            failed_checkpoint_ids=failed_ids if failed_ids else None,
            revision_instructions=revision_instructions if revision_instructions else None,
            passing_checkpoint_ids=passing_ids if passing_ids else None,
        )
    except Exception as exc:
        logger.error("Lesson generation failed", extra={"error": str(exc), "attempt": attempt})
        return {
            "final_status": "generation_error",
            "error_detail": f"Generation failed on attempt {attempt}: {_sanitize_error(exc)}",
        }

    all_drafts.append(lesson_text)

    return {
        "current_draft": lesson_text,
        "all_drafts": all_drafts,
    }


# ── Node 4: evaluate_lesson ───────────────────────────────────────────────────


def node_evaluate_lesson(state: WorkflowState) -> dict[str, Any]:
    """Evaluate the current draft against the rubric."""
    draft = state.get("current_draft", "")
    if not draft:
        return {
            "final_status": "evaluation_error",
            "error_detail": "Cannot evaluate: no draft available",
        }

    topic = state["topic"]
    learner_profile = state.get("learner_profile", "")
    rubric_version = state.get("rubric_version", "rag-beginner-v1")
    reference_material = state.get("reference_material")

    logger.info(
        "Evaluating lesson",
        extra={"rubric_version": rubric_version, "attempt": state.get("current_attempt", 0)},
    )

    try:
        evaluation = evaluator_agent.evaluate_lesson(
            lesson_content=draft,
            topic=topic,
            learner_profile=learner_profile,
            rubric_version=rubric_version,
            reference_material=reference_material,
        )
    except Exception as exc:
        logger.error("Evaluation failed", extra={"error": str(exc)})
        return {
            "final_status": "evaluation_error",
            "error_detail": f"Evaluation failed: {_sanitize_error(exc)}",
        }

    all_evals: list[EvaluationOutput] = list(state.get("all_evaluations", []))
    all_evals.append(evaluation)

    return {
        "current_evaluation": evaluation,
        "all_evaluations": all_evals,
    }


# ── Node 5: validate_evaluation ──────────────────────────────────────────────


def node_validate_evaluation(state: WorkflowState) -> dict[str, Any]:
    """
    Compute the application-level quality gate result from the evaluator output.

    The application determines pass/fail independently of the LLM's own
    overall_pass field. Also verifies that the rubric version matches.
    """
    evaluation = state.get("current_evaluation")
    if evaluation is None:
        return {
            "final_status": "evaluation_error",
            "error_detail": "No evaluation to validate",
        }

    rubric_version = state.get("rubric_version", "rag-beginner-v1")

    # Check rubric version matches
    if evaluation.rubric_version != rubric_version:
        logger.warning(
            "Rubric version mismatch in evaluator output",
            extra={
                "expected": rubric_version,
                "got": evaluation.rubric_version,
            },
        )
        return {
            "final_status": "evaluation_error",
            "error_detail": (
                f"Rubric version mismatch: expected {rubric_version}, "
                f"got {evaluation.rubric_version}"
            ),
        }

    try:
        gate_result = compute_quality_gate(evaluation, rubric_version)
    except Exception as exc:
        logger.error("Quality gate computation failed", extra={"error": str(exc)})
        return {
            "final_status": "evaluation_error",
            "error_detail": f"Quality gate error: {_sanitize_error(exc)}",
        }

    if gate_result.is_evaluation_error:
        logger.warning(
            "Evaluation output has structural errors — treating as evaluation_error",
            extra={
                "missing": gate_result.missing_checkpoint_ids,
                "duplicates": gate_result.duplicate_checkpoint_ids,
                "unknown": gate_result.unknown_checkpoint_ids,
                "error_message": gate_result.error_message,
            },
        )

    logger.info(
        "Quality gate computed",
        extra={
            "overall_pass": gate_result.overall_pass,
            "failed_count": len(gate_result.failed_checkpoint_ids),
            "is_eval_error": gate_result.is_evaluation_error,
        },
    )

    return {"quality_gate_result": gate_result}


# ── Node 6: decide_next_action ────────────────────────────────────────────────
# This node exists as a routing decision point in the graph. The actual routing
# logic lives in routing.py (route_after_decide).


def node_decide_next_action(state: WorkflowState) -> dict[str, Any]:
    """Routing decision point — logic is in routing.py (route_after_decide)."""
    return {}


# ── Node 7: build_revision_instructions ──────────────────────────────────────


def node_build_revision_instructions(state: WorkflowState) -> dict[str, Any]:
    """Build targeted revision instructions from failed checkpoints and log the failure."""
    gate_result = state.get("quality_gate_result")
    evaluation = state.get("current_evaluation")
    attempt = state.get("current_attempt", 0)
    rejection_log: list[dict] = list(state.get("rejection_log", []))

    if gate_result is None or evaluation is None:
        return {
            "final_status": "evaluation_error",
            "error_detail": "Cannot build revision instructions: missing evaluation data",
        }

    # Collect failed checkpoint data for the revision prompt
    failed_check_data = [
        {
            "id": c.id,
            "reason": c.reason,
            "evidence": c.evidence,
            "required_fix": c.required_fix or "",
        }
        for c in evaluation.checks
        if c.status == "FAIL"
    ]

    revision_instructions = build_revision_instructions(failed_check_data)

    # Build rejection log entry
    log_entry: dict[str, Any] = {
        "attempt": attempt,
        "timestamp": datetime.now(UTC).isoformat(),
        "failed_checkpoint_ids": gate_result.failed_checkpoint_ids,
        "failed_checks_detail": [
            {
                "id": c.id,
                "reason": c.reason,
                "evidence": c.evidence[:500] if c.evidence else "",
                "required_fix": c.required_fix or "",
            }
            for c in evaluation.checks
            if c.status == "FAIL"
        ],
        "revision_instructions": revision_instructions,
        "evaluation_error": gate_result.error_message,
    }
    rejection_log.append(log_entry)

    logger.info(
        "Revision instructions built",
        extra={
            "attempt": attempt,
            "failed_checkpoints": gate_result.failed_checkpoint_ids,
            "instruction_count": len(revision_instructions),
        },
    )

    return {
        "revision_instructions": revision_instructions,
        "rejection_log": rejection_log,
        "current_attempt": attempt + 1,
    }


# ── Node 8: finalize_run ──────────────────────────────────────────────────────


def node_finalize_run(state: WorkflowState) -> dict[str, Any]:
    """
    Set the final status, lesson, and attempt counts before persistence.

    All terminal paths (pass, fail, error) route through this node to ensure
    persist_results always receives a complete, valid final_status.
    """
    gate_result = state.get("quality_gate_result")
    rejection_log: list[dict] = list(state.get("rejection_log", []))
    all_drafts = state.get("all_drafts", [])
    current_attempt = state.get("current_attempt", 0)

    # Compute draft_count and retry_count
    draft_count = len(all_drafts) if all_drafts else (1 if state.get("current_draft") else 0)
    retry_count = current_attempt  # = number of revision cycles completed

    # If a status was already set by an error path, preserve it.
    # The latest draft is kept on error paths so a provider failure or malformed
    # evaluation output doesn't discard content we already generated.
    last_valid_draft: str | None = all_drafts[-1] if all_drafts else None
    existing_status: str | None = state.get("final_status")
    if existing_status and existing_status != "None":
        # Error path — status is already set (generation_error, evaluation_error)
        final_status: Literal[
            "passed", "failed_quality_gate", "generation_error", "evaluation_error"
        ] = existing_status  # type: ignore[assignment]
        final_lesson = last_valid_draft
    elif gate_result is None:
        final_status = "generation_error"
        final_lesson = last_valid_draft
    elif gate_result.is_evaluation_error:
        final_status = "evaluation_error"
        final_lesson = last_valid_draft
    elif gate_result.overall_pass:
        final_status = "passed"
        final_lesson = state.get("current_draft")
    else:
        final_status = "failed_quality_gate"
        final_lesson = None

        # Add final failure entry to rejection log if not already there.
        # Include full failed_checks_detail so the caller has actionable feedback
        # even when the retry limit is reached — not just the checkpoint IDs.
        if not rejection_log or rejection_log[-1].get("attempt") != current_attempt:
            evaluation = state.get("current_evaluation")
            failed_checks_detail = []
            if evaluation is not None and gate_result is not None:
                failed_checks_detail = [
                    {
                        "id": c.id,
                        "reason": c.reason,
                        "evidence": c.evidence[:500] if c.evidence else "",
                        "required_fix": c.required_fix or "",
                    }
                    for c in evaluation.checks
                    if c.id in gate_result.failed_checkpoint_ids
                ]
            rejection_log.append(
                {
                    "attempt": current_attempt,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "failed_checkpoint_ids": gate_result.failed_checkpoint_ids,
                    "failed_checks_detail": failed_checks_detail,
                    "revision_instructions": [],
                    "reason": "Maximum retry limit reached — no further revisions attempted",
                }
            )

    logger.info(
        "Workflow finalized",
        extra={
            "final_status": final_status,
            "draft_count": draft_count,
            "retry_count": retry_count,
        },
    )

    return {
        "final_status": final_status,
        "final_lesson": final_lesson,
        "rejection_log": rejection_log,
        "draft_count": draft_count,
        "retry_count": retry_count,
    }


# ── Node 9: persist_results ───────────────────────────────────────────────────


def node_persist_results(state: WorkflowState) -> dict[str, Any]:
    """
    Persist the final run to the database.
    Imported lazily to allow testing without a live database.
    """
    try:
        from app.memory.repository import persist_run_results

        persist_run_results(state)
        logger.info("Run results persisted", extra={"run_id": state.get("run_id")})
    except Exception as exc:
        # Database persistence failure should not override a passing result
        logger.error("Failed to persist results", extra={"error": str(exc)})
        # Continue — return the result even if persistence fails

    return {}


# ── Node 10: return_result ────────────────────────────────────────────────────


def node_return_result(state: WorkflowState) -> dict[str, Any]:
    """Terminal node — state is already complete after node_finalize_run."""
    return {}


# ── Helper ────────────────────────────────────────────────────────────────────


def _sanitize_error(exc: Exception) -> str:
    """Return a sanitized error message safe to include in API responses."""
    msg = str(exc)
    # Remove potential secrets from error messages
    for sensitive in ("api_key", "password", "secret", "token", "authorization"):
        if sensitive.lower() in msg.lower():
            return "An internal error occurred. Please check application logs."
    # Truncate very long error messages
    return msg[:500] if len(msg) > 500 else msg
