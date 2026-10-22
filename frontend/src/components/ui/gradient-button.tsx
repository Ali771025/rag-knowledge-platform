import type { ButtonHTMLAttributes, ReactNode } from "react";
import { LoaderCircle } from "lucide-react";
import { dsInteraction } from "@/design-system";

type GradientButtonSize = "sm" | "md" | "lg";

interface GradientButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  size?: GradientButtonSize;
  loading?: boolean;
  leadingIcon?: ReactNode;
}

const sizeClassMap: Record<GradientButtonSize, string> = {
  sm: "min-h-9 rounded-xl px-3 text-xs",
  md: "min-h-11 rounded-2xl px-4 text-sm",
  lg: "min-h-12 rounded-2xl px-5 text-sm"
};

export function GradientButton({
  className = "",
  size = "md",
  loading = false,
  leadingIcon,
  disabled,
  type = "button",
  children,
  ...props
}: GradientButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={[
        "premium-interactive premium-shine wave-button group inline-flex items-center justify-center gap-2 border border-white/15",
        "bg-gradient-to-r from-[color:var(--color-accent-cyan)] via-[color:var(--color-accent-blue)] to-[color:var(--color-accent-violet)]",
        "font-heading font-semibold text-slate-950 shadow-[0_12px_36px_rgba(54,224,255,0.32)]",
        "hover:brightness-110 active:scale-[0.98]",
        sizeClassMap[size],
        dsInteraction.focusRingClass,
        dsInteraction.disabledOpacityClass,
        className
      ].join(" ")}
      {...props}
    >
      {loading ? <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" /> : leadingIcon}
      <span>{children}</span>
    </button>
  );
}
