"""
FastAPI routes for lesson generation and retrieval.
Each route delegates to the workflow or repository — no business logic in route handlers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request, status

from app.api.schemas import (
    CheckpointResultResponse,
    EvaluationResponse,
    LessonRequest,
    LessonResponse,
    PriorRunSummary,
    RejectionLogEntry,
    RunHistoryResponse,
    RunStatusResponse,
)
from app.core.config import get_settings
from app.core.logging import get_logger, set_request_id, set_run_id
from app.core.security import RequireApiKey, sanitize_reference_material, sanitize_user_input
from app.observability.metrics import (
    record_generation_attempt,
    record_run_completed,
    record_run_started,
)
from app.workflow.graph import run_workflow
from app.workflow.state import WorkflowState

logger = get_logger(__name__)
router = APIRouter()


# ── POST /v1/lessons ──────────────────────────────────────────────────────────


@router.post(
    "/v1/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a lesson",
    description=(
        "Submit a topic and learner profile. The system generates a complete lesson, "
        "evaluates it against a strict binary rubric, and revises it up to max_retries times. "
        "Returns the accepted lesson and full evaluation, or a detailed failure report."
    ),
)
def create_lesson(
    request: Request,
    body: LessonRequest,
    _api_key: RequireApiKey,
) -> LessonResponse:
    # Generate a request ID for tracing
    request_id = str(uuid.uuid4())
    set_request_id(request_id)

    run_id = str(uuid.uuid4())
    set_run_id(run_id)

    # Protect against prompt injection in user-supplied fields
    try:
        topic = sanitize_user_input(body.topic)
        learner_profile = sanitize_user_input(body.learner_profile)
        # Sanitize each learning objective
        objectives = [sanitize_user_input(obj) for obj in body.learning_objectives]
        # Sanitize reference material if provided
        reference_material = (
            sanitize_reference_material(body.reference_material)
            if body.reference_material
            else None
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    logger.info(
        "Lesson generation request received",
        extra={
            "request_id": request_id,
            "run_id": run_id,
            "topic": topic,
            "max_retries": body.max_retries,
        },
    )

    record_run_started(topic)

    # Build initial workflow state
    initial_state: dict = {
        "run_id": run_id,
        "topic": topic,
        "learner_profile": learner_profile,
        "language": body.language,
        "learning_objectives": objectives,
        "max_retries": body.max_retries,
        "reference_material": reference_material,
    }

    try:
        final_state: WorkflowState = run_workflow(initial_state)
    except Exception as exc:
        logger.error(
            "Workflow execution failed unexpectedly",
            extra={"run_id": run_id, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during lesson generation.",
        ) from exc

    final_status = final_state.get("final_status") or "generation_error"
    attempt_count = final_state.get("current_attempt", 0) or 0

    record_run_completed(final_status)
    record_generation_attempt(attempt_count)

    return _build_lesson_response(final_state, run_id)


# ── GET /v1/lessons/{run_id} ──────────────────────────────────────────────────


@router.get(
    "/v1/lessons/{run_id}",
    response_model=RunStatusResponse,
    summary="Get run status",
    description="Retrieve the status and summary of a lesson generation run.",
)
def get_lesson_status(
    run_id: str,
    _api_key: RequireApiKey,
) -> RunStatusResponse:
    try:
        from app.memory.repository import get_run_by_id

        run = get_run_by_id(run_id)
    except Exception as exc:
        logger.error("Failed to retrieve run", extra={"run_id": run_id, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve run — database may be unavailable.",
        ) from exc

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return RunStatusResponse(
        run_id=run.id,
        status=run.status,
        topic=run.topic,
        attempt_count=run.attempt_count,
        draft_count=run.draft_count,
        retry_count=run.retry_count,
        created_at=run.created_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        rubric_version=run.rubric_version,
        model_name=run.model_name,
        error_detail=run.error_detail,
    )


# ── GET /v1/lessons/{run_id}/history ─────────────────────────────────────────


@router.get(
    "/v1/lessons/{run_id}/history",
    response_model=RunHistoryResponse,
    summary="Get run history",
    description=(
        "Retrieve all drafts, evaluations, and revision logs for a run. "
        "Requires authentication. Each draft includes its evaluation results."
    ),
)
def get_lesson_history(
    run_id: str,
    _api_key: RequireApiKey,
) -> RunHistoryResponse:
    try:
        from app.memory.repository import get_run_with_history

        history = get_run_with_history(run_id)
    except Exception as exc:
        logger.error("Failed to retrieve history", extra={"run_id": run_id, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to retrieve history — database may be unavailable.",
        ) from exc

    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found",
        )

    return RunHistoryResponse(**history)


# ── Helper: build LessonResponse from final WorkflowState ────────────────────


def _build_lesson_response(state: WorkflowState, run_id: str) -> LessonResponse:
    """Convert the final workflow state to the API response schema."""
    from typing import Literal, cast

    settings = get_settings()

    raw_status = state.get("final_status") or "generation_error"
    valid_statuses = ("passed", "failed_quality_gate", "generation_error", "evaluation_error")
    if raw_status not in valid_statuses:
        raw_status = "generation_error"
    final_status = cast(
        Literal["passed", "failed_quality_gate", "generation_error", "evaluation_error"],
        raw_status,
    )
    attempt_count = state.get("current_attempt", 0) or 0
    evaluation_data = state.get("current_evaluation")
    gate_result = state.get("quality_gate_result")
    has_reference_material = bool(state.get("reference_material"))

    # Build evaluation response
    evaluation_response: EvaluationResponse | None = None
    if evaluation_data and gate_result:
        checks = [
            CheckpointResultResponse(
                id=c.id,
                status=c.status,
                evidence=c.evidence,
                reason=c.reason,
                required_fix=c.required_fix,
            )
            for c in evaluation_data.checks
        ]
        # Grounding note: when no reference material was supplied, ACC-02 is
        # plausibility-based only. Surface this explicitly so callers understand
        # the confidence level and are not misled into treating it as verified.
        grounding_note: str | None = None
        if not has_reference_material:
            grounding_note = (
                "ACC-02 (Grounding) was evaluated without external reference material. "
                "The accuracy check is plausibility-based only — claims have not been "
                "independently verified against trusted sources. Supply 'reference_material' "
                "in the request for source-grounded accuracy verification."
            )
        evaluation_response = EvaluationResponse(
            rubric_version=state.get("rubric_version", settings.rubric_version),
            overall_pass=gate_result.overall_pass,
            checks=checks,
            passed_count=sum(1 for c in checks if c.status == "PASS"),
            failed_count=sum(1 for c in checks if c.status == "FAIL"),
            grounding_note=grounding_note,
        )

    # Build rejection log
    raw_log = state.get("rejection_log", [])
    rejection_log = []
    for entry in raw_log:
        rejection_log.append(
            RejectionLogEntry(
                attempt=entry.get("attempt", 0),
                timestamp=entry.get("timestamp", ""),
                failed_checkpoint_ids=entry.get("failed_checkpoint_ids", []),
                failed_checks_detail=entry.get("failed_checks_detail", []),
                revision_instructions=entry.get("revision_instructions", []),
                evaluation_error=entry.get("evaluation_error"),
                reason=entry.get("reason"),
            )
        )

    # Retrieve prior runs for the same topic — demonstrates persistent memory
    # across separate API requests without any client-side state.
    prior_run_summaries: list[PriorRunSummary] = []
    topic = state.get("topic", "")
    if topic:
        try:
            from app.memory.repository import get_prior_runs_for_topic

            raw_prior = get_prior_runs_for_topic(topic=topic, exclude_run_id=run_id, limit=5)
            prior_run_summaries = [
                PriorRunSummary(
                    run_id=p["run_id"],
                    status=p["status"],
                    draft_count=p["draft_count"],
                    retry_count=p["retry_count"],
                    failed_checkpoint_ids=p["failed_checkpoint_ids"],
                    created_at=p["created_at"],
                )
                for p in raw_prior
            ]
        except Exception as exc:
            # Prior run lookup is non-critical — log but never fail the request
            logger.warning(
                "Failed to retrieve prior runs for topic",
                extra={"topic": topic, "error": str(exc)[:200]},
            )

    # Determine if last draft is available for review
    has_drafts = bool(state.get("all_drafts"))

    return LessonResponse(
        run_id=run_id,
        status=final_status,
        attempt_count=state.get("draft_count", attempt_count) or attempt_count,
        draft_count=state.get("draft_count", attempt_count) or attempt_count,
        retry_count=state.get("retry_count", 0) or 0,
        rubric_version=state.get("rubric_version", settings.rubric_version),
        model_name=state.get("model_name", settings.generator_model),
        lesson=state.get("final_lesson"),
        evaluation=evaluation_response,
        rejection_log=rejection_log,
        prior_run_summaries=prior_run_summaries,
        last_draft_available_for_review=has_drafts and final_status != "passed",
        error_detail=state.get("error_detail"),
    )
