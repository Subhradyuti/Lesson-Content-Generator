# Project Requirements: Self-Evaluating Lesson Content Generator

**Project type:** Production-oriented AI/agentic system  
**Primary use case:** Generate and quality-check beginner learning lessons  
**Submission topic:** Introduction to RAG (Retrieval-Augmented Generation)  
**Target learner:** A student in India who has completed Class 12, has limited English vocabulary, and may not have studied in an English-medium school  
**Document status:** Product and technical requirements specification  
**Version:** 1.0

---

## 1. Project Overview

Build a production-oriented agentic system that creates a beginner-friendly lesson for a given topic, evaluates the lesson against a strict pass/fail rubric, and improves the lesson when it fails.

The system must do more than send one prompt to a language model. It must run a controlled workflow:

**Input → Plan → Generate → Evaluate → Revise if needed → Final decision → Store results**

The system should decide whether a lesson meets the minimum quality bar before presenting it to a learner. It must also retain evaluation results and revision history so the team can improve prompts, rubrics, and system behaviour over time.

The initial demonstration topic is **“Introduction to RAG.”** The architecture must support other topics later.

### 1.1 Product goal

Deliver a lesson that a learner with no prior technical background can understand, including:

- What the topic means.
- Why the topic is useful.
- How it works, explained step by step.
- A simple, realistic example.
- Important terms explained in plain language.
- A short recap and a way to check understanding.

### 1.2 Non-goals for the first version

- Automatically publishing lessons to a public course without approval.
- Training a foundation model from scratch.
- Guaranteeing that an LLM evaluator is always correct.
- Supporting every language and school curriculum on day one.
- Allowing unlimited regeneration or unbounded agent loops.

---

## 2. Users and Use Cases

### Primary user: Beginner learner

A learner who knows basic computer use but may not know terms such as *embedding*, *vector database*, *retrieval*, or *hallucination*.

### Secondary user: Content reviewer or administrator

A person who can inspect lessons, see why a draft failed, approve exceptional cases, and review quality trends.

### Core use cases

1. A user submits a topic and learner profile.
2. The system generates a standalone lesson.
3. The evaluator checks the lesson against every required checkpoint.
4. If any required check fails, the system revises the lesson using specific failure reasons.
5. The system stops after a maximum of two retries.
6. The API returns the accepted lesson if it passes, or a clear non-passing status if it does not.
7. The system stores drafts, scores, failure reasons, revisions, model settings, and final status.
8. Administrators inspect recurring failures and use approved evidence to improve prompts and rubrics.

---

## 3. Functional Requirements

Requirements use **MUST**, **SHOULD**, and **MAY** to indicate priority.

### FR-01: Lesson request

The API MUST accept:

- `topic` — required, non-empty string.
- `learner_profile` — optional; defaults to the target learner described above.
- `learning_objectives` — optional list of learning outcomes.
- `language` — optional; defaults to simple English.
- `max_retries` — optional integer restricted to `0`, `1`, or `2`; defaults to `2`.
- `reference_material` — optional trusted source text or source identifiers.

The service MUST validate inputs, limit input size, and reject unsupported or malformed requests with useful error messages.

### FR-02: Lesson planning

Before drafting, the system SHOULD create a compact lesson plan containing:

- Prerequisites (normally none for this topic).
- Learning objectives.
- The key ideas that must be covered.
- A suitable teaching order.
- A simple example.
- Likely misconceptions to avoid.

The plan MUST be checked for required fields before it is passed to the generator.

### FR-03: Lesson generation

The generator MUST produce a self-contained lesson with the following sections:

1. Title.
2. What you will learn.
3. What the topic means, in plain language.
4. Why it matters.
5. How it works, in numbered steps.
6. A worked example.
7. Key terms explained simply.
8. Common misunderstanding(s).
9. Short recap.
10. Three to five comprehension questions, with answers or an answer key.

The generated lesson MUST define technical terms before relying on them. It SHOULD use short sentences, familiar examples, and explain acronyms the first time they appear.

For the RAG demonstration, the lesson MUST explain that RAG combines retrieving relevant information from a source with generating an answer using a language model. It MUST distinguish retrieval from generation and MUST NOT claim that RAG guarantees truth or eliminates hallucinations.

### FR-04: Strict evaluation

The evaluator MUST assess the complete lesson against a versioned, binary rubric. Each checkpoint has only two outcomes: **PASS** or **FAIL**. There is no partial credit.

