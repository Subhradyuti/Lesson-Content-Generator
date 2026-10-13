"""
Prometheus-compatible metrics instrumentation.
Exposes counters, histograms, and gauges for the lesson generation workflow.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── Counters ──────────────────────────────────────────────────────────────────

RUNS_STARTED = Counter(
    "lesson_runs_started_total",
    "Total number of lesson generation runs started",
    ["topic_hash"],
)

RUNS_COMPLETED = Counter(
    "lesson_runs_completed_total",
    "Total number of lesson generation runs completed",
    ["status"],
)

GENERATION_ATTEMPTS = Counter(
    "lesson_generation_attempts_total",
    "Total number of lesson generation attempts (initial + revisions)",
)

PROVIDER_ERRORS = Counter(
    "lesson_provider_errors_total",
    "Total number of model provider errors",
    ["error_type"],
)

EVALUATION_ERRORS = Counter(
    "lesson_evaluation_errors_total",
    "Total number of evaluation errors (malformed output, etc.)",
)

CHECKPOINT_FAILURES = Counter(
    "lesson_checkpoint_failures_total",
    "Total number of individual checkpoint failures",
    ["checkpoint_id"],
)

# ── Histograms ────────────────────────────────────────────────────────────────

GENERATION_LATENCY = Histogram(
    "lesson_generation_latency_seconds",
    "Latency of lesson generation calls",
    buckets=[5, 10, 20, 30, 60, 90, 120, 180, 300],
)

EVALUATION_LATENCY = Histogram(
    "lesson_evaluation_latency_seconds",
    "Latency of lesson evaluation calls",
    buckets=[5, 10, 20, 30, 60, 90, 120],
)

WORKFLOW_DURATION = Histogram(
    "lesson_workflow_duration_seconds",
    "Total end-to-end workflow duration",
    buckets=[10, 30, 60, 120, 180, 300, 600],
)

# ── Gauges ────────────────────────────────────────────────────────────────────

ACTIVE_RUNS = Gauge(
    "lesson_active_runs",
    "Number of currently executing lesson generation runs",
)


# ── Helper functions ──────────────────────────────────────────────────────────


def record_run_started(topic: str) -> None:
    """Record a new run starting. Topic is hashed to avoid storing PII in labels."""
    import hashlib

    topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
    RUNS_STARTED.labels(topic_hash=topic_hash).inc()
    ACTIVE_RUNS.inc()


def record_run_completed(status: str) -> None:
    """Record a run completing with the given status."""
    RUNS_COMPLETED.labels(status=status).inc()
    ACTIVE_RUNS.dec()


def record_generation_attempt(attempt_count: int) -> None:
    """Record the number of generation attempts for a completed run."""
    GENERATION_ATTEMPTS.inc(attempt_count if attempt_count > 0 else 1)


def record_checkpoint_failures(failed_ids: list[str]) -> None:
    """Record individual checkpoint failures."""
    for cid in failed_ids:
        CHECKPOINT_FAILURES.labels(checkpoint_id=cid).inc()


def record_provider_error(error_type: str) -> None:
    """Record a model provider error."""
    PROVIDER_ERRORS.labels(error_type=error_type).inc()
