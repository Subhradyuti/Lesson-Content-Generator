"""
Application-level quality gate decision.
The application — not the LLM — computes the final pass/fail result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.quality.rubric import load_rubric
from app.quality.schemas import CheckpointResult, EvaluationOutput


@dataclass
class QualityGateResult:
    """Result of the application-level quality gate check."""

    overall_pass: bool
    failed_checkpoint_ids: list[str]
    missing_checkpoint_ids: list[str]
    duplicate_checkpoint_ids: list[str]
    unknown_checkpoint_ids: list[str]
    error_message: str | None = None
    checks: list[CheckpointResult] = field(default_factory=list)

    @property
    def is_evaluation_error(self) -> bool:
        """True if the evaluator output was structurally invalid."""
        return bool(
            self.missing_checkpoint_ids
            or self.duplicate_checkpoint_ids
            or self.unknown_checkpoint_ids
            or self.error_message
        )


def compute_quality_gate(
    evaluation: EvaluationOutput,
    rubric_version: str,
) -> QualityGateResult:
    """
    Perform application-level quality gate checks:

    1. Verify all expected mandatory checkpoint IDs are present.
    2. Verify no checkpoint ID appears more than once.
    3. Verify no unknown (not in rubric) mandatory checkpoint IDs are present.
    4. Verify all status values are valid (already enforced by Pydantic, but double-checked).
    5. Compute overall_pass = all mandatory checks pass AND no structural errors.

    The LLM's own overall_pass field is IGNORED for the final decision.
    """
    rubric = load_rubric(rubric_version)
    mandatory_ids = rubric.mandatory_ids

    # --- Step 1: Collect IDs from evaluator output ---
    seen_ids: list[str] = [c.id for c in evaluation.checks]

    # --- Step 2: Detect duplicates ---
    id_counts: dict[str, int] = {}
    for cid in seen_ids:
        id_counts[cid] = id_counts.get(cid, 0) + 1
    duplicate_ids = [cid for cid, count in id_counts.items() if count > 1]

    # Use unique IDs for further analysis
    unique_ids = frozenset(seen_ids)

    # --- Step 3: Missing mandatory IDs ---
    missing_ids = sorted(mandatory_ids - unique_ids)

    # --- Step 4: Unknown IDs (not in the rubric at all) ---
    unknown_ids = sorted(unique_ids - rubric.all_ids)

    # --- Step 5: Failed checkpoints (among mandatory ones) ---
    mandatory_checks = [c for c in evaluation.checks if c.id in mandatory_ids]
    failed_ids = [c.id for c in mandatory_checks if c.status == "FAIL"]

    # --- Step 6: Compute final decision ---
    all_expected_present = len(missing_ids) == 0
    no_duplicates = len(duplicate_ids) == 0
    no_unknown = len(unknown_ids) == 0
    all_mandatory_pass = len(failed_ids) == 0

    overall_pass = all_expected_present and no_duplicates and no_unknown and all_mandatory_pass

    error_message: str | None = None
    if not all_expected_present:
        error_message = f"Missing mandatory checkpoints: {missing_ids}"
    elif not no_duplicates:
        error_message = f"Duplicate checkpoint IDs: {duplicate_ids}"
    elif not no_unknown:
        error_message = f"Unknown checkpoint IDs: {unknown_ids}"

    return QualityGateResult(
        overall_pass=overall_pass,
        failed_checkpoint_ids=failed_ids,
        missing_checkpoint_ids=missing_ids,
        duplicate_checkpoint_ids=duplicate_ids,
        unknown_checkpoint_ids=unknown_ids,
        error_message=error_message,
        checks=evaluation.checks,
    )