Every checkpoint result MUST include:

- Checkpoint ID.
- Pass/fail status.
- A short reason.
- Evidence from the lesson, such as a short quote or section reference.
- A specific correction request if it fails.

A lesson passes only when **all mandatory checkpoints pass**. A numeric score MAY be shown for reporting, but it MUST NOT override a failed mandatory checkpoint.

### FR-05: Revision and regeneration

If the lesson fails and retries remain, the system MUST send the generator:

- The previous lesson.
- The failed checkpoint IDs.
- The evaluator’s reasons and evidence.
- Concrete revision instructions.
- The original learning objectives and lesson structure.

The revision SHOULD fix failed checks while preserving already-passing content. The evaluator MUST re-check the revised lesson from the beginning; it must not simply assume the changes worked.

The system MUST stop after the configured retry limit. With the default of two retries, there can be at most **three drafts**: the initial draft and two revised drafts.

### FR-06: Final decision

The system MUST return one of these statuses:

- `passed` — all mandatory checks pass.
- `failed_quality_gate` — the retry limit was reached and at least one mandatory check still fails.
- `generation_error` — generation failed after the configured technical retries.
- `evaluation_error` — the evaluator could not return a valid result after its configured technical retries.

A non-passing lesson MUST NOT be labelled “approved” or “ready to ship.” It MAY be returned for administrator review, clearly marked as not passing.

### FR-07: Rejection and revision log

The system MUST maintain an auditable log for each draft:

- Draft number and timestamp.
- Prompt/rubric versions.
- Model and relevant configuration.
- Evaluation result for every checkpoint.
- Failed checkpoint IDs and reasons.
- Revision instructions.
- Final decision and retry count.

Logs MUST avoid storing secrets and MUST support tracing a final lesson back to the drafts and evaluation results that produced it.

### FR-08: Persistent memory

The system MUST retain data across separate runs. Persistent memory has three distinct purposes:

1. **Run history:** previous lessons, evaluation results, and revisions.
2. **Approved improvement memory:** recurring failure patterns and improvements reviewed or validated before reuse.
3. **Configuration history:** versions of prompts, rubrics, and model settings.

The system MUST NOT silently rewrite its own production rubric based on one model-generated opinion. Proposed improvements MUST be stored as candidates, tested against a fixed evaluation set, and approved before becoming active.

### FR-09: Human review and override

An administrator SHOULD be able to inspect failed lessons and their evidence. Any manual approval or override MUST record the reviewer, time, reason, and previous automated status. Human override MUST NOT erase the original evaluation result.

### FR-10: Observability

The system MUST expose operational information such as request ID, stage durations, token usage when available, model/provider errors, retry count, and final status. Logs MUST not contain API keys or unnecessary personal data.

---

## 4. Quality Rubric: Binary Pass/Fail Checkpoints

Use a versioned rubric. The initial version is `rag-beginner-v1`.

A checkpoint passes only when its stated condition is satisfied. If the evaluator cannot find sufficient evidence, it MUST fail the checkpoint rather than assume the lesson covered it.

| ID | Dimension | Pass condition |
|---|---|---|
| ACC-01 | Accuracy | The explanation correctly describes the topic and does not contain a material factual error. |
| ACC-02 | Grounding | Claims that require support are consistent with supplied trusted references, when references are provided. Unsupported claims are flagged. |
| BEG-01 | Beginner language | The lesson assumes no prior knowledge and uses short, understandable sentences suitable for the target learner. |
| JAR-01 | Jargon | Every essential technical term is explained before or when it is first used. |
| EX-01 | Worked example | A concrete example is explained step by step and demonstrates the central idea rather than merely naming it. |
| COV-01 | Definition | The lesson clearly states what the topic is. |
| COV-02 | Purpose | The lesson explains why the topic matters and what problem it helps solve. |
| COV-03 | Process | The lesson explains the main workflow in a logical sequence. |
| COV-04 | Limitations | The lesson explains important limitations and avoids absolute guarantees. |
| FLOW-01 | Teaching order | The lesson moves from simple concepts to more detailed ideas without unexplained jumps. |
| FLOW-02 | Standalone | A learner can understand the lesson without opening an external link or reading another document. |
| CHECK-01 | Learning check | The lesson includes 3–5 relevant questions and a correct answer key. |
| CONS-01 | Internal consistency | Definitions, examples, and recap do not contradict one another. |
| SAFE-01 | Safe content | The lesson does not contain harmful instructions, private data, or fabricated citations. |

