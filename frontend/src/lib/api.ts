/**
 * Thin typed wrapper around fetch for the FastAPI backend.
 * Handles the X-API-Key authentication header, JSON serialization,
 * typed error extraction, and network/HTTP failures.
 */

import {
  type HistoryEvaluation,
  type LessonRequest,
  type LessonResponse,
  type LiveHealth,
  type ReadyHealth,
  type RunHistoryResponse,
  type LessonRunSummary,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  readonly isAuthError: boolean;

  constructor(status: number, message: string, detail: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.isAuthError = status === 401 || status === 403;
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NetworkError";
  }
}

interface ApiRequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(
  url: string,
  { method = "GET", body, signal }: ApiRequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
  };

  const { apiKey } = await import("./config").then((m) => m.config);
  if (apiKey) headers["X-API-Key"] = apiKey;

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw err;
    }
    throw new NetworkError(
      "Could not reach the backend server. Make sure the FastAPI service is running and the API base URL is correct.",
    );
  }

  let payload: unknown = null;
  const raw = await response.text();
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }

  if (!response.ok) {
    const detail = extractDetail(payload);
    throw new ApiError(response.status, detail.message, detail.raw);
  }

  return payload as T;
}

function extractDetail(payload: unknown): { message: string; raw: unknown } {
  if (payload && typeof payload === "object") {
    const obj = payload as Record<string, unknown>;
    if (typeof obj.detail === "string") {
      return { message: obj.detail, raw: obj.detail };
    }
    // FastAPI validates request bodies with an array of error objects.
    if (Array.isArray(obj.detail)) {
      const first = obj.detail[0] as Record<string, unknown> | undefined;
      const msg = first?.msg ?? first?.loc ?? "Invalid request";
      return { message: String(msg), raw: obj.detail };
    }
    const msg = obj.message;
    if (typeof msg === "string") return { message: msg, raw: obj };
  }
  return { message: "Request failed", raw: payload };
}

export const api = {
  async generateLesson(body: LessonRequest, signal?: AbortSignal): Promise<LessonResponse> {
    return request<LessonResponse>("/v1/lessons", {
      method: "POST",
      body,
      signal,
    });
  },

  async getRun(runId: string, signal?: AbortSignal): Promise<LessonRunSummary> {
    return request<LessonRunSummary>(`/v1/lessons/${encodeURIComponent(runId)}`, {
      signal,
    });
  },

  async getHistory(runId: string, signal?: AbortSignal): Promise<RunHistoryResponse> {
    return request<RunHistoryResponse>(
      `/v1/lessons/${encodeURIComponent(runId)}/history`,
      { signal },
    );
  },

  async getLiveHealth(signal?: AbortSignal): Promise<LiveHealth> {
    return request<LiveHealth>("/health/live", { signal });
  },

  async getReadyHealth(signal?: AbortSignal): Promise<ReadyHealth> {
    return request<ReadyHealth>("/health/ready", { signal });
  },

  parseEvaluations(draft: { evaluations: HistoryEvaluation[] }) {
    return draft.evaluations.map((ev) => ({
      ...ev,
      // evaluation_json is a JSON column returned by the backend already parsed.
      // Only JSON.parse when it's actually a string (forward compatibility).
      parsed:
        typeof ev.evaluation_json === "string"
          ? (JSON.parse(ev.evaluation_json) as unknown)
          : ev.evaluation_json,
    }));
  },
};
