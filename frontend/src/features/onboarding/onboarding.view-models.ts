import type {
  AdaptivePromptKind,
  ConversationSummaryState,
  ContextualWorkflowCardVariant,
  NextBestActionKind,
  OnboardingTimelineStepStatus,
  OnboardingWorkflowStage,
  OnboardingWorkflowStatus,
  SessionResumeStatus
} from "./onboarding.types";

export interface OnboardingTimelineStepViewModel {
  id: string;
  title: string;
  description: string;
  stage: OnboardingWorkflowStage;
  status: OnboardingTimelineStepStatus;
  order: number;
  isCurrent: boolean;
  isComplete: boolean;
  isBlocked: boolean;
  metadata: Record<string, unknown>;
}

export interface OnboardingNextBestActionViewModel {
  id: string;
  label: string;
  description: string;
  kind: NextBestActionKind;
  value: string;
  disabled: boolean;
  priority: number;
  isPrimary: boolean;
  metadata: Record<string, unknown>;
}

export interface OnboardingSessionResumeStateViewModel {
  sessionId: string;
  status: SessionResumeStatus;
  lastActiveAt: string | null;
  message: string;
  isAvailable: boolean;
  isRecommended: boolean;
  canResume: boolean;
  metadata: Record<string, unknown>;
}

export interface AdaptivePromptItemViewModel {
  id: string;
  prompt: string;
  kind: AdaptivePromptKind;
  stage: OnboardingWorkflowStage;
  priority: number;
  confidence: number | null;
  metadata: Record<string, unknown>;
}

export interface ConversationSummaryViewModel {
  id: string;
  title: string;
  summary: string;
  highlights: string[];
  stage: OnboardingWorkflowStage;
  state: ConversationSummaryState;
  messageCount: number;
  lastUpdatedAt: string | null;
  metadata: Record<string, unknown>;
}

export interface ContextualWorkflowCardViewModel {
  id: string;
  title: string;
  body: string;
  variant: ContextualWorkflowCardVariant;
  stage: OnboardingWorkflowStage;
  actions: OnboardingNextBestActionViewModel[];
  metadata: Record<string, unknown>;
}

export interface OnboardingWorkflowViewModel {
  stage: OnboardingWorkflowStage;
  status: OnboardingWorkflowStatus;
  timeline: OnboardingTimelineStepViewModel[];
  nextBestActions: OnboardingNextBestActionViewModel[];
  sessionResume: OnboardingSessionResumeStateViewModel;
  adaptivePrompts: AdaptivePromptItemViewModel[];
  conversationSummary: ConversationSummaryViewModel | null;
  workflowCards: ContextualWorkflowCardViewModel[];
  metadata: Record<string, unknown>;
}
