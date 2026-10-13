"""
Unit tests for provider error classification and logging in agent modules.
All tests mock LLM calls — no live API calls.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest


def _make_timeout_error() -> Exception:
    """Create an exception that simulates a provider timeout."""
    exc = Exception("Read timeout")
    exc.__class__.__name__ = "APITimeoutError"
    return exc


# ── Generator error classification ───────────────────────────────────────────


class TestGeneratorErrorClassification:
    def test_groq_timeout_classified_as_provider_timeout(self):
        from app.agents.generator import _classify_provider_error

        class APITimeoutError(Exception):
            pass

        exc = APITimeoutError("Request timed out")
        assert _classify_provider_error(exc) == "provider_timeout"

    def test_groq_rate_limit_classified_as_provider_rate_limit(self):
        from app.agents.generator import _classify_provider_error

        class RateLimitError(Exception):
            pass

        exc = RateLimitError("429 rate limit exceeded")
        assert _classify_provider_error(exc) == "provider_rate_limit"

    def test_groq_server_error_classified_as_provider_server_error(self):
        from app.agents.generator import _classify_provider_error

        exc = Exception("Internal Server Error 500")
        assert _classify_provider_error(exc) == "provider_server_error"

    def test_unknown_error_classified_as_provider_unknown(self):
        from app.agents.generator import _classify_provider_error

        exc = Exception("Something unexpected happened")
        assert _classify_provider_error(exc) == "provider_unknown_error"


# ── Evaluator error classification ────────────────────────────────────────────


class TestEvaluatorErrorClassification:
    def test_groq_timeout_classified_as_provider_timeout(self):
        from app.agents.evaluator import _classify_provider_error

        class APITimeoutError(Exception):
            pass

        exc = APITimeoutError("timeout")
        assert _classify_provider_error(exc) == "provider_timeout"

    def test_groq_rate_limit_classified_as_provider_rate_limit(self):
        from app.agents.evaluator import _classify_provider_error

        exc = Exception("429: rate limit")
        assert _classify_provider_error(exc) == "provider_rate_limit"

    def test_groq_server_error_classified_as_provider_server_error(self):
        from app.agents.evaluator import _classify_provider_error

        exc = Exception("503 service unavailable")
        assert _classify_provider_error(exc) == "provider_server_error"


# ── Elapsed time logged on provider error ────────────────────────────────────


class TestElapsedTimeLogging:
    def test_elapsed_time_logged_on_generator_provider_error(self, caplog):
        """When the generator LLM call fails, elapsed_seconds must be logged."""
        from app.agents import generator as generator_agent
        from app.agents.planner import LessonPlan
        from tests.fixtures.lesson_fixtures import PASSING_LESSON_PLAN

        plan = LessonPlan(**PASSING_LESSON_PLAN)

        with patch("app.agents.generator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("provider failure")
            mock_llm_class.return_value = mock_instance

            with caplog.at_level(logging.ERROR):
                with pytest.raises(Exception, match="provider failure"):
                    generator_agent.generate_lesson(
                        topic="RAG",
                        learner_profile="beginner",
                        language="English",
                        plan=plan,
                    )

        # Check that elapsed_seconds was logged
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) > 0
        # At least one record should have elapsed_seconds in its extra fields
        has_elapsed = any(
            hasattr(r, "elapsed_seconds") or "elapsed_seconds" in getattr(r, "__dict__", {})
            for r in error_records
        )
        # Also check via message formatting — the extra dict is logged
        log_messages = " ".join(str(r.__dict__) for r in error_records)
        assert "elapsed_seconds" in log_messages or has_elapsed

    def test_elapsed_time_logged_on_evaluator_provider_error(self, caplog):
        """When the evaluator LLM call fails, elapsed_seconds must be logged."""
        from app.agents import evaluator as evaluator_agent

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.side_effect = Exception("provider error")
            mock_llm_class.return_value = mock_instance

            with caplog.at_level(logging.ERROR):
                with pytest.raises(Exception, match="provider error"):
                    evaluator_agent.evaluate_lesson(
                        lesson_content="lesson text",
                        topic="RAG",
                        learner_profile="beginner",
                        rubric_version="rag-beginner-v1",
                    )

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) > 0
        log_messages = " ".join(str(r.__dict__) for r in error_records)
        assert "elapsed_seconds" in log_messages


# ── SDK retries not stacked ───────────────────────────────────────────────────


class TestProviderSdkRetries:
    def test_generator_uses_provider_sdk_retries_setting(self):
        """Generator ChatGroq is instantiated with max_retries=settings.provider_sdk_retries."""
        from app.agents import generator as generator_agent
        from app.agents.planner import LessonPlan
        from app.core.config import get_settings
        from tests.fixtures.lesson_fixtures import PASSING_LESSON_PLAN

        plan = LessonPlan(**PASSING_LESSON_PLAN)
        settings = get_settings()

        with patch("app.agents.generator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = MagicMock(content="A " * 60)
            mock_llm_class.return_value = mock_instance

            generator_agent.generate_lesson(
                topic="RAG",
                learner_profile="beginner",
                language="English",
                plan=plan,
            )

        call_kwargs = mock_llm_class.call_args.kwargs
        assert call_kwargs.get("max_retries") == settings.provider_sdk_retries

    def test_evaluator_uses_provider_sdk_retries_setting(self):
        """Evaluator ChatGroq is instantiated with max_retries=settings.provider_sdk_retries."""
        import json

        from app.agents import evaluator as evaluator_agent
        from app.core.config import get_settings
        from tests.fixtures.lesson_fixtures import make_passing_evaluation

        settings = get_settings()
        passing_eval = json.dumps(make_passing_evaluation())

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_instance = MagicMock()
            mock_instance.invoke.return_value = MagicMock(content=passing_eval)
            mock_llm_class.return_value = mock_instance

            evaluator_agent.evaluate_lesson(
                lesson_content="some lesson text",
                topic="RAG",
                learner_profile="beginner",
                rubric_version="rag-beginner-v1",
            )

        call_kwargs = mock_llm_class.call_args.kwargs
        assert call_kwargs.get("max_retries") == settings.provider_sdk_retries


# ── Evaluator retry behaviour ───────────────────────────────────────────────


class TestEvaluatorRetryBehavior:
    """Provider errors in the evaluator must be retried, not immediately fatal."""

    @staticmethod
    def _make_rate_limit_error(retry_after: str = "0") -> Exception:
        """Build a real groq RateLimitError with an httpx response attached."""
        import httpx
        from groq import RateLimitError

        return RateLimitError(
            "Rate limit exceeded",
            response=httpx.Response(
                429,
                request=httpx.Request("POST", "https://api.groq.com/responses"),
                headers={"retry-after": retry_after},
            ),
            body={"error": {"message": "rate limit"}},
        )

    @staticmethod
    def _passing_response() -> MagicMock:
        import json

        from tests.fixtures.lesson_fixtures import make_passing_evaluation

        return MagicMock(content=json.dumps(make_passing_evaluation()))

    def test_evaluator_retries_rate_limit_and_succeeds(self):
        """A 429 must be retried (bounded) and then succeed."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = [
            self._make_rate_limit_error(),
            self._make_rate_limit_error(),
            self._passing_response(),
        ]

        with (
            patch("app.agents.evaluator.ChatGroq") as mock_llm_class,
            patch("time.sleep", lambda _s: None),
        ):
            mock_llm_class.return_value = mock_instance
            evaluation = evaluator_agent.evaluate_lesson(
                lesson_content="some lesson text",
                topic="RAG",
                learner_profile="beginner",
                rubric_version="rag-beginner-v1",
            )

        assert mock_instance.invoke.call_count == 3  # 1 initial + 2 retries
        assert evaluation.overall_pass is True

    def test_evaluator_gives_up_after_bounded_retries(self):
        """Persistent 429s must stop after the bounded attempt limit."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = self._make_rate_limit_error()

        with (
            patch("app.agents.evaluator.ChatGroq") as mock_llm_class,
            patch("time.sleep", lambda _s: None),
        ):
            mock_llm_class.return_value = mock_instance
            with pytest.raises(Exception, match="Rate limit"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson text",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version="rag-beginner-v1",
                )

        # 1 initial call + 3 retries = 4 total attempts, then give up.
        assert mock_instance.invoke.call_count == 4

    def test_evaluator_does_not_retry_unrelated_errors(self):
        """Unrelated exceptions (e.g. validation errors) are NOT retried."""
        from app.agents import evaluator as evaluator_agent

        mock_instance = MagicMock()
        mock_instance.invoke.side_effect = RuntimeError("something else broke")

        with patch("app.agents.evaluator.ChatGroq") as mock_llm_class:
            mock_llm_class.return_value = mock_instance
            with pytest.raises(RuntimeError, match="something else broke"):
                evaluator_agent.evaluate_lesson(
                    lesson_content="some lesson text",
                    topic="RAG",
                    learner_profile="beginner",
                    rubric_version="rag-beginner-v1",
                )

        assert mock_instance.invoke.call_count == 1
