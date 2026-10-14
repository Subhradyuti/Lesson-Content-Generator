import { useEffect, useRef, useState } from "react";
import { Check, CircleAlert, Info, Loader2, X } from "lucide-react";
import clsx from "clsx";

type ToastTone = "success" | "error" | "info" | "loading";

interface Toast {
  id: number;
  tone: ToastTone;
  title: string;
  description?: string;
}

type Listener = (toasts: Toast[]) => void;

let toasts: Toast[] = [];
let nextId = 1;
const listeners = new Set<Listener>();

function emit() {
  for (const listener of listeners) listener([...toasts]);
}

function dismiss(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

let timers = new Map<number, ReturnType<typeof setTimeout>>();
function push(tone: ToastTone, title: string, description?: string, sticky = false) {
  const id = nextId++;
  toasts = [...toasts, { id, tone, title, description }];
  emit();
  if (!sticky) {
    const t = setTimeout(() => dismiss(id), tone === "loading" ? 6000 : 4200);
    timers.get(id) && clearTimeout(timers.get(id) as unknown as number);
    timers.set(id, t);
  }
  return id;
}

export const toast = {
  success: (title: string, description?: string) =>
    push("success", title, description),
  error: (title: string, description?: string) => push("error", title, description),
  info: (title: string, description?: string) => push("info", title, description),
  dismiss,
};

const TONE_STYLES: Record<ToastTone, { ring: string; Icon: typeof Check }> = {
  success: { ring: "border-pass/30", Icon: Check },
  error: { ring: "border-fail/30", Icon: CircleAlert },
  info: { ring: "border-info/30", Icon: Info },
  loading: { ring: "border-info/30", Icon: Loader2 },
};

export function ToastViewport() {
  const [items, setItems] = useState<Toast[]>([]);
  const stable = useRef<Listener>(() => undefined);

  stable.current = (next: Toast[]) => setItems(next);

  useEffect(() => {
    listeners.add(stable.current);
    return () => {
      listeners.delete(stable.current);
    };
  }, []);

  return (
    <div
      role="region"
      aria-live="polite"
      className="pointer-events-none fixed right-4 bottom-4 z-[90] flex w-[min(92vw,380px)] flex-col gap-2.5"
    >
      {items.map((item) => {
        const { ring, Icon } = TONE_STYLES[item.tone];
        return (
          <div
            key={item.id}
            role="status"
            className={clsx(
              "animate-scale-in pointer-events-auto flex items-start gap-3 rounded-xl border bg-elevated/95 p-4 shadow-2xl shadow-black/50 backdrop-blur",
              ring,
            )}
          >
            <div
              className={clsx(
                "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-lg",
                item.tone === "success" && "bg-pass-dim text-pass",
                item.tone === "error" && "bg-fail-dim text-fail",
                (item.tone === "info" || item.tone === "loading") &&
                  "bg-info-dim text-info",
              )}
            >
              <Icon
                className={clsx("h-4 w-4", item.tone === "loading" && "animate-spin")}
                aria-hidden="true"
              />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-ink">{item.title}</p>
              {item.description && (
                <p className="mt-0.5 line-clamp-3 text-xs leading-5 text-muted">
                  {item.description}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => dismiss(item.id)}
              className="icon-btn mt-0.5"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
