# Self-Evaluating Lesson Content Generator

An agentic system that autonomously generates, evaluates, and refines educational content for beginners. The system uses three specialized AI agents working in a bounded workflow loop: a **Planner** creates the lesson structure, a **Generator** writes the content, and an **Evaluator** validates it against 14 strict quality checkpoints. Failed lessons trigger automatic revision with targeted feedback until quality standards are met or retry limits are reached.

**Built with:** LangGraph · FastAPI · Groq API · SQLite/PostgreSQL · Python 3.11+

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Clone and enter the project
git clone https://github.com/Subhradyuti/Lesson-Content-Generator.git
cd Lesson-Content-Generator

# 2. Set up Python environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows; use `source .venv/bin/activate` on Linux/macOS

# 3. Install dependencies
pip install -e .

# 4. Configure your Groq API key
cp .env.example .env
# Edit .env and add: GROQ_API_KEY=your_groq_api_key_here

# 5. Start the server
uvicorn app.main:app --reload
```

**✅ API is now running at http://localhost:8000**

Visit http://localhost:8000/docs for interactive API documentation.

### Generate Your First Lesson

```bash
curl -X POST http://localhost:8000/v1/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Introduction to RAG",
    "learner_profile": "Class 12 graduate; beginner; limited English vocabulary",
    "language": "simple English",
    "max_retries": 2
  }'
```

---

## 📚 Table of Contents

- [Agentic Workflow Architecture](#-agentic-workflow-architecture)
- [Architecture and Data Flow](#architecture-and-data-flow)
- [Installation and Setup](#installation-and-setup)
- [Environment Variables](#environment-variables)
- [Usage Examples](#usage-examples)
- [How the Binary Rubric Works](#how-the-binary-rubric-works)
- [Testing](#running-tests)
- [Observability](#observability)
- [Security Considerations](#security-considerations)

---

## 🤖 Agentic Workflow Architecture

### Three Specialized Agents

The system employs three distinct AI agents, each with a dedicated role and prompt:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AGENTIC WORKFLOW                             │
└─────────────────────────────────────────────────────────────────────┘

  📝 PLANNER AGENT (planner_v1.md)
  ├─ Role: Educational planning expert
  ├─ Input: Topic, learner profile, objectives
  └─ Output: Structured lesson plan
       ├─ Learning objectives (3-5)
       ├─ Prerequisites
       ├─ Key concepts
       ├─ Teaching order
       ├─ Worked example design
       └─ Common misconceptions

         ↓

  ✍️ GENERATOR AGENT (generator_v1.md)
  ├─ Role: Content writer for beginners
  ├─ Input: Lesson plan + (optional) revision instructions
  └─ Output: Complete lesson markdown
       ├─ Title & objectives
       ├─ Definition & purpose
       ├─ Step-by-step process
       ├─ Worked example
       ├─ Key terms glossary
       ├─ Common misconceptions
       ├─ Recap
       └─ 3-5 comprehension questions + answers

         ↓

  🔍 EVALUATOR AGENT (evaluator_v1.md)
  ├─ Role: Strict quality reviewer
  ├─ Input: Generated lesson + rubric (14 checkpoints)
  └─ Output: Binary evaluation (PASS/FAIL per checkpoint)
       ├─ Checkpoint ID
       ├─ Status (PASS or FAIL)
       ├─ Evidence from lesson
       ├─ Reason for decision
       └─ Required fix (if FAIL)

         ↓

  🎯 QUALITY GATE (application logic, not LLM)
  ├─ Validates all 14 checkpoints present
  ├─ Computes overall_pass = all(checkpoints PASS)
  └─ Decision:
       ├─ ALL PASS → Accept lesson
       └─ ANY FAIL → Build revision instructions → loop back to Generator
```

### Bounded Revision Loop

The system implements a **controlled retry mechanism** that prevents infinite loops:

```
Initial Generation (Attempt 0)
       ↓
   Evaluate
       ↓
    PASS? ───Yes──→ ✅ Accept & Return
       │
       No
       ↓
 Retries remaining? ───No──→ ❌ failed_quality_gate
       │
       Yes (max 2 retries)
       ↓
 Build targeted revision instructions:
   • List failed checkpoint IDs
   • Include evaluator's evidence
   • Provide specific fixes
   • Keep successful parts
       ↓
   Revision (Attempt 1 or 2)
       ↓
   Re-evaluate ALL checkpoints
       ↓
   [Loop back to PASS check]
```

