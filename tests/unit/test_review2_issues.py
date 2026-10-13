"""
Tests for the four issues raised in the second API run review.

Issue 1: passed_count must equal the number of PASS objects in checks — enforced
         by EvaluationResponse.counts_match_checks model_validator.
Issue 2+3: ACC-02 claim-level verification — evaluator prompt now requires
           enumerated claims with labels; tested via prompt content checks.
Issue 4: prior_run_summaries in the API response proves persistent memory by
         returning previous run data retrieved from the DB.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.api.schemas import (
    CheckpointResultResponse,
    EvaluationResponse,
    PriorRunSummary,
)
from tests.fixtures.lesson_fixtures import (
    PASSING_LESSON,
    PASSING_LESSON_PLAN,
    make_failing_evaluation,
    make_passing_evaluation,
)

RUBRIC_VERSION = "rag-beginner-v1"
TEST_API_KEY = "test-integration-key"


@pytest.fixture
def client():
    from app.main import app
    from fastapi.testclient import TestClient

    return TestClient(
        app,
        raise_server_exceptions=False,
        headers={"X-API-Key": TEST_API_KEY},
    )


def _make_llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


# ── Issue 1: EvaluationResponse count validator ───────────────────────────────


class TestEvaluationResponseCountValidator:
    """EvaluationResponse must reject mismatched passed_count / failed_count at build time."""

    def _make_checks(self, n_pass: int, n_fail: int) -> list[CheckpointResultResponse]:
        checks = []
        for i in range(n_pass):
            checks.append(
                CheckpointResultResponse(
                    id=f"ACC-0{i + 1}",
                    status="PASS",
                    evidence="Evidence",
                    reason="Reason",
                )
            )
        for i in range(n_fail):
            checks.append(
                CheckpointResultResponse(
                    id=f"FAIL-0{i + 1}",
                    status="FAIL",
                    evidence="Evidence",
                    reason="Reason",
                    required_fix="Fix this",
                )
            )
        return checks

    def test_correct_counts_accepted(self):
        checks = self._make_checks(n_pass=2, n_fail=1)
        response = EvaluationResponse(
            rubric_version=RUBRIC_VERSION,
            overall_pass=False,
            checks=checks,
            passed_count=2,
            failed_count=1,
        )
        assert response.passed_count == 2
        assert response.failed_count == 1

    def test_inflated_passed_count_rejected(self):
        """passed_count=14 but only 13 PASS checks must be rejected."""
        checks = self._make_checks(n_pass=13, n_fail=0)
        with pytest.raises(Exception, match="passed_count=14"):
            EvaluationResponse(
                rubric_version=RUBRIC_VERSION,
                overall_pass=True,
                checks=checks,
                passed_count=14,   # ← inflated by 1, mimicking the reported bug
                failed_count=0,
            )

    def test_inflated_failed_count_rejected(self):
        """failed_count must match actual FAIL objects."""
        checks = self._make_checks(n_pass=13, n_fail=1)
        with pytest.raises(Exception, match="failed_count=2"):
            EvaluationResponse(
                rubric_version=RUBRIC_VERSION,
                overall_pass=False,
                checks=checks,
                passed_count=13,
                failed_count=2,   # ← inflated by 1
            )

    def test_zero_counts_with_empty_checks_rejected_by_schema(self):
        """EvaluationOutput requires min_length=1 on checks."""
        from pydantic import ValidationError

        from app.quality.schemas import EvaluationOutput

        with pytest.raises(ValidationError):
            EvaluationOutput(
                rubric_version=RUBRIC_VERSION,
                overall_pass=True,
                checks=[],
            )


# ── Issue 2+3: Evaluator prompt ACC-02 claim-level protocol ──────────────────


class TestEvaluatorPromptACC02Protocol:
    """
    The evaluator prompt must instruct the LLM to enumerate claims with
    [reference-supported] / [widely-accepted-concept] / [unverified-specific-claim]
    labels for ACC-02, and must prohibit using 'all claims are consistent with
    common knowledge' as evidence.
    """

    def _load_prompt_filled(self) -> str:
        """Load the evaluator prompt template and fill placeholders with dummy values."""
        from app.agents.evaluator import _build_reference_material_section, _format_rubric_checkpoints
        from app.prompts import __file__ as prompts_init
        from pathlib import Path

        prompt_path = Path(prompts_init).parent / "evaluator_v1.md"
        template = prompt_path.read_text(encoding="utf-8")
        checkpoints_text, count = _format_rubric_checkpoints(RUBRIC_VERSION)
        ref_section = _build_reference_material_section(None)
        return template.format(
            topic="Introduction to RAG",
            learner_profile="beginner",
            rubric_version=RUBRIC_VERSION,
            lesson_content="A short lesson.",
            rubric_checkpoints=checkpoints_text,
            checkpoint_count=count,
            reference_material_section=ref_section,
        )

    def test_prompt_contains_claim_level_protocol(self):
        """The evaluator prompt must describe claim-level enumeration for ACC-02."""
        filled = self._load_prompt_filled()
        assert "ACC-02 CLAIM-LEVEL VERIFICATION PROTOCOL" in filled, (
            "Evaluator prompt must contain 'ACC-02 CLAIM-LEVEL VERIFICATION PROTOCOL' section"
        )

    def test_prompt_defines_unverified_specific_claim_label(self):
        """The prompt must define [unverified-specific-claim] as a mandatory label."""
        filled = self._load_prompt_filled()
        assert "[unverified-specific-claim]" in filled, (
            "Evaluator prompt must define the [unverified-specific-claim] label"
        )

    def test_prompt_defines_widely_accepted_concept_label(self):
        filled = self._load_prompt_filled()
        assert "[widely-accepted-concept]" in filled

    def test_prompt_defines_reference_supported_label(self):
        filled = self._load_prompt_filled()
        assert "[reference-supported]" in filled

    def test_prompt_prohibits_common_knowledge_shortcut(self):
        """'all claims are consistent with common knowledge' must be banned."""
        filled = self._load_prompt_filled()
        assert "All claims are consistent with common knowledge\" is NOT acceptable" in filled

    def test_prompt_requires_768_dimensional_to_fail(self):
        """
        The prompt must explicitly name '768-dimensional vector' as an example
        of an [unverified-specific-claim] when no references are supplied.
        """
        filled = self._load_prompt_filled()
        assert "768-dimensional" in filled, (
            "Evaluator prompt must mention '768-dimensional vector' as an example "
            "of an unverified specific claim that causes ACC-02 to FAIL"
        )

    def test_evidence_field_requirement_for_acc02(self):
        """The IMPORTANT block must state that ACC-02 evidence must contain enumerated claims."""
        filled = self._load_prompt_filled()
        assert "enumerated claim list" in filled


# ── Issue 4: prior_run_summaries in API response (persistent memory) ──────────


class TestPriorRunSummariesInResponse:
    """
    The API response must include prior_run_summaries populated from the DB
    for any previous runs with the same topic. An empty list is valid when this
    is the first run; a non-empty list proves cross-request persistent memory.
    """

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_first_run_has_empty_prior_summaries(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """First run for a topic must return prior_run_summaries=[]."""
        plan_instance = MagicMock()
        plan_instance.invoke.return_value = _make_llm_response(json.dumps(PASSING_LESSON_PLAN))
        mock_plan_llm.return_value = plan_instance

        gen_instance = MagicMock()
        gen_instance.invoke.return_value = _make_llm_response(PASSING_LESSON)
        mock_gen_llm.return_value = gen_instance

        eval_instance = MagicMock()
        eval_instance.invoke.return_value = _make_llm_response(
            json.dumps(make_passing_evaluation())
        )
        mock_eval_llm.return_value = eval_instance

        response = client.post(
            "/v1/lessons",
            json={"topic": "First-time topic for memory test XYZ-unique-001", "max_retries": 0},
        )
        assert response.status_code == 200
        data = response.json()
        # First ever run for this topic — no prior runs to return
        assert data["prior_run_summaries"] == [], (
            f"Expected empty prior_run_summaries for first run, got: {data['prior_run_summaries']}"
        )

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_second_run_sees_first_run_in_summaries(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """
        After one run completes and is persisted, a second run for the same topic
        must return the first run in prior_run_summaries — proving persistent memory.
        """
        topic = "Memory-proof topic for cross-run test XYZ-unique-002"

        plan_instance = MagicMock()
        plan_instance.invoke.return_value = _make_llm_response(json.dumps(PASSING_LESSON_PLAN))
        mock_plan_llm.return_value = plan_instance

        gen_instance = MagicMock()
        gen_instance.invoke.return_value = _make_llm_response(PASSING_LESSON)
        mock_gen_llm.return_value = gen_instance

        eval_instance = MagicMock()
        eval_instance.invoke.return_value = _make_llm_response(
            json.dumps(make_passing_evaluation())
        )
        mock_eval_llm.return_value = eval_instance

        # ── Run 1 ──────────────────────────────────────────────────────────
        run1_response = client.post(
            "/v1/lessons",
            json={"topic": topic, "max_retries": 0},
        )
        assert run1_response.status_code == 200
        run1_data = run1_response.json()
        run1_id = run1_data["run_id"]
        assert run1_data["status"] == "passed"

        # ── Run 2: same topic, separate request ────────────────────────────
        run2_response = client.post(
            "/v1/lessons",
            json={"topic": topic, "max_retries": 0},
        )
        assert run2_response.status_code == 200
        run2_data = run2_response.json()

        # Run 2 must see Run 1 in prior_run_summaries
        prior = run2_data["prior_run_summaries"]
        assert len(prior) >= 1, (
            f"Expected at least 1 prior run summary, got: {prior}"
        )
        prior_ids = [p["run_id"] for p in prior]
        assert run1_id in prior_ids, (
            f"Run 1 ({run1_id}) should appear in prior_run_summaries of Run 2, "
            f"but prior_run_summaries contains: {prior_ids}"
        )

        # The summary must have the expected shape
        run1_summary = next(p for p in prior if p["run_id"] == run1_id)
        assert run1_summary["status"] == "passed"
        assert "draft_count" in run1_summary
        assert "retry_count" in run1_summary
        assert "created_at" in run1_summary

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_prior_summaries_exclude_current_run(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """The current run's own run_id must never appear in prior_run_summaries."""
        plan_instance = MagicMock()
        plan_instance.invoke.return_value = _make_llm_response(json.dumps(PASSING_LESSON_PLAN))
        mock_plan_llm.return_value = plan_instance

        gen_instance = MagicMock()
        gen_instance.invoke.return_value = _make_llm_response(PASSING_LESSON)
        mock_gen_llm.return_value = gen_instance

        eval_instance = MagicMock()
        eval_instance.invoke.return_value = _make_llm_response(
            json.dumps(make_passing_evaluation())
        )
        mock_eval_llm.return_value = eval_instance

        response = client.post(
            "/v1/lessons",
            json={"topic": "Self-exclusion test topic XYZ-unique-003", "max_retries": 0},
        )
        assert response.status_code == 200
        data = response.json()
        current_run_id = data["run_id"]

        prior_ids = [p["run_id"] for p in data["prior_run_summaries"]]
        assert current_run_id not in prior_ids, (
            f"Current run_id {current_run_id} must NOT appear in prior_run_summaries"
        )

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_grounding_note_present_without_reference_material(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """
        When no reference_material is supplied, evaluation.grounding_note must
        be a non-empty string explaining that ACC-02 is plausibility-based.
        """
        plan_instance = MagicMock()
        plan_instance.invoke.return_value = _make_llm_response(json.dumps(PASSING_LESSON_PLAN))
        mock_plan_llm.return_value = plan_instance

        gen_instance = MagicMock()
        gen_instance.invoke.return_value = _make_llm_response(PASSING_LESSON)
        mock_gen_llm.return_value = gen_instance

        eval_instance = MagicMock()
        eval_instance.invoke.return_value = _make_llm_response(
            json.dumps(make_passing_evaluation())
        )
        mock_eval_llm.return_value = eval_instance

        response = client.post(
            "/v1/lessons",
            json={"topic": "Grounding note test topic", "max_retries": 0},
            # No reference_material supplied
        )
        assert response.status_code == 200
        data = response.json()
        grounding_note = data["evaluation"]["grounding_note"]
        assert grounding_note is not None, (
            "grounding_note must be present when no reference_material is supplied"
        )
        assert "plausibility-based" in grounding_note, (
            f"grounding_note should describe plausibility-based assessment, got: {grounding_note}"
        )
        assert "ACC-02" in grounding_note

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.evaluate_lesson")
    def test_grounding_note_absent_with_reference_material(
        self, mock_evaluate, mock_gen_llm, mock_plan_llm, client
    ):
        """
        When reference_material IS supplied, grounding_note must be None —
        the accuracy check is source-grounded, not plausibility-based.
        """
        from app.quality.schemas import CheckpointResult, EvaluationOutput

        plan_instance = MagicMock()
        plan_instance.invoke.return_value = _make_llm_response(json.dumps(PASSING_LESSON_PLAN))
        mock_plan_llm.return_value = plan_instance

        gen_instance = MagicMock()
        gen_instance.invoke.return_value = _make_llm_response(PASSING_LESSON)
        mock_gen_llm.return_value = gen_instance

        eval_data = make_passing_evaluation()
        mock_evaluate.return_value = EvaluationOutput(
            rubric_version="rag-beginner-v1",
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in eval_data["checks"]],
        )

        response = client.post(
            "/v1/lessons",
            json={
                "topic": "Grounding note absent test",
                "max_retries": 0,
                "reference_material": "RAG uses a vector database. Embeddings are numerical representations.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["evaluation"]["grounding_note"] is None, (
            "grounding_note must be None when reference_material was supplied"
        )
