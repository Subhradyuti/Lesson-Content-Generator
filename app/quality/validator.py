"""
Rubric validator — structural validation of evaluator output.

This module is the second firewall between raw LLM output and a quality gate
decision. It verifies that the evaluator's JSON response:

  1. Passes Pydantic schema validation (done in evaluator.py before this runs).
  2. Contains every mandatory checkpoint ID exactly once.
  3. Contains no unknown checkpoint IDs.
  4. Has no duplicate IDs.
  5. Has valid PASS/FAIL status values (enforced by Pydantic).

The application always calls compute_quality_gate() (in decision.py) rather than
trusting the LLM-supplied overall_pass field.  This module provides helpers used
by tests and the improvement candidate system.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.quality.rubric import load_rubric
from app.quality.schemas import EvaluationOutput


@dataclass
class ValidationReport:
    """Detailed report from structural validation of an EvaluationOutput."""

    is_valid: bool
    missing_ids: list[str] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    unknown_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def summary(self) -> str:
        if self.is_valid:
            return "Evaluation output is structurally valid."
        parts = []
        if self.missing_ids:
            parts.append(f"Missing checkpoints: {self.missing_ids}")
        if self.duplicate_ids:
            parts.append(f"Duplicate checkpoint IDs: {self.duplicate_ids}")
        if self.unknown_ids:
            parts.append(f"Unknown checkpoint IDs: {self.unknown_ids}")
        if self.errors:
            parts.append(f"Other errors: {self.errors}")
        return " | ".join(parts)


def validate_evaluation_structure(
    evaluation: EvaluationOutput,
    rubric_version: str,
) -> ValidationReport:
    """
    Validate structural correctness of an EvaluationOutput against the rubric.

    Does NOT compute the pass/fail outcome — that is the job of compute_quality_gate().
    This function answers only: "Is the evaluator output structurally complete and
    consistent with the rubric definition?"

    Args:
        evaluation: The Pydantic-validated evaluation output from the evaluator LLM.
        rubric_version: The rubric version string (e.g. "rag-beginner-v1").

    Returns:
        A ValidationReport describing any structural problems found.
    """
    rubric = load_rubric(rubric_version)
    mandatory_ids = rubric.mandatory_ids
    all_rubric_ids = rubric.all_ids

    seen_ids: list[str] = [c.id for c in evaluation.checks]

    # Detect duplicates
    id_counts: dict[str, int] = {}
    for cid in seen_ids:
        id_counts[cid] = id_counts.get(cid, 0) + 1
    duplicate_ids = sorted(cid for cid, count in id_counts.items() if count > 1)

    unique_ids = frozenset(seen_ids)

    # Missing mandatory IDs
    missing_ids = sorted(mandatory_ids - unique_ids)

    # Unknown IDs (present in evaluation but not in rubric at all)
    unknown_ids = sorted(unique_ids - all_rubric_ids)

    errors: list[str] = []
    for check in evaluation.checks:
        if check.status == "FAIL" and not check.required_fix:
            errors.append(f"Checkpoint {check.id} has status FAIL but no required_fix provided.")

    is_valid = not (missing_ids or duplicate_ids or unknown_ids or errors)

    return ValidationReport(
        is_valid=is_valid,
        missing_ids=missing_ids,
        duplicate_ids=duplicate_ids,
        unknown_ids=unknown_ids,
        errors=errors,
    )


def assert_evaluation_valid(evaluation: EvaluationOutput, rubric_version: str) -> None:
    """
    Raise ValueError if the evaluation output fails structural validation.
    Used in tests and CI benchmark runs.
    """
    report = validate_evaluation_structure(evaluation, rubric_version)
    if not report.is_valid:
        raise ValueError(f"Evaluation structure invalid: {report.summary}")
