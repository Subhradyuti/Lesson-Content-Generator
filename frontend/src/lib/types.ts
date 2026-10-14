/**
 * TypeScript models mirroring the FastAPI backend response schemas.
 * Verified against `app/api/schemas.py` and live API responses.
 */

export type RunStatus =
  | "pending"
  | "running"
  | "passed"
  | "failed"
  | "failed_quality_gate"
  | "generation_error"
  | "evaluation_error";
export type CheckStatus = "PASS" | "FAIL";
export type RunOutcome = "passed" | "failed";

/** POST /v1/lessons — request body. */
export interface LessonRequest {
  topic: string;
  learner_profile?: string | null;
  language?: string | null;
  max_retries?: number;
  reference_material?: string | null;
}

/** Rubric check result inside an evaluation — matches CheckpointResultResponse in schemas.py. */
export interface EvaluationCheck {
  /** Checkpoint ID, e.g. "ACC-01" — field name is "id" in the API response. */
  id: string;
  status: CheckStatus;
  evidence: string;
  /** Evaluator's reason for the pass/fail decision. */
  reason: string;
  /** Specific fix required when status is FAIL. */
  required_fix?: string | null;
}

/** EvaluationLuck — passed/failed counts must reconcile with the checks array. */
export interface Evaluation {
  overall_pass: boolean;
  rubric_version: string;
  passed_count: number;
  failed_count: number;
  checks: EvaluationCheck[];
}

/** Run metadata returned by POST /v1/lessons and GET /v1/lessons/{id}. */
export interface LessonRunSummary {
  run_id: string;
  status: RunStatus;
  topic: string;
  attempt_count: number;
  draft_count: number;
  retry_count: number;
  created_at: string;
  completed_at?: string | null;
  rubric_version?: string | null;
  model_name?: string | null;
  error_detail?: string | null;
}

/** Full POST /v1/lessons response — matches LessonResponse in schemas.py. */
export interface LessonResponse extends LessonRunSummary {
  evaluation: Evaluation | null;
  /** The accepted lesson content. Field is named "lesson" in the API response. */
  lesson: string | null;
  rejection_log: RejectedAttempt[] | null;
  error_detail?: string | null;
  last_draft_available_for_review?: boolean;
  prior_run_summaries?: PriorRunSummary[];
}

/** Summary of a previous run for the same topic. */
export interface PriorRunSummary {
  run_id: string;
  status: string;
  draft_count: number;
  retry_count: number;
  failed_checkpoint_ids: string[];
  created_at: string;
}

/** One rejected draft inside `rejection_log`. */
export interface RejectedAttempt {
  attempt: number;
  failed_checkpoint_ids: string[];
  revision_instructions: string;
  evaluation_error?: string | null;
}

/** Draft record returned by GET /v1/lessons/{id}/history. */
export interface HistoryDraft {
  id: string;
  attempt_number: number;
  content_hash: string;
  created_at: string;
  /** The backend stores lesson text as {"text": "..."} in a JSON column. */
  lesson_content: { text?: string } | string;
  evaluations: HistoryEvaluation[];
}

/** Stored evaluation from the history endpoint. */
export interface HistoryEvaluation {
  id: string;
  overall_pass: boolean;
  rubric_version: string;
  /** The backend returns this JSON column already parsed as an object. */
  evaluation_json: Evaluation | Record<string, unknown>;
  created_at: string;
  evaluator_model: string;
}

/** Revision (rejection) log entry from the history endpoint. */
export interface RevisionLog {
  id: string;
  attempt_number: number;
  failed_checkpoint_ids: string[];
  revision_instructions: string | string[];
  /** The backend returns this JSON column already parsed as an array of objects. */
  failed_checks_detail: unknown[] | string | null;
  created_at: string;
  evaluation_error?: string | null;
}

/** Full history response. */
export interface RunHistoryResponse {
  run: {
    id: string;
    topic: string;
    learner_profile?: string | null;
    language?: string | null;
    status: RunStatus;
    max_retries: number;
    attempt_count: number;
    created_at: string;
    completed_at?: string | null;
    prompt_version?: string | null;
    rubric_version?: string | null;
    model_provider?: string | null;
    model_name?: string | null;
    error_detail?: string | null;
  };
  drafts: HistoryDraft[];
  revision_logs: RevisionLog[];
}

/** Health endpoint shapes. */
export interface LiveHealth {
  status: "ok";
}

export interface ReadyHealth {
  status: "ok" | "not_ready";
  database: boolean;
  details: { database?: string; [key: string]: unknown };
}
