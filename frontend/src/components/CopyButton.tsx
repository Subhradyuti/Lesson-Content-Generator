import { Copy, Check } from "lucide-react";
import { useState } from "react";
import clsx from "clsx";
import { copyToClipboard } from "../lib/utils";

interface CopyButtonProps {
  text: string;
  label?: string;
  size?: "sm" | "md";
  className?: string;
}

export function CopyButton({ text, label = "Copy", size = "sm", className }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      onClick={async () => {
        const ok = await copyToClipboard(text);
        if (ok) {
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        }
      }}
      className={clsx(
        "btn btn-ghost",
        size === "sm" ? "btn-sm" : "px-3 py-2",
        copied && "border-pass/40 text-pass hover:border-pass/40 hover:text-pass",
        className,
      )}
      aria-label={copied ? "Copied" : label}
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5" aria-hidden="true" /> Copied
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" aria-hidden="true" /> {label}
        </>
      )}
    </button>
  );
}
