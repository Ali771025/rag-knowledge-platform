import { useCallback, useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type MouseEvent as ReactMouseEvent, type RefObject } from "react";
import { MoreHorizontal } from "lucide-react";
import type { Project } from "@/types";
import { ArchiveConversationAction } from "./archive-conversation-action";
import { PinConversationAction } from "./pin-conversation-action";

interface ConversationActionsMenuProps {
  title: string;
  archived: boolean;
  pinned: boolean;
  projectId: string | null | undefined;
  projects: Project[];
  onRename: () => void;
  onArchive: () => void;
  onRestore: () => void;
  onDelete: () => void;
  onPin: () => void;
  onUnpin: () => void;
  onMoveToProject: (projectId: string | null) => void;
  triggerRef?: RefObject<HTMLButtonElement>;
}

export function ConversationActionsMenu({
  title,
  archived,
  pinned,
  projectId,
  projects,
  onRename,
  onArchive,
  onRestore,
  onDelete,
  onPin,
  onUnpin,
  onMoveToProject,
  triggerRef
}: ConversationActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const localTriggerRef = useRef<HTMLButtonElement>(null);
  const resolvedTriggerRef = triggerRef ?? localTriggerRef;

  const focusFirstMenuItem = useCallback(() => {
    const firstItem = menuRef.current?.querySelector<HTMLButtonElement>('button[role="menuitem"]');
    firstItem?.focus();
  }, []);

  const closeMenu = useCallback((restoreFocus = true) => {
    setIsOpen(false);
    if (restoreFocus) {
      window.setTimeout(() => {
        resolvedTriggerRef.current?.focus();
      }, 0);
    }
  }, [resolvedTriggerRef]);

  useEffect(() => {
    if (!isOpen) return;
    window.setTimeout(() => {
      focusFirstMenuItem();
    }, 0);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeMenu(true);
      }
    };

    const onPointerDown = (event: globalThis.MouseEvent) => {
      if (!containerRef.current) return;
      if (event.target instanceof Node && !containerRef.current.contains(event.target)) {
        closeMenu(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("mousedown", onPointerDown);

    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("mousedown", onPointerDown);
    };
  }, [closeMenu, focusFirstMenuItem, isOpen]);

  const handleToggle = (event: ReactMouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsOpen((previous) => !previous);
  };

  const handleItemClick = (callback: () => void, restoreFocus = true) => {
    callback();
    closeMenu(restoreFocus);
  };

  const handleMenuKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (!menuRef.current) return;

    const focusables = Array.from(menuRef.current.querySelectorAll<HTMLButtonElement>('button[role="menuitem"]'));
    if (focusables.length === 0) return;

    const activeElement = document.activeElement;
    const currentIndex = focusables.findIndex((button) => button === activeElement);

    if (event.key === "ArrowDown") {
      const nextIndex = (currentIndex + 1 + focusables.length) % focusables.length;
      focusables[nextIndex]?.focus();
      event.preventDefault();
      return;
    }

    if (event.key === "ArrowUp") {
      const nextIndex = (currentIndex - 1 + focusables.length) % focusables.length;
      focusables[nextIndex]?.focus();
      event.preventDefault();
      return;
    }

    if (event.key === "Home") {
      focusables[0]?.focus();
      event.preventDefault();
      return;
    }

    if (event.key === "End") {
      focusables[focusables.length - 1]?.focus();
      event.preventDefault();
      return;
    }

    if (event.key === "Escape") {
      event.preventDefault();
      closeMenu(true);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={resolvedTriggerRef}
        type="button"
        onClick={handleToggle}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && !isOpen) {
            event.preventDefault();
            setIsOpen(true);
          }
          if (event.key === "Escape" && isOpen) {
            event.preventDefault();
            closeMenu(true);
          }
        }}
        className={`inline-flex min-h-10 items-center rounded-md px-2 text-sm text-slate-400 hover:bg-slate-700 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60 ${
          isOpen ? "bg-slate-700 text-slate-100" : ""
        }`}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={`Conversation actions for ${title}`}
      >
        <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
      </button>

      {isOpen ? (
        <div
          ref={menuRef}
          role="menu"
          aria-label={`Actions for ${title}`}
          onKeyDown={handleMenuKeyDown}
          className="absolute right-0 top-9 z-30 w-52 rounded-lg border border-slate-700 bg-slate-900 p-1 shadow-xl"
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => handleItemClick(onRename, false)}
            className="min-h-9 w-full rounded-md px-2 py-1.5 text-left text-xs text-slate-200 hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55"
          >
            Rename
          </button>

          {!archived ? (
            <PinConversationAction
              pinned={pinned}
              onPin={() => handleItemClick(onPin)}
              onUnpin={() => handleItemClick(onUnpin)}
            />
          ) : null}

          <ArchiveConversationAction
            archived={archived}
            onArchive={() => handleItemClick(onArchive)}
            onRestore={() => handleItemClick(onRestore)}
          />

          <button
            type="button"
            role="menuitem"
            onClick={() => handleItemClick(onDelete, false)}
            className="min-h-9 w-full rounded-md px-2 py-1.5 text-left text-xs text-rose-300 hover:bg-rose-950/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55"
          >
            Delete
          </button>

          {!archived ? (
            <>
              <div className="my-1 h-px bg-slate-700" />
              <p className="px-2 py-1 text-[10px] uppercase tracking-wide text-slate-500">Move to project</p>
              <button
                type="button"
                role="menuitem"
                onClick={() => handleItemClick(() => onMoveToProject(null))}
                className="min-h-9 w-full rounded-md px-2 py-1.5 text-left text-xs text-slate-200 hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55"
              >
                Unassigned
              </button>
              {projects.map((project) => (
                <button
                  key={project.id}
                  type="button"
                  role="menuitem"
                  onClick={() => handleItemClick(() => onMoveToProject(project.id))}
                  className={`min-h-9 w-full truncate rounded-md px-2 py-1.5 text-left text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55 ${
                    project.id === projectId
                      ? "bg-slate-800 text-slate-100"
                      : "text-slate-200 hover:bg-slate-800"
                  }`}
                  title={project.name}
                >
                  {project.name}
                </button>
              ))}
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
