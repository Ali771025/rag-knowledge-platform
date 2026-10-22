import type { InputHTMLAttributes } from "react";
import { dsInteraction } from "@/design-system";

interface InputShellProps extends InputHTMLAttributes<HTMLInputElement> {}

export function InputShell({ className = "", ...props }: InputShellProps) {
  return (
    <input
      className={[
        "animated-input h-10 w-full rounded-lg border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground",
        dsInteraction.focusRingClass,
        dsInteraction.disabledOpacityClass,
        className
      ].join(" ")}
      {...props}
    />
  );
}
