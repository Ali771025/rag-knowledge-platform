import { motion, useReducedMotion } from "framer-motion";
import { dsFeedback, dsMotionVariants } from "@/design-system";
import type { FeedbackVariant } from "@/design-system";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastProps {
  id: string;
  title: string;
  description?: string;
  variant?: FeedbackVariant;
  action?: ToastAction;
  onDismiss: (id: string) => void;
}

export function Toast({ id, title, description, variant = "info", action, onDismiss }: ToastProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.article
      layout
      variants={dsMotionVariants.toast}
      initial={shouldReduceMotion ? false : "hidden"}
      animate="visible"
      exit="exit"
      className={`w-full rounded-xl border px-3 py-2 shadow-sm ${dsFeedback.variantClass[variant]}`}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-semibold leading-5">{title}</p>
          {description ? <p className="mt-1 text-xs leading-5 opacity-90">{description}</p> : null}
        </div>
        <button
          type="button"
          onClick={() => onDismiss(id)}
          className="min-h-8 rounded-full border border-current/30 px-2 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          aria-label="Dismiss notification"
        >
          Dismiss
        </button>
      </div>

      {action ? (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-2 min-h-8 rounded-full border border-current/30 px-3 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {action.label}
        </button>
      ) : null}
    </motion.article>
  );
}
