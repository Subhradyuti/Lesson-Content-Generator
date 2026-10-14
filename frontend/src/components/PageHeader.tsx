import type { LucideIcon } from "lucide-react";
import clsx from "clsx";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  icon: Icon,
  className,
}: PageHeaderProps) {
  return (
    <div className={clsx("mb-8", className)}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-2 text-xs font-semibold tracking-[0.18em] text-accent uppercase">
              {eyebrow}
            </p>
          )}
          <h1 className="flex items-center gap-3 text-2xl font-bold tracking-tight text-ink sm:text-[28px]">
            {Icon && (
              <span className="hidden h-10 w-10 items-center justify-center rounded-xl border border-line bg-raised text-accent sm:flex">
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
            )}
            {title}
          </h1>
          {description && (
            <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">{description}</p>
          )}
        </div>
        {actions && <div className="flex shrink-0 flex-wrap items-center gap-2.5">{actions}</div>}
      </div>
    </div>
  );
}
