import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  FileSearch,
  GitBranch,
  History as HistoryIcon,
  SearchX,
  Sparkles,
} from "lucide-react";
import { motion } from "framer-motion";

import { PageHeader } from "../components/PageHeader";
import { EmptyState } from "../components/Spinner";
import { StatusBadge } from "../components/StatusBadge";
import { api, ApiError, NetworkError } from "../lib/api";
import { loadRecentRuns } from "../lib/recentRuns";
import { compactRunId, formatDateTime, timeAgo } from "../lib/utils";
import { toast } from "../components/Toast";
import type { LessonRunSummary } from "../lib/types";

type LookupState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "found"; summary: LessonRunSummary }
  | { kind: "not-found"; message: string };

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function HistoryPage() {
  const [lookupId, setLookupId] = useState("");
  const [lookup, setLookup] = useState<LookupState>({ kind: "idle" });
  const [rows, setRows] = useState<LessonRunSummary[]>([]);
  const [loadingRows, setLoadingRows] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    (async () => {
      const recent = loadRecentRuns();
      if (recent.length === 0) {
        setRows([]);
        setLoadingRows(false);
        return;
      }
      const results = await Promise.allSettled(
        recent.map((r) => api.getRun(r.run_id, controller.signal)),
      );
      if (cancelled) return;
      const ok = results.flatMap((r) => (r.status === "fulfilled" ? [r.value] : []));
      setRows(ok);
      setLoadingRows(false);
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const onLookup = async (e: FormEvent) => {
    e.preventDefault();
    const id = lookupId.trim();
    if (!id) return;
    if (!UUID_RE.test(id)) {
      setLookup({
        kind: "not-found",
        message: "That does not look like a valid run UUID (e.g. 6502cbe8-…).",
      });
      return;
    }
    setLookup({ kind: "loading" });
    try {
      const summary = await api.getRun(id);
      setLookup({ kind: "found", summary });
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setLookup({
          kind: "not-found",
          message: "No run found with that ID in the backend database.",
        });
      } else if (err instanceof NetworkError) {
        setLookup({ kind: "not-found", message: err.message });
        toast.error("Backend unreachable", err.message);
      } else {
        setLookup({
          kind: "not-found",
          message: err instanceof Error ? err.message : "Lookup failed.",
        });
      }
    }
  };

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Archive"
        title="Run history"
        description="Runs created from this device, re-validated against the backend, plus direct lookup of any run by its UUID."
        icon={HistoryIcon}
      />

      {/* Lookup by run id */}
      <div className="card-pad mb-8">
        <p className="text-sm font-semibold text-ink">Look up a run by ID</p>
        <p className="mt-0.5 text-xs text-muted">
          The backend has no list endpoint, so any existing run can be opened directly by its
          UUID.
        </p>
        <form onSubmit={onLookup} className="mt-3 flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <FileSearch
              className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-faint"
              aria-hidden="true"
            />
            <input
              type="text"
              value={lookupId}
              onChange={(e) => setLookupId(e.target.value)}
              placeholder="6502cbe8-24d6-46e3-b1ba-6d2d0f89d83a"
              className="input pl-9 font-mono text-[13px]"
              aria-label="Run ID"
            />
          </div>
          <button
            type="submit"
            className="btn btn-ghost shrink-0"
            disabled={lookup.kind === "loading"}
          >
            {lookup.kind === "loading" ? "Looking up…" : "Open run"}
          </button>
        </form>

        {lookup.kind === "found" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-pass/25 bg-pass-dim px-4 py-3"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">
                {lookup.summary.topic}
              </p>
              <p className="font-mono text-xs text-faint">
                {lookup.summary.run_id} · {formatDateTime(lookup.summary.created_at)}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge status={lookup.summary.status} />
              <Link to={`/runs/${lookup.summary.run_id}`} className="btn btn-primary btn-sm">
                Open <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Link>
            </div>
          </motion.div>
        )}

        {lookup.kind === "not-found" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            role="alert"
            className="mt-3 flex items-start gap-2.5 rounded-xl border border-warn/25 bg-warn-dim px-4 py-3 text-sm text-warn"
          >
            <SearchX className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            {lookup.message}
          </motion.div>
        )}
      </div>

      {/* Local run list */}
      <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-ink">
        <GitBranch className="h-[18px] w-[18px] text-accent" aria-hidden="true" /> Runs from this
        device
      </h2>

      {loadingRows ? (
        <div className="space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="card-pad shimmer-bg animate-shimmer h-20" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={HistoryIcon}
          title="No runs recorded on this device"
          description="Generate a lesson and its run will appear here. Existing backend runs can always be opened with the lookup above."
          action={
            <Link to="/generate" className="btn btn-primary">
              <Sparkles className="h-4 w-4" aria-hidden="true" /> Generate a lesson
            </Link>
          }
        />
      ) : (
        <ul className="space-y-3">
          {rows.map((run, idx) => (
            <motion.li
              key={run.run_id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05, duration: 0.3 }}
            >
              <Link
                to={`/runs/${run.run_id}`}
                className="card card-hover group flex items-center gap-4 p-4 sm:p-5"
              >
                <span
                  className={
                    "hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl border sm:flex " +
                    (run.status === "passed"
                      ? "border-pass/25 bg-pass-dim text-pass"
                      : run.status === "failed"
                        ? "border-fail/25 bg-fail-dim text-fail"
                        : "border-line bg-raised text-faint")
                  }
                >
                  <GitBranch className="h-[18px] w-[18px]" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-ink">{run.topic}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-[11px] text-faint">
                    <span>{compactRunId(run.run_id)}</span>
                    <span>{run.draft_count} draft{run.draft_count === 1 ? "" : "s"}</span>
                    <span>{run.retry_count} retr{run.retry_count === 1 ? "y" : "ies"}</span>
                    <span>{timeAgo(run.completed_at ?? run.created_at)}</span>
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2.5">
                  <StatusBadge status={run.status} />
                  <ArrowRight
                    className="h-4 w-4 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                    aria-hidden="true"
                  />
                </div>
              </Link>
            </motion.li>
          ))}
        </ul>
      )}
    </div>
  );
}
