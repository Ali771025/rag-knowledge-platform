import type { Conversation, Project } from "@/types";
import type {
  ConversationRepository,
  CreateConversationInput,
  CreateProjectInput,
  ProjectRepository,
  UpdateConversationInput,
  UpdateProjectInput
} from "./workspace-repository.types";

const CONVERSATION_STORAGE_KEY = "ragai.workspace.conversations.v1";
const PROJECT_STORAGE_KEY = "ragai.workspace.projects.v1";
const DEFAULT_CONVERSATION_TITLE = "New chat";
const DEFAULT_PROJECT_NAME = "New project";

interface ConversationStorageSnapshot {
  conversations: Conversation[];
  activeConversationId?: string | null;
}

interface ProjectStorageSnapshot {
  projects: Project[];
}

function isBrowser() {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readJson<T>(key: string): T | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeJson<T>(key: string, value: T) {
  if (!isBrowser()) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Local fallback must never break runtime behavior.
  }
}

function nowIso() {
  return new Date().toISOString();
}

function createId(prefix: string) {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}`;
}

function sanitizeConversation(input: Conversation): Conversation {
  const createdAt = input.createdAt || nowIso();
  return {
    ...input,
    title: input.title?.trim() || DEFAULT_CONVERSATION_TITLE,
    status: input.status ?? "active",
    isPinned: Boolean(input.isPinned),
    createdAt,
    updatedAt: input.updatedAt || createdAt,
    projectId: input.projectId ?? null,
    messages: Array.isArray(input.messages) ? input.messages : []
  };
}

function sanitizeProject(input: Project): Project {
  const createdAt = input.createdAt || nowIso();
  return {
    ...input,
    name: input.name?.trim() || DEFAULT_PROJECT_NAME,
    status: input.status ?? "active",
    createdAt,
    updatedAt: input.updatedAt || createdAt,
    conversationIds: Array.isArray(input.conversationIds) ? [...new Set(input.conversationIds)] : []
  };
}

function readConversations(): Conversation[] {
  const snapshot = readJson<ConversationStorageSnapshot>(CONVERSATION_STORAGE_KEY);
  return (snapshot?.conversations ?? []).map(sanitizeConversation);
}

function writeConversations(conversations: Conversation[]) {
  const snapshot = readJson<ConversationStorageSnapshot>(CONVERSATION_STORAGE_KEY);
  writeJson<ConversationStorageSnapshot>(CONVERSATION_STORAGE_KEY, {
    activeConversationId: snapshot?.activeConversationId ?? null,
    conversations
  });
}

function readProjects(): Project[] {
  const snapshot = readJson<ProjectStorageSnapshot>(PROJECT_STORAGE_KEY);
  return (snapshot?.projects ?? []).map(sanitizeProject);
}

function writeProjects(projects: Project[]) {
  writeJson<ProjectStorageSnapshot>(PROJECT_STORAGE_KEY, { projects });
}

export class LocalConversationRepository implements ConversationRepository {
  listConversations(): Conversation[] {
    return readConversations();
  }

  getConversation(conversationId: string): Conversation | null {
    if (!conversationId) return null;
    return readConversations().find((conversation) => conversation.id === conversationId) ?? null;
  }

  createConversation(input: CreateConversationInput = {}): Conversation {
    const createdAt = nowIso();
    const conversation: Conversation = {
      id: input.id ?? createId("conversation"),
      title: input.title?.trim() || DEFAULT_CONVERSATION_TITLE,
      status: "active",
      isPinned: false,
      createdAt,
      updatedAt: createdAt,
      archivedAt: undefined,
      deletedAt: undefined,
      projectId: input.projectId ?? null,
      messages: input.messages ? [...input.messages] : [],
      metadata: input.metadata
    };
    const conversations = [conversation, ...readConversations()];
    writeConversations(conversations);
    return conversation;
  }

  updateConversation(conversationId: string, patch: UpdateConversationInput): Conversation | null {
    if (!conversationId) return null;
    const conversations = readConversations();
    let updatedConversation: Conversation | null = null;
    const next = conversations.map((conversation) => {
      if (conversation.id !== conversationId) return conversation;

      const updated: Conversation = {
        ...conversation,
        ...patch,
        id: conversation.id,
        updatedAt: patch.updatedAt ?? nowIso()
      };
      updatedConversation = sanitizeConversation(updated);
      return updatedConversation;
    });

    if (!updatedConversation) return null;
    writeConversations(next);
    return updatedConversation;
  }

  archiveConversation(conversationId: string): Conversation | null {
    const timestamp = nowIso();
    return this.updateConversation(conversationId, {
      status: "archived",
      archivedAt: timestamp,
      updatedAt: timestamp
    });
  }

  deleteConversation(conversationId: string): boolean {
    if (!conversationId) return false;
    const conversations = readConversations();
    const next = conversations.filter((conversation) => conversation.id !== conversationId);
    if (next.length === conversations.length) return false;
    writeConversations(next);
    return true;
  }
}

export class LocalProjectRepository implements ProjectRepository {
  listProjects(): Project[] {
    return readProjects();
  }

  getProject(projectId: string): Project | null {
    if (!projectId) return null;
    return readProjects().find((project) => project.id === projectId) ?? null;
  }

  createProject(input: CreateProjectInput = {}): Project {
    const createdAt = nowIso();
    const project: Project = {
      id: input.id ?? createId("project"),
      name: input.name?.trim() || DEFAULT_PROJECT_NAME,
      status: "active",
      createdAt,
      updatedAt: createdAt,
      archivedAt: undefined,
      deletedAt: undefined,
      conversationIds: [],
      metadata: input.metadata
    };
    const projects = [project, ...readProjects()];
    writeProjects(projects);
    return project;
  }

  updateProject(projectId: string, patch: UpdateProjectInput): Project | null {
    if (!projectId) return null;
    const projects = readProjects();
    let updatedProject: Project | null = null;
    const next = projects.map((project) => {
      if (project.id !== projectId) return project;
      const updated: Project = {
        ...project,
        ...patch,
        id: project.id,
        updatedAt: patch.updatedAt ?? nowIso()
      };
      updatedProject = sanitizeProject(updated);
      return updatedProject;
    });

    if (!updatedProject) return null;
    writeProjects(next);
    return updatedProject;
  }

  deleteProject(projectId: string): boolean {
    if (!projectId) return false;
    const projects = readProjects();
    const next = projects.filter((project) => project.id !== projectId);
    if (next.length === projects.length) return false;
    writeProjects(next);
    return true;
  }
}
