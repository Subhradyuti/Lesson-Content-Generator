import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BookOpenText,
  KeyRound,
  Sparkles,
  TriangleAlert,
  Wand2,
} from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";

import { PageHeader } from "../components/PageHeader";
import { GenerationProgress } from "../components/GenerationProgress";
import { EvaluationPanel } from "../components/EvaluationPanel";
import { RejectionLog } from "../components/RejectionLog";
import { LessonViewer } from "../components/LessonViewer";
import { StatusBadge } from "../components/StatusBadge";
import { CopyButton } from "../components/CopyButton";
import { api, ApiError, NetworkError } from "../lib/api";
import { config } from "../lib/config";
import { saveRecentRun } from "../lib/recentRuns";
import { toast } from "../components/Toast";
import { formatDateTime } from "../lib/utils";
import type { LessonResponse } from "../lib/types";

interface FormState {
  topic: string;
  learnerProfile: string;
  language: string;
  maxRetries: number;
  referenceMaterial: string;
}

const INITIAL_FORM: FormState = {
  topic: "",
  learnerProfile: "",
  language: "",
  maxRetries: 2,
  referenceMaterial: "",
};

type Phase = "idle" | "running" | "done" | "error";

function errorMessage(err: unknown): { title: string; detail: string } {
  if (err instanceof ApiError) {
    if (err.isAuthError) {
      return {
        title: "Authentication failed",
        detail:
          "The backend rejected the X-API-Key header. Set VITE_API_KEY in frontend/.env to the API key configured in the backend, then restart the dev server.",
      };
    }
    if (err.status === 422) {
      return {
        title: "Invalid request",
        detail: err.message,
      };
    }
    return { title: `Backend error (${err.status})`, detail: err.message };
  }
  if (err instanceof NetworkError) {
    return { title: "Backend unreachable", detail: err.message };
  }
  return {
    title: "Unexpected error",
    detail: err instanceof Error ? err.message : String(err),
  };
}

function FormField({
  id,
  label,
  hint,
  error,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="label">
        {label}
      </label>
      {children}
      {hint && !error && <p className="hint">{hint}</p>}
      {error && (
        <p className="mt-1.5 flex items-center gap-1 text-xs text-fail">
          <TriangleAlert className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}
    </div>
  );
}

function AuthWarning() {
  if (config.authRequired) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-warn/25 bg-warn-dim px-4 py-3 text-xs leading-5 text-warn">
      <KeyRound className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <p>
        <span className="font-semibold">API key not configured.</span> The frontend will
        only work if the backend is running without an API key. Set{" "}
        <code className="rounded bg-sunken px-1 py-0.5 font-mono">VITE_API_KEY</code> in{" "}
        <code className="rounded bg-sunken px-1 py-0.5 font-mono">frontend/.env</code> when
        the backend requires authentication.
      </p>
    </div>
  );
}

