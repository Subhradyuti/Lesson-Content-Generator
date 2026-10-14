import { useState } from "react";
import { BookOpenCheck, FileCode2 } from "lucide-react";
import clsx from "clsx";

import { Markdown } from "./Markdown";
import { CopyButton } from "./CopyButton";

interface LessonViewerProps {
  content: string;
  className?: string;
  initiallyRaw?: boolean;
}

export function LessonViewer({
  content,
  className,
  initiallyRaw = false,
}: LessonViewerProps) {
  const [mode, setMode] = useState<"preview" | "raw">(
    initiallyRaw ? "raw" : "preview",
  );

  return (
    <div className={clsx("card overflow-hidden", className)}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-raised/40 px-5 py-3.5 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/10 text-accent ring-1 ring-accent/25">
            <BookOpenCheck className="h-4.5 w-4.5" aria-hidden="true" />
          </span>
          <div>
            <h3 className="text-sm font-semibold text-ink">Generated lesson</h3>
            <p className="text-xs text-faint">
              {content.length.toLocaleString()} chars · markdown
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div
            className="flex rounded-lg border border-line bg-sunken p-0.5"
            role="tablist"
            aria-label="Lesson view mode"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === "preview"}
              onClick={() => setMode("preview")}
              className={clsx(
                "rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === "preview"
                  ? "bg-raised text-ink shadow-sm"
                  : "text-faint hover:text-muted",
              )}
            >
              Preview
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "raw"}
              onClick={() => setMode("raw")}
              className={clsx(
                "flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium transition-colors",
                mode === "raw"
                  ? "bg-raised text-ink shadow-sm"
                  : "text-faint hover:text-muted",
              )}
            >
              <FileCode2 className="h-3.5 w-3.5" aria-hidden="true" /> Raw
            </button>
          </div>
          <CopyButton text={content} label="Copy" />
        </div>
      </div>

      <div className="scroll-thin max-h-[70vh] overflow-y-auto px-5 py-5 sm:px-6 sm:py-6">
        {mode === "preview" ? (
          <Markdown content={content} />
        ) : (
          <pre className="scroll-thin overflow-x-auto font-mono text-[13px] leading-6 whitespace-pre-wrap text-muted">
            {content}
          </pre>
        )}
      </div>
    </div>
  );
}
