import { NavLink, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { BookOpen } from "lucide-react";
import clsx from "clsx";

import { formatDate, compactRunId } from "../lib/utils";
import { loadRecentRuns } from "../lib/recentRuns";
import { StatusBadge } from "./StatusBadge";
import type { RunStatus } from "../lib/types";

interface LocalEntry {
  run_id: string;
  topic: string;
  created_at: string;
  status?: RunStatus;
}

export function RecentRuns({
  onNavigate,
}: {
  onNavigate: () => void;
}) {
  const [items, setItems] = useState<LocalEntry[]>([]);
  const location = useLocation();

  // Refresh whenever the route changes so newly generated runs appear.
  useEffect(() => {
    setItems(loadRecentRuns().slice(0, 5));
  }, [location.pathname]);

  const activeId = location.pathname.startsWith("/runs/")
    ? location.pathname.split("/")[2]
    : null;

  return (
    <div className="mt-8">
      <p className="px-2 text-[11px] font-semibold tracking-wider text-faint uppercase">
        Recent runs
      </p>
      <nav className="mt-2 space-y-0.5" aria-label="Recent runs">
        {items.length === 0 ? (
          <p className="px-2 pt-1 text-xs leading-5 text-faint">
            No runs yet. Generate your first lesson to see it here.
          </p>
        ) : (
          items.map((run) => (
            <NavLink
              key={run.run_id}
              to={`/runs/${run.run_id}`}
              onClick={onNavigate}
              className={({ isActive }) =>
                clsx(
                  "group flex items-center gap-2.5 rounded-xl px-2.5 py-2 transition-colors",
                  isActive || activeId === run.run_id
                    ? "bg-raised text-ink"
                    : "text-muted hover:bg-raised/60 hover:text-ink",
                )
              }
            >
              <span
                className={clsx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border",
                  run.status === "passed"
                    ? "border-pass/25 bg-pass-dim text-pass"
                    : run.status === "failed"
                      ? "border-fail/25 bg-fail-dim text-fail"
                      : "border-line bg-raised text-faint",
                )}
              >
                <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[13px] font-medium">{run.topic}</span>
                <span className="block font-mono text-[10px] text-faint">
                  {compactRunId(run.run_id)} · {formatDate(run.created_at)}
                </span>
              </span>
              {run.status && (
                <StatusBadge
                  status={run.status}
                  className="!py-0.5 !text-[10px]"
                  showIcon={false}
                />
              )}
            </NavLink>
          ))
        )}
      </nav>
    </div>
  );
}
