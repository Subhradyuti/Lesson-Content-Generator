"""
Unit tests for evaluator JSON parsing, validation, and repair behaviour.

Tests cover:
- Valid JSON accepted and parsed correctly
- Malformed / truncated JSON triggers one bounded repair attempt
- Repair success returns a valid EvaluationOutput
- Repair failure raises ValueError (never silently approves)
- Schema validation failures (wrong structure, missing fields)
- Missing checkpoint IDs detected and raised
- Duplicate checkpoint IDs detected by quality gate
- response_format kwarg is passed on the primary evaluator invoke call
- evaluator_max_tokens is used (not model_max_tokens)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, call, patch

import pytest

from app.quality.schemas import CheckpointResult, EvaluationOutput
from tests.fixtures.lesson_fixtures import make_failing_evaluation, make_passing_evaluation

RUBRIC_VERSION = "rag-beginner-v1"


def _llm_response(content: str) -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


def _passing_json() -> str:
    return json.dumps(make_passing_evaluation())


def _failing_json(failed_ids: list[str]) -> str:
    return json.dumps(make_failing_evaluation(failed_ids))


# ── Helpers ────────────────────────────────────────────────────────────────────


class TestParseAndValidate:
    """Unit tests for the internal _parse_and_validate helper."""

    def test_valid_passing_json_accepted(self):
        from app.agents.evaluator import _parse_and_validate

        result = _parse_and_validate(_passing_json(), RUBRIC_VERSION)
        assert result.overall_pass is True
        assert len(result.checks) == 14

    def test_valid_failing_json_accepted(self):
        from app.agents.evaluator import _parse_and_validate

        result = _parse_and_validate(_failing_json(["JAR-01", "BEG-01"]), RUBRIC_VERSION)
        assert result.overall_pass is False

    def test_markdown_fenced_json_accepted(self):
        from app.agents.evaluator import _parse_and_validate

        fenced = "```json\n" + _passing_json() + "\n```"
        result = _parse_and_validate(fenced, RUBRIC_VERSION)
        assert len(result.checks) == 14

    def test_malformed_json_raises_valueerror(self):
        from app.agents.evaluator import _parse_and_validate

        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_and_validate("this is not json at all", RUBRIC_VERSION)

    def test_truncated_json_raises_valueerror(self):
        from app.agents.evaluator import _parse_and_validate

        # Simulate truncation mid-string (char 6493 in the real failure)
        truncated = _passing_json()[:200]
        with pytest.raises(ValueError, match="invalid JSON"):
            _parse_and_validate(truncated, RUBRIC_VERSION)

    def test_wrong_structure_raises_valueerror(self):
        from app.agents.evaluator import _parse_and_validate

        bad = json.dumps({"rubric_version": RUBRIC_VERSION, "checks": "not_a_list"})
        with pytest.raises(ValueError, match="schema validation"):
            _parse_and_validate(bad, RUBRIC_VERSION)

    def test_missing_required_field_raises_valueerror(self):
        """overall_pass missing — schema validation must catch it."""
        from app.agents.evaluator import _parse_and_validate

        data = make_passing_evaluation()
        del data["overall_pass"]
        with pytest.raises(ValueError, match="schema validation"):
            _parse_and_validate(json.dumps(data), RUBRIC_VERSION)

    def test_13_of_14_checkpoints_raises_valueerror(self):
        from app.agents.evaluator import _parse_and_validate

        data = make_passing_evaluation()
        data["checks"] = [c for c in data["checks"] if c["id"] != "SAFE-01"]
        with pytest.raises(ValueError, match="requires exactly 14"):
            _parse_and_validate(json.dumps(data), RUBRIC_VERSION)

    def test_15_checkpoints_raises_valueerror(self):
        from app.agents.evaluator import _parse_and_validate

        data = make_passing_evaluation()
        extra = dict(data["checks"][0])
        extra["id"] = "EXTRA-01"
        data["checks"].append(extra)
        with pytest.raises(ValueError, match="requires exactly 14"):
            _parse_and_validate(json.dumps(data), RUBRIC_VERSION)


# ── Primary call: response_format and max_tokens ──────────────────────────────


class TestEvaluatorInvokeParameters:
    """The primary LLM call must use response_format and evaluator_max_tokens."""

    def test_response_format_json_object_passed_on_primary_call(self):
        from app.agents import evaluator as evaluator_agent

        captured_kwargs: list[dict] = []

        def capture_invoke(prompt: str, **kwargs):
            captured_kwargs.append(kwargs)
            return _llm_response(_passing_json())

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = capture_invoke
            mock_llm_class.return_value = mock_instance

            evaluator_agent.evaluate_lesson(
                lesson_content="some lesson",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        assert len(captured_kwargs) >= 1
        assert captured_kwargs[0].get("response_format") == {"type": "json_object"}, (
            "Primary evaluator call must pass response_format={'type': 'json_object'}"
        )

    def test_evaluator_max_tokens_used_not_model_max_tokens(self):
        """ChatGroq must be instantiated with evaluator_max_tokens, not model_max_tokens."""
        from app.agents import evaluator as evaluator_agent
        from app.core.config import get_settings

        settings = get_settings()

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = _llm_response(_passing_json())
            mock_llm_class.return_value = mock_instance

            evaluator_agent.evaluate_lesson(
                lesson_content="some lesson",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        call_kwargs = mock_llm_class.call_args.kwargs
        assert call_kwargs.get("max_tokens") == settings.evaluator_max_tokens, (
            f"Expected max_tokens={settings.evaluator_max_tokens} "
            f"(evaluator_max_tokens), got {call_kwargs.get('max_tokens')}"
        )
        # Also verify it is NOT using the smaller model_max_tokens
        assert call_kwargs.get("max_tokens") != settings.model_max_tokens or \
            settings.evaluator_max_tokens == settings.model_max_tokens, (
            "evaluator_max_tokens should differ from model_max_tokens by default"
        )


# ── Repair path ────────────────────────────────────────────────────────────────


class TestEvaluatorRepairBehavior:
    """
    When primary JSON parsing fails, evaluate_lesson must attempt exactly one
    repair call. The repair must be bounded (short prompt, low token cap).
    """

    def test_repair_succeeds_on_malformed_primary_response(self):
        """Primary returns malformed JSON → repair call returns valid JSON → success."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        # First invoke: malformed; second invoke (repair): valid
        mock_instance.invoke.side_effect = [
            _llm_response("this is not json at all !!!"),
            _llm_response(_passing_json()),  # repair response
        ]
        # bind() returns something whose invoke is also on mock_instance
        mock_instance.bind.return_value = mock_instance

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            result = evaluator_agent.evaluate_lesson(
                lesson_content="some lesson",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        assert result.overall_pass is True
        assert len(result.checks) == 14
        # Two invoke calls: one primary, one repair
        assert mock_instance.invoke.call_count == 2

    def test_repair_attempted_on_truncated_json(self):
        """Truncated primary response → repair is attempted."""
        from app.agents import evaluator as evaluator_agent

        truncated = _passing_json()[:150]  # truncated mid-JSON

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = [
            _llm_response(truncated),
            _llm_response(_passing_json()),
        ]
        mock_instance.bind.return_value = mock_instance

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            result = evaluator_agent.evaluate_lesson(
                lesson_content="some lesson",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        assert result.overall_pass is True
        assert mock_instance.invoke.call_count == 2

    def test_repair_failed_raises_valueerror(self):
        """Primary malformed, repair also malformed → original ValueError raised, never approves."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = [
            _llm_response("not json"),
            _llm_response("also not json"),  # repair also fails
        ]
        mock_instance.bind.return_value = mock_instance

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError, match="invalid JSON"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )

    def test_original_error_message_preserved_through_repair(self):
        """The original parse error message must survive through a failed repair."""
        from app.agents import evaluator as evaluator_agent
        import json

        # Valid JSON but wrong checkpoint count — parse error says "requires exactly 14"
        data = make_passing_evaluation()
        data["checks"] = data["checks"][:13]  # drop one
        short_json = json.dumps(data)

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = [
            _llm_response(short_json),
            _llm_response("also broken"),  # repair also fails
        ]
        mock_instance.bind.return_value = mock_instance

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError, match="requires exactly 14"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )
    def test_repair_call_raises_does_not_mask_original_error(self):
        """If the repair call itself throws (provider error), ValueError still raised."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        mock_instance.invoke.return_value = _llm_response("not json")
        mock_instance.bind.return_value = mock_instance

        # The repair llm.invoke raises
        repair_instance = MagicMock()
        repair_instance.invoke.side_effect = RuntimeError("repair call failed")
        mock_instance.bind.return_value = repair_instance

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )

    def test_exactly_one_repair_attempt_not_two(self):
        """The repair path must not loop — at most one repair call per evaluation."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        # Both primary and repair return invalid JSON
        mock_instance.invoke.side_effect = [
            _llm_response("not json"),
            _llm_response("also not json"),
            _llm_response(_passing_json()),  # third call — must never happen
        ]
        mock_instance.bind.return_value = mock_instance

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            with pytest.raises(ValueError):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version=RUBRIC_VERSION,
                )

        # Never more than 2 calls (primary + 1 repair)
        assert mock_instance.invoke.call_count <= 2


# ── Duplicate checkpoints detected by quality gate ────────────────────────────


class TestDuplicateCheckpointHandling:
    """
    Duplicate checkpoint IDs must be caught by the application quality gate,
    not silently merged or approved.
    """

    def test_duplicate_ids_flagged_as_evaluation_error(self):
        from app.quality.decision import compute_quality_gate

        # Build 14 checks but with ACC-01 duplicated and SAFE-01 missing
        data = make_passing_evaluation()
        checks = [c for c in data["checks"] if c["id"] != "SAFE-01"]
        checks.append(dict(data["checks"][0]))  # duplicate ACC-01
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in checks],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.is_evaluation_error is True
        assert "ACC-01" in result.duplicate_checkpoint_ids

    def test_all_14_unique_ids_not_flagged(self):
        from app.quality.decision import compute_quality_gate

        data = make_passing_evaluation()
        evaluation = EvaluationOutput(
            rubric_version=RUBRIC_VERSION,
            overall_pass=True,
            checks=[CheckpointResult(**c) for c in data["checks"]],
        )
        result = compute_quality_gate(evaluation, RUBRIC_VERSION)
        assert result.duplicate_checkpoint_ids == []
        assert not result.is_evaluation_error


# ── Valid JSON accepted end-to-end ─────────────────────────────────────────────


class TestValidJsonEndToEnd:
    """Verify the happy path: valid primary response, no repair needed."""

    def test_valid_passing_response_no_repair_call(self):
        from app.agents import evaluator as evaluator_agent

        invoke_count = 0

        def count_invoke(prompt: str, **kwargs):
            nonlocal invoke_count
            invoke_count += 1
            return _llm_response(_passing_json())

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = count_invoke

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            result = evaluator_agent.evaluate_lesson(
                lesson_content="some lesson",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        assert result.overall_pass is True
        # Only one invoke call — no repair needed
        assert invoke_count == 1

    def test_valid_failing_response_returned_correctly(self):
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        mock_instance.invoke.return_value = _llm_response(_failing_json(["COV-04", "JAR-01"]))

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance

            result = evaluator_agent.evaluate_lesson(
                lesson_content="some lesson",
                topic="RAG",
                learner_profile="beginner",
                rubric_version=RUBRIC_VERSION,
            )

        assert result.overall_pass is False
        failed = [c.id for c in result.checks if c.status == "FAIL"]
        assert "COV-04" in failed
        assert "JAR-01" in failed
