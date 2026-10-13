# Self-Evaluating Lesson Content Generator

A production-oriented agentic system that generates beginner-friendly lessons, evaluates them against a strict binary rubric, revises them when they fail, and stores a full audit trail of every draft and evaluation decision.

Built with **LangGraph**, **FastAPI**, **Groq**, and **PostgreSQL**.

---

## Architecture and Data Flow

```
Client
  │
  ▼
FastAPI + Pydantic (input validation, API key auth, prompt-injection check)
  │
  ▼
LangGraph Workflow (bounded state machine)
  │
  ├── validate_request ──────────────────────────────────────────────┐
  │                                                                    │
  ├── create_lesson_plan  (Groq LLM, planner_v1.md prompt)           │
  │                                                                    │
  ├── generate_lesson  (Groq LLM, generator_v1.md prompt)            │ any
  │                                                                    │ error
  ├── evaluate_lesson  (Groq LLM, evaluator_v1.md prompt;             │ path
  │      retries 429/5xx with bounded back-off)                       │
  │                                                                    │
  ├── validate_evaluation  (application logic, no LLM)               │
  │                                                                    │
  ├── decide_next_action  (routing: pass / retry / exhaust)          │
  │       │                                                            │
  │       ├─ PASS ──┐                                                 │
  │       │          │                                                │
  │       ├─ RETRY ► build_revision_instructions ──► generate_lesson  │
  │       │           (loops back, max 2 retries)                     │
  │       │                                                            │
  │       └─ EXHAUSTED ─┐                                             │
  │                      ▼                                            │
  └──────────────► finalize_run  (sets status + final_lesson; ◄──────┘
                        │          preserves last draft on error)
                        ▼
                   persist_results ──► return_result ──► END
  │
  ▼
PostgreSQL  (generation_runs, lesson_drafts, evaluations, revision_logs,
             improvement_candidates, configuration_versions)
  │
  ▼
Prometheus metrics  /  OpenTelemetry traces  /  Structured JSON logs
```

### Key components

| Component | File | Responsibility |
|---|---|---|
| API routes | `app/api/routes_lessons.py` | Request/response handling, no business logic |
| Request schemas | `app/api/schemas.py` | Pydantic validation for all API I/O |
| Workflow graph | `app/workflow/graph.py` | LangGraph state machine assembly |
| Workflow nodes | `app/workflow/nodes.py` | One function per workflow stage |
| Routing logic | `app/workflow/routing.py` | Conditional edge functions |
| Workflow state | `app/workflow/state.py` | TypedDict: all per-run data |
| Planner agent | `app/agents/planner.py` | Lesson planning via Groq |
| Generator agent | `app/agents/generator.py` | Lesson generation and revision via Groq |
| Evaluator agent | `app/agents/evaluator.py` | Lesson evaluation via Groq |
| Quality gate | `app/quality/decision.py` | Application-level pass/fail (not LLM) |
| Rubric schema | `app/quality/rubric.py` | YAML rubric loader |
| Rubric validator | `app/quality/validator.py` | Structural validation helpers |
| Eval schemas | `app/quality/schemas.py` | Pydantic schemas for evaluator output |
| Rubric definition | `rubric/rag-beginner-v1.yaml` | 14 mandatory checkpoints |
| DB models | `app/db/models.py` | SQLAlchemy ORM models |
| Repository | `app/memory/repository.py` | Persist and retrieve run data |
| Candidates | `app/memory/improvement_candidates.py` | Improvement candidate lifecycle |
| Config | `app/core/config.py` | Environment-based settings |
| Security | `app/core/security.py` | API key auth, injection protection |
| Metrics | `app/observability/metrics.py` | Prometheus counters and histograms |
| Tracing | `app/observability/tracing.py` | OpenTelemetry setup |

---

## Prerequisites

