import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Database,
  GitBranch,
  Link2,
  Plus,
  Sparkles,
  Timer,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import clsx from "clsx";

import { PageHeader } from "../components/PageHeader";
import { api, ApiError, NetworkError } from "../lib/api";
import { StatusBadge } from "../components/StatusBadge";
import { EmptyState } from "../components/Spinner";
import { LogoMark } from "../components/Logo";
import { compactRunId, timeAgo } from "../lib/utils";
import { loadRecentRuns, saveRecentRun, removeRecentRun, type RecentRun } from "../lib/recentRuns";
import type { LessonRunSummary, ReadyHealth } from "../lib/types";

type HealthState =
  | { kind: "checking" }
  | { kind: "ok"; ready: ReadyHealth }
  | { kind: "down"; message: string };

interface Stat {
  id: string;
  label: string;
  value: string;
  sub?: string;
  tone?: "pass" | "fail" | "accent" | "muted";
}

interface RunRowData {
  run: LessonRunSummary;
  local?: RecentRun;
}

function StatCard({ stat, index }: { stat: Stat; index: number }) {
  const valueColor =
    stat.tone === "pass"
      ? "text-pass"
      : stat.tone === "fail"
        ? "text-fail"
        : stat.tone === "accent"
          ? "text-accent"
          : "text-ink";
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className="card-pad flex flex-col"
    >
      <p className="text-xs font-medium tracking-wide text-faint uppercase">{stat.label}</p>
      <motion.p
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ delay: index * 0.1 + 0.2, type: "spring", stiffness: 200 }}
        className={clsx("mt-2 text-3xl font-bold tracking-tight", valueColor)}
      >
        {stat.value}
      </motion.p>
      {stat.sub && <p className="mt-1 text-xs text-muted">{stat.sub}</p>}
    </motion.div>
  );
}

function HealthCard() {
  const [state, setState] = useState<HealthState>({ kind: "checking" });

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    (async () => {
      try {
        await api.getLiveHealth(controller.signal);
        const ready = await api.getReadyHealth(controller.signal);
        if (cancelled) return;
        setState({
          kind: "ok",
          ready: ready.database ? ready : { status: "not_ready", database: false, details: {} },
        });
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === "AbortError")) return;
        const message =
          err instanceof NetworkError
            ? "Backend unreachable"
            : err instanceof ApiError
              ? `Backend error (${err.status})`
              : "Health check failed";
        setState({ kind: "down", message });
      }
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const online = state.kind === "ok";
  const ready = state.kind === "ok" && state.ready.database;

  return (
    <div className="card-pad">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="relative flex h-2.5 w-2.5" aria-hidden="true">
            <span
              className={clsx(
                "absolute inline-flex h-full w-full rounded-full animate-ping-dot",
                state.kind === "checking" ? "bg-warn" : online ? "bg-pass" : "bg-fail",
              )}
            />
            <span
              className={clsx(
                "relative inline-flex h-2.5 w-2.5 rounded-full",
                state.kind === "checking" ? "bg-warn" : online ? "bg-pass" : "bg-fail",
              )}
            />
          </span>
          <p className="text-sm font-semibold text-ink">Backend health</p>
        </div>
        <span className="chip">
          {state.kind === "checking" ? (
            <>
              <Activity className="h-3.5 w-3.5 text-warn" /> Checking…
            </>
          ) : online ? (
            <>
              <Wifi className="h-3.5 w-3.5 text-pass" /> Online
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5 text-fail" /> Offline
            </>
          )}
        </span>
      </div>

      <dl className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-line bg-raised/50 p-3">
          <dt className="font-mono text-[10px] tracking-wider text-faint uppercase">/health/live</dt>
          <dd className="mt-1 flex items-center gap-1.5 text-sm font-medium">
            <span className={clsx("h-1.5 w-1.5 rounded-full", online ? "bg-pass" : "bg-fail")} aria-hidden="true" />
            {online ? "OK" : "Unreachable"}
          </dd>
        </div>
        <div className="rounded-xl border border-line bg-raised/50 p-3">
          <dt className="font-mono text-[10px] tracking-wider text-faint uppercase">/health/ready</dt>
          <dd className="mt-1 flex items-center gap-1.5 text-sm font-medium">
            <span className={clsx("h-1.5 w-1.5 rounded-full", ready ? "bg-pass" : "bg-fail")} aria-hidden="true" />
            {ready ? "Ready" : "Degraded"}
          </dd>
        </div>
        <div className="rounded-xl border border-line bg-raised/50 p-3">
          <dt className="font-mono text-[10px] tracking-wider text-faint uppercase">Database</dt>
          <dd className="mt-1 flex items-center gap-1.5 text-sm font-medium">
            <Database className="h-3.5 w-3.5 text-muted" aria-hidden="true" />
            {state.kind === "ok" ? (state.ready.database ? "Connected" : "Unreachable") : "—"}
          </dd>
        </div>
      </dl>
      {state.kind === "down" && (
        <p className="mt-3 rounded-lg border border-fail/25 bg-fail-dim px-3 py-2 text-xs text-fail">
          {state.message} — check that FastAPI is running and VITE_API_BASE_URL / the Vite
          proxy point at it.
        </p>
      )}
    </div>
  );
}

