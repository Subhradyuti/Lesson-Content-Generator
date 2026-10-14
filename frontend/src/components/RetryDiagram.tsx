import { Fragment } from "react";
import {
  CheckCircle2,
  GitBranch,
  Loader2,
  XCircle,
} from "lucide-react";
import clsx from "clsx";

import type { HistoryDraft, LessonRunSummary } from "../lib/types";

interface RetryDiagramProps {
  run: LessonRunSummary;
  drafts: HistoryDraft[];
  selectedAttempt: number;
  onSelect: (attempt: number) => void;
}

interface DraftSummary {
  attempt: number;
  passed?: boolean;
  hasEval: boolean;
}

function parseOverallPass(draft: HistoryDraft): boolean | undefined {
  const ev = draft.evaluations?.[0];
  if (!ev) return undefined;
  // evaluation_json is a JSON column: the backend may return it already parsed.
  const raw: unknown =
    typeof ev.evaluation_json === "string"
      ? (() => { try { return JSON.parse(ev.evaluation_json); } catch { return undefined; } })()
      : ev.evaluation_json;
  if (raw && typeof raw === "object") {
    const overall = (raw as { overall_pass?: unknown }).overall_pass;
    if (typeof overall === "boolean") return overall;
  }
  return undefined;
}

function draftSummary(drafts: HistoryDraft[]): DraftSummary[] {
  return drafts.map((d) => ({
    attempt: d.attempt_number,
    hasEval: (d.evaluations?.length ?? 0) > 0,
    passed: parseOverallPass(d),
  }));
}

const MODE_TEXT: Record<string, string> = {
  passed: "Run ended — a draft passed all checkpoints",
  failed: "Run ended — retries exhausted",
  running: "In progress…",
  pending: "This run was not found in the current backend database",
};

export function RetryDiagram({
  run,
  drafts,
  selectedAttempt,
  onSelect,
}: RetryDiagramProps) {
  const attempts = draftSummary(drafts);
  const totalSteps = Math.max(run.draft_count ?? 0, attempts.length, 1);

  return (
    <div className="card-pad">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-ink">
          Retry pipeline{" "}
          <span className="ml-1 font-normal text-muted">
            — {attempts.length} draft{attempts.length === 1 ? "" : "s"} across this run
          </span>
        </p>
        <span className="chip">
          {run.status === "passed" ? (
            <>
              <CheckCircle2 className="h-3.5 w-3.5 text-pass" aria-hidden="true" /> Passed
            </>
          ) : run.status === "failed" ? (
            <>
              <XCircle className="h-3.5 w-3.5 text-fail" aria-hidden="true" /> Failed
            </>
          ) : (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" aria-hidden="true" />
              {MODE_TEXT[run.status] ?? "In progress"}
            </>
          )}
        </span>
      </div>

      <div className="mt-5 flex items-center">
        {Array.from({ length: Math.min(totalSteps, 6) }).map((_, i) => {
          const draft = attempts.find((a) => a.attempt === i);
          const isLast = i === Math.min(totalSteps, 6) - 1;
          const state: "draft" | "passed" | "failed" | "empty" = !draft
            ? "empty"
            : draft.passed === true
              ? "passed"
              : draft.passed === false
                ? "failed"
                : "draft";
          const selected = selectedAttempt === i;

          return (
            <Fragment key={i}>
              <button
                type="button"
                onClick={() => draft && onSelect(draft.attempt)}
                disabled={!draft}
                className={clsx(
                  "flex shrink-0 flex-col items-center gap-1.5 transition-transform",
                  draft && "cursor-pointer hover:-translate-y-0.5",
                  !draft && "cursor-default opacity-45",
                )}
                aria-label={
                  draft ? `Select draft ${draft.attempt}` : "No draft for this attempt"
                }
              >
                <span
                  className={clsx(
                    "flex h-10 w-10 items-center justify-center rounded-xl border-2 transition-all",
                    state === "empty" && "border-dashed border-line bg-sunken/40 text-faint",
                    state === "draft" && "border-accent/40 bg-accent/10 text-accent",
                    state === "passed" && "border-pass/40 bg-pass-dim text-pass",
                    state === "failed" && "border-fail/40 bg-fail-dim text-fail",
                    selected && "ring-2 ring-accent/40 ring-offset-2 ring-offset-canvas",
                  )}
                >
                  {state === "empty" ? (
                    <span className="h-2 w-2 rounded-full bg-line" />
                  ) : state === "passed" ? (
                    <CheckCircle2 className="h-5 w-5" strokeWidth={2.25} aria-hidden="true" />
                  ) : state === "failed" ? (
                    <XCircle className="h-5 w-5" strokeWidth={2.25} aria-hidden="true" />
                  ) : (
                    <GitBranch className="h-5 w-5" aria-hidden="true" />
                  )}
                </span>
                <span className="font-mono text-[10px] font-semibold text-faint">
                  D{i}
                </span>
              </button>

              {!isLast && (
                <div
                  className={clsx(
                    "h-0.5 flex-1 rounded-full",
                    state === "failed" ? "bg-fail/40" : "bg-line",
                  )}
                  aria-hidden="true"
                />
              )}
            </Fragment>
          );
        })}
      </div>

      <p className="mt-4 text-xs leading-5 text-faint">
        {MODE_TEXT[run.status] ?? "Pipeline overview — click a draft to inspect it."}{" "}
        Retries are bounded by the max_retries configured per request.
      </p>
    </div>
  );
}