- **Python 3.11+** (tested on 3.12)
- **Docker** and **Docker Compose** (for the database)
- A **Groq API key** — sign up at [console.groq.com](https://console.groq.com)
- `psycopg[binary]` and `psycopg2-binary` (installed automatically)

---

## Installation and Setup

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd lesson-content-generator

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install --no-deps -e .
pip install fastapi uvicorn pydantic pydantic-settings langchain langchain-core \
    langchain-groq langgraph sqlalchemy alembic psycopg psycopg2-binary \
    opentelemetry-api opentelemetry-sdk prometheus-client pyyaml httpx groq

# Install dev dependencies
pip install pytest pytest-asyncio pytest-cov ruff mypy types-PyYAML httpx

# 4. Copy and edit environment file
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the required values:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | **Yes** | Your Groq API key |
| `DATABASE_URL` | **Yes** | PostgreSQL connection string |
| `API_KEY` | Recommended | X-API-Key for protected endpoints |
| `APP_ENV` | No | `development` / `testing` / `production` |
| `GENERATOR_MODEL` | No | Groq model name (default: `llama-3.3-70b-versatile`) |
| `EVALUATOR_MODEL` | No | Groq model for evaluation (default: `llama-3.3-70b-versatile`) |
| `DEFAULT_MAX_RETRIES` | No | 0, 1, or 2 (default: `2`) |
| `RUBRIC_VERSION` | No | Active rubric file (default: `rag-beginner-v1`) |
| `LOG_LEVEL` | No | `DEBUG` / `INFO` / `WARNING` (default: `INFO`) |
| `METRICS_BEARER_TOKEN` | No | Protects `/metrics` endpoint in production |

See `.env.example` for the full list.

---

## Configuring the Groq API Key

1. Sign up at [console.groq.com](https://console.groq.com) and create an API key.
2. Add it to your `.env` file:
   ```
   GROQ_API_KEY=gsk_your_actual_key_here
   ```
3. The key is never logged, never included in API responses, and never stored in the database.

**Available models verified on Groq** (as of the project's development):
- `llama-3.3-70b-versatile` — recommended for both generation and evaluation
- `llama-3.1-8b-instant` — faster and cheaper, less thorough for evaluation

---

## Starting PostgreSQL and the Application

### Using Docker Compose (recommended)

```bash
# Start the database (and API if you want)
docker compose up db -d

# Wait for the database to be healthy
docker compose ps

# Run migrations, then start the API locally or via Docker:
docker compose up api -d
```

### Database only (for local development)

```bash
docker compose up db -d
```

The database is available at `localhost:5432` with:
- Database: `lesson_db`
- User: `lesson_user`
- Password: `lesson_pass`

---

## Running Database Migrations

```bash
# Generate a new migration from model changes (requires live DB):
alembic revision --autogenerate -m "description of change"

# Apply all pending migrations:
alembic upgrade head

# Check current migration state:
alembic current

# Roll back one migration:
alembic downgrade -1
```

The initial migration `0001_initial_schema` creates all six tables:
`generation_runs`, `lesson_drafts`, `evaluations`, `revision_logs`,
`improvement_candidates`, `configuration_versions`.

---

## Starting the FastAPI Server

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (single worker, Docker handles scaling)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

The server starts at `http://localhost:8000`.

---

## Using Swagger UI

Open `http://localhost:8000/docs` in your browser (available in `development` and `testing` environments).

All protected endpoints require the `X-API-Key` header. Click the **Authorize** button in Swagger UI and enter your API key.

---

## Submitting a Lesson Generation Request

### curl example

```bash
curl -X POST http://localhost:8000/v1/lessons \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "topic": "Introduction to RAG",
    "learner_profile": "Class 12 graduate in India; beginner; limited English vocabulary",
    "language": "simple English",
    "learning_objectives": [
      "Explain what RAG means",
      "Describe the basic RAG workflow",
      "Give one practical example"
    ],
    "max_retries": 2
  }'
```

### Successful response (`status: "passed"`)

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "passed",
  "attempt_count": 1,
  "rubric_version": "rag-beginner-v1",
  "model_name": "llama-3.3-70b-versatile",
  "lesson": "# Introduction to RAG...",
  "evaluation": {
    "overall_pass": true,
    "rubric_version": "rag-beginner-v1",
    "checks": [
      { "id": "ACC-01", "status": "PASS", "evidence": "...", "reason": "..." },
      ...14 total checkpoints...
    ],
    "passed_count": 14,
    "failed_count": 0
  },
  "rejection_log": []
}
```

### Non-passing response (`status: "failed_quality_gate"`)

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440001",
  "status": "failed_quality_gate",
  "attempt_count": 3,
  "lesson": null,
  "last_draft_available_for_review": true,
  "rejection_log": [
    {
      "attempt": 0,
      "timestamp": "2024-01-15T10:00:00+00:00",
      "failed_checkpoint_ids": ["JAR-01"],
      "failed_checks_detail": [
        {
          "id": "JAR-01",
          "reason": "Term 'embedding' used without explanation",
          "evidence": "embeddings are created for each chunk",
          "required_fix": "Define 'embedding' in plain English before using the term"
        }
      ],
      "revision_instructions": [
        "[JAR-01] Define 'embedding' in plain English before using the term..."
      ]
    }
  ]
}
```

### Error statuses preserve the last valid draft

Transient provider failures (HTTP 429 rate limits, 5xx) and malformed evaluator
output must not throw away a lesson that was already generated. When a run ends
in `generation_error` or `evaluation_error`, the API still returns the last
valid draft in `lesson`:

```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440002",
  "status": "evaluation_error",
  "attempt_count": 1,
  "draft_count": 1,
  "lesson": "# Introduction to RAG...",
  "last_draft_available_for_review": true,
  "error_detail": "Evaluation failed on attempt 0: ..."
}
```

- `generation_error` / `evaluation_error` → `lesson` contains the last valid
  draft (if one exists), so the work is never lost.
- `failed_quality_gate` → `lesson` is `null` **by design**: the drafts exist and
  failed the rubric, so they are exposed through the history endpoint and
  `last_draft_available_for_review` instead of being returned as a usable lesson.

Before an error is recorded, the evaluator retries transient provider failures
with bounded exponential back-off:

| Provider error | Behaviour |
|---|---|
| `RateLimitError` (429) | Retry up to 4 total attempts; wait from the `Retry-After` header (+0.5 s buffer), else exponential back-off (2s, 4s, 8s … capped at 60s) |
| `InternalServerError` (5xx) | Retry up to 4 total attempts with exponential back-off |
| Any other error | Propagates immediately (no retry) |

This retry budget is separate from the **content** retry budget (`max_retries`,
max 2 revisions): provider retries recover from transient infrastructure
failures without consuming a lesson revision.

### Retrieve run status

```bash
curl http://localhost:8000/v1/lessons/{run_id} -H "X-API-Key: your-api-key"
```

### Retrieve full run history (drafts + evaluations)

```bash
curl http://localhost:8000/v1/lessons/{run_id}/history -H "X-API-Key: your-api-key"
```

---

## How the Binary Rubric Works

The rubric file `rubric/rag-beginner-v1.yaml` defines **14 mandatory checkpoints**:

| ID | Dimension | What it checks |
|---|---|---|
| ACC-01 | Accuracy | No material factual errors |
| ACC-02 | Grounding | Consistent with supplied references |
| BEG-01 | Beginner language | No assumed prior knowledge, short sentences |
| JAR-01 | Jargon | Every technical term explained before use |
| EX-01 | Worked example | Concrete step-by-step example |
| COV-01 | Definition | Topic clearly defined |
| COV-02 | Purpose | Why the topic matters |
| COV-03 | Process | Workflow explained in logical steps |
| COV-04 | Limitations | Honest limitations, no absolute guarantees |
| FLOW-01 | Teaching order | Simple to complex, no unexplained jumps |
| FLOW-02 | Standalone | No external links required |
| CHECK-01 | Learning check | 3–5 questions with correct answer key |
| CONS-01 | Internal consistency | No contradictions |
| SAFE-01 | Safe content | No harmful content or fabricated citations |

**The pass/fail decision is computed by the application, not the LLM.** The evaluator produces structured JSON with evidence and reasons for each checkpoint. The application then:

1. Verifies all 14 checkpoint IDs are present exactly once.
2. Verifies there are no unknown or duplicate IDs.
3. Computes `overall_pass = all(check.status == "PASS" for check in mandatory_checks)`.

The LLM's own `overall_pass` field is **ignored**. A lesson passes only when every single mandatory checkpoint passes.

---

## How Regeneration and the Retry Budget Work

```
Attempt 0  →  Generate  →  Evaluate  →  PASS?  →  Done
                                          │
                                         FAIL
                                          │
                                     attempt < max_retries?
                                          │
                                    YES  ─┤─ NO → failed_quality_gate
                                          │
                              Build revision instructions
                              (from failed checkpoint evidence)
                                          │
                                   Attempt 1  → ...
```

- `max_retries=0`: one draft only (no revisions)
- `max_retries=1`: initial draft + up to 1 revision
- `max_retries=2` (default): initial draft + up to 2 revisions (3 drafts total)

Values above 2 are **rejected at the API level** and also clamped inside the workflow node. The system cannot enter an unbounded loop.

Each revision includes the previous draft, the exact failed checkpoint IDs, the evidence from the evaluator, and specific correction instructions. After revision, the **entire rubric is re-evaluated from scratch** — not just the previously failed checkpoints.

---

## Inspecting Rejection Logs

Every failed attempt is recorded in the `rejection_log` array of the API response. Each entry contains:

- `attempt`: which draft number failed (0 = initial, 1 = first revision, 2 = second)
- `timestamp`: when it failed
- `failed_checkpoint_ids`: which rubric checks failed
- `failed_checks_detail`: evidence, reason, and required fix for each failed check
- `revision_instructions`: the exact instructions sent to the generator for the next draft

For persisted runs, the full history including all draft content, evaluation JSON, and revision logs is available via:

```bash
GET /v1/lessons/{run_id}/history
```

The database tables `lesson_drafts`, `evaluations`, and `revision_logs` store every draft and evaluation, linked by `run_id`, so the entire decision trail is auditable after the fact.

---

## Running Tests

```bash
# All tests (unit + integration)
python -m pytest tests/ -v

# Unit tests only (no DB, no LLM — fast, deterministic)
python -m pytest tests/unit/ -v

# Integration tests only (LLM mocked, no DB required)
python -m pytest tests/integration/ -v

# With coverage report
python -m pytest tests/ --cov=app --cov-report=term-missing

# Run a specific test file
python -m pytest tests/unit/test_quality_gate.py -v

# Run a specific test class
python -m pytest tests/unit/test_workflow_routing.py::TestRetryTermination -v
```

### What the tests cover

**Unit tests** (`tests/unit/`):
- Input validation and retry-limit enforcement
- Prompt-injection detection
- Quality gate: pass, single fail, multiple fail, missing/duplicate/unknown checkpoints
- Workflow routing for all pass/fail/error/exhaustion paths
- Schema validation: `CheckpointResult`, `EvaluationOutput`
- Provider-error handling: retry on 429/5xx, `Retry-After` back-off, and
  immediate propagation of non-retryable errors

**Integration tests** (`tests/integration/`):
- First draft passes → `status: "passed"`, full lesson and 14 checkpoints returned
- First draft fails, second passes → `rejection_log` has one entry
- All drafts fail → `status: "failed_quality_gate"`, `lesson` is `null`
- `max_retries=0` → only one generation attempt made
- Invalid JSON from evaluator → `status: "evaluation_error"` (last draft preserved in `lesson`)
- Missing checkpoints in evaluator output → evaluation error
- Rate limit (429) on the evaluator → retried, then last draft preserved
- Prompt injection in topic → HTTP 400
- `max_retries > 2` → HTTP 422 validation error

All standard tests use mocked LLM calls — **no Groq API key is needed** to run the test suite.

---

## Running Optional Live-Model Tests

Live tests make actual Groq API calls and require a valid `GROQ_API_KEY`. They are not run in standard CI.

```bash
# Set your API key
export GROQ_API_KEY=gsk_your_real_key_here

# Run only tests marked as "live"
python -m pytest tests/ -m live -v
```

To run CI live smoke tests, set the `RUN_LIVE_TESTS` variable to `true` in your GitHub repository variables and add `GROQ_API_KEY` as a secret.

---

## Observability

### Structured logs

Logs are emitted as newline-delimited JSON. Every log record includes `request_id` and `run_id` for correlation. API keys and credentials are automatically redacted.

```bash
# View formatted logs in development
uvicorn app.main:app --reload 2>&1 | python -c "import sys, json; [print(json.dumps(json.loads(l), indent=2)) for l in sys.stdin if l.strip()]"
```

### Prometheus metrics

```bash
# With metrics token configured:
curl http://localhost:8000/metrics -H "Authorization: Bearer your-metrics-token"

# Without token (development):
curl http://localhost:8000/metrics
```

Key metrics:
- `lesson_runs_started_total` — by topic hash
- `lesson_runs_completed_total` — by status (passed/failed_quality_gate/error)
- `lesson_generation_attempts_total` — total draft generation calls
- `lesson_checkpoint_failures_total` — by checkpoint ID
- `lesson_generation_latency_seconds` — histogram
- `lesson_evaluation_latency_seconds` — histogram
- `lesson_workflow_duration_seconds` — end-to-end histogram
- `lesson_active_runs` — gauge

### Health endpoints

```bash
curl http://localhost:8000/health/live   # {"status": "ok"}
curl http://localhost:8000/health/ready  # {"status": "ready", "database": true}
```

### OpenTelemetry traces

In production, set `OTEL_EXPORTER_OTLP_ENDPOINT` to your collector endpoint. In development, traces are logged to console.

---

## Security Considerations

- **API key authentication**: All `/v1/lessons` endpoints require `X-API-Key`. Set `API_KEY` in `.env`. If unset, all requests are permitted (dev mode only).
- **Prompt-injection protection**: Topic and learner profile fields are checked for common injection patterns before being passed to the LLM. User content is always treated as data, not as system instructions.
- **No credentials in logs**: API keys, passwords, and tokens are redacted from all structured log output.
- **No LLM code execution**: Generated lesson text is stored and returned as text — it is never executed.
- **Input size limits**: `max_topic_length=500`, `max_reference_material_length=50000`, `max_learning_objectives=10`.
- **Bounded retries**: Maximum 2 content retries (3 drafts). Maximum 3 provider retries for transient errors. No unbounded loops.
- **Secrets outside source control**: `.env` is in `.gitignore`. `.env.example` contains only placeholder values.
- **TLS**: Not handled by the application — use a reverse proxy (nginx, Caddy, AWS ALB) in production.
- **Database credentials**: Never hardcoded. Set via `DATABASE_URL` environment variable.
- **Metrics endpoint**: Protected by bearer token (`METRICS_BEARER_TOKEN`). Hidden from public Swagger docs.
- **Improvement candidates**: Require human approval (`approved_by`) before activation. The system cannot autonomously modify its own prompts or rubric during a live run.

---

## Known Limitations and Future Work

1. **No async workflow**: LangGraph workflow runs synchronously. Long-running generations may block. For high traffic, add a task queue (Celery + Redis) and return a `202 Accepted` with a `run_id` to poll.
2. **LLM evaluator bias**: The evaluator and generator use the same underlying model, which can introduce shared-model bias. The application-level quality gate mitigates but does not eliminate this.
3. **No rate limiting implemented**: `slowapi` is in dependencies but rate limiting middleware is not yet wired into the FastAPI app.
4. **pgvector not implemented**: Vector search for approved examples is designed in the schema but not yet activated.
5. **Improvement candidate automation**: The data model and lifecycle are fully implemented. The automated failure-pattern aggregation and candidate-proposal pipeline are not yet built.
6. **No admin UI**: Administrator review of improvement candidates is done directly via the database or API.
7. **No async database operations**: SQLAlchemy sync sessions are used for LangGraph compatibility.

Future directions include Celery + Redis for async generation, automated failure-pattern clustering, pgvector retrieval for grounded generation, admin API endpoints, per-key rate limiting, and an Ollama adapter for self-hosted inference.

---

## Architectural Trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Strict binary rubric (no partial credit) | Prevents a high average hiding a serious omission | May reject otherwise useful lessons for a single weak checkpoint |
| Max 2 content retries | Keeps cost and latency bounded; prevents runaway loops | Some lessons may not reach the quality bar in 3 attempts |
| Separate generator and evaluator roles | Reduces single-decision bias; generator cannot approve its own work | Adds 2–3 extra LLM calls per run; shared model may still have bias |
| LangGraph state machine | Retry rules and termination are explicit and testable | Adds a framework dependency vs plain Python |
| Synchronous workflow | Simpler code and direct testability with LangGraph | Blocks a worker thread per request; add task queue for scale |
| PostgreSQL as source of truth | Durable, auditable, relational history | Requires migrations, backups, and connection management |
| Human-approved improvement candidates | Prevents accidental rubric drift and evaluator gaming | Improvement cycle requires manual intervention |
| Application-computed quality gate | LLM cannot override its own pass/fail result | Requires robust schema validation before gate runs |
| pgvector optional | Core loop works without vector search; avoids premature complexity | Retrieval-grounded generation not yet available |