**Key Features:**
- **Maximum 3 total drafts** (initial + 2 revisions)
- **Targeted feedback**: Only failed checkpoints trigger revisions
- **Full re-evaluation**: Every revision is evaluated against all 14 checkpoints
- **Preserved context**: Evaluator sees failed IDs + evidence from previous attempt
- **Hard limits**: API rejects `max_retries > 2`, workflow clamps invalid values

---

## Architecture and Data Flow

```
User/API Client
      │
      ▼
FastAPI + Pydantic (input validation, API key auth, injection protection)
      │
      ▼
LangGraph State Machine (bounded workflow with 10 nodes)
      │
      ├─1─→ validate_request ─────────────────────────────────────┐
      │        • Validate topic, retries, constraints              │
      │        • Initialize run_id and tracking fields             │
      │                                                             │
      ├─2─→ create_lesson_plan                                     │
      │        • Agent: Planner (planner_v1.md)                    │
      │        • Output: Structured lesson plan                    │
      │                                                             │
      ├─3─→ generate_lesson ◄────────────────────┐                │
      │        • Agent: Generator (generator_v1.md)                │
      │        • Initial draft OR targeted revision                │
      │                                           │                │
      ├─4─→ evaluate_lesson                       │                │
      │        • Agent: Evaluator (evaluator_v1.md)                │
      │        • Returns 14 checkpoint results                     │
      │                                           │                │
      ├─5─→ validate_evaluation                   │                │
      │        • Application logic (NO LLM)       │                │
      │        • Verifies all checkpoints present │                │
      │        • Computes quality gate result     │                │
      │                                           │                │
      ├─6─→ decide_next_action                    │                │
      │        • Routing decision point           │                │
      │        ├─ ALL PASS → finalize_run         │                │
      │        ├─ FAIL + retries remain → build_revision           │
      │        └─ FAIL + no retries → finalize_run                │
      │                                           │                │ 
      ├─7─→ build_revision_instructions           │                │
      │        • Extract failed checkpoint details                 │
      │        • Build targeted fix instructions  │                │
      │        • Increment attempt counter        │                │
      │        • Loop back to generate_lesson ────┘                │
      │                                                             │
      ├─8─→ finalize_run  ◄───────────────────────────────────────┘
      │        • Set final_status (passed / failed_quality_gate /  │
      │          generation_error / evaluation_error)              │
      │        • Preserve last draft on errors                     │
      │        • Complete rejection log                            │
      │                                                             │
      ├─9─→ persist_results                                        │
      │        • Save to database (SQLite or PostgreSQL)           │
      │        • generation_runs, lesson_drafts, evaluations,      │
      │          revision_logs tables                              │
      │                                                             │
      └─10→ return_result                                          │
             • Terminal node                                       │
             • Return to API                                       │
      ↓
API Response
  • run_id, status, lesson, evaluation
  • rejection_log (if revisions occurred)
  • Full audit trail

Observability Layer (runs in parallel)
  ├─ Structured JSON logs (run_id, timestamps, errors)
  ├─ Prometheus metrics (latency, pass rates, checkpoint failures)
  └─ OpenTelemetry traces (distributed tracing)
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

## Installation and Setup

### Prerequisites

- **Python 3.11 or higher** (tested on Python 3.12)
- **Git** for cloning the repository
- **Groq API key** — sign up at [console.groq.com](https://console.groq.com) (free tier available)
- Optional: **Docker** for PostgreSQL (or use SQLite for local development)

### Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/Subhradyuti/Lesson-Content-Generator.git
cd Lesson-Content-Generator

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies (one command installs everything)
pip install -e .

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (get it from console.groq.com)

# 5. Initialize the database
python -c "from app.db.session import init_db; init_db()"

# 6. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**✅ The API is now running at http://localhost:8000**

Open http://localhost:8000/docs in your browser to see the interactive API documentation (Swagger UI).

---

### Detailed Installation Steps

#### 1. Clone and Navigate

```bash
git clone https://github.com/Subhradyuti/Lesson-Content-Generator.git
cd Lesson-Content-Generator
```

#### 2. Set Up Python Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
# Windows PowerShell:
.venv\Scripts\Activate.ps1

# Windows Command Prompt:
.venv\Scripts\activate.bat

# Linux/macOS:
source .venv/bin/activate
```

Verify Python version:
```bash
python --version  # Should show 3.11 or higher
```

#### 3. Install Dependencies

The `pyproject.toml` file defines all dependencies. Install with:

```bash
# Install the package in editable mode (includes all dependencies)
pip install -e .

# Verify installation
python -c "import fastapi, langchain, langgraph; print('✅ All dependencies installed')"
```

