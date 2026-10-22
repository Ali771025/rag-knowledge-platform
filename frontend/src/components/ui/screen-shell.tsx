import type { PropsWithChildren } from "react";

interface ScreenShellProps extends PropsWithChildren {
  className?: string;
}

export function ScreenShell({ children, className = "" }: ScreenShellProps) {
  return <main className={`min-h-dvh bg-background text-foreground ${className}`.trim()}>{children}</main>;
}