export function DashboardPage() {
  const [rows, setRows] = useState<RunRowData[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [noData, setNoData] = useState(false);

  // Track-by-ID state
  const [trackId, setTrackId] = useState("");
  const [trackLoading, setTrackLoading] = useState(false);
  const [trackError, setTrackError] = useState<string | null>(null);
  const [showTrack, setShowTrack] = useState(false);

  const refreshRows = async (signal?: AbortSignal) => {
    const recent = loadRecentRuns();
    setRunsLoading(true);
    setRunsError(null);
    setNoData(false);
    if (recent.length === 0) {
      setRows([]);
      setNoData(true);
      setRunsLoading(false);
      return;
    }

    const results = await Promise.allSettled(
      recent.map((r) => api.getRun(r.run_id, signal)),
    );
    if (signal?.aborted) return;

    const live = new Map<string, LessonRunSummary>();
    for (const res of results) {
      if (res.status === "fulfilled") live.set(res.value.run_id, res.value);
    }

    setRows(
      recent.flatMap((local) => {
        const run = live.get(local.run_id);
        return run ? [{ run, local }] : [];
      }),
    );
    if (live.size === 0) {
      setRunsError(
        "None of the locally tracked runs could be found on the backend. They may belong to a different database.",
      );
    }
    setRunsLoading(false);
  };

  useEffect(() => {
    const controller = new AbortController();
    refreshRows(controller.signal);
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleRemove = (runId: string) => {
    removeRecentRun(runId);
    setRows((prev) => prev.filter((r) => r.run.run_id !== runId));
  };

  const handleTrack = async () => {
    const id = trackId.trim();
    if (!id) return;
    setTrackLoading(true);
    setTrackError(null);
    try {
      const run = await api.getRun(id);
      saveRecentRun({ run_id: run.run_id, topic: run.topic, created_at: run.created_at });
      setRows((prev) => {
        if (prev.some((r) => r.run.run_id === run.run_id)) return prev;
        return [{ run, local: { run_id: run.run_id, topic: run.topic, created_at: run.created_at } }, ...prev];
      });
      setTrackId("");
      setShowTrack(false);
    } catch (err) {
      setTrackError(
        err instanceof ApiError
          ? err.status === 404
            ? "Run not found — check the ID and that the backend DB is correct."
            : `Backend error (${err.status}): ${err.message}`
          : err instanceof NetworkError
            ? "Backend unreachable."
            : "Unexpected error.",
      );
    } finally {
      setTrackLoading(false);
    }
  };

  const stats = useMemo<Stat[]>(() => {
    const total = rows.length;
    const passed = rows.filter((r) => r.run.status === "passed").length;
    const failed = rows.filter(
      (r) => r.run.status === "failed_quality_gate" || r.run.status === "generation_error" || r.run.status === "evaluation_error",
    ).length;
    const running = rows.filter((r) => r.run.status === "running").length;
    const totalRetries = rows.reduce((acc, r) => acc + (r.run.retry_count ?? 0), 0);
    return [
      { id: "total", label: "Runs tracked", value: String(total), tone: "accent" },
      {
        id: "passed",
        label: "Passed",
        value: String(passed),
        tone: "pass",
        sub: running > 0 ? `${running} still running` : undefined,
      },
      { id: "failed", label: "Failed / error", value: String(failed), tone: "fail" },
      { id: "retries", label: "Retries total", value: String(totalRetries), tone: "muted" },
    ];
  }, [rows]);

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Workspace"
        title="Dashboard"
        description="Generate, evaluate and refine beginner lessons with a strict 14-point binary rubric — all routed through the live FastAPI backend."
        actions={
          <Link to="/generate" className="btn btn-primary">
            <Sparkles className="h-4 w-4" aria-hidden="true" /> New lesson
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((s, idx) => (
          <StatCard key={s.id} stat={s} index={idx} />
        ))}
      </div>

      <div className="mt-5">
        <HealthCard />
      </div>

      {/* Recent runs */}
      <div className="mt-10">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
            <Timer className="h-[18px] w-[18px] text-accent" aria-hidden="true" /> Recent runs
          </h2>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => { setShowTrack((v) => !v); setTrackError(null); }}
              className="btn btn-ghost btn-sm"
              title="Track an existing run by ID"
            >
              <Link2 className="h-3.5 w-3.5" aria-hidden="true" /> Track by ID
            </button>
            <Link to="/history" className="link-link text-sm">
              View all <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            </Link>
          </div>
        </div>

        {/* Track-by-ID panel */}
        <AnimatePresence>
          {showTrack && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 overflow-hidden"
            >
              <div className="card-pad border-accent/20 bg-raised/60">
                <p className="text-sm font-semibold text-ink">Track a run from this backend</p>
                <p className="mt-0.5 text-xs text-muted">
                  Paste any run ID from the backend database to add it to your recent runs list.
                </p>
                <div className="mt-3 flex gap-2">
                  <input
                    type="text"
                    className="input font-mono text-xs"
                    placeholder="e.g. b3039d09-b3dd-45c6-ac10-29cae60ebc26"
                    value={trackId}
                    onChange={(e) => setTrackId(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleTrack()}
                    aria-label="Run ID to track"
                  />
                  <button
                    type="button"
                    className="btn btn-primary btn-sm shrink-0"
                    onClick={handleTrack}
                    disabled={trackLoading || !trackId.trim()}
                  >
                    {trackLoading ? (
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" aria-hidden="true" />
                    ) : (
                      <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    Add
                  </button>
                </div>
                {trackError && (
                  <p className="mt-2 text-xs text-fail">{trackError}</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {runsLoading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="card-pad shimmer-bg animate-shimmer h-36" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={GitBranch}
            title={noData ? "No runs tracked on this device yet" : "No persisted runs found"}
            description={
              noData
                ? "Generate a lesson or paste a run ID above to start tracking."
                : "Runs tracked here were not found on the backend — they may belong to a different database."
            }
            action={
              <Link to="/generate" className="btn btn-primary">
                <Sparkles className="h-4 w-4" aria-hidden="true" /> Generate a lesson
              </Link>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            {rows.map(({ run, local }, idx) => (
              <motion.div
                key={run.run_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.3 }}
                className="group relative"
              >
                <Link
                  to={`/runs/${run.run_id}`}
                  className="card card-hover block p-5"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-ink">{run.topic}</p>
                      <p className="mt-0.5 font-mono text-xs text-faint">
                        {compactRunId(run.run_id)}
                      </p>
                    </div>
                    <StatusBadge status={run.status} />
                  </div>

                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                    <span className="inline-flex items-center gap-1.5">
                      <GitBranch className="h-3.5 w-3.5 text-faint" aria-hidden="true" />
                      {run.draft_count ?? 0} draft{(run.draft_count ?? 0) === 1 ? "" : "s"}
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <Activity className="h-3.5 w-3.5 text-faint" aria-hidden="true" />
                      {run.retry_count ?? 0} retr{(run.retry_count ?? 0) === 1 ? "y" : "ies"}
                    </span>
                    <span className="ml-auto text-faint">
                      {timeAgo(run.completed_at ?? local?.created_at)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-1.5 text-xs font-medium text-accent opacity-0 transition-opacity group-hover:opacity-100">
                    Open run <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                  </div>
                </Link>
                {/* Remove from tracking */}
                <button
                  type="button"
                  onClick={(e) => { e.preventDefault(); handleRemove(run.run_id); }}
                  className="absolute right-3 top-3 hidden rounded-lg p-1 text-faint hover:bg-raised hover:text-ink group-hover:flex"
                  title="Remove from recent runs"
                  aria-label={`Remove ${run.topic} from recent runs`}
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </motion.div>
            ))}
          </div>
        )}

        {runsError && (
          <p className="mt-3 rounded-xl border border-fail/25 bg-fail-dim px-4 py-2.5 text-sm text-fail">
            {runsError}
          </p>
        )}
      </div>

      {/* How it works */}
      <div className="card-pad mt-10 border-accent/15 bg-gradient-to-br from-surface to-raised/60">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-ink">
          <LogoMark className="h-8 w-8" /> How Lesson Forge works
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {[
            {
              step: "01",
              title: "Plan & generate",
              body: "Plans a structured beginner lesson, then drafts it with the configured LLM provider.",
            },
            {
              step: "02",
              title: "Evaluate against 14 checkpoints",
              body: "A strict binary rubric scores accuracy, assumptions, coverage, clarity and alignment.",
            },
            {
              step: "03",
              title: "Revise until it passes",
              body: "Failed checkpoints drive targeted revision instructions. Runs stop early on success or when retries are exhausted.",
            },
          ].map(({ step, title, body }) => (
            <div key={step} className="relative rounded-xl border border-line bg-sunken/60 p-4">
              <span className="font-mono text-xs font-bold text-accent">{step}</span>
              <p className="mt-1.5 text-sm font-semibold text-ink">{title}</p>
              <p className="mt-1 text-[13px] leading-5 text-muted">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
