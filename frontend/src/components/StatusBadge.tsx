import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";
import type { RunStatus } from "../lib/types";

const STYLES: Record<RunStatus, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  passed:              { label: "Passed",          className: "border-pass/30 bg-pass-dim text-pass",  Icon: CheckCircle2 },
  failed:              { label: "Failed",           className: "border-fail/30 bg-fail-dim text-fail",  Icon: XCircle },
  failed_quality_gate: { label: "Quality gate",    className: "border-fail/30 bg-fail-dim text-fail",  Icon: XCircle },
  generation_error:    { label: "Gen error",        className: "border-warn/30 bg-warn-dim text-warn",  Icon: XCircle },
  evaluation_error:    { label: "Eval error",       className: "border-warn/30 bg-warn-dim text-warn",  Icon: XCircle },
  running:             { label: "Running",          className: "border-info/30 bg-info-dim text-info",  Icon: Loader2 },
  pending:             { label: "Pending",          className: "border-line bg-raised text-muted",      Icon: CircleDashed },
};

interface StatusBadgeProps {
  status: RunStatus;
  className?: string;
  showIcon?: boolean;
}

export function StatusBadge({ status, className, showIcon = true }: StatusBadgeProps) {
  const { label, className: tone, Icon } = STYLES[status] ?? STYLES.pending;
  return (
    <motion.span
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: "spring", stiffness: 200, damping: 15 }}
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        tone,
        className,
      )}
    >
      {showIcon && (
        <Icon
          className={clsx("h-3.5 w-3.5", status === "running" && "animate-spin-slow")}
          aria-hidden="true"
        />
      )}
      <span>{label}</span>
    </motion.span>
  );
}

export function PassFailBadge({ passed }: { passed: boolean }) {
  const tone = passed
    ? "border-pass/30 bg-pass-dim text-pass"
    : "border-fail/30 bg-fail-dim text-fail";
  const Icon = passed ? CheckCircle2 : XCircle;
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold",
        tone,
      )}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {passed ? "Rubric passed" : "Rubric failed"}
    </span>
  );
}
