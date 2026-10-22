import type { ChatState } from "./chat-store";
import type { ConnectionState } from "./connection-store";
import type { MessageStreamingState } from "./message-streaming-store";
import type { OnboardingState } from "./onboarding-store";
import type { SessionState } from "./session-store";
import type { UiState } from "./ui-store";
import {
  selectHasNextBestActions,
  selectResumableSession,
  selectSummaryAvailable,
  selectTimelineCompletionPercent
} from "@/features/onboarding";

export const selectMessages = (state: ChatState) => state.messages;
export const selectConnectionStatusModel = (state: ConnectionState) => state.statusModel;
export const selectConnectionStatus = (state: ConnectionState) => state.statusModel.status;
export const selectConnectionBannerState = (state: ConnectionState) => state.statusModel.banner;
export const selectConnectionHealthState = (state: ConnectionState) => state.statusModel.health;
export const selectConnectionRecoveryState = (state: ConnectionState) => state.statusModel.recovery;
export const selectIsConnectionRecovering = (state: ConnectionState) => state.statusModel.isRecovering;
export const selectIsConnectionOffline = (state: ConnectionState) => state.statusModel.isOffline;
export const selectIsConnectionUnavailable = (state: ConnectionState) => state.statusModel.isUnavailable;
export const selectSessionPersona = (state: SessionState) => state.persona;
export const selectFunnelStage = (state: SessionState) => state.funnelStage;
export const selectIsStreaming = (state: UiState) => state.isStreaming;
export const selectStreamingLifecycle = (state: MessageStreamingState) => state.lifecycle;
export const selectStreamingActiveMessageId = (state: MessageStreamingState) => state.activeMessageId;

export const selectOnboardingWorkflow = (state: OnboardingState) => state.workflow;
export const selectCurrentWorkflowStage = (state: OnboardingState) => state.workflow.stage;
export const selectTimelineReadiness = (state: OnboardingState) => selectTimelineCompletionPercent(state.workflow.timeline) > 0;
export const selectNextActionsAvailability = (state: OnboardingState) => selectHasNextBestActions(state.workflow.nextBestActions);
export const selectSessionResumability = (state: OnboardingState) => selectResumableSession(state.workflow.sessionResume);
export const selectSummaryAvailability = (state: OnboardingState) => selectSummaryAvailable(state.workflow.conversationSummary);
