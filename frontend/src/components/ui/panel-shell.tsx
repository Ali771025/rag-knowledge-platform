import type { PropsWithChildren } from "react";

interface PanelShellProps extends PropsWithChildren {
  className?: string;
}

export function PanelShell({ children, className = "" }: PanelShellProps) {
  return <aside className={`rounded-xl border border-border bg-muted/40 p-3 ${className}`.trim()}>{children}</aside>;
}

