"""
Unit tests for the application-level quality gate decision logic.
These tests are fully deterministic — no LLM calls or database.
"""

from __future__ import annotations

import pytest

from app.quality.decision import compute_quality_gate
from app.quality.schemas import CheckpointResult, EvaluationOutput
from tests.fixtures.lesson_fixtures import (
    make_failing_evaluation,
    make_passing_evaluation,
)

RUBRIC_VERSION = "rag-beginner-v1"
ALL_CHECKPOINT_IDS = [
    "ACC-01",
    "ACC-02",
    "BEG-01",
    "JAR-01",
    "EX-01",
    "COV-01",
    "COV-02",
    "COV-03",
    "COV-04",
    "FLOW-01",
    "FLOW-02",
    "CHECK-01",
    "CONS-01",
    "SAFE-01",
]


def _make_evaluation(checks_data: list[dict]) -> EvaluationOutput:
    """Helper to build an EvaluationOutput from a list of check dicts."""
    checks = [CheckpointResult(**c) for c in checks_data]
    return EvaluationOutput(
        rubric_version=RUBRIC_VERSION,
        overall_pass=all(c.status == "PASS" for c in checks),
        checks=checks,
    )


# ── Tests: all checks pass ────────────────────────────────────────────────────


class TestQualityGatePass:
    def test_all_pass_returns_overall_pass_true(self):
        eval_data = make_passing_evaluation()
        evaluation = _make_evaluation(eval_data["checks"])
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is True

    def test_all_pass_no_failed_checkpoints(self):
        eval_data = make_passing_evaluation()
        evaluation = _make_evaluation(eval_data["checks"])
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.failed_checkpoint_ids == []

    def test_all_pass_no_structural_errors(self):
        eval_data = make_passing_evaluation()
        evaluation = _make_evaluation(eval_data["checks"])
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert not result.is_evaluation_error


# ── Tests: single failure ─────────────────────────────────────────────────────


class TestQualityGateSingleFailure:
    def test_one_fail_returns_overall_pass_false(self):
        eval_data = make_failing_evaluation(failed_ids=["JAR-01"])
        evaluation = _make_evaluation(eval_data["checks"])
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is False

    def test_one_fail_lists_correct_failed_id(self):
        eval_data = make_failing_evaluation(failed_ids=["JAR-01"])
        evaluation = _make_evaluation(eval_data["checks"])
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert "JAR-01" in result.failed_checkpoint_ids

    def test_llm_says_pass_but_one_check_fails(self):
        """The application must override the LLM's overall_pass when a check fails."""
        checks_data = make_failing_evaluation(failed_ids=["COV-04"])["checks"]
        # Simulate LLM incorrectly claiming overall_pass=True
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,  # LLM says pass — but it's wrong
            checks=[CheckpointResult(**c) for c in checks_data],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        # Application must override and say FAIL
        assert result.overall_pass is False
        assert "COV-04" in result.failed_checkpoint_ids


# ── Tests: multiple failures ──────────────────────────────────────────────────


class TestQualityGateMultipleFailures:
    def test_multiple_failures_all_listed(self):
        failed = ["JAR-01", "BEG-01", "EX-01"]
        eval_data = make_failing_evaluation(failed_ids=failed)
        evaluation = _make_evaluation(eval_data["checks"])
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is False
        for fid in failed:
            assert fid in result.failed_checkpoint_ids


# ── Tests: missing checkpoints ────────────────────────────────────────────────


class TestQualityGateMissingCheckpoints:
    def test_missing_checkpoint_is_evaluation_error(self):
        """Only providing 1 of 14 checkpoints is a structural error."""
        checks_data = [
            {
                "id": "ACC-01",
                "status": "PASS",
                "evidence": "Clear evidence here.",
                "reason": "This checkpoint is satisfied by content.",
                "required_fix": None,
            }
        ]
        evaluation = _make_evaluation(checks_data)
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.is_evaluation_error is True
        assert result.overall_pass is False
        assert len(result.missing_checkpoint_ids) > 0

    def test_missing_checkpoint_ids_are_correct(self):
        checks_data = [
            {
                "id": "ACC-01",
                "status": "PASS",
                "evidence": "Clear evidence here.",
                "reason": "This checkpoint is satisfied by content.",
                "required_fix": None,
            }
        ]
        evaluation = _make_evaluation(checks_data)
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        expected_missing = set(ALL_CHECKPOINT_IDS) - {"ACC-01"}
        assert set(result.missing_checkpoint_ids) == expected_missing


# ── Tests: duplicate checkpoints ──────────────────────────────────────────────


class TestQualityGateDuplicateCheckpoints:
    def test_duplicate_checkpoint_is_evaluation_error(self):
        checks_data = [
            {
                "id": "ACC-01",
                "status": "PASS",
                "evidence": "Evidence one is here.",
                "reason": "Reason one is satisfied.",
                "required_fix": None,
            },
            {
                "id": "ACC-01",
                "status": "PASS",
                "evidence": "Evidence two is here.",
                "reason": "Reason two is satisfied.",
                "required_fix": None,
            },
        ]
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in checks_data],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.is_evaluation_error is True
        assert "ACC-01" in result.duplicate_checkpoint_ids

    def test_duplicate_never_interpreted_as_passing(self):
        checks_data = [
            {
                "id": "ACC-01",
                "status": "PASS",
                "evidence": "Evidence one is here.",
                "reason": "Reason one is satisfied.",
                "required_fix": None,
            },
            {
                "id": "ACC-01",
                "status": "PASS",
                "evidence": "Evidence two is here.",
                "reason": "Reason two is satisfied.",
                "required_fix": None,
            },
        ]
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in checks_data],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is False


# ── Tests: unknown checkpoint IDs ─────────────────────────────────────────────


class TestQualityGateUnknownCheckpoints:
    def test_unknown_checkpoint_id_is_evaluation_error(self):
        checks_data = [
            {
                "id": "FAKE-99",
                "status": "PASS",
                "evidence": "Evidence is present.",
                "reason": "This checkpoint passes.",
                "required_fix": None,
            }
        ]
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in checks_data],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.is_evaluation_error is True
        assert "FAKE-99" in result.unknown_checkpoint_ids


# ── Tests: schema validation ───────────────────────────────────────────────────


class TestCheckpointResultSchema:
    def test_fail_requires_required_fix(self):
        with pytest.raises(Exception):
            CheckpointResult(
                id="JAR-01",
                status="FAIL",
                evidence="Some evidence",
                reason="Some reason",
                required_fix=None,  # Must not be None when status is FAIL
            )

    def test_pass_allows_null_required_fix(self):
        result = CheckpointResult(
            id="ACC-01",
            status="PASS",
            evidence="Evidence here",
            reason="Reason here",
            required_fix=None,
        )
        assert result.status == "PASS"

    def test_invalid_status_rejected(self):
        with pytest.raises(Exception):
            CheckpointResult(
                id="ACC-01",
                status="MAYBE",  # Invalid
                evidence="e",
                reason="r",
            )
