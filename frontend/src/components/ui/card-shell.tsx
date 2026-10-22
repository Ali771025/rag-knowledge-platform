import type { PropsWithChildren } from "react";

interface CardShellProps extends PropsWithChildren {
  className?: string;
}

export function CardShell({ children, className = "" }: CardShellProps) {
  return (
    <section
      className={[
        "premium-glass-panel rounded-2xl border border-border bg-surface-1 shadow-sm",
        "dark:border-[color:var(--color-border-glow)] dark:bg-[color:var(--color-surface-glass)]",
        className
      ].join(" ").trim()}
    >
      {children}
    </section>
  );
}
