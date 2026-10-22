import { useChatStore } from "./chat-store";
import { useConnectionStore } from "./connection-store";
import { useMessageStreamingStore } from "./message-streaming-store";
import { useOnboardingStore } from "./onboarding-store";
import { useSessionStore } from "./session-store";
import { useUiStore } from "./ui-store";
import {
  selectCurrentWorkflowStage,
  selectConnectionBannerState,
  selectConnectionHealthState,
  selectConnectionRecoveryState,
  selectConnectionStatus,
  selectConnectionStatusModel,
  selectFunnelStage,
  selectIsStreaming,
  selectIsConnectionOffline,
  selectIsConnectionRecovering,
  selectIsConnectionUnavailable,
  selectMessages,
  selectNextActionsAvailability,
  selectSessionPersona,
  selectSessionResumability,
  selectSummaryAvailability,
  selectTimelineReadiness,
  selectStreamingLifecycle
} from "./selectors";

export const useChatMessages = () => useChatStore(selectMessages);
export const useConnectionStatusModel = () => useConnectionStore(selectConnectionStatusModel);
export const useConnectionStatus = () => useConnectionStore(selectConnectionStatus);
export const useConnectionBannerState = () => useConnectionStore(selectConnectionBannerState);
export const useConnectionHealthState = () => useConnectionStore(selectConnectionHealthState);
export const useConnectionRecoveryState = () => useConnectionStore(selectConnectionRecoveryState);
export const useIsConnectionRecovering = () => useConnectionStore(selectIsConnectionRecovering);
export const useIsConnectionOffline = () => useConnectionStore(selectIsConnectionOffline);
export const useIsConnectionUnavailable = () => useConnectionStore(selectIsConnectionUnavailable);
export const useSessionPersona = () => useSessionStore(selectSessionPersona);
export const useSessionFunnelStage = () => useSessionStore(selectFunnelStage);
export const useUiStreaming = () => useUiStore(selectIsStreaming);
export const useStreamingLifecycle = () => useMessageStreamingStore(selectStreamingLifecycle);
export const useCurrentWorkflowStage = () => useOnboardingStore(selectCurrentWorkflowStage);
export const useTimelineReadiness = () => useOnboardingStore(selectTimelineReadiness);
export const useNextActionsAvailability = () => useOnboardingStore(selectNextActionsAvailability);
export const useSessionResumability = () => useOnboardingStore(selectSessionResumability);
export const useSummaryAvailability = () => useOnboardingStore(selectSummaryAvailability);
export {
  useActiveWorkspaceConversation,
  useWorkspaceConversations,
  useWorkspaceProjects,
  useWorkspaceSearchQuery,
  useWorkspaceSidebarState,
  useWorkspaceView
} from "./workspace-hooks";
