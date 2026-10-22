import { LocalConversationRepository, LocalProjectRepository } from "./local-storage-repositories";
import type { ConversationRepository, ProjectRepository } from "./workspace-repository.types";

export type { ConversationRepository, ProjectRepository } from "./workspace-repository.types";
export type { CreateConversationInput, CreateProjectInput, UpdateConversationInput, UpdateProjectInput } from "./workspace-repository.types";

/**
 * Default persistence adapters are local-storage based.
 * Swap these with API-backed implementations later without touching UI components.
 */
export const workspaceConversationRepository: ConversationRepository = new LocalConversationRepository();
export const workspaceProjectRepository: ProjectRepository = new LocalProjectRepository();
