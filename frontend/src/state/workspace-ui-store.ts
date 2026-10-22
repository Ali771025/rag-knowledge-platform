import { create } from "zustand";
import type { ProjectSortOrder, SidebarState, WorkspaceView } from "@/types";
import { createLocalStorageAdapter } from "./workspace-storage";

interface WorkspaceUiPersistedState {
  sidebarState: SidebarState;
  currentView: WorkspaceView;
  searchQuery: string;
  activeProjectId: string | null;
  projectSortOrder: ProjectSortOrder;
}

export interface WorkspaceUiState {
  sidebarState: SidebarState;
  isMobileDrawerOpen: boolean;
  searchQuery: string;
  currentView: WorkspaceView;
  activeProjectId: string | null;
  projectSortOrder: ProjectSortOrder;
}

export interface WorkspaceUiActions {
  setSidebarState: (state: SidebarState) => void;
  toggleSidebarState: () => void;
  setMobileDrawerOpen: (isOpen: boolean) => void;
  toggleMobileDrawer: () => void;
  setSearchQuery: (query: string) => void;
  setWorkspaceView: (view: WorkspaceView, projectId?: string | null) => void;
  setProjectSortOrder: (order: ProjectSortOrder) => void;
  clearWorkspaceUi: () => void;
}

export type WorkspaceUiStore = WorkspaceUiState & WorkspaceUiActions;

const STORAGE_KEY = "ragai.workspace.ui.v1";

const workspaceUiStorage = createLocalStorageAdapter<WorkspaceUiPersistedState>(STORAGE_KEY);

function persistUiState(state: WorkspaceUiState) {
  workspaceUiStorage.save({
    sidebarState: state.sidebarState,
    currentView: state.currentView,
    searchQuery: state.searchQuery,
    activeProjectId: state.activeProjectId,
    projectSortOrder: state.projectSortOrder
  });
}

const persistedState = workspaceUiStorage.load();

export const initialWorkspaceUiState: WorkspaceUiState = {
  sidebarState: persistedState?.sidebarState ?? "expanded",
  isMobileDrawerOpen: false,
  searchQuery: persistedState?.searchQuery ?? "",
  currentView: persistedState?.currentView ?? "all_chats",
  activeProjectId: persistedState?.activeProjectId ?? null,
  projectSortOrder: persistedState?.projectSortOrder ?? "last_active"
};

export const useWorkspaceUiStore = create<WorkspaceUiStore>((set) => ({
  ...initialWorkspaceUiState,
  setSidebarState: (sidebarState) => {
    set((state) => {
      const nextState = { ...state, sidebarState };
      persistUiState(nextState);
      return nextState;
    });
  },
  toggleSidebarState: () => {
    set((state) => {
      const nextState: WorkspaceUiState = {
        ...state,
        sidebarState: state.sidebarState === "expanded" ? "collapsed" : "expanded"
      };
      persistUiState(nextState);
      return nextState;
    });
  },
  setMobileDrawerOpen: (isMobileDrawerOpen) => {
    set((state) => {
      if (state.isMobileDrawerOpen === isMobileDrawerOpen) {
        return state;
      }
      return {
        ...state,
        isMobileDrawerOpen
      };
    });
  },
  toggleMobileDrawer: () => {
    set((state) => ({
      ...state,
      isMobileDrawerOpen: !state.isMobileDrawerOpen
    }));
  },
  setSearchQuery: (searchQuery) => {
    set((state) => {
      if (state.searchQuery === searchQuery) {
        return state;
      }
      const nextState: WorkspaceUiState = {
        ...state,
        searchQuery
      };
      persistUiState(nextState);
      return nextState;
    });
  },
  setWorkspaceView: (currentView, projectId = null) => {
    set((state) => {
      const nextProjectId = currentView === "project" ? projectId : null;
      if (state.currentView === currentView && state.activeProjectId === nextProjectId) {
        return state;
      }
      const nextState: WorkspaceUiState = {
        ...state,
        currentView,
        activeProjectId: nextProjectId
      };
      persistUiState(nextState);
      return nextState;
    });
  },
  setProjectSortOrder: (projectSortOrder) => {
    set((state) => {
      if (state.projectSortOrder === projectSortOrder) {
        return state;
      }
      const nextState: WorkspaceUiState = {
        ...state,
        projectSortOrder
      };
      persistUiState(nextState);
      return nextState;
    });
  },
  clearWorkspaceUi: () => {
    workspaceUiStorage.clear();
    set(initialWorkspaceUiState);
  }
}));
