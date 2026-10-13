"""
API request and response Pydantic schemas.
All user-facing data structures are defined here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Request Schemas ────────────────────────────────────────────────────────────


class LessonRequest(BaseModel):
    """POST /v1/lessons request body."""

    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The topic for the lesson (e.g., 'Introduction to RAG')",
    )
    learner_profile: str = Field(
        default="Class 12 graduate in India; beginner; limited English vocabulary; "
        "may not have studied in an English-medium school",
        max_length=1000,
        description="Description of the target learner",
    )
    language: str = Field(
        default="simple English",
        max_length=100,
        description="Language and register for the lesson",
    )
    learning_objectives: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Optional list of specific learning outcomes",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=2,
        description="Maximum number of revision attempts (0, 1, or 2)",
    )
    reference_material: str | None = Field(
        default=None,
        max_length=50000,
        description="Optional trusted reference text to ground the lesson",
    )

    @field_validator("max_retries")
    @classmethod
    def validate_max_retries(cls, v: int) -> int:
        if v not in (0, 1, 2):
            raise ValueError("max_retries must be 0, 1, or 2")
        return v

    @field_validator("learning_objectives")
    @classmethod
    def validate_objectives(cls, v: list[str]) -> list[str]:
        if len(v) > 10:
            raise ValueError("At most 10 learning objectives are allowed")
        cleaned = [obj.strip() for obj in v if obj.strip()]
        for obj in cleaned:
            if len(obj) > 300:
                raise ValueError(
                    f"Each learning objective must be at most 300 characters "
                    f"(got {len(obj)} characters)"
                )
        return cleaned


# ── Response Schemas ───────────────────────────────────────────────────────────


class CheckpointResultResponse(BaseModel):
    """Single rubric checkpoint result in the API response."""

    id: str
    status: Literal["PASS", "FAIL"]
    evidence: str
    reason: str
    required_fix: str | None = None


class EvaluationResponse(BaseModel):
    """Evaluation summary in the API response."""

    rubric_version: str
    overall_pass: bool  # Application-computed, not LLM-supplied
    checks: list[CheckpointResultResponse]
    passed_count: int
    failed_count: int
    grounding_note: str | None = Field(
        default=None,
        description=(
            "Grounding confidence note for ACC-02. Present when no reference material "
            "was supplied — indicates the accuracy check is plausibility-based only."
        ),
    )

    @model_validator(mode="after")
    def counts_match_checks(self) -> "EvaluationResponse":
        """Assert that passed_count + failed_count equals the number of check objects.

        This fires at serialization time as a final defensive check: even if the evaluator
        count enforcement in evaluator.py passes, this validator makes it structurally
        impossible to return a response where the count fields disagree with the checks array.
        """
        actual_passed = sum(1 for c in self.checks if c.status == "PASS")
        actual_failed = sum(1 for c in self.checks if c.status == "FAIL")
        if self.passed_count != actual_passed:
            raise ValueError(
                f"passed_count={self.passed_count} does not match "
                f"the number of PASS checks ({actual_passed}) in the checks array"
            )
        if self.failed_count != actual_failed:
            raise ValueError(
                f"failed_count={self.failed_count} does not match "
                f"the number of FAIL checks ({actual_failed}) in the checks array"
            )
        return self


class RejectionLogEntry(BaseModel):
    """One entry in the rejection log — describes a failed draft and its revision."""

    attempt: int
    timestamp: str
    failed_checkpoint_ids: list[str]
    failed_checks_detail: list[dict[str, Any]] = Field(default_factory=list)
    revision_instructions: list[str]
    evaluation_error: str | None = None
    reason: str | None = None


class PriorRunSummary(BaseModel):
    """Summary of a previous run for the same topic, surfaced for transparency."""

    run_id: str
    status: str
    draft_count: int
    retry_count: int
    failed_checkpoint_ids: list[str] = Field(default_factory=list)
    created_at: str


class LessonResponse(BaseModel):
    """POST /v1/lessons response."""

    run_id: str
    status: Literal["passed", "failed_quality_gate", "generation_error", "evaluation_error"]
    attempt_count: int
    draft_count: int = Field(default=0, description="Total drafts generated (1-indexed)")
    retry_count: int = Field(default=0, description="Number of revision cycles completed")
    rubric_version: str
    model_name: str
    lesson: str | None = Field(
        default=None,
        description=(
            "The final lesson content. On status='passed' this is the accepted "
            "lesson. On 'evaluation_error'/'generation_error' it is the last valid "
            "draft preserved for review when one exists; otherwise None."
        ),
    )
    evaluation: EvaluationResponse | None = Field(
        default=None,
        description="The final evaluation result.",
    )
    rejection_log: list[RejectionLogEntry] = Field(
        default_factory=list,
        description="History of all failed drafts and revision instructions.",
    )
    prior_run_summaries: list[PriorRunSummary] = Field(
        default_factory=list,
        description=(
            "Summaries of previous runs for the same topic retrieved from persistent "
            "storage. Demonstrates that memory persists across separate API requests."
        ),
    )
    last_draft_available_for_review: bool = False
    error_detail: str | None = None


class RunStatusResponse(BaseModel):
    """GET /v1/lessons/{run_id} response."""

    run_id: str
    status: str
    topic: str
    attempt_count: int
    draft_count: int = Field(default=0)
    retry_count: int = Field(default=0)
    created_at: str
    completed_at: str | None
    rubric_version: str
    model_name: str
    error_detail: str | None = None


class RunHistoryResponse(BaseModel):
    """GET /v1/lessons/{run_id}/history response."""

    run: dict[str, Any]
    drafts: list[dict[str, Any]]
    revision_logs: list[dict[str, Any]]


# ── Health Schemas ─────────────────────────────────────────────────────────────


class LivenessResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "degraded", "not_ready"]
    database: bool
    details: dict[str, Any] = Field(default_factory=dict)
