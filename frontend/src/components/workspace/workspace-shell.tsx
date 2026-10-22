import { useEffect, useRef, type ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { ChatMain, ChatMobileSidebarDrawer, ChatSidebar, ChatWorkspaceLayout } from "./chat-workspace-layout";
import { useActiveWorkspaceConversation, useWorkspaceUiStore } from "@/state";

interface WorkspaceShellProps {
  children: ReactNode;
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )
  ).filter((element) => !element.hasAttribute("disabled") && element.offsetParent !== null);
}

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const sidebarState = useWorkspaceUiStore((state) => state.sidebarState);
  const isMobileDrawerOpen = useWorkspaceUiStore((state) => state.isMobileDrawerOpen);
  const toggleMobileDrawer = useWorkspaceUiStore((state) => state.toggleMobileDrawer);
  const setMobileDrawerOpen = useWorkspaceUiStore((state) => state.setMobileDrawerOpen);
  const activeConversation = useActiveWorkspaceConversation();
  const drawerRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const compact = sidebarState === "collapsed";

  useEffect(() => {
    if (!isMobileDrawerOpen) return;

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMobileDrawerOpen(false);
      }
    };

    window.addEventListener("keydown", onEscape);
    return () => {
      window.removeEventListener("keydown", onEscape);
    };
  }, [isMobileDrawerOpen, setMobileDrawerOpen]);

  useEffect(() => {
    if (!isMobileDrawerOpen) return;

    previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const firstFocusable = drawerRef.current ? getFocusableElements(drawerRef.current)[0] : null;
    firstFocusable?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab" || !drawerRef.current) return;

      const focusables = getFocusableElements(drawerRef.current);
      if (focusables.length === 0) {
        event.preventDefault();
        return;
      }

      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const activeElement = document.activeElement;

      if (event.shiftKey) {
        if (activeElement === first || activeElement === drawerRef.current) {
          event.preventDefault();
          last?.focus();
        }
        return;
      }

      if (activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previousFocusRef.current?.focus();
    };
  }, [isMobileDrawerOpen]);

  return (
    <ChatWorkspaceLayout>
      <ChatSidebar compact={compact}>
        <Sidebar compact={compact} mobile={false} />
      </ChatSidebar>

      <ChatMain
        mobileHeader={
          <header className="flex h-14 items-center gap-3 border-b border-border bg-background px-4 md:hidden">
            <button
              type="button"
              onClick={toggleMobileDrawer}
              className="min-h-10 rounded-md border border-border bg-background px-3 py-1.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label="Open workspace sidebar"
            >
              Menu
            </button>
            <p className="truncate text-sm text-muted-foreground">{activeConversation?.title ?? "Workspace chat"}</p>
          </header>
        }
      >
        {children}
      </ChatMain>

      <ChatMobileSidebarDrawer isOpen={isMobileDrawerOpen} drawerRef={drawerRef} onClose={() => setMobileDrawerOpen(false)}>
        <Sidebar compact={false} mobile onCloseMobile={() => setMobileDrawerOpen(false)} />
      </ChatMobileSidebarDrawer>
    </ChatWorkspaceLayout>
  );
}
