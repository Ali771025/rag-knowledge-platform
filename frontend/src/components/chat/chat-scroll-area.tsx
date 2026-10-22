import type { ReactNode, RefObject } from "react";

interface ChatScrollAreaProps {
  scrollContainerRef: RefObject<HTMLDivElement>;
  children: ReactNode;
}

export function ChatScrollArea({ scrollContainerRef, children }: ChatScrollAreaProps) {
  return (
    <div
      ref={scrollContainerRef}
      className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-gradient-to-b from-slate-950/10 via-transparent to-transparent px-2.5 py-3 sm:px-5 sm:py-5"
    >
      {children}
    </div>
  );
}
