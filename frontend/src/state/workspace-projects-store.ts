import { create } from "zustand";
import {
  workspaceProjectRepository,
  type CreateProjectInput as RepositoryCreateProjectInput
} from "@/core/workspace/repositories";
import type { Project } from "@/types";
import { useWorkspaceConversationsStore } from "./workspace-conversations-store";

interface ProjectListOptions {
  includeArchived?: boolean;
  includeDeleted?: boolean;
}

interface CreateProjectInput extends RepositoryCreateProjectInput {
  id?: string;
  name?: string;
  metadata?: Record<string, unknown>;
}

export interface WorkspaceProjectsState {
  projects: Project[];
}

export interface WorkspaceProjectsActions {
  listProjects: (options?: ProjectListOptions) => Project[];
  getProjectById: (projectId: string) => Project | null;
  createProject: (input?: CreateProjectInput) => string;
  renameProject: (projectId: string, name: string) => void;
  archiveProject: (projectId: string) => void;
  unarchiveProject: (projectId: string) => void;
  deleteProject: (projectId: string) => void;
  associateConversation: (projectId: string, conversationId: string) => void;
  removeConversation: (projectId: string, conversationId: string) => void;
}

export type WorkspaceProjectsStore = WorkspaceProjectsState & WorkspaceProjectsActions;

function nowIso() {
  return new Date().toISOString();
}

function refreshProjectsFromRepository(): Project[] {
  return workspaceProjectRepository.listProjects();
}

const initialState: WorkspaceProjectsState = {
  projects: refreshProjectsFromRepository()
};

export const useWorkspaceProjectsStore = create<WorkspaceProjectsStore>((set, get) => ({
  ...initialState,
  listProjects: (options) => {
    const includeArchived = options?.includeArchived ?? true;
    const includeDeleted = options?.includeDeleted ?? false;

    return get().projects.filter((project) => {
      if (!includeDeleted && project.status === "deleted") return false;
      if (!includeArchived && project.status === "archived") return false;
      return true;
    });
  },
  getProjectById: (projectId) => {
    if (!projectId) return null;
    return get().projects.find((project) => project.id === projectId) ?? null;
  },
  createProject: (input) => {
    const project = workspaceProjectRepository.createProject(input);

    set({
      projects: refreshProjectsFromRepository()
    });

    return project.id;
  },
  renameProject: (projectId, name) => {
    const trimmed = name.trim();
    if (!projectId || !trimmed) return;

    const updated = workspaceProjectRepository.updateProject(projectId, {
      name: trimmed
    });
    if (!updated) return;

    set({
      projects: refreshProjectsFromRepository()
    });
  },
  archiveProject: (projectId) => {
    if (!projectId) return;

    const updated = workspaceProjectRepository.updateProject(projectId, {
      status: "archived",
      archivedAt: nowIso()
    });
    if (!updated) return;

    set({
      projects: refreshProjectsFromRepository()
    });
  },
  unarchiveProject: (projectId) => {
    if (!projectId) return;

    const updated = workspaceProjectRepository.updateProject(projectId, {
      status: "active",
      archivedAt: undefined
    });
    if (!updated) return;

    set({
      projects: refreshProjectsFromRepository()
    });
  },
  deleteProject: (projectId) => {
    if (!projectId) return;
    const deleted = workspaceProjectRepository.deleteProject(projectId);
    if (!deleted) return;

    for (const conversationId of useWorkspaceConversationsStore.getState().conversations
      .filter((conversation) => conversation.projectId === projectId)
      .map((conversation) => conversation.id)) {
      useWorkspaceConversationsStore.getState().setConversationProject(conversationId, null);
    }

    set({
      projects: refreshProjectsFromRepository()
    });
  },
  associateConversation: (projectId, conversationId) => {
    if (!projectId || !conversationId) return;

    const conversation = useWorkspaceConversationsStore.getState().getConversationById(conversationId);
    if (!conversation || conversation.status === "deleted") return;

    const previousProjectId = conversation.projectId ?? null;
    const target = workspaceProjectRepository.getProject(projectId);
    if (!target || target.status === "deleted") return;

    const updatedTargetConversationIds = [...new Set([...target.conversationIds, conversationId])];
    workspaceProjectRepository.updateProject(projectId, {
      conversationIds: updatedTargetConversationIds
    });

    if (previousProjectId && previousProjectId !== projectId) {
      const previousProject = workspaceProjectRepository.getProject(previousProjectId);
      if (previousProject) {
        workspaceProjectRepository.updateProject(previousProject.id, {
          conversationIds: previousProject.conversationIds.filter((id) => id !== conversationId)
        });
      }
    }

    useWorkspaceConversationsStore.getState().setConversationProject(conversationId, projectId);
    set({
      projects: refreshProjectsFromRepository()
    });
  },
  removeConversation: (projectId, conversationId) => {
    if (!projectId || !conversationId) return;
    const target = workspaceProjectRepository.getProject(projectId);
    if (!target) return;

    workspaceProjectRepository.updateProject(projectId, {
      conversationIds: target.conversationIds.filter((id) => id !== conversationId)
    });

    const conversation = useWorkspaceConversationsStore.getState().getConversationById(conversationId);
    if (conversation?.projectId === projectId) {
      useWorkspaceConversationsStore.getState().setConversationProject(conversationId, null);
    }

    set({
      projects: refreshProjectsFromRepository()
    });
  }
}));
