"""
Security: API key authentication, role checks, and prompt-injection protection.
"""

from __future__ import annotations

import re
import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Header scheme — clients send: X-API-Key: <value>
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# ── Prompt-injection patterns ─────────────────────────────────────────────────
# These heuristic patterns protect against common prompt-injection attempts in
# user-supplied topic strings. The list is not exhaustive; user content is
# also treated as data at the LLM boundary.
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|above|prior|all)\s+(instructions?|prompts?|context)",
    r"(?i)you\s+are\s+now\s+a",
    r"(?i)disregard\s+(your|all)\s+(instructions?|rules?|constraints?)",
    r"(?i)act\s+as\s+if\s+you\s+(are|were|have)",
    r"(?i)system\s*:\s*",
    r"(?i)do\s+not\s+follow\s+(the\s+)?(previous|above|your)\s+(instructions?|rules?)",
    r"(?i)reveal\s+(your|the)\s+(system\s+)?prompt",
    r"(?i)print\s+(your|the)\s+(system\s+)?prompt",
    r"(?i)override\s+(your|all)\s+(instructions?|settings?)",
]
_INJECTION_RE = [re.compile(p) for p in _INJECTION_PATTERNS]


def sanitize_user_input(text: str) -> str:
    """
    Return the text unchanged but raise 400 if obvious prompt-injection is detected.
    User content is always treated as *data*, not as system instructions.
    """
    for pattern in _INJECTION_RE:
        if pattern.search(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input contains potentially unsafe instructions. "
                "Please provide a plain topic description.",
            )
    return text


def sanitize_reference_material(text: str) -> str:
    """
    Sanitize reference material for injection patterns.
    Reference material is injected into the evaluator prompt; check for
    instructions that might try to override the evaluator's behaviour.
    """
    for pattern in _INJECTION_RE:
        if pattern.search(text):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference material contains potentially unsafe instructions. "
                "Please provide plain reference content without system-instruction-like text.",
            )
    return text


# ── Authentication ────────────────────────────────────────────────────────────


async def verify_api_key(
    x_api_key: Annotated[str | None, Security(_api_key_header)] = None,
) -> str:
    """
    Verify the X-API-Key header against the configured value.
    Constant-time comparison prevents timing attacks.
    """
    settings = get_settings()

    if not settings.api_key:
        # Dev/test mode: no key configured, allow all requests
        logger.warning("No API_KEY configured — authentication is disabled")
        return "unauthenticated"

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not secrets.compare_digest(x_api_key, settings.api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key


async def verify_metrics_access(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Protect the /metrics endpoint with a bearer token."""
    settings = get_settings()
    if not settings.metrics_bearer_token:
        return  # disabled in dev

    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    if not secrets.compare_digest(token, settings.metrics_bearer_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid metrics token")


# Type alias for route dependencies
RequireApiKey = Annotated[str, Depends(verify_api_key)]
