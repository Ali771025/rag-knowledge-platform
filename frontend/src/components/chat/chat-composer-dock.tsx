import type { ReactNode } from "react";

interface ChatComposerDockProps {
  children: ReactNode;
}

export function ChatComposerDock({ children }: ChatComposerDockProps) {
  return (
    <div className="sticky bottom-0 z-10 flex justify-center bg-transparent px-2.5 pb-[calc(env(safe-area-inset-bottom)+0.75rem)] pt-1.5 sm:px-4 sm:pb-[calc(env(safe-area-inset-bottom)+1rem)] sm:pt-2">
      {children}
    </div>
  );
}
