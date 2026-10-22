import type {
  AdaptivePromptItemViewModel,
  ConversationSummaryViewModel,
  ContextualWorkflowCardViewModel,
  OnboardingNextBestActionViewModel,
  OnboardingSessionResumeStateViewModel,
  OnboardingTimelineStepViewModel,
  OnboardingWorkflowViewModel
} from "./onboarding.view-models";

export function selectCurrentTimelineStep(
  timeline: OnboardingTimelineStepViewModel[]
): OnboardingTimelineStepViewModel | null {
  return timeline.find((step) => step.isCurrent) ?? timeline.find((step) => step.status === "current") ?? null;
}

export function selectTimelineCompletionPercent(timeline: OnboardingTimelineStepViewModel[]): number {
  if (timeline.length === 0) {
    return 0;
  }

  const completedCount = timeline.filter((step) => step.isComplete).length;
  return Math.round((completedCount / timeline.length) * 100);
}

export function selectHasNextBestActions(actions: OnboardingNextBestActionViewModel[]): boolean {
  return actions.some((action) => !action.disabled);
}

export function selectPrimaryNextBestAction(
  actions: OnboardingNextBestActionViewModel[]
): OnboardingNextBestActionViewModel | null {
  return actions.find((action) => action.isPrimary && !action.disabled) ?? actions.find((action) => !action.disabled) ?? null;
}

export function selectResumableSession(
  sessionResume: OnboardingSessionResumeStateViewModel
): boolean {
  return sessionResume.canResume;
}

export function selectSummaryAvailable(summary: ConversationSummaryViewModel | null): boolean {
  return summary !== null && summary.state !== "empty";
}

export function selectVisibleAdaptivePrompts(
  prompts: AdaptivePromptItemViewModel[],
  limit = 3
): AdaptivePromptItemViewModel[] {
  return prompts.slice(0, Math.max(0, limit));
}

export function selectVisibleWorkflowCards(
  cards: ContextualWorkflowCardViewModel[],
  limit = 3
): ContextualWorkflowCardViewModel[] {
  return cards.slice(0, Math.max(0, limit));
}

export function selectOnboardingReady(viewModel: OnboardingWorkflowViewModel): boolean {
  return viewModel.status === "ready" || viewModel.status === "completed";
}
