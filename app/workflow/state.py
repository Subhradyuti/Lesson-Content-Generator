"""
LangGraph workflow state definition.
All workflow data flows through this typed state dict, isolated per run.
"""

from __future__ import annotations

from typing import Any, TypedDict

from app.agents.planner import LessonPlan
from app.quality.decision import QualityGateResult
from app.quality.schemas import EvaluationOutput


class WorkflowState(TypedDict, total=False):
    """Complete state for a single lesson generation run. Each field is set by a workflow node."""

    # ── Request inputs ─────────────────────────────────────────────────────
    run_id: str
    topic: str
    learner_profile: str
    language: str
    learning_objectives: list[str]
    max_retries: int
    reference_material: str | None
    rubric_version: str
    prompt_version: str
    model_provider: str
    model_name: str

    # ── Planning ───────────────────────────────────────────────────────────
    lesson_plan: LessonPlan | None

    # ── Generation ────────────────────────────────────────────────────────
    current_attempt: int   # 0 = initial draft, 1 = first revision, 2 = second
    current_draft: str | None
    all_drafts: list[str]

    # ── Evaluation ────────────────────────────────────────────────────────
    current_evaluation: EvaluationOutput | None
    all_evaluations: list[EvaluationOutput]
    quality_gate_result: QualityGateResult | None

    # ── Revision tracking ─────────────────────────────────────────────────
    revision_instructions: list[str]
    rejection_log: list[dict[str, Any]]

    # ── Terminal state ────────────────────────────────────────────────────
    # final_status: "passed" | "failed_quality_gate" | "generation_error" | "evaluation_error"
    final_status: str | None
    # final_lesson: accepted lesson on pass; last valid draft on error paths; None on quality fail
    final_lesson: str | None
    error_detail: str | None

    # ── Attempt counts (set in node_finalize_run) ─────────────────────────
    draft_count: int   # total drafts generated, 1-indexed
    retry_count: int   # revision cycles completed

    # ── Persistence ───────────────────────────────────────────────────────
    draft_db_ids: list[str]
