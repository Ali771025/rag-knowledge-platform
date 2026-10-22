import { AnimatePresence } from "framer-motion";
import { createContext, useCallback, useEffect, useMemo, useRef, useState, type PropsWithChildren } from "react";
import { dsToastDefaults, type FeedbackVariant } from "@/design-system";
import { Toast, type ToastAction } from "./toast";

export interface ToastInput {
  title: string;
  description?: string;
  variant?: FeedbackVariant;
  durationMs?: number;
  action?: ToastAction;
}

export interface ToastRecord extends ToastInput {
  id: string;
}

export interface ToastContextValue {
  toasts: ToastRecord[];
  pushToast: (toast: ToastInput) => string;
  dismissToast: (toastId: string) => void;
  clearToasts: () => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

function createToastId() {
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ToastProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<ToastRecord[]>([]);
  const timeoutsRef = useRef<Record<string, number>>({});

  const dismissToast = useCallback((toastId: string) => {
    window.clearTimeout(timeoutsRef.current[toastId]);
    delete timeoutsRef.current[toastId];
    setToasts((prev) => prev.filter((toast) => toast.id !== toastId));
  }, []);

  const clearToasts = useCallback(() => {
    Object.values(timeoutsRef.current).forEach((timeoutId) => {
      window.clearTimeout(timeoutId);
    });
    timeoutsRef.current = {};
    setToasts([]);
  }, []);

  const pushToast = useCallback(
    (toast: ToastInput) => {
      const id = createToastId();
      const durationMs = toast.durationMs ?? dsToastDefaults.durationMs;
      const record: ToastRecord = {
        id,
        ...toast
      };

      setToasts((prev) => [record, ...prev].slice(0, dsToastDefaults.maxVisible));

      if (durationMs > 0) {
        timeoutsRef.current[id] = window.setTimeout(() => {
          dismissToast(id);
        }, durationMs);
      }

      return id;
    },
    [dismissToast]
  );

  useEffect(() => {
    return () => {
      Object.values(timeoutsRef.current).forEach((timeoutId) => {
        window.clearTimeout(timeoutId);
      });
      timeoutsRef.current = {};
    };
  }, []);

  const contextValue = useMemo<ToastContextValue>(
    () => ({
      toasts,
      pushToast,
      dismissToast,
      clearToasts
    }),
    [clearToasts, dismissToast, pushToast, toasts]
  );

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <section className="pointer-events-none fixed inset-x-0 top-3 z-[60] flex justify-center px-3" aria-label="Notifications">
        <div className="pointer-events-auto w-full max-w-sm space-y-2">
          <AnimatePresence initial={false}>
            {toasts.map((toast) => (
              <Toast
                key={toast.id}
                id={toast.id}
                title={toast.title}
                description={toast.description}
                variant={toast.variant}
                action={toast.action}
                onDismiss={dismissToast}
              />
            ))}
          </AnimatePresence>
        </div>
      </section>
    </ToastContext.Provider>
  );
}