### 4.1 Rubric evaluation rules

- Every checkpoint is mandatory in the initial release.
- Each result must be valid structured data matching the schema.
- The evaluator must cite lesson evidence by section or short quote.
- The evaluator must not mark a checkpoint PASS solely because the lesson says it meets the checkpoint.
- A second validation step MUST verify that all expected checkpoint IDs are present exactly once.
- If the evaluator output is malformed, treat it as an **evaluation error**, not as a passing lesson.
- An LLM evaluator is a useful quality filter, not proof of correctness. High-risk or factual lessons may require trusted-reference checks and human review.

### 4.2 Structured evaluation result

```json
{
  "rubric_version": "rag-beginner-v1",
  "overall_pass": false,
  "checks": [
    {
      "id": "JAR-01",
      "status": "FAIL",
      "evidence": "The term 'embedding' appears without an explanation.",
      "reason": "A beginner may not understand this technical term.",
      "required_fix": "Explain the term in simple language before using it."
    }
  ]
}
```

This is an illustrative schema example, not a claim that a real evaluation has already been run.

---

## 5. Agent Workflow and State Machine

Use a bounded, explicit state machine rather than an open-ended autonomous agent.

```text
RECEIVED
   |
   v
VALIDATE_INPUT
   |
   v
CREATE_PLAN
   |
   v
GENERATE_DRAFT <-----------------------------+
   |                                         |
   v                                         |
EVALUATE_DRAFT                               |
   |                                         |
   +---- all checks PASS ----> ACCEPTED      |
   |                                         |
   +---- any check FAIL ----> RETRY_ALLOWED? |
                                  |          |
                          yes     |     no   |
                            v     |          |
                     BUILD_REVISION_PROMPT  |
                            |                |
                            +----------------+

If retries are exhausted: REJECTED / NEEDS_REVIEW
Technical failures: GENERATION_ERROR or EVALUATION_ERROR
```

### Required loop logic

1. Set `attempt = 0`.
2. Generate a draft.
3. Evaluate all mandatory checks.
4. If all checks pass, save the result and stop.
5. If any check fails and `attempt < max_retries`, create a revision prompt, increment the attempt, and repeat.
6. Otherwise, return `failed_quality_gate` and retain the rejection log.
7. Enforce a hard maximum of two content retries, even if a request tries to set a larger value.

Technical retries for transient API/network errors MUST be separate from content regeneration and MUST also have a finite limit.

---

## 6. Recommended Open-Source Technology Stack

Use open-source frameworks and self-hostable components wherever practical. The language model provider may be external; Groq API access is not itself an open-source model deployment.

| Layer | Recommended technology | Responsibility |
|---|---|---|
| Language | Python 3.11+ | Core application logic |
| API | FastAPI + Pydantic | Validated REST endpoints and schemas |
| Agent orchestration | LangGraph | Explicit states, bounded loops, conditional routing |
| LLM integration | LangChain | Model adapters, prompt templates, structured output helpers |
| Model inference | Groq API with an available instruction-tuned model | Lesson planning, generation, evaluation |
| Alternative inference | Ollama with a suitable open-weight model | Local development or self-hosted deployments |
| Database | PostgreSQL | Requests, drafts, evaluations, audit records, versioned configuration |
| Vector search (optional) | pgvector | Search approved examples and improvement records |
| Cache / rate limiting (optional) | Redis | Short-lived cache, throttling, distributed coordination |
| Migrations | Alembic | Version-controlled database schema changes |
| API server | Uvicorn | ASGI serving |
| Testing | pytest + HTTPX | Unit, integration, and API tests |
| Linting and typing | Ruff + mypy | Code quality and static checks |
| Observability | OpenTelemetry + Prometheus/Grafana | Traces, metrics, dashboards |
| Error reporting | Sentry-compatible self-hosted option, if required | Exception monitoring |
| Packaging | Docker + Docker Compose | Reproducible local and test environments |
| CI | GitHub Actions or another CI runner | Automated lint, tests, security checks |
| Secrets | Environment variables locally; managed secret store in production | API credentials and sensitive configuration |

### Stack decisions

