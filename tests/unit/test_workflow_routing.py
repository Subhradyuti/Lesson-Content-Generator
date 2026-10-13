"""
Unit tests for workflow routing logic.
All tests use mocked state — no LLM calls or database.
"""

from __future__ import annotations

import pytest

from app.quality.decision import QualityGateResult
from app.workflow.routing import (
    route_after_decide,
    route_after_validate,
    route_after_validate_evaluation,
)


def _make_gate_result(
    overall_pass: bool,
    failed_ids: list[str] | None = None,
    is_eval_error: bool = False,
) -> QualityGateResult:
    """Build a minimal QualityGateResult for routing tests."""
    return QualityGateResult(
        overall_pass=overall_pass,
        failed_checkpoint_ids=failed_ids or [],
        missing_checkpoint_ids=["MISSING-01"] if is_eval_error else [],
        duplicate_checkpoint_ids=[],
        unknown_checkpoint_ids=[],
        error_message="Structural error" if is_eval_error else None,
        checks=[],
    )


# ── route_after_validate ──────────────────────────────────────────────────────


class TestRouteAfterValidate:
    def test_no_error_goes_to_plan(self):
        state = {"topic": "Test"}
        assert route_after_validate(state) == "create_lesson_plan"

    def test_error_goes_to_finalize(self):
        """Error paths now route through finalize_run to ensure persistence."""
        state = {"topic": "Test", "final_status": "generation_error"}
        assert route_after_validate(state) == "finalize_run"


# ── route_after_decide ────────────────────────────────────────────────────────


class TestRouteAfterDecide:
    def test_pass_goes_to_finalize(self):
        """Passing runs go through finalize_run before persist."""
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=True),
            "current_attempt": 0,
            "max_retries": 2,
        }
        assert route_after_decide(state) == "finalize_run"

    def test_fail_with_retry_available_goes_to_revision(self):
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": 0,
            "max_retries": 2,
        }
        assert route_after_decide(state) == "build_revision_instructions"

    def test_fail_after_max_retries_goes_to_finalize(self):
        """After attempt 2 with max_retries=2, no more retries — finalize."""
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": 2,
            "max_retries": 2,
        }
        assert route_after_decide(state) == "finalize_run"

    def test_max_retries_0_no_retry_on_failure(self):
        """With max_retries=0, any failure immediately goes to finalize."""
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": 0,
            "max_retries": 0,
        }
        assert route_after_decide(state) == "finalize_run"

    def test_max_retries_1_allows_one_retry(self):
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": 0,
            "max_retries": 1,
        }
        assert route_after_decide(state) == "build_revision_instructions"

    def test_max_retries_1_exhausted_after_attempt_1(self):
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": 1,
            "max_retries": 1,
        }
        assert route_after_decide(state) == "finalize_run"

    def test_hard_limit_clamped_to_2(self):
        """Even if max_retries were somehow > 2, hard limit still applies."""
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": 2,
            "max_retries": 99,  # Bypassed validation — hard limit still applies
        }
        assert route_after_decide(state) == "finalize_run"

    def test_none_gate_result_goes_to_finalize(self):
        """If gate result is missing (error state), go to finalize."""
        state = {
            "quality_gate_result": None,
            "current_attempt": 0,
            "max_retries": 2,
        }
        assert route_after_decide(state) == "finalize_run"


# ── route_after_validate_evaluation ──────────────────────────────────────────


class TestRouteAfterValidateEvaluation:
    def test_eval_error_goes_to_finalize(self):
        """Evaluation errors route through finalize_run for persistence."""
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, is_eval_error=True),
        }
        assert route_after_validate_evaluation(state) == "finalize_run"

    def test_no_eval_error_goes_to_decide(self):
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=True),
        }
        assert route_after_validate_evaluation(state) == "decide_next_action"

    def test_final_status_set_goes_to_finalize(self):
        """Pre-existing final_status routes to finalize for persistence."""
        state = {
            "final_status": "evaluation_error",
            "quality_gate_result": _make_gate_result(overall_pass=True),
        }
        assert route_after_validate_evaluation(state) == "finalize_run"


# ── Retry termination tests ───────────────────────────────────────────────────


class TestRetryTermination:
    """Verify the system never exceeds 2 content retries."""

    @pytest.mark.parametrize(
        "attempt,max_r,expected",
        [
            (0, 0, "finalize_run"),  # 0 retries: fail immediately → finalize
            (0, 1, "build_revision_instructions"),  # 1 retry: first attempt can retry
            (1, 1, "finalize_run"),  # 1 retry exhausted → finalize
            (0, 2, "build_revision_instructions"),  # 2 retries: attempt 0 can retry
            (1, 2, "build_revision_instructions"),  # 2 retries: attempt 1 can retry
            (2, 2, "finalize_run"),  # 2 retries exhausted → finalize
        ],
    )
    def test_retry_routing(self, attempt, max_r, expected):
        state = {
            "quality_gate_result": _make_gate_result(overall_pass=False, failed_ids=["JAR-01"]),
            "current_attempt": attempt,
            "max_retries": max_r,
        }
        assert route_after_decide(state) == expected
