"""
Hardening tests for the quality gate — false approvals, malformed output, incomplete checkpoints.
All tests are deterministic with no LLM calls or database access.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.quality.decision import compute_quality_gate
from app.quality.schemas import CheckpointResult, EvaluationOutput
from tests.fixtures.lesson_fixtures import (
    make_failing_evaluation,
    make_passing_evaluation,
)

RUBRIC_VERSION = "rag-beginner-v1"
ALL_14_IDS = [
    "ACC-01", "ACC-02", "BEG-01", "JAR-01", "EX-01",
    "COV-01", "COV-02", "COV-03", "COV-04",
    "FLOW-01", "FLOW-02", "CHECK-01", "CONS-01", "SAFE-01",
]


def _make_eval_from_checks(checks_data: list[dict], llm_overall_pass: bool = True) -> EvaluationOutput:
    checks = [CheckpointResult(**c) for c in checks_data]
    return EvaluationOutput(
        rubric_version=RUBRIC_VERSION,
        overall_pass=llm_overall_pass,
        checks=checks,
    )


# ── 1. False approval: LLM claims all pass but one check is FAIL ──────────────


class TestFalseApproval:
    def test_false_approval_all_checks_pass_but_one_fail(self):
        """LLM says overall_pass=True but one check has status=FAIL — gate must return False."""
        checks_data = make_failing_evaluation(failed_ids=["ACC-01"])["checks"]
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,  # LLM erroneously claims pass
            checks=[CheckpointResult(**c) for c in checks_data],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is False
        assert "ACC-01" in result.failed_checkpoint_ids

    def test_false_approval_missing_checkpoint_blocks_pass(self):
        """13 of 14 checkpoints all PASS — missing one must block approval and set eval error."""
        checks_data = make_passing_evaluation()["checks"]
        # Remove one checkpoint
        checks_data_13 = [c for c in checks_data if c["id"] != "SAFE-01"]
        evaluation = _make_eval_from_checks(checks_data_13, llm_overall_pass=True)
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is False
        assert result.is_evaluation_error is True
        assert "SAFE-01" in result.missing_checkpoint_ids


# ── 2. Malformed evaluator output ─────────────────────────────────────────────


class TestMalformedEvaluatorOutput:
    def test_malformed_eval_invalid_json_raises(self):
        """A non-JSON string from the LLM must raise ValueError in the evaluator parse path."""
        import json as json_mod

        raw = "this is not json at all !!!"
        with pytest.raises((ValueError, json_mod.JSONDecodeError)):
            json_mod.loads(raw)

    def test_malformed_eval_invalid_json_via_evaluator_raises_valueerror(self):
        """The evaluator module must raise ValueError for invalid JSON."""
        from app.agents import evaluator as evaluator_agent

        mock_response = MagicMock()
        mock_response.content = "this is not json at all !!!"

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_response
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError, match="invalid JSON"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )

    def test_malformed_eval_schema_violation_raises(self):
        """Valid JSON but wrong schema (checks is a string) must raise ValueError."""
        from app.agents import evaluator as evaluator_agent

        bad_eval = json.dumps({
            "rubric_version": RUBRIC_VERSION,
            "overall_pass": True,
            "checks": "not_a_list",  # Wrong type
        })
        mock_response = MagicMock()
        mock_response.content = bad_eval

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_response
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError, match="schema validation"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )


# ── 3. Incomplete checkpoint sets ─────────────────────────────────────────────


class TestIncompleteCheckpoints:
    def test_incomplete_checkpoint_set_never_approves(self):
        """13 of 14 checkpoints all PASS — gate must return overall_pass=False."""
        checks_data = make_passing_evaluation()["checks"]
        checks_13 = [c for c in checks_data if c["id"] != "CHECK-01"]
        evaluation = _make_eval_from_checks(checks_13)
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.overall_pass is False
        assert result.is_evaluation_error is True

    def test_empty_checkpoint_list_never_approves(self):
        """Empty checks list must be rejected either at schema level or gate level."""
        # Pydantic requires min_length=1 on checks, so this should raise
        with pytest.raises(Exception):
            EvaluationOutput(
                rubric_version=RUBRIC_VERSION,
                overall_pass=True,
                checks=[],
            )


# ── 4. Rubric version mismatch ────────────────────────────────────────────────


class TestRubricVersionMismatch:
    def test_rubric_version_mismatch_is_eval_error(self):
        """
        When evaluation.rubric_version != expected rubric_version in state,
        node_validate_evaluation must treat this as evaluation_error.
        """
        from app.workflow.nodes import node_validate_evaluation
        from tests.fixtures.lesson_fixtures import make_passing_evaluation

        passing_eval_data = make_passing_evaluation()
        eval_obj = EvaluationOutput(
            rubric_version="rag-advanced-v99",  # Wrong version
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in passing_eval_data["checks"]],
        )

        state = {
            "current_evaluation": eval_obj,
            "rubric_version": RUBRIC_VERSION,  # Expected: rag-beginner-v1
        }
        result = node_validate_evaluation(state)
        assert result.get("final_status") == "evaluation_error"
        assert "mismatch" in (result.get("error_detail") or "").lower()


# ── 5. App-level override of LLM overall_pass ────────────────────────────────


class TestAppOverrideLLMOverallPass:
    def test_all_pass_llm_says_false_app_overrides_to_true(self):
        """All 14 checkpoints PASS but LLM says overall_pass=False — app must compute True."""
        checks_data = make_passing_evaluation()["checks"]
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=False,  # LLM erroneously says fail
            checks=[CheckpointResult(**c) for c in checks_data],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        # App must override LLM and compute True
        assert result.overall_pass is True
        assert not result.is_evaluation_error


# ── 6. Reference material prompt injection tests ──────────────────────────────


class TestReferenceMateria:
    def test_reference_material_absent_prompt_contains_model_based(self):
        """When no reference material, prompt must contain 'model-based assessment'."""
        from app.agents import evaluator as evaluator_agent
        from tests.fixtures.lesson_fixtures import make_passing_evaluation

        captured_prompts: list[str] = []

        passing_eval_json = json.dumps(make_passing_evaluation())
        mock_response = MagicMock()
        mock_response.content = passing_eval_json

        def capture_invoke(prompt: str, **kwargs):
            captured_prompts.append(prompt)
            return mock_response

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = capture_invoke
            mock_llm_class.return_value = mock_instance

            evaluator_agent.evaluate_lesson(
                lesson_content="A lesson about RAG.",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
                reference_material=None,
            )

        assert len(captured_prompts) == 1
        assert "model-based assessment" in captured_prompts[0]

    def test_reference_material_present_injected_into_prompt(self):
        """When reference material is supplied, it must appear in the evaluator prompt."""
        from app.agents import evaluator as evaluator_agent
        from tests.fixtures.lesson_fixtures import make_passing_evaluation

        captured_prompts: list[str] = []
        ref_text = "This is the trusted reference: RAG uses vector databases."

        passing_eval_json = json.dumps(make_passing_evaluation())
        mock_response = MagicMock()
        mock_response.content = passing_eval_json

        def capture_invoke(prompt: str, **kwargs):
            captured_prompts.append(prompt)
            return mock_response

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = capture_invoke
            mock_llm_class.return_value = mock_instance

            evaluator_agent.evaluate_lesson(
                lesson_content="A lesson about RAG.",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
                reference_material=ref_text,
            )

        assert len(captured_prompts) == 1
        assert ref_text in captured_prompts[0]
        assert "REFERENCE MATERIAL" in captured_prompts[0]


# ── 7. Checkpoint count mismatch → hard ValueError ────────────────────────────


class TestCheckpointCountEnforcement:
    """
    The evaluator must reject responses where the LLM returned a different number
    of checkpoints than the rubric defines. This prevents the API from reporting
    a passed_count that disagrees with the actual checks array.
    """

    def _build_partial_eval_json(self, n_checks: int) -> str:
        """Build a JSON response with exactly n_checks checkpoints from the rubric."""
        all_ids = ALL_14_IDS[:n_checks]
        checks = [
            {
                "id": cid,
                "status": "PASS",
                "evidence": "Clear evidence here.",
                "reason": f"Checkpoint {cid} is satisfied.",
                "required_fix": None,
            }
            for cid in all_ids
        ]
        return json.dumps({
            "rubric_version": RUBRIC_VERSION,
            "overall_pass": True,
            "checks": checks,
        })

    def test_13_of_14_checks_raises_valueerror(self):
        """Evaluator must raise ValueError when LLM returns 13 of 14 required checkpoints."""
        from app.agents import evaluator as evaluator_agent

        partial_json = self._build_partial_eval_json(13)
        mock_response = MagicMock()
        mock_response.content = partial_json

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_response
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError, match="requires exactly 14"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="Some lesson text about RAG.",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )

    def test_15_checks_raises_valueerror(self):
        """Evaluator must raise ValueError when LLM returns 15 checks (one extra invented ID)."""
        from app.agents import evaluator as evaluator_agent

        # Build a valid 14-check response then add an extra invented check
        checks = json.loads(self._build_partial_eval_json(14))["checks"]
        checks.append({
            "id": "ACC-01",  # duplicate — will also fail schema/gate but count check fires first
            "status": "PASS",
            "evidence": "Extra check.",
            "reason": "Should not exist.",
            "required_fix": None,
        })
        bad_json = json.dumps({
            "rubric_version": RUBRIC_VERSION,
            "overall_pass": True,
            "checks": checks,
        })

        mock_response = MagicMock()
        mock_response.content = bad_json

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_response
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError, match="requires exactly 14"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="Some lesson text about RAG.",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )

    def test_exact_14_checks_does_not_raise(self):
        """Evaluator must not raise when LLM returns exactly 14 checkpoints."""
        from app.agents import evaluator as evaluator_agent
        from tests.fixtures.lesson_fixtures import make_passing_evaluation

        passing_json = json.dumps(make_passing_evaluation())
        mock_response = MagicMock()
        mock_response.content = passing_json

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = mock_response
            mock_llm_class.return_value = mock_instance

            # Should succeed without raising
            result = evaluator_agent.evaluate_lesson(
                lesson_content="Some lesson text about RAG.",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        assert len(result.checks) == 14
        assert result.overall_pass is True
