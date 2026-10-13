"""
Structured JSON logging for the application.
Logs must never contain API keys, credentials, or sensitive content.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

# Context variable for request correlation
_request_id: ContextVar[str] = ContextVar("request_id", default="")
_run_id: ContextVar[str] = ContextVar("run_id", default="")


def get_request_id() -> str:
    return _request_id.get() or str(uuid.uuid4())


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def set_run_id(run_id: str) -> None:
    _run_id.set(run_id)


def get_run_id() -> str:
    return _run_id.get()


class StructuredFormatter(logging.Formatter):
    """Emit log records as newline-delimited JSON."""

    SENSITIVE_KEYS = frozenset(
        {
            "api_key",
            "groq_api_key",
            "password",
            "secret",
            "token",
            "authorization",
            "x-api-key",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": _request_id.get(),
            "run_id": _run_id.get(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Merge any extra fields — redact sensitive keys
        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "name",
                "message",
            }:
                continue
            if key.lower() in self.SENSITIVE_KEYS:
                payload[key] = "[REDACTED]"
            else:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger with structured JSON output."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
