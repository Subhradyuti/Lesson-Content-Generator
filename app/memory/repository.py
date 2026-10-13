"""
Repository: persist and retrieve workflow run data.
All database operations are in transactions. Concurrent runs are isolated by run_id.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models import (
    Evaluation,
    GenerationRun,
    LessonDraft,
    RevisionLog,
)
from app.db.session import get_db_session
from app.workflow.state import WorkflowState

logger = get_logger(__name__)


def persist_run_results(state: WorkflowState) -> None:
    """
    Persist the complete run state to the database.
    Called at the end of every workflow run regardless of outcome.
    Each draft, evaluation, and revision log is stored atomically.
    """
    settings = get_settings()
    run_id: str = state.get("run_id") or ""
    final_status: str = state.get("final_status") or "generation_error"

    with get_db_session() as session:
        # ── Upsert the GenerationRun record ──────────────────────────────
        existing_run = session.get(GenerationRun, run_id)

        if existing_run is None:
            run = GenerationRun(
                id=run_id,
                topic=state.get("topic", ""),
                learner_profile=state.get("learner_profile", ""),
                language=state.get("language", "simple English"),
                status=final_status,
                max_retries=state.get("max_retries", settings.default_max_retries),
                attempt_count=state.get("current_attempt", 0),
                draft_count=state.get("draft_count", len(state.get("all_drafts", []))),
                retry_count=state.get("retry_count", state.get("current_attempt", 0)),
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                prompt_version=state.get("prompt_version", settings.prompt_version),
                rubric_version=state.get("rubric_version", settings.rubric_version),
                model_provider=state.get("model_provider", "groq"),
                model_name=state.get("model_name", settings.generator_model),
                error_detail=state.get("error_detail"),
            )
            session.add(run)
        else:
            existing_run.status = final_status
            existing_run.attempt_count = state.get("current_attempt", 0) or 0
            existing_run.draft_count = state.get("draft_count", len(state.get("all_drafts", []))) or 0
            existing_run.retry_count = state.get("retry_count", state.get("current_attempt", 0)) or 0
            existing_run.completed_at = datetime.now(UTC)
            existing_run.error_detail = state.get("error_detail") or None  # type: ignore[assignment]

        session.flush()

        # ── Persist each draft and its evaluation ────────────────────────
        all_drafts = state.get("all_drafts", [])
        all_evaluations = state.get("all_evaluations", [])

        draft_db_ids = []
        for attempt_num, draft_text in enumerate(all_drafts):
            draft_record = LessonDraft(
                run_id=run_id,
                attempt_number=attempt_num,
                lesson_content={"text": draft_text},
                content_hash=LessonDraft.compute_hash(draft_text),
            )
            session.add(draft_record)
            session.flush()
            draft_db_ids.append(draft_record.id)

            # Persist evaluation for this draft if available
            if attempt_num < len(all_evaluations):
                evaluation = all_evaluations[attempt_num]
                gate_result = None
                if attempt_num == len(all_drafts) - 1:
                    gate_result = state.get("quality_gate_result")

                # Intermediate drafts (not the last) definitionally failed — they triggered
                # a revision. Only use the app-computed gate result for the final draft.
                if attempt_num < len(all_drafts) - 1:
                    app_overall_pass = False
                elif gate_result is not None:
                    app_overall_pass = gate_result.overall_pass
                else:
                    app_overall_pass = evaluation.overall_pass

                eval_record = Evaluation(
                    draft_id=draft_record.id,
                    rubric_version=state.get("rubric_version", settings.rubric_version),
                    overall_pass=app_overall_pass,
                    evaluation_json=evaluation.model_dump(),
                    evaluator_model=settings.evaluator_model,
                )
                session.add(eval_record)

        # ── Persist revision logs ────────────────────────────────────────
        rejection_log = state.get("rejection_log", [])
        for log_entry in rejection_log:
            attempt_num = log_entry.get("attempt", 0)
            rev_log = RevisionLog(
                run_id=run_id,
                attempt_number=attempt_num,
                failed_checkpoint_ids=log_entry.get("failed_checkpoint_ids", []),
                revision_instructions=log_entry.get("revision_instructions", []),
                failed_checks_detail=log_entry.get("failed_checks_detail", []),
                evaluation_error=log_entry.get("evaluation_error"),
            )
            session.add(rev_log)

        logger.info(
            "Run persisted",
            extra={
                "run_id": run_id,
                "status": final_status,
                "drafts_count": len(all_drafts),
                "revision_logs_count": len(rejection_log),
            },
        )


def get_run_by_id(run_id: str) -> GenerationRun | None:
    """Retrieve a GenerationRun by ID."""
    with get_db_session() as session:
        return session.get(GenerationRun, run_id)


def get_run_with_history(run_id: str) -> dict[str, Any] | None:
    """Retrieve a run with all its drafts, evaluations, and revision logs."""
    with get_db_session() as session:
        run = session.get(GenerationRun, run_id)
        if run is None:
            return None

        # Load drafts with evaluations
        drafts_stmt = (
            select(LessonDraft)
            .where(LessonDraft.run_id == run_id)
            .order_by(LessonDraft.attempt_number)
        )
        drafts = list(session.scalars(drafts_stmt))

        drafts_data = []
        for draft in drafts:
            evals = [
                {
                    "id": e.id,
                    "overall_pass": e.overall_pass,
                    "rubric_version": e.rubric_version,
                    "evaluation_json": e.evaluation_json,
                    "created_at": e.created_at.isoformat(),
                    "evaluator_model": e.evaluator_model,
                }
                for e in draft.evaluations
            ]
            drafts_data.append(
                {
                    "id": draft.id,
                    "attempt_number": draft.attempt_number,
                    "content_hash": draft.content_hash,
                    "created_at": draft.created_at.isoformat(),
                    "lesson_content": draft.lesson_content,
                    "evaluations": evals,
                }
            )

        # Load revision logs
        revisions_stmt = (
            select(RevisionLog)
            .where(RevisionLog.run_id == run_id)
            .order_by(RevisionLog.attempt_number)
        )
        revision_logs = [
            {
                "id": r.id,
                "attempt_number": r.attempt_number,
                "failed_checkpoint_ids": r.failed_checkpoint_ids,
                "revision_instructions": r.revision_instructions,
                "failed_checks_detail": r.failed_checks_detail,
                "created_at": r.created_at.isoformat(),
                "evaluation_error": r.evaluation_error,
            }
            for r in session.scalars(revisions_stmt)
        ]

        return {
            "run": {
                "id": run.id,
                "topic": run.topic,
                "learner_profile": run.learner_profile,
                "language": run.language,
                "status": run.status,
                "max_retries": run.max_retries,
                "attempt_count": run.attempt_count,
                "created_at": run.created_at.isoformat(),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "prompt_version": run.prompt_version,
                "rubric_version": run.rubric_version,
                "model_provider": run.model_provider,
                "model_name": run.model_name,
                "error_detail": run.error_detail,
            },
            "drafts": drafts_data,
            "revision_logs": revision_logs,
        }


def get_prior_runs_for_topic(
    topic: str,
    exclude_run_id: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Retrieve lightweight summaries of previous completed runs for the same topic.

    Returns at most `limit` runs ordered by creation time (newest first), each
    with their failed checkpoint IDs collected across all revision logs.

    This is the persistence layer for cross-request memory: callers can use the
    returned summaries to show that the system remembers prior attempts, and the
    workflow can use them to avoid repeating known failure patterns.

    Args:
        topic: The lesson topic to match (case-sensitive exact match).
        exclude_run_id: A run ID to exclude (typically the current run).
        limit: Maximum number of prior runs to return.

    Returns:
        List of dicts with keys: run_id, status, draft_count, retry_count,
        failed_checkpoint_ids (union across all revision logs), created_at.
    """
    with get_db_session() as session:
        stmt = (
            select(GenerationRun)
            .where(GenerationRun.topic == topic)
            .where(GenerationRun.status.in_(["passed", "failed_quality_gate"]))
            .order_by(GenerationRun.created_at.desc())
            .limit(limit + 1)  # fetch one extra so we can exclude current and still get limit
        )
        runs = list(session.scalars(stmt))

        summaries = []
        for run in runs:
            if exclude_run_id and run.id == exclude_run_id:
                continue
            if len(summaries) >= limit:
                break

            # Collect all failed checkpoint IDs across revision logs for this run
            rev_stmt = select(RevisionLog).where(RevisionLog.run_id == run.id)
            failed_ids: list[str] = []
            for rev in session.scalars(rev_stmt):
                for fid in (rev.failed_checkpoint_ids or []):
                    if fid not in failed_ids:
                        failed_ids.append(fid)

            summaries.append(
                {
                    "run_id": run.id,
                    "status": run.status,
                    "draft_count": run.draft_count,
                    "retry_count": run.retry_count,
                    "failed_checkpoint_ids": failed_ids,
                    "created_at": run.created_at.isoformat(),
                }
            )

        return summaries
