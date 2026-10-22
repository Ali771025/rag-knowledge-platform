import type { Conversation, ConversationMetadata, Project } from "@/types";

export interface CreateConversationInput {
  id?: string;
  title?: string;
  projectId?: string | null;
  messages?: Conversation["messages"];
  metadata?: ConversationMetadata;
}

export interface UpdateConversationInput {
  title?: string;
  projectId?: string | null;
  messages?: Conversation["messages"];
  metadata?: ConversationMetadata;
  status?: Conversation["status"];
  isPinned?: boolean;
  archivedAt?: string;
  deletedAt?: string;
  updatedAt?: string;
}

export interface CreateProjectInput {
  id?: string;
  name?: string;
  metadata?: Record<string, unknown>;
}

export interface UpdateProjectInput {
  name?: string;
  status?: Project["status"];
  archivedAt?: string;
  deletedAt?: string;
  conversationIds?: string[];
  metadata?: Record<string, unknown>;
  updatedAt?: string;
}

export interface ConversationRepository {
  listConversations: () => Conversation[];
  getConversation: (conversationId: string) => Conversation | null;
  createConversation: (input?: CreateConversationInput) => Conversation;
  updateConversation: (conversationId: string, patch: UpdateConversationInput) => Conversation | null;
  archiveConversation: (conversationId: string) => Conversation | null;
  deleteConversation: (conversationId: string) => boolean;
}

export interface ProjectRepository {
  listProjects: () => Project[];
  getProject: (projectId: string) => Project | null;
  createProject: (input?: CreateProjectInput) => Project;
  updateProject: (projectId: string, patch: UpdateProjectInput) => Project | null;
  deleteProject: (projectId: string) => boolean;
}
