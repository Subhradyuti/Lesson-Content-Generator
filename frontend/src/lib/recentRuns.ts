/**
 * Session-local tracking of recent runs.
 *
 * The backend exposes no list endpoint, so the sidebar keeps a local record
 * of run IDs created in this browser. Each run's *status and topic* are
 * re-validated against the backend when the dashboard/list is viewed, which
 * keeps the list honest without inventing API capabilities.
 */

import type { LessonRunSummary } from "../lib/types";

const STORAGE_KEY = "lesson-forge.recent-runs.v1";
const MAX_ITEMS = 8;

export interface RecentRun {
  run_id: string;
  topic: string;
  created_at: string;
}

export function loadRecentRuns(): RecentRun[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (r): r is RecentRun =>
          !!r &&
          typeof r === "object" &&
          typeof (r as RecentRun).run_id === "string" &&
          typeof (r as RecentRun).topic === "string",
      )
      .slice(0, MAX_ITEMS);
  } catch {
    return [];
  }
}

export function saveRecentRun(run: { run_id: string; topic: string; created_at?: string }): void {
  try {
    const next: RecentRun = {
      run_id: run.run_id,
      topic: run.topic,
      created_at: run.created_at ?? new Date().toISOString(),
    };
    const existing = loadRecentRuns().filter((r) => r.run_id !== run.run_id);
    const merged = [next, ...existing].slice(0, MAX_ITEMS);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  } catch {
    // Storage may be unavailable (private mode) — silently degrade.
  }
}

export function removeRecentRun(runId: string): void {
  try {
    const next = loadRecentRuns().filter((r) => r.run_id !== runId);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    // ignore
  }
}

/**
 * Enriches locally-stored recent runs with live status from the backend.
 * Runs that no longer exist on the backend are dropped.
 */
export async function enrichRuns(
  recent: RecentRun[],
  fetchRun: (id: string, signal?: AbortSignal) => Promise<LessonRunSummary>,
  signal?: AbortSignal,
): Promise<LessonRunSummary[]> {
  const results = await Promise.allSettled(
    recent.map(async (r) => {
      const summary = await fetchRun(r.run_id, signal);
      return summary;
    }),
  );
  return results.flatMap((res) =>
    res.status === "fulfilled" ? [res.value] : [],
  );
}
