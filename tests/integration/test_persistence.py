"""
Integration tests for cross-request database persistence.

These tests verify that run results (drafts, evaluations, revision logs) are
genuinely written to and retrievable from the database across separate HTTP
requests — proving that persistent memory works beyond a single API call.

LLM calls are mocked for speed and determinism; database operations are NOT
mocked, so these tests exercise the real SQLite persistence layer.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.lesson_fixtures import (
    PASSING_LESSON,
    PASSING_LESSON_PLAN,
    make_failing_evaluation,
    make_passing_evaluation,
)

TEST_API_KEY = "test-integration-key"


@pytest.fixture
def client():
    """
    Test client with a clean in-memory SQLite database.
    LLM calls are NOT mocked here — individual tests do that selectively.
    DB persistence runs for real so we can prove cross-request retrieval.
    """
    from app.main import app

    return TestClient(
        app,
        raise_server_exceptions=False,
        headers={"X-API-Key": TEST_API_KEY},
    )


def _make_llm_response(content: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = content
    return mock_response


# ── Test: passed run is retrievable via GET /v1/lessons/{run_id} ──────────────


class TestCrossRequestPersistence:
    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_passed_run_retrievable_by_id(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """
        A run that passes on the first draft must be retrievable via GET after
        the POST returns. This proves data is actually written to the DB and
        is not just held in memory for the duration of the request.
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

        # ── Request 1: Generate a lesson ──────────────────────────────────
        post_response = client.post(
            "/v1/lessons",
            json={"topic": "Introduction to RAG", "max_retries": 0},
        )
        assert post_response.status_code == 200
        post_data = post_response.json()
        assert post_data["status"] == "passed"
        run_id = post_data["run_id"]
        assert run_id  # must be a non-empty string

        # ── Request 2: Retrieve the run by ID (separate request) ──────────
        get_response = client.get(f"/v1/lessons/{run_id}")
        assert get_response.status_code == 200, (
            f"GET /v1/lessons/{run_id} returned {get_response.status_code}: "
            f"{get_response.text}"
        )
        get_data = get_response.json()

        assert get_data["run_id"] == run_id
        assert get_data["status"] == "passed"
        assert get_data["topic"] == "Introduction to RAG"
        assert get_data["rubric_version"] == post_data["rubric_version"]

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_history_endpoint_returns_both_drafts_and_revision_log(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """
        A run that fails on attempt 0 and passes on attempt 1 must have both
        drafts AND the revision log stored and returned by GET .../history.
        This confirms that retry history survives beyond the originating request.
        """
        plan_instance = MagicMock()
        plan_instance.invoke.return_value = _make_llm_response(json.dumps(PASSING_LESSON_PLAN))
        mock_plan_llm.return_value = plan_instance

        # First generation returns a stub that's long enough to pass the generator's
        # minimum-length guard (>100 chars) but sparse enough to fail the evaluator rubric
        failing_lesson = (
            "RAG stands for Retrieval-Augmented Generation. "
            "It uses embeddings stored in a vector database to retrieve relevant chunks. "
            "The model then generates an answer using those chunks as context."
        )
        gen_instance = MagicMock()
        gen_instance.invoke.side_effect = [
            _make_llm_response(failing_lesson),
            _make_llm_response(PASSING_LESSON),
        ]
        mock_gen_llm.return_value = gen_instance

        # First eval fails (COV-04), second passes
        eval_instance = MagicMock()
        eval_instance.invoke.side_effect = [
            _make_llm_response(json.dumps(make_failing_evaluation(["COV-04"]))),
            _make_llm_response(json.dumps(make_passing_evaluation())),
        ]
        mock_eval_llm.return_value = eval_instance

        # ── Request 1: Generate with one retry ────────────────────────────
        post_response = client.post(
            "/v1/lessons",
            json={"topic": "Introduction to RAG", "max_retries": 2},
        )
        assert post_response.status_code == 200
        post_data = post_response.json()
        assert post_data["status"] == "passed"
        assert post_data["retry_count"] == 1
        run_id = post_data["run_id"]

        # ── Request 2: Retrieve full history (separate request) ───────────
        history_response = client.get(f"/v1/lessons/{run_id}/history")
        assert history_response.status_code == 200, (
            f"GET /v1/lessons/{run_id}/history returned "
            f"{history_response.status_code}: {history_response.text}"
        )
        history_data = history_response.json()

        # Must have two drafts stored
        drafts = history_data["drafts"]
        assert len(drafts) == 2, (
            f"Expected 2 drafts in history, got {len(drafts)}"
        )
        assert drafts[0]["attempt_number"] == 0
        assert drafts[1]["attempt_number"] == 1

        # Must have one revision log entry for the failed attempt
        revision_logs = history_data["revision_logs"]
        assert len(revision_logs) >= 1, (
            f"Expected at least 1 revision log entry, got {len(revision_logs)}"
        )
        first_log = revision_logs[0]
        assert "COV-04" in first_log["failed_checkpoint_ids"], (
            f"Expected COV-04 in failed_checkpoint_ids, got {first_log['failed_checkpoint_ids']}"
        )

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_unknown_run_id_returns_404(self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client):
        """
        GET /v1/lessons/{run_id} with an ID that was never created must return 404.
        This confirms the endpoint does not silently return empty data.
        """
        response = client.get("/v1/lessons/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @patch("app.agents.planner.ChatGroq")
    @patch("app.agents.generator.ChatGroq")
    @patch("app.agents.evaluator.ChatGroq")
    def test_evaluation_counts_match_checks_array(
        self, mock_eval_llm, mock_gen_llm, mock_plan_llm, client
    ):
        """
        The passed_count in the response must equal the number of PASS checks
        in the checks array. This guards against the count-mismatch bug where
        passed_count: 14 was reported but only 13 objects appeared in checks.
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
            json={"topic": "Introduction to RAG", "max_retries": 0},
        )
        assert response.status_code == 200
        data = response.json()

        evaluation = data["evaluation"]
        checks = evaluation["checks"]

        # Recompute counts from the actual checks array
        actual_passed = sum(1 for c in checks if c["status"] == "PASS")
        actual_failed = sum(1 for c in checks if c["status"] == "FAIL")

        assert evaluation["passed_count"] == actual_passed, (
            f"passed_count={evaluation['passed_count']} but "
            f"{actual_passed} PASS checks exist in the checks array"
        )
        assert evaluation["failed_count"] == actual_failed, (
            f"failed_count={evaluation['failed_count']} but "
            f"{actual_failed} FAIL checks exist in the checks array"
        )
        # And the total must equal the rubric checkpoint count (14)
        assert len(checks) == 14, (
            f"Expected 14 checkpoint results, got {len(checks)}"
        )