export function GeneratePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<LessonResponse | null>(null);
  const [error, setError] = useState<{ title: string; detail: string } | null>(null);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const running = phase === "running";

  // Track elapsed wall-clock time while a run is in flight.
  useEffect(() => {
    if (!running || startedAt === null) return;
    const interval = window.setInterval(() => {
      setElapsedMs(Date.now() - startedAt);
    }, 500);
    return () => window.clearInterval(interval);
  }, [running, startedAt]);

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
    setErrors((e) => (e[key] ? { ...e, [key]: undefined } : e));
  };

  const validate = (): boolean => {
    const next: Partial<Record<keyof FormState, string>> = {};
    const topic = form.topic.trim();
    if (!topic) next.topic = "A topic is required.";
    else if (topic.length < 3) next.topic = "Topic must be at least 3 characters.";
    else if (topic.length > 120) next.topic = "Topic must be 120 characters or fewer.";
    if (form.language.trim() && form.language.trim().length > 100) {
      next.language = "Language must be 100 characters or fewer.";
    }
    if (form.learnerProfile.trim().length > 500) {
      next.learnerProfile = "Keep the learner profile under 500 characters.";
    }
    if (form.referenceMaterial.trim().length > 20000) {
      next.referenceMaterial = "Reference material is limited to 20,000 characters.";
    }
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setPhase("running");
    setResult(null);
    setError(null);
    setElapsedMs(0);
    setStartedAt(Date.now());

    try {
      const res = await api.generateLesson({
        topic: form.topic.trim(),
        learner_profile: form.learnerProfile.trim() || null,
        language: form.language.trim() || null,
        max_retries: form.maxRetries,
        reference_material: form.referenceMaterial.trim() || null,
      });
      saveRecentRun({
        run_id: res.run_id,
        topic: res.topic,
        created_at: res.created_at,
      });
      setResult(res);
      setPhase("done");
      toast.success("Lesson generated", `${res.topic} — run ${res.run_id.slice(0, 8)}…`);
    } catch (err) {
      const { title, detail } = errorMessage(err);
      setError({ title, detail });
      setPhase("error");
      toast.error(title, detail);
    } finally {
      setStartedAt(null);
      setElapsedMs(0);
    }
  };

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Create"
        title="Generate a lesson"
        description="Describe the topic and let the pipeline plan, draft, evaluate and revise a beginner lesson against the 14-point rubric."
        icon={Sparkles}
      />

      <div className="grid gap-6 lg:grid-cols-[360px,1fr] lg:items-start">
        {/* ── Request form ─────────────────────────────────────────── */}
        <form
          onSubmit={onSubmit}
          noValidate
          aria-busy={running}
          className={clsx("card-pad space-y-5", running && "pointer-events-none opacity-75")}
        >
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/10 text-accent ring-1 ring-accent/25">
              <BookOpenText className="h-[18px] w-[18px]" aria-hidden="true" />
            </span>
            <div>
              <h2 className="text-sm font-semibold text-ink">Lesson request</h2>
              <p className="font-mono text-xs text-faint">POST /v1/lessons</p>
            </div>
          </div>

          <FormField
            id="topic"
            label="Topic *"
            hint="What beginner lesson should be written? Keep it specific."
            error={errors.topic}
          >
            <input
              id="topic"
              type="text"
              value={form.topic}
              onChange={(e) => update("topic", e.target.value)}
              placeholder="e.g. Introduction to RAG"
              className="input"
              maxLength={120}
              disabled={running}
              autoComplete="off"
            />
          </FormField>

          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="learner"
              label="Learner profile"
              hint="Defaults to beginner if empty."
              error={errors.learnerProfile}
            >
              <input
                id="learner"
                type="text"
                value={form.learnerProfile}
                onChange={(e) => update("learnerProfile", e.target.value)}
                placeholder="e.g. Beginner data scientists"
                className="input"
                maxLength={500}
                disabled={running}
              />
            </FormField>

            <FormField id="language" label="Language" error={errors.language}>
              <input
                id="language"
                type="text"
                value={form.language}
                onChange={(e) => update("language", e.target.value)}
                placeholder="e.g. English"
                className="input"
                maxLength={100}
                disabled={running}
              />
            </FormField>
          </div>

          <FormField
            id="retries"
            label="Max retries"
            hint="0 = evaluate once and stop. Each retry produces a new draft only if the rubric failed."
          >
            <div className="flex items-center gap-3">
              <input
                id="retries"
                type="range"
                min={0}
                max={4}
                step={1}
                value={form.maxRetries}
                onChange={(e) => update("maxRetries", Number(e.target.value))}
                className="w-full accent-[#7c8bff]"
                disabled={running}
              />
              <span className="chip w-14 justify-center font-mono text-sm">
                {form.maxRetries}
              </span>
            </div>
          </FormField>

          <FormField
            id="reference"
            label="Reference material"
            hint="Optional source text the evaluator uses for the accuracy checkpoints."
            error={errors.referenceMaterial}
          >
            <textarea
              id="reference"
              value={form.referenceMaterial}
              onChange={(e) => update("referenceMaterial", e.target.value)}
              placeholder="Paste grounding material here…"
              className="input min-h-28 resize-y font-mono text-[13px]"
              maxLength={20000}
              disabled={running}
            />
          </FormField>

          <AuthWarning />

          <button
            type="submit"
            className="btn btn-primary btn-lg w-full"
            disabled={running}
          >
            {running ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                Generating…
              </>
            ) : (
              <>
                <Wand2 className="h-[18px] w-[18px]" aria-hidden="true" /> Generate lesson
              </>
            )}
          </button>
        </form>

        {/* ── Progress / results column ────────────────────────────── */}
        <div className="min-w-0 space-y-6">
          {phase === "error" && error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              role="alert"
              className="rounded-2xl border border-fail/30 bg-fail-dim p-5"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-fail/15 text-fail">
                  <TriangleAlert className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0">
                  <h3 className="text-sm font-semibold text-ink">{error.title}</h3>
                  <p className="mt-1 text-[13px] leading-5 text-muted">{error.detail}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setPhase("idle")}
                className="btn btn-ghost btn-sm mt-4"
              >
                Back to form
              </button>
            </motion.div>
          )}

          {phase === "running" && (
            <GenerationProgress
              topic={form.topic}
              maxRetries={form.maxRetries}
              elapsedMs={elapsedMs}
            />
          )}

          {phase === "done" && result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="card-pad flex flex-wrap items-center justify-between gap-4 border-pass/20"
              >
                <div className="min-w-0">
                  <p className="text-xs tracking-wider text-faint uppercase">Run completed</p>
                  <h2 className="mt-1 truncate text-lg font-semibold text-ink">{result.topic}</h2>
                  <p className="mt-0.5 font-mono text-xs text-faint">
                    {result.run_id} · {formatDateTime(result.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={result.status} />
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => navigate(`/runs/${result.run_id}`)}
                  >
                    Open run detail <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              </motion.div>

              {result.lesson && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                >
                  <LessonViewer content={result.lesson} />
                </motion.div>
              )}

              {result.evaluation && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  <EvaluationPanel evaluation={result.evaluation} />
                </motion.div>
              )}

              {result.rejection_log && result.rejection_log.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <RejectionLog logs={result.rejection_log} />
                </motion.div>
              )}

              {result.error_detail && (
                <div
                  role="alert"
                  className="rounded-2xl border border-fail/30 bg-fail-dim p-5 text-sm text-fail"
                >
                  <span className="font-semibold">Run creation warning:</span>{" "}
                  {result.error_detail}
                </div>
              )}
            </motion.div>
          )}

          {phase === "idle" && (
            <div className="card-pad border-dashed">
              <div className="flex items-center gap-3 text-sm font-medium text-ink">
                <Sparkles className="h-[18px] w-[18px] text-accent" aria-hidden="true" />
                Ready when you are
              </div>
              <p className="mt-2 text-[13px] leading-6 text-muted">
                Fill in the request and press <span className="font-semibold">Generate
                lesson</span>. The pipeline will plan, draft and evaluate the lesson, then show
                the rubric verdict, any rejected attempts and the final lesson here.
              </p>
              <div className="mt-4 flex items-center gap-2">
                <CopyButton text={window.location.origin} label="Copy origin" />
                <span className="text-xs text-faint">Useful if the backend has CORS enabled.</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