- **LangGraph** is responsible for workflow control, state transitions, and bounded retries.
- **LangChain** is used for reusable model calls and prompt construction; it should not obscure the workflow.
- **FastAPI** provides the stable interface for web clients or other services.
- **PostgreSQL** is the source of truth for run history and auditability.
- **pgvector is optional.** The core lesson loop does not require vector search. Add it only if retrieval over approved reference material or improvement examples is needed.
- **Redis is optional** for a single-instance MVP and should be added when rate limiting, caching, or distributed coordination justify it.
- **Groq** is a model-serving API choice, not an open-source framework. Verify current model availability, context limits, rate limits, data terms, and pricing before deployment.
- Keep provider calls behind an interface so the model provider can be changed without rewriting the workflow.

---

## 7. High-Level Architecture

```text
Client / Admin UI
       |
       v
FastAPI + Pydantic
       |
       v
Request Validator + Policy Checks
       |
       v
LangGraph Workflow
  |        |          |
  |        |          +--> Bounded Retry Controller
  |        |
  |        +--> Evaluator --> Rubric Validator
  |
  +--> Planner --> Lesson Generator
                    |
                    v
              Draft Lesson
                    |
                    v
              Quality Gate
                    |
         +----------+----------+
         |                     |
       PASS                   FAIL
         |                     |
         v                     v
    Final Result       Feedback + Regenerate
         |                     |
         +----------+----------+
                    |
                    v
          PostgreSQL Audit Store
                    |
                    v
          Metrics, Traces, Logs
```

### Component responsibilities

**Request validator**
- Validates topic, language, learner profile, and retry limit.
- Applies input-size and rate limits.
- Treats user-provided topic/reference text as data, not system instructions.

**Planner**
- Converts the request into learning objectives and a lesson outline.
- Ensures the outline covers the required content before drafting.

**Generator**
- Produces the lesson using a versioned system prompt and the validated plan.
- Returns a predictable lesson structure.

**Evaluator**
- Applies the binary rubric independently of the generator.
- Uses separate prompts and structured output.
- Must be instructed to find evidence and actively look for failure, not to praise the draft.

**Rubric validator**
- Confirms every required checkpoint appears once and only once.
- Rejects malformed or incomplete evaluator output.
- Computes `overall_pass` in application code from the checkpoint results rather than trusting the model's summary field.

**Revision controller**
- Builds a focused revision request from failed checks.
- Enforces the retry budget and terminates every path.

**Memory and audit store**
- Stores run artifacts and approved improvement candidates.
- Makes it possible to compare quality by prompt version, rubric version, and model.

---

## 8. Prompt and Model Design

### 8.1 Separate roles

Do not use one prompt that asks the same model to write a lesson and then casually approve its own work. Use distinct generation and evaluation calls, preferably with different system prompts. If practical, use different model configurations or models for the two roles.

### 8.2 Generator prompt requirements

The generator prompt MUST instruct the model to:

- Teach a complete beginner using simple English.
- Follow the required lesson structure.
- Define acronyms and technical terms.
- Use one worked example with clear steps.
- Include limitations and a knowledge check.
- Avoid fabricated facts, fake citations, and unsupported claims.
- Use supplied references when available and distinguish sourced facts from examples.
- Apply evaluator feedback precisely on revision.

### 8.3 Evaluator prompt requirements

The evaluator prompt MUST instruct the model to:

- Act as a strict reviewer, not a writing assistant.
- Assess every rubric checkpoint independently.
- Return only the required structured result.
- Use PASS only when the stated condition is clearly supported by lesson evidence.
- Treat missing or ambiguous evidence as FAIL.
- Identify concrete fixes without rewriting the whole lesson.
- Never change the rubric to make a draft pass.

### 8.4 Model configuration

- Make temperature, token limits, timeout, and model name configurable.
- Use lower temperature for evaluation than generation where the provider supports it.
- Record provider and model identifiers for each call.
- Validate structured output with Pydantic.
- Use finite timeouts and retry only transient failures.
- Do not rely on hidden model reasoning; store concise evidence and decisions instead.

---

## 9. Self-Evolving Improvement System

“Self-evolving” MUST mean controlled, measurable improvement—not unrestricted self-modification.

### 9.1 Failure pattern collection

Group failures by checkpoint and reason, for example:

- Technical terms are not defined.
- The example is too abstract.
- The lesson skips a step.
- The recap introduces new information.
- A claim is too absolute.
- The answer key conflicts with the lesson.

