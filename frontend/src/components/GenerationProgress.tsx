import { useEffect, useState } from "react";
import {
  Check,
  FileText,
  ListChecks,
  PenLine,
  RefreshCcw,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import clsx from "clsx";

interface Step {
  id: string;
  label: string;
  description: string;
  duration: [number, number];
  Icon: typeof PenLine;
}

const BASE = {
  planning: {
    label: "Planning the lesson",
    description: "Structuring sections, scope, and learner assumptions…",
    Icon: PenLine,
  },
  generating: {
    label: "Generating draft",
    description: "Writing the beginner lesson content…",
    Icon: FileText,
  },
  evaluating: {
    label: "Evaluating against rubric",
    description: "Scoring 14 binary checkpoints with strict evidence…",
    Icon: ListChecks,
  },
  revising: {
    label: "Revising draft",
    description: "Applying revision instructions from failed checkpoints…",
    Icon: RefreshCcw,
  },
} as const;

function buildSteps(maxRetries: number): Step[] {
  const widths: [number, number][] = [
    [1600, 4500],
    [3500, 9000],
    [4500, 11000],
  ];
  const plan: Step = { id: "planning", ...BASE.planning, duration: widths[0] };
  const gen: Step = { id: "generating", ...BASE.generating, duration: widths[1] };
  const evals: Step[] = Array.from(
    { length: Math.min(Math.max(maxRetries, 0), 4) + 1 },
    (_, i) => {
      const base = i === 0 ? BASE.evaluating : BASE.revising;
      return {
        id: i === 0 ? "evaluating" : `revising-${i}`,
        label: i === 0 ? BASE.evaluating.label : `Revising draft (round ${i})`,
        description: base.description,
        duration: widths[Math.min(i, 2)],
        Icon: base.Icon,
      };
    },
  );
  const finalize: Step = {
    id: "finalizing",
    label: "Finalizing run",
    description: "Persisting drafts, evaluations and revision logs…",
    duration: [800, 2500],
    Icon: ShieldCheck,
  };
  return [plan, gen, ...evals, finalize];
}

export function GenerationProgress({
  topic,
  maxRetries,
  elapsedMs,
}: {
  topic: string;
  maxRetries: number;
  elapsedMs: number;
}) {
  const [current, setCurrent] = useState(0);

  const steps = buildSteps(maxRetries);
  const elapsedSeconds = Math.max(0, Math.floor(elapsedMs / 1000));

  // The POST endpoint is synchronous, so we animate an honest staged
  // progression while the request is in flight.
  useEffect(() => {
    let cancelled = false;
    let timeout: ReturnType<typeof setTimeout> | undefined;

    const schedule = (index: number) => {
      if (cancelled || index >= steps.length) return;
      const [min, max] = steps[index].duration;
      const delay = min + Math.random() * (max - min);
      timeout = setTimeout(() => {
        if (cancelled) return;
        setCurrent(index + 1);
        schedule(index + 1);
      }, delay);
    };
    setCurrent(0);
    schedule(0);
    return () => {
      cancelled = true;
      if (timeout) clearTimeout(timeout);
    };
  }, [steps.length, maxRetries]);

  const done = current >= steps.length;

  return (
    <div className="card-pad w-full">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-ink">
            {done ? "Finishing up…" : "Running the pipeline"}
          </h3>
          <p className="mt-0.5 truncate text-xs text-muted">{topic}</p>
        </div>
        <span className="chip shrink-0 font-mono">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" aria-hidden="true" />
          {elapsedSeconds}s
        </span>
      </div>

      {/* Indeterminate progress bar */}
      <div
        className="mt-4 h-1.5 overflow-hidden rounded-full bg-raised"
        role="progressbar"
        aria-label="Generation progress"
      >
        <div
          className="h-full w-1/3 rounded-full bg-gradient-to-r from-accent-deep via-accent to-accent-strong"
          style={{
            animation: "indeterminate-slide 1.6s ease-in-out infinite",
          }}
        />
      </div>
      <style>{`@keyframes indeterminate-slide{0%{transform:translateX(-110%)}50%{transform:translateX(260%)}100%{transform:translateX(460%)}}`}</style>

      <ol className="mt-5 space-y-1" aria-label="Pipeline stages">
        {steps.map((step, index) => {
          const state =
            index < current ? "done" : index === current ? "active" : "waiting";
          const Icon = step.Icon;
          return (
            <li key={step.id} className="flex items-start gap-3 py-1.5">
              <span
                className={clsx(
                  "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border transition-colors duration-300",
                  state === "done" && "border-pass/30 bg-pass-dim text-pass",
                  state === "active" && "border-accent/40 bg-accent/10 text-accent",
                  state === "waiting" && "border-line bg-raised text-faint",
                )}
              >
                {state === "done" ? (
                  <Check className="h-4 w-4" strokeWidth={2.5} aria-hidden="true" />
                ) : state === "active" ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Icon className="h-4 w-4" aria-hidden="true" />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p
                  className={clsx(
                    "text-[13px] font-medium transition-colors",
                    state === "active"
                      ? "text-ink"
                      : state === "done"
                        ? "text-pass"
                        : "text-faint",
                  )}
                >
                  {step.label}
                </p>
                <p className="truncate text-xs text-faint">{step.description}</p>
              </div>
            </li>
          );
        })}
      </ol>

      <p className="mt-4 rounded-lg border border-line bg-sunken/60 px-3 py-2 text-[11px] leading-4 text-faint">
        A single run can take 1–3 minutes. Reaching all 14 passing checkpoints ends
        the run early.
      </p>
    </div>
  );
}

