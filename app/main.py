"""
FastAPI application entry point.
Assembles all routers, middleware, and startup/shutdown lifecycle handlers.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.routes_lessons import router as lessons_router
from app.api.schemas import LivenessResponse, ReadinessResponse
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, set_request_id
from app.core.security import verify_metrics_access
from app.db.session import check_db_health
from app.observability.tracing import configure_tracing

# ── Application lifecycle ─────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)

    logger = get_logger(__name__)
    logger.info(
        "Application starting",
        extra={
            "env": settings.app_env,
            "generator_model": settings.generator_model,
            "rubric_version": settings.rubric_version,
        },
    )

    configure_tracing(
        service_name=settings.otel_service_name,
        otlp_endpoint=settings.otel_exporter_otlp_endpoint
        if settings.app_env != "development"
        else None,
    )

    yield

    logger.info("Application shutting down")


# ── FastAPI app ───────────────────────────────────────────────────────────────

settings = get_settings()

app = FastAPI(
    title="Self-Evaluating Lesson Content Generator",
    description=(
        "A production-oriented agentic system that generates beginner lessons, "
        "evaluates them against a strict binary rubric, and revises them when they fail. "
        "Built with LangGraph, FastAPI, and Groq."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)

# ── Middleware ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Inject a unique request ID into every request for tracing."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    set_request_id(request_id)
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(lessons_router, tags=["Lessons"])


# ── Health endpoints ──────────────────────────────────────────────────────────


@app.get(
    "/health/live",
    response_model=LivenessResponse,
    tags=["Health"],
    summary="Liveness check",
    description="Returns ok if the application process is alive.",
)
def health_live() -> LivenessResponse:
    return LivenessResponse(status="ok")


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    summary="Readiness check",
    description="Returns ready only if all required dependencies are reachable.",
)
def health_ready() -> ReadinessResponse:
    db_ok = check_db_health()

    overall: Literal["ready", "degraded", "not_ready"] = "ready" if db_ok else "not_ready"

    return ReadinessResponse(
        status=overall,
        database=db_ok,
        details={"database": "connected" if db_ok else "unreachable"},
    )


# ── Metrics endpoint ──────────────────────────────────────────────────────────


@app.get(
    "/metrics",
    tags=["Observability"],
    summary="Prometheus metrics",
    description="Exposes operational metrics. Protected by bearer token in production.",
    include_in_schema=False,  # Hide from public Swagger
)
async def metrics(request: Request) -> Response:
    await verify_metrics_access(request.headers.get("authorization"))
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ── Global exception handler ──────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger = get_logger(__name__)
    logger.error(
        "Unhandled exception",
        extra={"path": request.url.path, "error": str(exc)[:200]},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )
