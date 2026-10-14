import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Clock,
  Database,
  FileText,
  GitBranch,
  Hash,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { motion } from "framer-motion";

import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { EvaluationPanel } from "../components/EvaluationPanel";
import { LessonViewer } from "../components/LessonViewer";
import { CardSkeleton } from "../components/Spinner";
import { api, ApiError, NetworkError } from "../lib/api";
import { formatDateTime, timeAgo, compactRunId } from "../lib/utils";
import { saveRecentRun } from "../lib/recentRuns";
import type {
  RunHistoryResponse,
  HistoryDraft,
  RevisionLog,
  Evaluation,
} from "../lib/types";

interface ErrorState {
  title: string;
  detail: string;
}

function errorMessage(err: unknown): ErrorState {
  if (err instanceof ApiError) {
    return {
      title: `Backend error (${err.status})`,
      detail: err.message,
    };
  }
  if (err instanceof NetworkError) {
    return { title: "Backend unreachable", detail: err.message };
  }
  return {
    title: "Unexpected error",
    detail: err instanceof Error ? err.message : String(err),
  };
}

function DraftCard({
  draft,
  index,
  total,
}: {
  draft: HistoryDraft;
  index: number;
  total: number;
}) {
  const [expanded, setExpanded] = useState(index === total - 1); // Last draft expanded by default
  // evaluation_json is a JSON column: the backend may return it already parsed
  // (SQLAlchemy deserialises JSON columns before serialising to the HTTP response),
  // so guard against the string case for forward compatibility.
  const evaluations = draft.evaluations.map((ev) => ({
    ...ev,
    parsed: (typeof ev.evaluation_json === "string"
      ? JSON.parse(ev.evaluation_json)
      : ev.evaluation_json) as Evaluation,
  }));
  const lastEval = evaluations[evaluations.length - 1];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="card-pad"
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between text-left"
        aria-expanded={expanded}
        aria-controls={`draft-${draft.id}`}
      >
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 font-mono text-sm font-semibold text-accent ring-1 ring-accent/25">
            {draft.attempt_number}
          </span>
          <div>
            <p className="text-sm font-semibold text-ink">
              Draft {draft.attempt_number} {index === total - 1 && "(final)"}
            </p>
            <p className="font-mono text-xs text-faint">{timeAgo(draft.created_at)}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {lastEval && (
            <StatusBadge status={lastEval.parsed.overall_pass ? "passed" : "failed"} />
          )}
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
          )}
        </div>
      </button>

      {expanded && (
        <div id={`draft-${draft.id}`} className="mt-5 space-y-5">
          <div className="rounded-xl border border-line bg-raised/50 p-3">
            <div className="grid gap-2 text-xs sm:grid-cols-3">
              <div>
                <span className="text-faint">Created</span>
                <p className="mt-0.5 font-medium text-ink">{formatDateTime(draft.created_at)}</p>
              </div>
              <div>
                <span className="text-faint">Content hash</span>
                <p className="mt-0.5 font-mono text-ink">{draft.content_hash.slice(0, 12)}…</p>
              </div>
              <div>
                <span className="text-faint">Evaluations</span>
                <p className="mt-0.5 font-medium text-ink">{evaluations.length}</p>
              </div>
            </div>
          </div>

          {evaluations.length > 0 && lastEval && (
            <EvaluationPanel evaluation={lastEval.parsed} />
          )}

          <LessonViewer content={
            typeof draft.lesson_content === "string"
              ? draft.lesson_content
              : (draft.lesson_content as { text?: string })?.text ?? JSON.stringify(draft.lesson_content)
          } />
        </div>
      )}
    </motion.div>
  );
}

function RevisionLogCard({ log, index }: { log: RevisionLog; index: number }) {
  const [expanded, setExpanded] = useState(false);
  // failed_checks_detail is a JSON column returned already parsed as an array.
  const failedDetails: unknown[] = Array.isArray(log.failed_checks_detail)
    ? log.failed_checks_detail
    : typeof log.failed_checks_detail === "string" && log.failed_checks_detail
    ? (JSON.parse(log.failed_checks_detail) as unknown[])
    : [];

  // revision_instructions may be an array (DB) or a plain string.
  const revisionText = Array.isArray(log.revision_instructions)
    ? log.revision_instructions.join("\n")
    : log.revision_instructions ?? "";

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className="relative border-l-2 border-fail/30 pl-4"
    >
      <div className="absolute -left-[9px] top-0 h-4 w-4 rounded-full border-2 border-fail bg-surface" />
      <div className="pb-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-ink">
              Attempt {log.attempt_number} rejected
            </p>
            <p className="mt-0.5 font-mono text-xs text-faint">{timeAgo(log.created_at)}</p>
          </div>
          <span className="chip shrink-0">
            {log.failed_checkpoint_ids.length} failed
          </span>
        </div>

        <div className="mt-3 rounded-lg bg-raised/50 p-3 text-xs">
          <p className="font-semibold text-faint uppercase tracking-wide">Failed checkpoints</p>
          <ul className="mt-1.5 space-y-0.5">
            {log.failed_checkpoint_ids.map((id) => (
              <li key={id} className="font-mono text-muted">
                {id}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-3 rounded-lg border border-warn/25 bg-warn-dim p-3 text-xs">
          <p className="font-semibold text-warn">Revision instructions</p>
          <p className="mt-1 leading-5 text-ink">{revisionText}</p>
        </div>

        {failedDetails.length > 0 && (
          <div className="mt-3">
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1.5 text-xs font-medium text-accent hover:underline"
              aria-expanded={expanded}
            >
              {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              {expanded ? "Hide" : "Show"} check details ({failedDetails.length})
            </button>
            {expanded && (
              <pre className="mt-2 overflow-x-auto rounded-lg border border-line bg-sunken p-3 font-mono text-[11px] text-muted">
                {JSON.stringify(failedDetails, null, 2)}
              </pre>
            )}
          </div>
        )}

        {log.evaluation_error && (
          <div className="mt-3 rounded-lg border border-fail/25 bg-fail-dim p-2 text-xs text-fail">
            <span className="font-semibold">Evaluation error:</span> {log.evaluation_error}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export function RunDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<ErrorState | null>(null);
  const [data, setData] = useState<RunHistoryResponse | null>(null);

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    const controller = new AbortController();

    (async () => {
      setLoading(true);
      setError(null);
      try {
        const history = await api.getHistory(runId, controller.signal);
        if (cancelled) return;
        setData(history);
        // Auto-save to localStorage so this run appears in Dashboard recent runs,
        // even if it was generated in a different session or shared via URL.
        saveRecentRun({
          run_id: history.run.id,
          topic: history.run.topic,
          created_at: history.run.created_at,
        });
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        setError(errorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [runId]);

  if (!runId) {
    return (
      <div className="animate-fade-up">
        <PageHeader title="Run not found" description="No run ID was provided." />
        <div className="card-pad">
          <Link to="/" className="btn btn-ghost">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="Loading"
          title="Run detail"
        />
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="animate-fade-up">
        <PageHeader eyebrow="Error" title="Failed to load run" />
        <div
          role="alert"
          className="card-pad border-fail/30 bg-fail-dim"
        >
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-fail/15 text-fail">
              <TriangleAlert className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-ink">{error.title}</h3>
              <p className="mt-1 text-[13px] leading-5 text-muted">{error.detail}</p>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => window.location.reload()}
              className="btn btn-ghost btn-sm"
            >
              Retry
            </button>
            <Link to="/" className="btn btn-ghost btn-sm">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { run, drafts, revision_logs } = data;
  const elapsedMs = run.completed_at
    ? new Date(run.completed_at).getTime() - new Date(run.created_at).getTime()
    : null;
  const elapsedSec = elapsedMs ? Math.round(elapsedMs / 1000) : null;

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Run detail"
        title={run.topic}
        description={`${compactRunId(run.id)} · ${formatDateTime(run.created_at)}`}
        actions={
          <Link to="/history" className="btn btn-ghost">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" /> All runs
          </Link>
        }
      />

      {/* Run metadata card */}
      <div className="card-pad">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-ink">Run metadata</h2>
          <StatusBadge status={run.status} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl border border-line bg-raised/50 p-3">
            <div className="flex items-center gap-2 text-xs text-faint">
              <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Drafts</span>
            </div>
            <p className="mt-1.5 text-2xl font-bold text-ink">{run.attempt_count}</p>
          </div>
          <div className="rounded-xl border border-line bg-raised/50 p-3">
            <div className="flex items-center gap-2 text-xs text-faint">
              <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Retries</span>
            </div>
            <p className="mt-1.5 text-2xl font-bold text-ink">{revision_logs.length}</p>
          </div>
          <div className="rounded-xl border border-line bg-raised/50 p-3">
            <div className="flex items-center gap-2 text-xs text-faint">
              <Clock className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Duration</span>
            </div>
            <p className="mt-1.5 text-2xl font-bold text-ink">
              {elapsedSec ? `${elapsedSec}s` : "—"}
            </p>
          </div>
          <div className="rounded-xl border border-line bg-raised/50 p-3">
            <div className="flex items-center gap-2 text-xs text-faint">
              <Database className="h-3.5 w-3.5" aria-hidden="true" />
              <span>Model</span>
            </div>
            <p className="mt-1.5 truncate font-mono text-xs font-semibold text-ink">
              {run.model_name ?? "—"}
            </p>
          </div>
        </div>

        {run.error_detail && (
          <div className="mt-3 rounded-xl border border-fail/25 bg-fail-dim p-3 text-xs text-fail">
            <span className="font-semibold">Error:</span> {run.error_detail}
          </div>
        )}

        <div className="mt-4 grid gap-2 border-t border-line pt-4 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {run.learner_profile && (
            <div>
              <span className="text-faint">Learner profile</span>
              <p className="mt-0.5 text-ink">{run.learner_profile}</p>
            </div>
          )}
          {run.language && (
            <div>
              <span className="text-faint">Language</span>
              <p className="mt-0.5 text-ink">{run.language}</p>
            </div>
          )}
          {run.rubric_version && (
            <div>
              <span className="text-faint">Rubric version</span>
              <p className="mt-0.5 font-mono text-ink">{run.rubric_version}</p>
            </div>
          )}
          <div>
            <span className="text-faint">Max retries</span>
            <p className="mt-0.5 font-mono text-ink">{run.max_retries}</p>
          </div>
        </div>
      </div>

      {/* Revision timeline */}
      {revision_logs.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-ink">
            <FileText className="h-[18px] w-[18px] text-fail" aria-hidden="true" />
            Revision timeline
            <span className="chip ml-1">{revision_logs.length}</span>
          </h2>
          <div className="card-pad space-y-0">
            {revision_logs.map((log, idx) => (
              <RevisionLogCard key={log.id} log={log} index={idx} />
            ))}
          </div>
        </div>
      )}

      {/* Drafts */}
      <div className="mt-6">
        <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-ink">
          <Hash className="h-[18px] w-[18px] text-accent" aria-hidden="true" />
          All drafts
          <span className="chip ml-1">{drafts.length}</span>
        </h2>
        <div className="space-y-4">
          {drafts.map((draft, idx) => (
            <DraftCard key={draft.id} draft={draft} index={idx} total={drafts.length} />
          ))}
        </div>
      </div>

      {/* Footer actions */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-raised/50 p-4">
        <Link to="/history" className="btn btn-ghost">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> View all runs
        </Link>
        <Link to="/generate" className="btn btn-primary">
          <Sparkles className="h-4 w-4" aria-hidden="true" /> Generate another
        </Link>
      </div>
    </div>
  );
}
