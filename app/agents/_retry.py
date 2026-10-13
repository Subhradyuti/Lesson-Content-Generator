"""
Shared retry logic for Groq LLM calls.

Both the generator and evaluator use the same transient-error retry strategy:
- RateLimitError (429): wait for the Retry-After header duration, fall back to
  exponential back-off if the header is absent.
- InternalServerError (5xx): exponential back-off.
- All other exceptions propagate immediately without retrying.

Maximum 4 total attempts (1 initial + 3 retries).
"""

from __future__ import annotations

from groq import InternalServerError as GroqInternalServerError
from groq import RateLimitError as GroqRateLimitError
from tenacity import RetryCallState, retry, retry_if_exception_type, stop_after_attempt


def wait_from_retry_after(retry_state: RetryCallState) -> float:
    """
    Compute the wait duration for a Groq rate-limit retry.

    Reads the Retry-After (or x-ratelimit-reset-tokens) response header and
    adds a 0.5 s buffer. Falls back to exponential back-off (2 s, 4 s, 8 s …
    capped at 60 s) when the header is absent or unparseable.
    """
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if exc is not None and isinstance(exc, GroqRateLimitError):
        try:
            raw = exc.response.headers.get("retry-after") or exc.response.headers.get(
                "x-ratelimit-reset-tokens"
            )
            if raw:
                return float(raw) + 0.5
        except (AttributeError, ValueError, TypeError):
            pass

    # Exponential back-off: 2 s, 4 s, 8 s … capped at 60 s
    return min(2.0 ** retry_state.attempt_number, 60.0)


def make_retry_decorator():
    """Return a tenacity retry decorator configured for Groq transient errors."""
    return retry(
        retry=retry_if_exception_type((GroqRateLimitError, GroqInternalServerError)),
        wait=wait_from_retry_after,
        stop=stop_after_attempt(4),
        reraise=True,
    )
