export type FeedbackVariant = "success" | "error" | "warning" | "info";

export const dsFeedback = {
  variantClass: {
    success: "border-success/35 bg-success/10 text-success",
    error: "border-error/35 bg-error/10 text-error",
    warning: "border-warning/35 bg-warning/10 text-warning",
    info: "border-accent/35 bg-accent/10 text-foreground"
  }
} as const;

export const dsToastDefaults = {
  durationMs: 4200,
  maxVisible: 3
} as const;