### 9.2 Candidate improvement workflow

1. Collect evaluation failures across runs.
2. Cluster repeated failure patterns.
3. Propose a prompt or rubric clarification.
4. Save the proposal as a versioned candidate.
5. Run it against a fixed benchmark set containing successful, failed, and edge-case lessons.
6. Compare pass rates, false approvals, false rejections, latency, and token cost.
7. Require human approval before promoting a rubric change to production.
8. Keep the previous version available for rollback.

### 9.3 Preventing evaluator gaming

- Freeze the rubric during a single request.
- Do not let the generator edit the evaluator prompt or rubric.
- Do not treat repeated model agreement as proof of correctness.
- Test evaluator decisions against human-labelled examples.
- Track false-pass rate as a key quality metric.
- Use independent factual checks or trusted references where possible.
- Retain a fixed benchmark set that is not used to write the candidate prompt.

---

## 10. Persistent Memory and Data Model

Use PostgreSQL as the durable system of record.

### Suggested tables

**`generation_runs`**
- `id` (UUID, primary key)
- `topic`
- `learner_profile`
- `language`
- `status`
- `max_retries`
- `attempt_count`
- `created_at`
- `completed_at`
- `prompt_version`
- `rubric_version`
- `model_provider`
- `model_name`

**`lesson_drafts`**
- `id` (UUID, primary key)
- `run_id` (foreign key)
- `attempt_number`
- `lesson_content` (JSONB or structured text)
- `created_at`
- `content_hash`

**`evaluations`**
- `id` (UUID, primary key)
- `draft_id` (foreign key)
- `rubric_version`
- `overall_pass`
- `evaluation_json` (JSONB)
- `created_at`
- `evaluator_model`

**`revision_logs`**
- `id` (UUID, primary key)
- `draft_id` (foreign key)
- `failed_checkpoint_ids`
- `revision_instructions`
- `created_at`

**`improvement_candidates`**
- `id` (UUID, primary key)
- `candidate_type`
- `description`
- `evidence_summary`
- `benchmark_results`
- `status` (`proposed`, `testing`, `approved`, `rejected`, `rolled_back`)
- `created_by`
- `approved_by`
- `created_at`
- `approved_at`

**`configuration_versions`**
- `id` (UUID, primary key)
- `config_type` (`generator_prompt`, `evaluator_prompt`, `rubric`, `model_config`)
- `version`
- `content`
- `created_at`
- `created_by`
- `active`

Store secrets outside the database. Define data retention and deletion policies before collecting real learner information.

---

## 11. API Requirements

### `POST /v1/lessons`

Starts a generation run.

**Example request**

```json
{
  "topic": "Introduction to RAG",
  "learner_profile": "Class 12 graduate in India; beginner; limited English vocabulary",
  "language": "simple English",
  "learning_objectives": [
    "Explain what RAG means",
    "Describe the basic RAG workflow",
    "Give one practical example"
  ],
  "max_retries": 2
}
```

**Example successful response**

```json
{
  "run_id": "generated-uuid",
  "status": "passed",
  "attempt_count": 1,
  "rubric_version": "rag-beginner-v1",
  "lesson": {
    "title": "Introduction to RAG",
    "sections": []
  },
  "evaluation": {
    "overall_pass": true,
    "checks": []
  },
  "rejection_log": []
}
```

The empty arrays above illustrate the response shape only. A real successful response must contain the full lesson and every rubric check.

**Example non-passing response**

```json
{
  "run_id": "generated-uuid",
  "status": "failed_quality_gate",
  "attempt_count": 3,
  "lesson": null,
  "last_draft_available_for_review": true,
  "rejection_log": [
    {
      "attempt": 0,
      "failed_checks": ["JAR-01"],
      "reason": "A required technical term was not explained.",
      "change_made": "The revision instruction asks for a plain-language definition."
    }
  ]
}
```

In the real response, include the full rejection history. Do not claim that a lesson passed when the quality gate failed.

### Additional endpoints

- `GET /v1/lessons/{run_id}` — retrieve the run status and final result.
- `GET /v1/lessons/{run_id}/history` — retrieve drafts and evaluations, subject to access control.
- `GET /health/live` — process liveness.
- `GET /health/ready` — readiness including required dependencies.
- `GET /metrics` — internal metrics endpoint, protected from public access.

Administrative endpoints for reviewing improvement candidates MAY be added in a later milestone.

