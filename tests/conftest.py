"""
Root conftest.py — session-scoped environment patches for all tests.

Sets a known API_KEY in the environment and clears the settings LRU cache
before tests run, so integration tests can authenticate predictably
without depending on the real .env file.
"""
from __future__ import annotations

import os

import pytest

# The test API key used by the integration test client fixture.
TEST_API_KEY = "test-integration-key"


@pytest.fixture(autouse=True, scope="session")
def patch_env_for_tests():
    """
    Ensure all tests run with a predictable API_KEY and cleared settings cache.
    Called once per test session before any test runs.
    """
    os.environ.setdefault("API_KEY", TEST_API_KEY)
    # Force the API_KEY to the test value so auth checks work in integration tests
    original_api_key = os.environ.get("API_KEY")
    os.environ["API_KEY"] = TEST_API_KEY

    # Clear the lru_cache so get_settings() picks up the patched env vars
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass

    # Reset DB state to ensure clean in-memory SQLite for tests
    try:
        from app.db.session import reset_db_state

        reset_db_state()
    except Exception:
        pass

    yield

    # Restore
    if original_api_key is not None:
        os.environ["API_KEY"] = original_api_key
    else:
        os.environ.pop("API_KEY", None)

    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
    except Exception:
        pass
