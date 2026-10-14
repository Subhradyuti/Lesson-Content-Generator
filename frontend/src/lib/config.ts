/**
 * Centralized frontend configuration.
 * All values come from environment variables — never hardcode secrets.
 */

const DEFAULT_API_BASE = ""; // same-origin → Vite dev proxy forwards to FastAPI

function resolveApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL?.trim();
  if (!raw) return DEFAULT_API_BASE;
  return raw.replace(/\/+$/, "");
}

export const config = {
  /** Base URL for backend calls. Empty string → same origin (proxied in dev). */
  apiBaseUrl: resolveApiBase(),
  /** Optional X-API-Key header value (from VITE_API_KEY). */
  apiKey: import.meta.env.VITE_API_KEY?.trim() ?? "",
  /** Whether the backend requires an API key. True when one is configured. */
  authRequired: Boolean(import.meta.env.VITE_API_KEY?.trim()),
} as const;

export const API_ENDPOINTS = {
  generateLesson: "/v1/lessons",
  runById: (runId: string) => `/v1/lessons/${encodeURIComponent(runId)}`,
  runHistory: (runId: string) =>
    `/v1/lessons/${encodeURIComponent(runId)}/history`,
  healthLive: "/health/live",
  healthReady: "/health/ready",
} as const;

export const DEFAULT_NEW_API_KEY = config.apiKey;
