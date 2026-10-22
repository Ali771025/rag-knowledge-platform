import type { AgentMessage } from "./conversation";

export type ChatMessage = AgentMessage;

export const CONVERSATION_STATUSES = ["active", "archived", "deleted"] as const;
export type ConversationStatus = (typeof CONVERSATION_STATUSES)[number];

export interface ConversationMetadata {
  model?: string;
  provider?: string;
  [key: string]: unknown;
}

export interface Conversation {
  id: string;
  title: string;
  status: ConversationStatus;
  isPinned?: boolean;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string;
  deletedAt?: string;
  projectId?: string | null;
  messages: ChatMessage[];
  metadata?: ConversationMetadata;
}

export const PROJECT_STATUSES = ["active", "archived", "deleted"] as const;
export type ProjectStatus = (typeof PROJECT_STATUSES)[number];

export const PROJECT_SORT_ORDERS = ["last_active", "alphabetical"] as const;
export type ProjectSortOrder = (typeof PROJECT_SORT_ORDERS)[number];

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  createdAt: string;
  updatedAt: string;
  archivedAt?: string;
  deletedAt?: string;
  conversationIds: string[];
  metadata?: Record<string, unknown>;
}

export const WORKSPACE_VIEWS = ["all_chats", "project", "archived"] as const;
export type WorkspaceView = (typeof WORKSPACE_VIEWS)[number];

export const SIDEBAR_STATES = ["expanded", "collapsed"] as const;
export type SidebarState = (typeof SIDEBAR_STATES)[number];
