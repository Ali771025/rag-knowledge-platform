import { useAnalytics } from "@/hooks/use-analytics";
import { Archive, FolderKanban, MessageSquareText } from "lucide-react";
import { useWorkspaceConversationsStore, useWorkspaceUiStore } from "@/state";
import { ConversationList } from "./conversation-list";
import { NewChatButton } from "./new-chat-button";
import { ProjectSection } from "./project-section";
import { SidebarHeader } from "./sidebar-header";
import { SidebarSearch } from "./sidebar-search";

interface SidebarProps {
  compact: boolean;
  mobile: boolean;
  onCloseMobile?: () => void;
}

export function Sidebar({ compact, mobile, onCloseMobile }: SidebarProps) {
  const { trackNewChatClicked } = useAnalytics();
  const createConversation = useWorkspaceConversationsStore((state) => state.createConversation);
  const conversations = useWorkspaceConversationsStore((state) => state.conversations);
  const activeConversationId = useWorkspaceConversationsStore((state) => state.activeConversationId);
  const setActiveConversation = useWorkspaceConversationsStore((state) => state.setActiveConversation);
  const currentView = useWorkspaceUiStore((state) => state.currentView);
  const activeProjectId = useWorkspaceUiStore((state) => state.activeProjectId);
  const setWorkspaceView = useWorkspaceUiStore((state) => state.setWorkspaceView);
  const searchQuery = useWorkspaceUiStore((state) => state.searchQuery);
  const setSearchQuery = useWorkspaceUiStore((state) => state.setSearchQuery);
  const toggleSidebarState = useWorkspaceUiStore((state) => state.toggleSidebarState);

  const handleCreateChat = () => {
    const shouldCreateInProject = currentView === "project";
    trackNewChatClicked(currentView, activeConversationId);
    createConversation({
      projectId: shouldCreateInProject ? activeProjectId : null
    });
    setWorkspaceView(shouldCreateInProject ? "project" : "all_chats", shouldCreateInProject ? activeProjectId : undefined);
    onCloseMobile?.();
  };

  const activeChatsCount = conversations.filter((conversation) => conversation.status === "active").length;
  const archivedChatsCount = conversations.filter((conversation) => conversation.status === "archived").length;

  return (
    <div
      className="flex h-full flex-col bg-slate-950 text-slate-100"
      aria-label="Workspace sidebar"
      role="complementary"
    >
      <SidebarHeader
        compact={compact}
        showClose={mobile}
        onClose={onCloseMobile}
        onToggleCompact={mobile ? undefined : toggleSidebarState}
      />

      <div className="flex flex-1 flex-col gap-3 overflow-y-auto px-3 py-3">
        <NewChatButton compact={compact} onClick={handleCreateChat} />
        <SidebarSearch compact={compact} query={searchQuery} onQueryChange={setSearchQuery} onClear={() => setSearchQuery("")} />

        {!compact ? (
          <nav className="space-y-1" aria-label="Main sidebar navigation">
            <button
              type="button"
              onClick={() => {
                setWorkspaceView("all_chats");
                const latestConversation = conversations
                  .filter((conversation) => conversation.status === "active")
                  .sort((a, b) => {
                    const pinDelta = Number(Boolean(b.isPinned)) - Number(Boolean(a.isPinned));
                    if (pinDelta !== 0) return pinDelta;
                    return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
                  })[0];
                if (latestConversation) {
                  setActiveConversation(latestConversation.id);
                }
                onCloseMobile?.();
              }}
              className={`min-h-10 w-full rounded-md px-2 py-1.5 text-left text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 ${
                currentView === "all_chats" ? "bg-slate-700 text-slate-100" : "text-slate-300 hover:bg-slate-800"
              }`}
            >
                <span className="flex w-full items-center justify-between">
                  <span className="inline-flex items-center gap-2">
                    <MessageSquareText className="h-3.5 w-3.5 text-slate-400" />
                    <span>All chats</span>
                  </span>
                  <span className="text-[10px] text-slate-400">{activeChatsCount}</span>
                </span>
              </button>
            <button
              type="button"
              onClick={() => {
                setWorkspaceView("archived");
                const latestArchivedConversation = conversations
                  .filter((conversation) => conversation.status === "archived")
                  .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())[0];
                if (latestArchivedConversation) {
                  setActiveConversation(latestArchivedConversation.id);
                }
                onCloseMobile?.();
              }}
              className={`min-h-10 w-full rounded-md px-2 py-1.5 text-left text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 ${
                currentView === "archived" ? "bg-slate-700 text-slate-100" : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <span className="flex w-full items-center justify-between">
                <span className="inline-flex items-center gap-2">
                  <Archive className="h-3.5 w-3.5 text-slate-400" />
                  <span>Archived chats</span>
                </span>
                <span className="text-[10px] text-slate-400">{archivedChatsCount}</span>
              </span>
            </button>
          </nav>
        ) : null}

        <ConversationList compact={compact} onAfterSelect={onCloseMobile} />
        {!compact ? (
          <p className="mt-1 inline-flex items-center gap-1.5 px-1 text-[10px] uppercase tracking-wide text-slate-500">
            <FolderKanban className="h-3 w-3" />
            Projects
          </p>
        ) : null}
        <ProjectSection compact={compact} onAfterSelect={onCloseMobile} />
      </div>
    </div>
  );
}
