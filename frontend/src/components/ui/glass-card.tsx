import type { PropsWithChildren } from "react";

interface GlassCardProps extends PropsWithChildren {
  className?: string;
}

export function GlassCard({ children, className = "" }: GlassCardProps) {
  return (
    <section
      className={[
        "premium-glass-panel rounded-3xl border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-glass)] backdrop-blur-2xl",
        className
      ].join(" ")}
    >
      {children}
    </section>
  );
}
