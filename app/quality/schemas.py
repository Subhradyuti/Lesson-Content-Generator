"""
Pydantic schemas for evaluator output.
The evaluator must return exactly this structure; any deviation is treated as an evaluation error.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CheckpointResult(BaseModel):
    """Result for a single rubric checkpoint."""

    id: str = Field(..., description="Checkpoint ID, e.g. 'JAR-01'")
    status: Literal["PASS", "FAIL"] = Field(..., description="Binary outcome")
    evidence: str = Field(
        ..., min_length=5, description="Short quote or section reference from the lesson"
    )
    reason: str = Field(..., min_length=10, description="Explanation of the decision")
    required_fix: str | None = Field(
        default=None,
        description="Concrete correction instruction — required when status is FAIL",
    )

    @model_validator(mode="after")
    def fix_required_on_fail(self) -> CheckpointResult:
        if self.status == "FAIL" and not self.required_fix:
            raise ValueError(
                f"required_fix must be provided when status is FAIL (checkpoint {self.id})"
            )
        return self


class EvaluationOutput(BaseModel):
    """
    Structured output returned by the evaluator LLM call.
    NOTE: The application recomputes overall_pass from the check results;
    it does NOT trust the LLM-supplied overall_pass field.
    """

    rubric_version: str = Field(..., description="Version of the rubric used")
    overall_pass: bool = Field(
        ..., description="LLM-supplied summary — overridden by application logic"
    )
    checks: list[CheckpointResult] = Field(..., min_length=1)