---

## 12. Security, Privacy, and Reliability

The production implementation MUST include:

- API authentication for protected endpoints.
- Role-based access for administrator and reviewer actions.
- Rate limiting and request-size limits.
- Input validation and output schema validation.
- Secrets managed outside source control.
- Dependency pinning and vulnerability scanning.
- Protection against prompt injection in user topics and supplied reference text.
- Clear separation between trusted system instructions and untrusted user/source content.
- No execution of code generated by the model.
- Redaction of credentials and sensitive content from logs.
- Timeouts, bounded retries, and graceful handling of provider outages.
- Database migrations, backups, and a tested restore procedure.
- Audit records for changes to prompts, rubrics, and manual approvals.
- Data retention and deletion policies.
- TLS in deployed environments.

The API MUST NOT expose internal prompts, secrets, raw provider credentials, or another user's lesson history.

---

## 13. Testing and Acceptance Criteria

### 13.1 Unit tests

Test at minimum:

- Input validation and retry-limit enforcement.
- Rubric schema validation.
- Missing, duplicated, and unknown checkpoint IDs.
- Overall pass calculation.
- Revision prompt creation.
- State transitions and termination.
- Logging and status mapping for provider failures.
- Protection against malformed model responses.

### 13.2 Integration tests

Test at minimum:

1. A lesson passes on the first draft.
2. A first draft fails and the next draft passes.
3. All drafts fail and the system stops after two retries.
4. The evaluator returns malformed JSON.
5. The model provider times out or returns a rate-limit error.
6. The database is temporarily unavailable.
7. Two requests run concurrently without mixing drafts or memory.
8. User-provided text attempts to override system instructions.
9. An unapproved improvement candidate is not activated.
10. A reviewer override retains the original failure history.

### 13.3 Acceptance criteria

The project is ready for an initial production pilot when:

- [ ] A request for “Introduction to RAG” creates a complete beginner lesson.
- [ ] Every mandatory rubric checkpoint receives PASS or FAIL with evidence.
- [ ] A single failed mandatory checkpoint prevents automated approval.
- [ ] The system regenerates only when a retry remains.
- [ ] The system never exceeds two content retries.
- [ ] A passing revision is re-evaluated in full.
- [ ] The rejection log explains what failed and what changed on every retry.
- [ ] Results and configuration versions persist across runs.
- [ ] Evaluator output is schema-validated and application logic computes the final pass decision.
- [ ] Non-passing output is clearly marked and not presented as approved.
- [ ] API errors are predictable and do not leak secrets.
- [ ] Automated tests cover the pass, retry, exhaustion, and error paths.
- [ ] The service can be started reproducibly using the documented setup.
- [ ] Metrics report latency, retry count, provider errors, and quality-gate outcomes.

### 13.4 Quality metrics to track

- First-draft pass rate.
- Final pass rate after retries.
- Average number of drafts per accepted lesson.
- False-pass rate against a human-reviewed benchmark.
- False-rejection rate against a human-reviewed benchmark.
- Per-checkpoint failure frequency.
- Average generation and evaluation latency.
- Token usage and estimated cost per accepted lesson.
- Provider failure rate.
- Percentage of lessons escalated for human review.

Do not optimize only for pass rate. A system that approves weak lessons can show a high pass rate while delivering poor quality.

---

## 14. Deployment and Operations

### Local development

Provide a Docker Compose setup for the API and PostgreSQL. Redis and any optional vector service should be included only when used. Use a `.env.example` file with placeholder values, never real secrets.

### Production deployment

- Run the API behind a TLS-terminating reverse proxy or managed gateway.
- Use a managed PostgreSQL service or a properly operated database.
- Store secrets in a managed secret store.
- Configure resource limits, health checks, structured logs, and alerts.
- Separate development, test, and production environments.
- Pin dependency versions and promote changes through CI.
- Use database backups and test restoration regularly.
- Use a queue/worker system if lesson generation becomes long-running or traffic requires asynchronous processing.

### CI pipeline

On each pull request:

1. Run formatting and lint checks.
2. Run type checks.
3. Run unit tests.
4. Run integration tests with mocked model calls.
5. Run dependency and secret scanning.
6. Build the container image.
7. Optionally run a small model-backed smoke test outside normal deterministic CI.

Model-backed tests should use fixed fixtures or mocked outputs for reliable CI; live model outputs can vary and should not be the only basis for regression testing.