**Main dependencies installed:**
- FastAPI 0.135.3 (API framework)
- LangChain 0.3.14 (LLM integration)
- LangGraph 0.2.60 (workflow orchestration)
- Groq 0.37.1 (model provider SDK)
- SQLAlchemy 2.0.36 (database ORM)
- Pydantic 2.13.0 (data validation)

**Optional dev dependencies:**
```bash
pip install -e ".[dev]"  # Installs pytest, ruff, mypy, coverage tools
```

#### 4. Configure Environment Variables

Copy the example configuration and fill in your values:

```bash
cp .env.example .env
```

**Edit `.env` and set these critical values:**

```bash
# Required: Your Groq API key (get from console.groq.com)
GROQ_API_KEY=your_groq_api_key_here

# Model selection (Groq supports multiple models)
GENERATOR_MODEL=openai/gpt-oss-120b    # or llama-3.3-70b-versatile
EVALUATOR_MODEL=openai/gpt-oss-120b

# Database (SQLite for local dev, PostgreSQL for production)
DATABASE_URL=sqlite:///./lesson_generator.db

# API security (optional for local development)
API_KEY=your-secret-api-key-here

# Application environment
APP_ENV=development
LOG_LEVEL=INFO
```

**Available Groq Models:**
- `llama-3.3-70b-versatile` — Llama 3.3 70B (fast, good quality)
- `llama-3.1-8b-instant` — Llama 3.1 8B (faster, lower quality)
- `openai/gpt-oss-120b` — GPT-OSS 120B (best quality if available)

Check [Groq's model documentation](https://console.groq.com/docs/models) for the latest available models.

#### 5. Initialize the Database

**Option A: SQLite (Default - No Setup Needed)**

SQLite is the default and requires no server. The database file is created automatically on first run.

```bash
# The database will be created automatically when you start the server
# Or initialize it manually:
python -c "from app.db.session import init_db; init_db()"
```

**Option B: PostgreSQL (Production)**

If using PostgreSQL, start it with Docker:

```bash
# Start PostgreSQL container
docker compose up db -d

# Update DATABASE_URL in .env:
DATABASE_URL=postgresql+psycopg://lesson_user:lesson_pass@localhost:5432/lesson_db

# Run migrations
alembic upgrade head
```

**Verify database initialization:**
```bash
# Check that tables were created
python -c "from app.db.models import Base; from app.db.session import engine; print([t.name for t in Base.metadata.sorted_tables])"
```

You should see: `['generation_runs', 'lesson_drafts', 'evaluations', 'revision_logs', 'improvement_candidates', 'configuration_versions']`

#### 6. Start the API Server

**Development mode (with auto-reload):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

**Using Docker (alternative):**
```bash
# Build and start both API and database
docker compose up --build

# The API will be available at http://localhost:8000
```

#### 7. Verify Installation

Open your browser and navigate to:

- **Swagger UI (Interactive API docs):** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health/live
- **API version:** http://localhost:8000/

You should see:
```json
{
  "message": "Self-Evaluating Lesson Content Generator",
  "version": "1.0.0",
  "environment": "development"
}
```

---

### Troubleshooting Setup

#### "No module named 'app'"
```bash
# Make sure you installed the package in editable mode
pip install -e .
```

#### "GROQ_API_KEY not found"
```bash
# Verify .env file exists and contains GROQ_API_KEY
cat .env | grep GROQ_API_KEY

# The key should start with "gsk_"
```

#### Database connection errors (PostgreSQL)
```bash
# Check if PostgreSQL is running
docker compose ps

# Verify DATABASE_URL format:
# postgresql+psycopg://user:password@host:port/database
```

#### Port 8000 already in use
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001

# Or find and kill the process using port 8000
# Windows: netsh http show servicestate
# Linux/macOS: lsof -ti:8000 | xargs kill
```

#### Import errors for langchain/langgraph
```bash
# Reinstall with specific versions
pip install --force-reinstall langchain==0.3.14 langgraph==0.2.60
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

## Usage Examples

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/lessons` | POST | Generate a new lesson |
| `/v1/lessons/{run_id}` | GET | Get lesson status and result |
| `/v1/lessons/{run_id}/history` | GET | Get full generation history (drafts + evaluations) |
| `/health/live` | GET | Liveness check |
| `/health/ready` | GET | Readiness check (includes DB status) |
| `/docs` | GET | Interactive API documentation (Swagger UI) |

### Submitting a Lesson Generation Request

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
