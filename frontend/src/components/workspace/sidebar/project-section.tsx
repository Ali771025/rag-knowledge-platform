import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUpDown, Check, ChevronDown, ChevronRight, FolderPlus, Plus, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { useWorkspaceConversationsStore, useWorkspaceProjectsStore, useWorkspaceUiStore } from "@/state";
import { ProjectListItem } from "./project-list-item";

interface ProjectSectionProps {
  compact: boolean;
  onAfterSelect?: () => void;
}

export function ProjectSection({ compact, onAfterSelect }: ProjectSectionProps) {
  const allProjects = useWorkspaceProjectsStore((state) => state.projects);
  const createProject = useWorkspaceProjectsStore((state) => state.createProject);
  const renameProject = useWorkspaceProjectsStore((state) => state.renameProject);
  const archiveProject = useWorkspaceProjectsStore((state) => state.archiveProject);
  const deleteProject = useWorkspaceProjectsStore((state) => state.deleteProject);
  const associateConversation = useWorkspaceProjectsStore((state) => state.associateConversation);
  const removeConversation = useWorkspaceProjectsStore((state) => state.removeConversation);

  const conversations = useWorkspaceConversationsStore((state) => state.conversations);
  const setActiveConversation = useWorkspaceConversationsStore((state) => state.setActiveConversation);
  const getConversationById = useWorkspaceConversationsStore((state) => state.getConversationById);

  const currentView = useWorkspaceUiStore((state) => state.currentView);
  const activeProjectId = useWorkspaceUiStore((state) => state.activeProjectId);
  const setWorkspaceView = useWorkspaceUiStore((state) => state.setWorkspaceView);
  const projectSortOrder = useWorkspaceUiStore((state) => state.projectSortOrder);
  const setProjectSortOrder = useWorkspaceUiStore((state) => state.setProjectSortOrder);

  const { success, error: showError } = useToast();

  const [isExpanded, setIsExpanded] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const projectInputRef = useRef<HTMLInputElement>(null);

  const activeProjects = useMemo(
    () => allProjects.filter((project) => project.status !== "archived" && project.status !== "deleted"),
    [allProjects]
  );

  const projectCounts = useMemo(() => {
    const counts = new Map<string | null, number>();
    counts.set(null, 0);
    conversations.forEach((conversation) => {
      if (conversation.status !== "active") return;
      const key = conversation.projectId ?? null;
      counts.set(key, (counts.get(key) ?? 0) + 1);
    });
    return counts;
  }, [conversations]);

  const projectActivityTimestamp = useMemo(() => {
    const activity = new Map<string, number>();
    conversations.forEach((conversation) => {
      if (conversation.status !== "active" || !conversation.projectId) return;
      const timestamp = new Date(conversation.updatedAt).getTime();
      const previous = activity.get(conversation.projectId) ?? 0;
      if (timestamp > previous) {
        activity.set(conversation.projectId, timestamp);
      }
    });
    return activity;
  }, [conversations]);

  const sortedProjects = useMemo(() => {
    const next = [...activeProjects];
    if (projectSortOrder === "alphabetical") {
      next.sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));
      return next;
    }

    next.sort((a, b) => {
      const aActivity = projectActivityTimestamp.get(a.id) ?? new Date(a.updatedAt).getTime();
      const bActivity = projectActivityTimestamp.get(b.id) ?? new Date(b.updatedAt).getTime();
      if (bActivity !== aActivity) {
        return bActivity - aActivity;
      }
      return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    });

    return next;
  }, [activeProjects, projectActivityTimestamp, projectSortOrder]);

  const activeConversationFallback = useMemo(
    () =>
      conversations
        .filter((conversation) => conversation.status === "active")
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0] ?? null,
    [conversations]
  );

  useEffect(() => {
    if (!isCreating) return;
    projectInputRef.current?.focus();
    projectInputRef.current?.select();
  }, [isCreating]);

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Project name is required.");
      return;
    }

    const duplicate = activeProjects.some((project) => project.name.trim().toLowerCase() === trimmed.toLowerCase());
    if (duplicate) {
      setError("A project with this name already exists.");
      return;
    }

    try {
      const projectId = createProject({ name: trimmed });
      setWorkspaceView("project", projectId);
      setValue("");
      setError(null);
      setIsCreating(false);
      success("Project created");
    } catch {
      setError("Could not create project. Please try again.");
    }
  };

  const handleInputKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setIsCreating(false);
      setError(null);
      setValue("");
    }
  };

  const handleProjectRename = (projectId: string, nextName: string) => {
    try {
      renameProject(projectId, nextName);
      success("Project renamed");
    } catch {
      showError("Rename failed", "Could not rename this project.");
    }
  };

  const handleProjectArchive = (projectId: string) => {
    try {
      archiveProject(projectId);
      if (currentView === "project" && activeProjectId === projectId) {
        setWorkspaceView("all_chats");
        if (activeConversationFallback) {
          setActiveConversation(activeConversationFallback.id);
        }
      }
      success("Project archived");
    } catch {
      showError("Archive failed", "Could not archive this project.");
    }
  };

  const handleProjectDelete = (projectId: string) => {
    try {
      deleteProject(projectId);
      if (currentView === "project" && activeProjectId === projectId) {
        setWorkspaceView("all_chats");
        if (activeConversationFallback) {
          setActiveConversation(activeConversationFallback.id);
        }
      }
      success("Project deleted");
    } catch {
      showError("Delete failed", "Could not delete this project.");
    }
  };

  const handleDropConversation = (conversationId: string, projectId: string | null) => {
    try {
      const conversation = getConversationById(conversationId);
      if (!conversation || conversation.status !== "active") return;

      const currentProjectId = conversation.projectId ?? null;
      if (currentProjectId === projectId) return;

      if (projectId === null) {
        if (currentProjectId) {
          removeConversation(currentProjectId, conversationId);
        }
        success("Conversation moved", "Moved to unassigned chats.");
        return;
      }

      associateConversation(projectId, conversationId);
      success("Conversation moved", "Moved to project.");
    } catch {
      showError("Move failed", "Could not move this conversation.");
    }
  };

  if (compact) {
    return null;
  }

  const projectNames = sortedProjects.map((project) => project.name);

  return (
    <section className="space-y-2" aria-label="Projects">
      <div className="flex items-center justify-between gap-2 px-1">
        <button
          type="button"
          onClick={() => setIsExpanded((previous) => !previous)}
          className="inline-flex min-h-8 items-center gap-1 rounded-md px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400 hover:bg-slate-800 hover:text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          aria-expanded={isExpanded}
          aria-controls="workspace-project-list"
        >
          {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          <span>Projects</span>
          <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">{sortedProjects.length}</span>
        </button>
        <button
          type="button"
          onClick={() => {
            setIsExpanded(true);
            setIsCreating(true);
            setError(null);
          }}
          className="inline-flex min-h-8 items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          aria-label="Create project"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>New project</span>
        </button>
      </div>

      {isExpanded ? (
        <div id="workspace-project-list" className="space-y-2">
          <div className="flex items-center justify-end px-1">
            <label className="inline-flex items-center gap-1 text-[10px] text-slate-400" htmlFor="workspace-project-sort">
              <ArrowUpDown className="h-3.5 w-3.5" />
              <span>Sort</span>
            </label>
            <select
              id="workspace-project-sort"
              value={projectSortOrder}
              onChange={(event) => setProjectSortOrder(event.target.value as "last_active" | "alphabetical")}
              className="ml-2 h-8 rounded-md border border-slate-700 bg-slate-900 px-2 text-xs text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            >
              <option value="last_active">Last active</option>
              <option value="alphabetical">Alphabetical</option>
            </select>
          </div>

          {isCreating ? (
            <form onSubmit={handleCreate} className="space-y-2 rounded-lg border border-slate-700 bg-slate-900 p-2">
              <label htmlFor="workspace-project-name" className="sr-only">
                Project name
              </label>
              <div className="flex items-center gap-2">
                <FolderPlus className="h-4 w-4 shrink-0 text-slate-400" />
                <input
                  ref={projectInputRef}
                  id="workspace-project-name"
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="New project"
                  className="h-8 w-full rounded-md border border-slate-700 bg-slate-950 px-2 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  className="inline-flex h-8 items-center gap-1 rounded-md bg-slate-700 px-3 text-xs font-medium text-slate-100 hover:bg-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Create</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false);
                    setValue("");
                    setError(null);
                  }}
                  className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-700 px-3 text-xs text-slate-300 hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
                >
                  <X className="h-3.5 w-3.5" />
                  <span>Cancel</span>
                </button>
              </div>
              <p className="text-[10px] text-slate-500">Press Enter to create, Esc to cancel.</p>
              {error ? <p className="text-[11px] text-rose-300">{error}</p> : null}
            </form>
          ) : null}

          <div className="space-y-1">
            <ProjectListItem
              project={null}
              active={currentView === "project" && activeProjectId === null}
              count={projectCounts.get(null) ?? 0}
              onSelect={() => {
                setWorkspaceView("project", null);
                const unassignedConversation = conversations
                  .filter((conversation) => conversation.status === "active" && !conversation.projectId)
                  .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                if (unassignedConversation) {
                  setActiveConversation(unassignedConversation.id);
                }
                onAfterSelect?.();
              }}
              onDropConversation={handleDropConversation}
            />

            {sortedProjects.map((project) => (
              <ProjectListItem
                key={project.id}
                project={project}
                active={currentView === "project" && activeProjectId === project.id}
                count={projectCounts.get(project.id) ?? 0}
                canManage
                existingProjectNames={projectNames}
                onRenameProject={handleProjectRename}
                onArchiveProject={handleProjectArchive}
                onDeleteProject={handleProjectDelete}
                onDropConversation={handleDropConversation}
                onSelect={() => {
                  setWorkspaceView("project", project.id);
                  const projectConversation = conversations
                    .filter((conversation) => conversation.status === "active" && conversation.projectId === project.id)
                    .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                  if (projectConversation) {
                    setActiveConversation(projectConversation.id);
                  }
                  onAfterSelect?.();
                }}
              />
            ))}

            {sortedProjects.length === 0 ? (
              <p className="px-2 text-xs text-slate-500">No projects yet. Create your first project.</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
