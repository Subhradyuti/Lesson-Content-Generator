"""
LangGraph conditional routing functions.
Each function receives the current state and returns the name of the next node.
All paths must terminate — no unbounded loops.
All error paths route through finalize_run → persist_results → return_result
to ensure every run is persisted regardless of outcome.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.workflow.state import WorkflowState

logger = get_logger(__name__)


def route_after_validate(state: WorkflowState) -> str:
    """After validation: go to planning or finalize (error path)."""
    if state.get("final_status"):
        return "finalize_run"
    return "create_lesson_plan"


def route_after_plan(state: WorkflowState) -> str:
    """After planning: generate or finalize (error path)."""
    if state.get("final_status"):
        return "finalize_run"
    return "generate_lesson"


def route_after_generate(state: WorkflowState) -> str:
    """After generation: evaluate or finalize (error path)."""
    if state.get("final_status"):
        return "finalize_run"
    return "evaluate_lesson"


def route_after_evaluate(state: WorkflowState) -> str:
    """After evaluation: validate the evaluator output or finalize (error path)."""
    if state.get("final_status"):
        return "finalize_run"
    return "validate_evaluation"


def route_after_validate_evaluation(state: WorkflowState) -> str:
    """After evaluation validation: decide next action or finalize (error path)."""
    if state.get("final_status"):
        return "finalize_run"

    gate_result = state.get("quality_gate_result")

    if gate_result is None:
        # Should not happen — treat as error
        logger.error("No quality gate result after validation")
        return "finalize_run"

    if gate_result.is_evaluation_error:
        # Structural problem with evaluator output — route to finalize (evaluation_error)
        return "finalize_run"

    return "decide_next_action"


def route_after_decide(state: WorkflowState) -> str:
    """
    Core routing decision:
    - If the quality gate passed → finalize and persist
    - If it failed and retries remain → build revision instructions
    - If retries exhausted → finalize failure and persist

    Retry budget enforcement:
      attempt 0 = initial draft
      attempt 1 = first revision
      attempt 2 = second revision (max)
    After attempt 2, no more retries regardless of max_retries setting.
    """
    gate_result = state.get("quality_gate_result")

    if gate_result is None or gate_result.overall_pass:
        # PASS path
        return "finalize_run"

    # FAIL path — check retry budget
    current_attempt = state.get("current_attempt", 0)
    max_retries = state.get("max_retries", 2)

    # Hard limit: max 2 content retries (3 total drafts)
    max_retries = min(max_retries, 2)

    if current_attempt < max_retries:
        logger.info(
            "Quality gate failed — retry available",
            extra={
                "current_attempt": current_attempt,
                "max_retries": max_retries,
                "failed_checkpoints": gate_result.failed_checkpoint_ids,
            },
        )
        return "build_revision_instructions"
    else:
        logger.info(
            "Quality gate failed — retry budget exhausted",
            extra={
                "current_attempt": current_attempt,
                "max_retries": max_retries,
            },
        )
        return "finalize_run"


def route_after_build_revision(state: WorkflowState) -> str:
    """After building revision instructions: generate the next draft."""
    if state.get("final_status"):
        return "finalize_run"
    return "generate_lesson"


def route_after_finalize(state: WorkflowState) -> str:
    """After finalize_run: always persist."""
    return "persist_results"


def route_after_persist(state: WorkflowState) -> str:
    """After persisting: always return the result."""
    return "return_result"