---

## 15. Suggested Repository Structure

```text
self-evaluating-lesson-generator/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── routes_lessons.py
│   │   └── schemas.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   ├── workflow/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── nodes.py
│   │   └── routing.py
│   ├── agents/
│   │   ├── planner.py
│   │   ├── generator.py
│   │   └── evaluator.py
│   ├── quality/
│   │   ├── rubric.py
│   │   ├── validator.py
│   │   └── decision.py
│   ├── memory/
│   │   ├── repository.py
│   │   └── improvement_candidates.py
│   ├── prompts/
│   │   ├── planner_v1.md
│   │   ├── generator_v1.md
│   │   └── evaluator_v1.md
│   ├── db/
│   │   ├── models.py
│   │   └── session.py
│   └── observability/
│       ├── metrics.py
│       └── tracing.py
├── rubric/
│   └── rag-beginner-v1.yaml
├── benchmarks/
│   ├── lesson_cases.jsonl
│   └── evaluator_labels.jsonl
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── migrations/
├── Dockerfile
├── compose.yaml
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

This structure is a recommended starting point. Avoid adding empty modules or unnecessary services before their responsibilities are implemented.

---

## 16. Delivery Plan

### Phase 1 — Reliable core loop

- Define the lesson schema and rubric.
- Build generator and evaluator calls.
- Implement the LangGraph state machine.
- Enforce strict pass/fail decisions and a two-retry maximum.
- Return the final lesson and rejection log.
- Add unit tests for all control-flow paths.

**Exit condition:** The core workflow behaves correctly with mocked model responses.

### Phase 2 — API and persistence

- Add FastAPI endpoints.
- Add PostgreSQL models and migrations.
- Persist drafts, evaluations, versions, and audit logs.
- Add authentication, rate limiting, and input limits.
- Add Docker-based local setup.

**Exit condition:** A run can be created, retrieved, and audited after the service restarts.

### Phase 3 — Quality and observability

- Build a human-reviewed benchmark set.
- Measure evaluator false passes and false rejections.
- Add traces, metrics, structured logs, and alerts.
- Add trusted-reference checks where appropriate.
- Test provider failures and malformed responses.

**Exit condition:** The team can measure quality and diagnose a failed run.

### Phase 4 — Controlled self-improvement

- Aggregate common failure patterns.
- Propose prompt/rubric improvements.
- Evaluate candidates against the benchmark.
- Add approval, version activation, and rollback.
- Compare quality and cost before promoting changes.

**Exit condition:** Improvements are evidence-based, versioned, reviewable, and reversible.

---

## 17. Key Engineering Trade-offs

| Decision | Reason | Trade-off |
|---|---|---|
| Strict binary checkpoints | Prevents a high average score from hiding a serious omission | Can reject otherwise useful lessons because of one failed check |
| Two content retries | Keeps cost and latency bounded | Some lessons may remain below the quality bar |
| Separate generator and evaluator roles | Reduces the chance that generation and approval become one unchallenged decision | Adds model calls and does not eliminate shared-model bias |
| LangGraph state machine | Makes retry rules and termination explicit and testable | Adds a framework dependency compared with plain Python |
| PostgreSQL audit history | Supports durable history, reporting, and traceability | Requires migrations, backups, and retention management |
| Human-approved improvement candidates | Reduces accidental rubric drift and evaluator gaming | Improvement is slower than unrestricted automatic updates |
| Optional vector search | Adds retrieval only when reference search or example recall is needed | Extra operational complexity if added too early |
| Provider abstraction | Reduces lock-in and makes model swaps easier | Requires a small amount of interface and compatibility work |

---

## 18. Definition of Done

The project is complete for its first production pilot when a user can submit **“Introduction to RAG”**, the service generates a beginner lesson, evaluates it against the complete binary rubric, revises it at most twice when necessary, and returns either:

1. a lesson that passed every mandatory checkpoint, together with its evaluation evidence and full revision history; or
2. a clearly labelled non-passing result, with the failed checkpoints, reasons, and changes attempted.

Every run must be reproducible enough to audit, persist across service restarts, and produce measurable operational and quality metrics. Prompt or rubric improvements must be benchmarked, versioned, and reversible.

**Core principle:** The system does not succeed because it generated polished text. It succeeds only when its defined quality checks pass—or when it honestly reports that the lesson did not pass.
