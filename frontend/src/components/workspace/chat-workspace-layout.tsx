import type { ReactNode, RefObject } from "react";

interface ChatWorkspaceLayoutProps {
  children: ReactNode;
}

interface ChatSidebarProps {
  compact: boolean;
  children: ReactNode;
}

interface ChatMainProps {
  mobileHeader?: ReactNode;
  children: ReactNode;
}

interface ChatMobileSidebarDrawerProps {
  isOpen: boolean;
  drawerRef: RefObject<HTMLDivElement>;
  onClose: () => void;
  children: ReactNode;
}

export function ChatWorkspaceLayout({ children }: ChatWorkspaceLayoutProps) {
  return (
    <div data-theme="dark" className="flex h-dvh w-full overflow-hidden bg-background text-foreground">
      {children}
    </div>
  );
}

export function ChatSidebar({ compact, children }: ChatSidebarProps) {
  return (
    <aside className={`hidden h-full shrink-0 border-r border-border md:flex ${compact ? "w-20" : "w-72"}`}>{children}</aside>
  );
}

export function ChatMain({ mobileHeader, children }: ChatMainProps) {
  return (
    <main className="flex min-w-0 flex-1 flex-col overflow-hidden">
      {mobileHeader}
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </main>
  );
}

export function ChatMobileSidebarDrawer({ isOpen, drawerRef, onClose, children }: ChatMobileSidebarDrawerProps) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label="Workspace sidebar drawer">
      <button type="button" onClick={onClose} className="absolute inset-0 bg-black/40" aria-label="Close workspace sidebar" />
      <aside ref={drawerRef} className="relative z-10 h-full w-72 border-r border-border bg-slate-950">
        {children}
      </aside>
    </div>
  );
}
