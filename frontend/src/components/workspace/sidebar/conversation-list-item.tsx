import { useMemo, useRef, useState } from "react";
import type { Conversation } from "@/types";
import { useAnalytics } from "@/hooks/use-analytics";
import { useToast } from "@/hooks/use-toast";
import { useWorkspaceConversationsStore, useWorkspaceProjectsStore, useWorkspaceUiStore } from "@/state";
import { ConversationActionsMenu } from "./conversation-actions-menu";
import { DeleteConversationDialog } from "./delete-conversation-dialog";
import { RenameConversationDialog } from "./rename-conversation-dialog";
import { writeDraggedConversationId } from "./drag-drop";

interface ConversationListItemProps {
  conversation: Conversation;
  active: boolean;
  onSelect: () => void;
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  const now = new Date();
  const today = now.toDateString();
  const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000).toDateString();

  if (date.toDateString() === today) return "Today";
  if (date.toDateString() === yesterday) return "Yesterday";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function buildConversationPreview(conversation: Conversation): string {
  const lastMessage = conversation.messages[conversation.messages.length - 1];
  if (!lastMessage) return "No messages yet";
  const compact = lastMessage.text.trim().split(/\s+/).join(" ");
  if (!compact) return "No message content";
  return compact;
}

export function ConversationListItem({ conversation, active, onSelect }: ConversationListItemProps) {
  const actionsTriggerRef = useRef<HTMLButtonElement>(null);
  const renameConversation = useWorkspaceConversationsStore((state) => state.renameConversation);
  const archiveConversation = useWorkspaceConversationsStore((state) => state.archiveConversation);
  const unarchiveConversation = useWorkspaceConversationsStore((state) => state.unarchiveConversation);
  const setConversationPinned = useWorkspaceConversationsStore((state) => state.setConversationPinned);
  const setActiveConversation = useWorkspaceConversationsStore((state) => state.setActiveConversation);
  const deleteConversation = useWorkspaceConversationsStore((state) => state.deleteConversation);
  const removeConversationFromProject = useWorkspaceProjectsStore((state) => state.removeConversation);
  const associateConversation = useWorkspaceProjectsStore((state) => state.associateConversation);
  const allProjects = useWorkspaceProjectsStore((state) => state.projects);
  const currentView = useWorkspaceUiStore((state) => state.currentView);
  const setWorkspaceView = useWorkspaceUiStore((state) => state.setWorkspaceView);
  const { success, error } = useToast();
  const {
    trackConversationRenamed,
    trackConversationDeleted,
    trackConversationArchived,
    trackConversationPinned
  } = useAnalytics();

  const [isRenameDialogOpen, setRenameDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  const updatedLabel = useMemo(() => formatUpdatedAt(conversation.updatedAt), [conversation.updatedAt]);
  const previewLabel = useMemo(() => buildConversationPreview(conversation), [conversation]);
  const projects = useMemo(
    () => allProjects.filter((project) => project.status !== "archived" && project.status !== "deleted"),
    [allProjects]
  );

  const handleRename = (nextTitle: string) => {
    try {
      renameConversation(conversation.id, nextTitle);
      setRenameDialogOpen(false);
      trackConversationRenamed(conversation.id);
      success("Conversation renamed");
    } catch {
      error("Rename failed", "Could not rename this conversation.");
    }
  };

  const handleArchive = () => {
    try {
      archiveConversation(conversation.id);
      trackConversationArchived(conversation.id, true);
      success("Conversation archived");
    } catch {
      error("Archive failed", "Could not archive this conversation.");
    }
  };

  const handleRestore = () => {
    try {
      unarchiveConversation(conversation.id);
      setActiveConversation(conversation.id);
      if (currentView === "archived") {
        setWorkspaceView("all_chats");
      }
      trackConversationArchived(conversation.id, false);
      success("Conversation restored");
    } catch {
      error("Restore failed", "Could not restore this conversation.");
    }
  };

  const handleDelete = () => {
    try {
      if (conversation.projectId) {
        removeConversationFromProject(conversation.projectId, conversation.id);
      }
      deleteConversation(conversation.id);
      setDeleteDialogOpen(false);
      trackConversationDeleted(conversation.id);
      success("Conversation deleted");
    } catch {
      error("Delete failed", "Could not delete this conversation.");
    }
  };

  const handlePin = () => {
    try {
      setConversationPinned(conversation.id, true);
      trackConversationPinned(conversation.id, true);
      success("Conversation pinned");
    } catch {
      error("Pin failed", "Could not pin this conversation.");
    }
  };

  const handleUnpin = () => {
    try {
      setConversationPinned(conversation.id, false);
      trackConversationPinned(conversation.id, false);
      success("Conversation unpinned");
    } catch {
      error("Unpin failed", "Could not unpin this conversation.");
    }
  };

  const handleMoveToProject = (projectId: string | null) => {
    try {
      if (projectId === null && conversation.projectId) {
        removeConversationFromProject(conversation.projectId, conversation.id);
      } else if (projectId) {
        associateConversation(projectId, conversation.id);
      }
      success("Conversation updated");
    } catch {
      error("Update failed", "Could not update this conversation.");
    }
  };

  return (
    <>
      <div className="group relative">
        <button
          type="button"
          onClick={onSelect}
          draggable={conversation.status === "active"}
          onDragStart={(event) => {
            writeDraggedConversationId(event.dataTransfer, conversation.id);
            setIsDragging(true);
          }}
          onDragEnd={() => {
            setIsDragging(false);
          }}
          aria-current={active ? "true" : undefined}
          className={`flex min-h-14 w-full items-start justify-between gap-2 rounded-md px-2 py-2 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60 ${
            active ? "bg-slate-700 text-slate-100" : "text-slate-300 hover:bg-slate-800 hover:text-slate-100"
          } ${isDragging ? "opacity-60" : ""}`}
          aria-label={`Open conversation ${conversation.title}`}
        >
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium">{conversation.title}</span>
            <span className="mt-0.5 block truncate text-[11px] text-slate-400">{previewLabel}</span>
          </span>
          <span className="mt-0.5 flex shrink-0 items-center gap-1">
            {conversation.isPinned ? <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-cyan-300">PIN</span> : null}
            {conversation.projectId ? <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">P</span> : null}
            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">{updatedLabel}</span>
          </span>
        </button>

        <div className="pointer-events-none absolute right-1 top-1 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100">
          <ConversationActionsMenu
            title={conversation.title}
            archived={conversation.status === "archived"}
            pinned={Boolean(conversation.isPinned)}
            projectId={conversation.projectId}
            projects={projects}
            onRename={() => setRenameDialogOpen(true)}
            onArchive={handleArchive}
            onRestore={handleRestore}
            onDelete={() => setDeleteDialogOpen(true)}
            onPin={handlePin}
            onUnpin={handleUnpin}
            onMoveToProject={handleMoveToProject}
            triggerRef={actionsTriggerRef}
          />
        </div>
      </div>

      <RenameConversationDialog
        open={isRenameDialogOpen}
        title={conversation.title}
        onClose={() => setRenameDialogOpen(false)}
        onConfirm={handleRename}
        restoreFocusRef={actionsTriggerRef}
      />

      <DeleteConversationDialog
        open={isDeleteDialogOpen}
        title={conversation.title}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        restoreFocusRef={actionsTriggerRef}
      />
    </>
  );
}
