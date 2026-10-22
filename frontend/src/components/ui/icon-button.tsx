import type { ButtonHTMLAttributes } from "react";
import { dsInteraction } from "@/design-system";

type IconButtonVariant = "ghost" | "secondary";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: IconButtonVariant;
}

const variantClassMap: Record<IconButtonVariant, string> = {
  ghost: "border border-transparent bg-transparent text-[color:var(--color-text-main)] hover:border-[color:var(--color-border-glow)] hover:bg-white/10",
  secondary: "premium-icon-surface border border-[color:var(--color-border-glow)] text-[color:var(--color-text-main)] hover:border-white/35"
};

export function IconButton({ className = "", variant = "ghost", type = "button", ...props }: IconButtonProps) {
  return (
    <button
      type={type}
      className={[
        "premium-interactive wave-button inline-flex h-10 w-10 items-center justify-center rounded-xl",
        variantClassMap[variant],
        dsInteraction.focusRingClass,
        dsInteraction.disabledOpacityClass,
        className
      ].join(" ")}
      {...props}
    />
  );
}
