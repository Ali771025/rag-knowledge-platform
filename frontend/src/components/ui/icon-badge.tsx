import type { ReactNode } from "react";

interface IconBadgeProps {
  icon: ReactNode;
  label: string;
  className?: string;
}

export function IconBadge({ icon, label, className = "" }: IconBadgeProps) {
  return (
    <span
      className={[
        "premium-interactive inline-flex min-h-9 items-center gap-1.5 rounded-full border border-white/15 bg-[color:var(--color-surface-soft)] px-2.5 py-1.5 sm:min-h-11 sm:gap-2 sm:px-3 sm:py-2",
        "font-heading text-[11px] font-medium text-[color:var(--color-text-main)] shadow-[inset_0_1px_0_rgba(255,255,255,0.12)] sm:text-xs",
        className
      ].join(" ")}
    >
      <span className="premium-icon-surface inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[color:var(--color-accent-cyan)] sm:h-6 sm:w-6">{icon}</span>
      <span>{label}</span>
    </span>
  );
}
