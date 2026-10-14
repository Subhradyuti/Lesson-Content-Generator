import { History, RefreshCw, TriangleAlert } from "lucide-react";
import clsx from "clsx";

import type { RejectedAttempt, RevisionLog } from "../lib/types";
import { formatDateTime } from "../lib/utils";

export type RejectionSource = RejectedAttempt | RevisionLog;

interface RejectionLogProps {
  logs: RejectionSource[];
  className?: string;
}

function isRevisionLog(log: RejectionSource): log is RevisionLog {
  return "revision_instructions" in log && "attempt_number" in log && "created_at" in log;
}

function attemptLabel(log: RejectionSource): number {
  if (isRevisionLog(log)) return log.attempt_number;
  return log.attempt;
}

function failedChips(log: RejectionSource): string[] {
  if (isRevisionLog(log)) return log.failed_checkpoint_ids ?? [];
  return log.failed_checkpoint_ids ?? [];
}

function instructions(log: RejectionSource): string {
  if (isRevisionLog(log)) {
    const ri = log.revision_instructions;
    if (Array.isArray(ri)) return ri.join("\n");
    return ri ?? "";
  }
  return log.revision_instructions ?? "";
}

function evaluationError(log: RejectionSource): string | null | undefined {
  if (isRevisionLog(log)) return log.evaluation_error;
  return log.evaluation_error;
}

export function RejectionLog({ logs, className }: RejectionLogProps) {
  const sorted = [...logs].sort((a, b) => attemptLabel(a) - attemptLabel(b));

  return (
    <div className={clsx("card overflow-hidden", className)}>
      <div className="flex items-center gap-3 border-b border-line bg-raised/40 px-5 py-4 sm:px-6">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-warn-dim text-warn ring-1 ring-warn/25">
          <History className="h-5 w-5" aria-hidden="true" />
        </span>
        <div>
          <h3 className="text-sm font-semibold text-ink">Rejected attempts</h3>
          <p className="text-xs text-muted">
            Drafts that failed the rubric and were fed back for revision.
          </p>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        {sorted.length === 0 ? (
          <p className="text-sm text-muted">
            No rejected attempts — every draft passed on the first evaluation.
          </p>
        ) : (
          <ol className="relative space-y-5 border-l border-line pl-6">
            {sorted.map((log, index) => {
              const chips = failedChips(log);
              const instruction = instructions(log);
              const evalErr = evaluationError(log);
              return (
                <li key={index} className="relative">
                  <span
                    className="absolute -left-[31px] top-1 flex h-4 w-4 items-center justify-center rounded-full border border-warn/40 bg-canvas"
                    aria-hidden="true"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-warn" />
                  </span>

                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                      <RefreshCw className="h-4 w-4 text-warn" aria-hidden="true" />
                      Draft {attemptLabel(log)} rejected
                    </p>
                    {"created_at" in log && log.created_at && (
                      <span className="font-mono text-[11px] text-faint">
                        {formatDateTime(log.created_at)}
                      </span>
                    )}
                  </div>

                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {chips.length > 0 ? (
                      chips.map((id) => (
                        <span
                          key={id}
                          className="inline-flex items-center gap-1 rounded-md border border-fail/25 bg-fail-dim px-2 py-0.5 font-mono text-[11px] font-semibold text-fail"
                        >
                          <TriangleAlert className="h-3 w-3" aria-hidden="true" />
                          {id}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-faint">No checkpoint ids recorded.</span>
                    )}
                  </div>

                  {instruction && (
                    <p className="mt-2.5 rounded-lg border border-line bg-sunken/60 px-3 py-2.5 text-[13px] leading-5 text-muted">
                      <span className="font-semibold text-warn">Revision instructions: </span>
                      {instruction}
                    </p>
                  )}

                  {evalErr && (
                    <p className="mt-2 rounded-lg border border-fail/25 bg-fail-dim px-3 py-2 text-xs text-fail">
                      Evaluation error: {evalErr}
                    </p>
                  )}
                </li>
              );
            })}
          </ol>
        )}
      </div>
    </div>
  );
}
