import { useMemo } from "react";
import {
  selectCurrentTimelineStep,
  selectHasNextBestActions,
  selectOnboardingReady,
  selectPrimaryNextBestAction,
  selectResumableSession,
  selectSummaryAvailable,
  selectTimelineCompletionPercent,
  selectVisibleAdaptivePrompts,
  selectVisibleWorkflowCards
} from "@/features/onboarding";
import {
  useConnectionStatusModel,
  useOnboardingStore,
  useSessionFunnelStage,
  useSessionPersona,
  useStreamingLifecycle,
  useUiStreaming
} from "@/state";
import { useChatMessages } from "@/state";

export interface WorkflowDerivedContext {
  persona: ReturnType<typeof useSessionPersona>;
  funnelStage: ReturnType<typeof useSessionFunnelStage>;
  isStreaming: boolean;
  streamingLifecycle: ReturnType<typeof useStreamingLifecycle>;
  connection: ReturnType<typeof useConnectionStatusModel>;
  messageCount: number;
}

export interface UseOnboardingWorkflowResult {
  stage: ReturnType<typeof useOnboardingStore.getState>["workflow"]["stage"];
  status: ReturnType<typeof useOnboardingStore.getState>["workflow"]["status"];
  timeline: ReturnType<typeof useOnboardingStore.getState>["workflow"]["timeline"];
  timelineCompletionPercent: number;
  currentTimelineStep: ReturnType<typeof selectCurrentTimelineStep>;
  nextBestActions: ReturnType<typeof useOnboardingStore.getState>["workflow"]["nextBestActions"];
  hasNextBestActions: boolean;
  primaryNextBestAction: ReturnType<typeof selectPrimaryNextBestAction>;
  sessionResume: ReturnType<typeof useOnboardingStore.getState>["workflow"]["sessionResume"];
  resumable: boolean;
  adaptivePrompts: ReturnType<typeof useOnboardingStore.getState>["workflow"]["adaptivePrompts"];
  visibleAdaptivePrompts: ReturnType<typeof selectVisibleAdaptivePrompts>;
  conversationSummary: ReturnType<typeof useOnboardingStore.getState>["workflow"]["conversationSummary"];
  summaryAvailable: boolean;
  workflowCards: ReturnType<typeof useOnboardingStore.getState>["workflow"]["workflowCards"];
  visibleWorkflowCards: ReturnType<typeof selectVisibleWorkflowCards>;
  isReady: boolean;
  context: WorkflowDerivedContext;
}

export function useOnboardingWorkflow(): UseOnboardingWorkflowResult {
  const workflow = useOnboardingStore((state) => state.workflow);
  const persona = useSessionPersona();
  const funnelStage = useSessionFunnelStage();
  const isStreaming = useUiStreaming();
  const streamingLifecycle = useStreamingLifecycle();
  const connection = useConnectionStatusModel();
  const messages = useChatMessages();

  return useMemo(() => {
    const currentTimelineStep = selectCurrentTimelineStep(workflow.timeline);
    const timelineCompletionPercent = selectTimelineCompletionPercent(workflow.timeline);
    const hasNextBestActions = selectHasNextBestActions(workflow.nextBestActions);
    const primaryNextBestAction = selectPrimaryNextBestAction(workflow.nextBestActions);
    const resumable = selectResumableSession(workflow.sessionResume);
    const summaryAvailable = selectSummaryAvailable(workflow.conversationSummary);
    const visibleAdaptivePrompts = selectVisibleAdaptivePrompts(workflow.adaptivePrompts);
    const visibleWorkflowCards = selectVisibleWorkflowCards(workflow.workflowCards);
    const isReady = selectOnboardingReady(workflow);

    return {
      stage: workflow.stage,
      status: workflow.status,
      timeline: workflow.timeline,
      timelineCompletionPercent,
      currentTimelineStep,
      nextBestActions: workflow.nextBestActions,
      hasNextBestActions,
      primaryNextBestAction,
      sessionResume: workflow.sessionResume,
      resumable,
      adaptivePrompts: workflow.adaptivePrompts,
      visibleAdaptivePrompts,
      conversationSummary: workflow.conversationSummary,
      summaryAvailable,
      workflowCards: workflow.workflowCards,
      visibleWorkflowCards,
      isReady,
      context: {
        persona,
        funnelStage,
        isStreaming,
        streamingLifecycle,
        connection,
        messageCount: messages.length
      }
    };
  }, [connection, funnelStage, isStreaming, messages.length, persona, streamingLifecycle, workflow]);
}
