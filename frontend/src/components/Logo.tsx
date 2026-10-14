import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import clsx from "clsx";

interface LogoProps {
  className?: string;
  markOnly?: boolean;
  href?: string;
}

export function LogoMark({ className }: { className?: string }) {
  return (
    <div
      className={clsx(
        "relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
        "bg-gradient-to-br from-accent-deep via-accent to-accent-strong shadow-lg shadow-accent/30",
        className,
      )}
      aria-hidden="true"
    >
      <Sparkles className="h-5 w-5 text-white" strokeWidth={2} />
    </div>
  );
}

export function Logo({ className, markOnly = false, href = "/" }: LogoProps) {
  if (markOnly) return <LogoMark className={className} />;
  return (
    <Link
      to={href}
      className={clsx(
        "group inline-flex items-center gap-3 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-accent/50",
        className,
      )}
      aria-label="Lesson Forge home"
    >
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className="text-[15px] font-bold tracking-tight text-ink">
          Lesson <span className="text-gradient">Forge</span>
        </span>
        <span className="mt-0.5 text-[10px] font-medium tracking-wide text-faint uppercase">
          Self-Evaluating Generator
        </span>
      </span>
    </Link>
  );
}
