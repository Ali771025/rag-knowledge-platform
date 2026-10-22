import { useContext } from "react";
import { ToastContext } from "@/components/ui/toast-provider";
import type { ToastInput } from "@/components/ui/toast-provider";

export function useToast() {
  const context = useContext(ToastContext);

  if (!context) {
    return {
      toasts: [],
      toast: (_input: ToastInput) => "toast-noop",
      success: (_title: string, _description?: string) => "toast-noop",
      info: (_title: string, _description?: string) => "toast-noop",
      warning: (_title: string, _description?: string) => "toast-noop",
      error: (_title: string, _description?: string) => "toast-noop",
      dismissToast: (_id: string) => {},
      clearToasts: () => {}
    };
  }

  return {
    toasts: context.toasts,
    toast: (input: ToastInput) => context.pushToast(input),
    success: (title: string, description?: string) =>
      context.pushToast({ title, description, variant: "success" }),
    info: (title: string, description?: string) => context.pushToast({ title, description, variant: "info" }),
    warning: (title: string, description?: string) =>
      context.pushToast({ title, description, variant: "warning" }),
    error: (title: string, description?: string) => context.pushToast({ title, description, variant: "error" }),
    dismissToast: context.dismissToast,
    clearToasts: context.clearToasts
  };
}
