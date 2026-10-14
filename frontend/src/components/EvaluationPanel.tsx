import { CheckCircle2, ShieldCheck, XCircle } from "lucide-react";
import clsx from "clsx";

import { CheckpointCard } from "./CheckpointCard";
import { PassFailBadge } from "./StatusBadge";
import type { Evaluation, EvaluationCheck } from "../lib/types";

interface EvaluationPanelProps {
  evaluation: Evaluation;
  /** Attempt round, e.g. 1 for the first draft. Label appears in the header. */
  roundLabel?: string;
  className?: string;
}

/** Adapts the wire shape (degenerate score / missing evidence) defensively. */
export function normalizeCheck(check: EvaluationCheck): EvaluationCheck {
  return {
    ...check,
    status: check.status === "PASS" ? "PASS" : "FAIL",
  };
}

function CountPill({
  passed,
  count,
}: {
  passed: boolean;
  count: number;
}) {
  return (
    <div
      className={clsx(
        "flex items-center gap-2 rounded-xl border px-3 py-2",
        passed ? "border-pass/25 bg-pass-dim" : "border-fail/25 bg-fail-dim",
      )}
    >
      {passed ? (
        <CheckCircle2 className="h-4 w-4 text-pass" aria-hidden="true" />
      ) : (
        <XCircle className="h-4 w-4 text-fail" aria-hidden="true" />
      )}
      <div>
        <p className={clsx("text-base leading-none font-bold", passed ? "text-pass" : "text-fail")}>
          {count}
        </p>
        <p className="text-[10px] tracking-wider text-faint uppercase">
          {passed ? "passed" : "failed"}
        </p>
      </div>
    </div>
  );
}

export function EvaluationPanel({
  evaluation,
  roundLabel,
  className,
}: EvaluationPanelProps) {
  const checks = evaluation.checks.map(normalizeCheck);
  const passedCount = checks.filter((c) => c.status === "PASS").length;
  const failedCount = checks.filter((c) => c.status === "FAIL").length;

  return (
    <div className={clsx("card overflow-hidden", className)}>
      <div className="border-b border-line bg-raised/40 px-5 pt-5 pb-4 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <span
              className={clsx(
                "flex h-10 w-10 items-center justify-center rounded-xl",
                evaluation.overall_pass
                  ? "bg-pass-dim text-pass ring-1 ring-pass/25"
                  : "bg-fail-dim text-fail ring-1 ring-fail/25",
              )}
            >
              <ShieldCheck className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <p className="text-sm font-semibold text-ink">
                {roundLabel ?? "Evaluation"}
                <span className="ml-2 font-mono text-xs font-medium text-faint">
                  {evaluation.rubric_version}
                </span>
              </p>
              <p className="mt-0.5 text-xs text-muted">
                {checks.length} checkpoints · binary scoring
              </p>
            </div>
          </div>
          <PassFailBadge passed={evaluation.overall_pass} />
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <CountPill passed count={passedCount} />
          <CountPill passed={false} count={failedCount} />
        </div>
      </div>

      <div className="space-y-2.5 p-5 sm:p-6">
        {checks.map((check, i) => (
          <CheckpointCard key={`${check.id}-${i}`} check={check} index={i} />
        ))}
      </div>
    </div>
  );
}
