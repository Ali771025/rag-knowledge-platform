import type { ButtonHTMLAttributes } from "react";
import { dsInteraction } from "@/design-system";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClassMap: Record<ButtonVariant, string> = {
  primary: "premium-shine border border-white/15 bg-gradient-to-r from-[color:var(--color-accent-cyan)] via-[color:var(--color-accent-blue)] to-[color:var(--color-accent-violet)] text-slate-950 shadow-[0_12px_34px_rgba(54,224,255,0.24)] hover:brightness-110",
  secondary: "border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-soft)] text-[color:var(--color-text-main)] hover:bg-white/10",
  ghost: "border border-transparent bg-transparent text-[color:var(--color-text-main)] hover:border-[color:var(--color-border-glow)] hover:bg-white/10"
};

const sizeClassMap: Record<ButtonSize, string> = {
  sm: "min-h-8 px-3 text-xs rounded-md",
  md: "min-h-10 px-4 text-sm rounded-lg",
  lg: "min-h-11 px-5 text-sm rounded-xl"
};

export function Button({
  className = "",
  variant = "secondary",
  size = "md",
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[
        "premium-interactive wave-button font-heading inline-flex items-center justify-center gap-2 font-medium",
        variantClassMap[variant],
        sizeClassMap[size],
        dsInteraction.focusRingClass,
        dsInteraction.disabledOpacityClass,
        className
      ].join(" ")}
      {...props}
    />
  );
}
