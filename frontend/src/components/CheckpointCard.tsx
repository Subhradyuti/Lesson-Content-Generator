import { AlertTriangle, Check, Wrench, X } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import type { EvaluationCheck } from "../lib/types";

interface CheckpointStatusIconProps {
  status: EvaluationCheck["status"];
}

export function CheckpointStatusIcon({ status }: CheckpointStatusIconProps) {
  if (status === "PASS") {
    return (
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-pass-dim text-pass ring-1 ring-pass/25">
        <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
      </div>
    );
  }
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-fail-dim text-fail ring-1 ring-fail/25">
      <X className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
    </div>
  );
}

export interface CheckpointCardProps {
  check: EvaluationCheck;
  index?: number;
  defaultOpen?: boolean;
}

export function CheckpointCard({ check, index, defaultOpen = false }: CheckpointCardProps) {
  const passed = check.status === "PASS";

  // The API returns "id" for the checkpoint identifier (e.g. "ACC-01").
  const checkId = check.id;

  return (
    <motion.details
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: (index ?? 0) * 0.025, duration: 0.2 }}
      className={clsx(
        "group rounded-xl border transition-colors",
        passed
          ? "border-line bg-raised/40 open:border-pass/30 open:bg-pass-dim/10"
          : "border-fail/30 bg-fail-dim/10 open:border-fail/45",
      )}
      open={defaultOpen || !passed}
    >
      {/* ── Summary row (always visible) ── */}
      <summary className="flex cursor-pointer list-none items-center gap-3 rounded-xl px-4 py-3 select-none [&::-webkit-details-marker]:hidden">
        <CheckpointStatusIcon status={check.status} />

        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-2">
            {index !== undefined && (
              <span className="font-mono text-[11px] font-bold text-faint">
                {String(index + 1).padStart(2, "0")}
              </span>
            )}
            <span
              className={clsx(
                "font-mono text-xs font-bold tracking-wide",
                passed ? "text-pass" : "text-fail",
              )}
            >
              {checkId}
            </span>
          </p>
        </div>

        <span
          className={clsx(
            "shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold tracking-widest uppercase",
            passed ? "bg-pass-dim text-pass" : "bg-fail-dim text-fail",
          )}
        >
          {check.status}
        </span>
      </summary>

      {/* ── Expanded body ── */}
      <div className="border-t border-line/60 px-4 pb-4 pt-3">
        <div className="space-y-3.5">
          {/* Reason */}
          <div>
            <p className="mb-1.5 text-[10px] font-semibold tracking-widest text-faint uppercase">
              Reasoning
            </p>
            <p className="text-[13px] leading-6 text-muted">{check.reason}</p>
          </div>

          {/* Evidence */}
          {check.evidence && (
            <div>
              <p className="mb-1.5 text-[10px] font-semibold tracking-widest text-faint uppercase">
                Evidence
              </p>
              <p
                className={clsx(
                  "rounded-lg border px-3 py-2.5 text-xs leading-5",
                  passed
                    ? "border-line bg-sunken text-muted"
                    : "border-fail/20 bg-fail-dim/30 text-fail/90",
                )}
              >
                {check.evidence}
              </p>
            </div>
          )}

          {/* Required fix — only shown on FAIL */}
          {!passed && check.required_fix && (
            <div>
              <p className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold tracking-widest text-warn uppercase">
                <Wrench className="h-3 w-3" aria-hidden="true" />
                Required fix
              </p>
              <p className="rounded-lg border border-warn/20 bg-warn-dim/30 px-3 py-2.5 text-xs leading-5 text-warn/90">
                {check.required_fix}
              </p>
            </div>
          )}

          {/* Pass indicator */}
          {passed && (
            <div className="flex items-center gap-1.5 text-xs font-medium text-pass/80">
              <AlertTriangle className="h-3.5 w-3.5 opacity-0" aria-hidden="true" />
              All criteria met for this checkpoint.
            </div>
          )}
        </div>
      </div>
    </motion.details>
  );
}
