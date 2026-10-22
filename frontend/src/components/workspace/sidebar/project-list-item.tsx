import { useRef, useState, type DragEvent } from "react";
import { Folder, Inbox } from "lucide-react";
import type { Project } from "@/types";
import { readDraggedConversationId } from "./drag-drop";
import { DeleteProjectDialog } from "./delete-project-dialog";
import { ProjectActionsMenu } from "./project-actions-menu";
import { RenameProjectDialog } from "./rename-project-dialog";

interface ProjectListItemProps {
  project: Project | null;
  active: boolean;
  count?: number;
  canManage?: boolean;
  existingProjectNames?: string[];
  onSelect: () => void;
  onRenameProject?: (projectId: string, nextName: string) => void;
  onArchiveProject?: (projectId: string) => void;
  onDeleteProject?: (projectId: string) => void;
  onDropConversation?: (conversationId: string, projectId: string | null) => void;
}

export function ProjectListItem({
  project,
  active,
  count = 0,
  canManage = false,
  existingProjectNames = [],
  onSelect,
  onRenameProject,
  onArchiveProject,
  onDeleteProject,
  onDropConversation,
}: ProjectListItemProps) {
  const label = project?.name ?? "Unassigned chats";
  const menuTriggerRef = useRef<HTMLButtonElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isRenameDialogOpen, setRenameDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    if (!onDropConversation) return;
    const conversationId = readDraggedConversationId(event.dataTransfer);
    if (!conversationId) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setIsDragOver(true);
  };

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    if (!onDropConversation) return;
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) return;
    setIsDragOver(false);
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    if (!onDropConversation) return;
    const conversationId = readDraggedConversationId(event.dataTransfer);
    setIsDragOver(false);
    if (!conversationId) return;

    event.preventDefault();
    onDropConversation(conversationId, project?.id ?? null);
  };

  const handleRename = (nextName: string) => {
    if (!project || !onRenameProject) return;
    onRenameProject(project.id, nextName);
    setRenameDialogOpen(false);
  };

  const handleArchive = () => {
    if (!project || !onArchiveProject) return;
    onArchiveProject(project.id);
  };

  const handleDelete = () => {
    if (!project || !onDeleteProject) return;
    onDeleteProject(project.id);
    setDeleteDialogOpen(false);
  };

  return (
    <>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`group rounded-md transition ${isDragOver ? "ring-2 ring-cyan-400/70" : ""}`}
      >
        <div
          className={`flex min-h-9 items-center justify-between gap-1 rounded-md px-1 py-0.5 ${
            active ? "bg-slate-700 text-slate-100" : "text-slate-300 hover:bg-slate-800 hover:text-slate-100"
          }`}
        >
          <button
            type="button"
            onClick={onSelect}
            className="flex min-h-8 min-w-0 flex-1 items-center justify-between gap-2 rounded-md px-1 py-1 text-left text-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            title={label}
            aria-label={`Open project ${label}`}
          >
            <span className="inline-flex min-w-0 items-center gap-1.5">
              {project ? (
                <Folder className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              ) : (
                <Inbox className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              )}
              <span className="truncate">{label}</span>
            </span>
            <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">{count}</span>
          </button>

          {project && canManage && onRenameProject && onArchiveProject && onDeleteProject ? (
            <div className="pointer-events-none opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100">
              <ProjectActionsMenu
                title={project.name}
                onRename={() => setRenameDialogOpen(true)}
                onArchive={handleArchive}
                onDelete={() => setDeleteDialogOpen(true)}
                triggerRef={menuTriggerRef}
              />
            </div>
          ) : null}
        </div>
      </div>

      {project ? (
        <RenameProjectDialog
          open={isRenameDialogOpen}
          name={project.name}
          existingNames={existingProjectNames}
          onClose={() => setRenameDialogOpen(false)}
          onConfirm={handleRename}
          restoreFocusRef={menuTriggerRef}
        />
      ) : null}

      {project ? (
        <DeleteProjectDialog
          open={isDeleteDialogOpen}
          name={project.name}
          onClose={() => setDeleteDialogOpen(false)}
          onConfirm={handleDelete}
          restoreFocusRef={menuTriggerRef}
        />
      ) : null}
    </>
  );
}
