import { useMemo } from "react";
import { useWorkspaceConversationsStore } from "./workspace-conversations-store";
import { useWorkspaceProjectsStore } from "./workspace-projects-store";
import { useWorkspaceUiStore } from "./workspace-ui-store";

export const useWorkspaceConversations = () => {
  const conversations = useWorkspaceConversationsStore((state) => state.conversations);
  return useMemo(
    () => conversations.filter((conversation) => conversation.status !== "deleted"),
    [conversations]
  );
};

export const useWorkspaceProjects = () => {
  const projects = useWorkspaceProjectsStore((state) => state.projects);
  return useMemo(() => projects.filter((project) => project.status !== "deleted"), [projects]);
};

export function useActiveWorkspaceConversation() {
  const conversations = useWorkspaceConversationsStore((state) => state.conversations);
  const activeConversationId = useWorkspaceConversationsStore((state) => state.activeConversationId);

  return useMemo(() => {
    if (!activeConversationId) return null;
    return conversations.find((conversation) => conversation.id === activeConversationId) ?? null;
  }, [activeConversationId, conversations]);
}

export const useWorkspaceSidebarState = () => useWorkspaceUiStore((state) => state.sidebarState);
export const useWorkspaceSearchQuery = () => useWorkspaceUiStore((state) => state.searchQuery);
export const useWorkspaceView = () => useWorkspaceUiStore((state) => state.currentView);
