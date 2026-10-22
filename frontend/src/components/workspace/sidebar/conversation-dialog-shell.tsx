import { useEffect, useId, useRef, type ReactNode, type RefObject } from "react";

interface ConversationDialogShellProps {
  title: string;
  description: string;
  onClose: () => void;
  children: ReactNode;
  initialFocusRef?: RefObject<HTMLElement>;
  restoreFocusRef?: RefObject<HTMLElement>;
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hasAttribute("disabled") && element.offsetParent !== null);
}

export function ConversationDialogShell({
  title,
  description,
  onClose,
  children,
  initialFocusRef,
  restoreFocusRef
}: ConversationDialogShellProps) {
  const dialogRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  const titleId = useId();
  const descriptionId = useId();

  onCloseRef.current = onClose;

  useEffect(() => {
    previousFocusRef.current =
      restoreFocusRef?.current ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    const dialog = dialogRef.current;
    if (!dialog) return;

    const initialTarget = initialFocusRef?.current ?? getFocusableElements(dialog)[0];
    initialTarget?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (!dialogRef.current) return;
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab") return;

      const focusables = getFocusableElements(dialogRef.current);
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;

      if (event.shiftKey) {
        if (active === first || active === dialogRef.current) {
          event.preventDefault();
          last?.focus();
        }
        return;
      }

      if (active === last) {
        event.preventDefault();
        first?.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.setTimeout(() => {
        previousFocusRef.current?.focus();
      }, 0);
    };
  }, [initialFocusRef, restoreFocusRef]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
    >
      <button type="button" onClick={onClose} className="absolute inset-0 bg-black/55" aria-label="Close dialog overlay" />
      <section ref={dialogRef} className="relative z-10 w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-4 shadow-2xl">
        <header>
          <h3 id={titleId} className="text-base font-semibold text-slate-100">
            {title}
          </h3>
          <p id={descriptionId} className="mt-1 text-sm text-slate-400">
            {description}
          </p>
        </header>
        <div className="mt-4">{children}</div>
      </section>
    </div>
  );
}
