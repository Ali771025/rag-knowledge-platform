import { FUNNEL_STAGES, type FunnelStage } from "@/types";
import {
  ONBOARDING_ADAPTIVE_PROMPT_KIND_LABELS,
  ONBOARDING_CONVERSATION_SUMMARY_STATE_LABELS,
  ONBOARDING_DEFAULT_ADAPTIVE_PROMPT_KIND,
  ONBOARDING_DEFAULT_ADAPTIVE_PROMPT_TEXT,
  ONBOARDING_DEFAULT_CONVERSATION_SUMMARY_STATE,
  ONBOARDING_DEFAULT_CONVERSATION_SUMMARY_TITLE,
  ONBOARDING_DEFAULT_NEXT_BEST_ACTION_KIND,
  ONBOARDING_DEFAULT_SESSION_RESUME_STATUS,
  ONBOARDING_DEFAULT_STAGE,
  ONBOARDING_DEFAULT_STATUS,
  ONBOARDING_DEFAULT_TIMELINE_STEP_STATUS,
  ONBOARDING_DEFAULT_WORKFLOW_CARD_TITLE,
  ONBOARDING_DEFAULT_WORKFLOW_CARD_VARIANT,
  ONBOARDING_EMPTY_TEXT,
  ONBOARDING_NEXT_BEST_ACTION_KIND_LABELS,
  ONBOARDING_SESSION_RESUME_STATUS_LABELS,
  ONBOARDING_TIMELINE_STEP_STATUS_LABELS,
  ONBOARDING_WORKFLOW_CARD_VARIANT_LABELS,
  ONBOARDING_WORKFLOW_STAGE_LABELS,
  ONBOARDING_WORKFLOW_STATUS_LABELS,
  ONBOARDING_WORKFLOW_STAGES,
  ONBOARDING_WORKFLOW_STATUSES
} from "./onboarding.constants";
import type {
  AdaptivePromptItemInput,
  ConversationSummaryInput,
  ContextualWorkflowCardInput,
  NextBestActionKind,
  OnboardingNextBestActionInput,
  OnboardingSessionResumeStateInput,
  OnboardingTimelineStepInput,
  OnboardingTimelineStepStatus,
  OnboardingWorkflowSnapshotInput,
  OnboardingWorkflowStage,
  OnboardingWorkflowStatus,
  SessionResumeStatus
} from "./onboarding.types";
import type {
  AdaptivePromptItemViewModel,
  ConversationSummaryViewModel,
  ContextualWorkflowCardViewModel,
  OnboardingNextBestActionViewModel,
  OnboardingSessionResumeStateViewModel,
  OnboardingTimelineStepViewModel,
  OnboardingWorkflowViewModel
} from "./onboarding.view-models";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeText(value: unknown, fallback = ONBOARDING_EMPTY_TEXT): string {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : fallback;
}

function normalizeInteger(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? Math.trunc(value) : fallback;
}

function normalizeBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeMetadata(value: unknown): Record<string, unknown> {
  return isRecord(value) ? { ...value } : {};
}

function isWorkflowStage(value: string): value is OnboardingWorkflowStage {
  return ONBOARDING_WORKFLOW_STAGES.includes(value as OnboardingWorkflowStage);
}

function isWorkflowStatus(value: string): value is OnboardingWorkflowStatus {
  return ONBOARDING_WORKFLOW_STATUSES.includes(value as OnboardingWorkflowStatus);
}

function isTimelineStatus(value: string): value is OnboardingTimelineStepStatus {
  return value === "not_started" || value === "current" || value === "complete" || value === "upcoming" || value === "blocked";
}

function isNextBestActionKind(value: string): value is NextBestActionKind {
  return value === "primary" || value === "secondary" || value === "link" || value === "system";
}

function isSessionResumeStatus(value: string): value is SessionResumeStatus {
  return value === "unavailable" || value === "available" || value === "recommended" || value === "required";
}

function normalizeWorkflowStage(value: unknown): OnboardingWorkflowStage {
  if (typeof value !== "string") {
    return ONBOARDING_DEFAULT_STAGE;
  }

  if (isWorkflowStage(value)) {
    return value;
  }

  const funnelStageMap: Record<FunnelStage, OnboardingWorkflowStage> = {
    ENTRY: "welcome",
    EXPLORATION: "context_capture",
    TRUST: "recommendation_review",
    OPPORTUNITY: "recommendation_review",
    MICRO_COMMITMENT: "resume_ready",
    ECONOMIC_ACTION: "active"
  };

  return FUNNEL_STAGES.includes(value as FunnelStage) ? funnelStageMap[value as FunnelStage] : ONBOARDING_DEFAULT_STAGE;
}

function normalizeWorkflowStatus(value: unknown, stage: OnboardingWorkflowStage): OnboardingWorkflowStatus {
  if (typeof value === "string" && isWorkflowStatus(value)) {
    return value;
  }

  const stageToStatus: Record<OnboardingWorkflowStage, OnboardingWorkflowStatus> = {
    idle: "not_started",
    welcome: "in_progress",
    context_capture: "in_progress",
    recommendation_review: "in_progress",
    resume_ready: "ready",
    active: "ready",
    paused: "paused",
    completed: "completed",
    error: "failed"
  };

  return stageToStatus[stage] ?? ONBOARDING_DEFAULT_STATUS;
}

function normalizeTimelineStepStatus(
  value: unknown,
  completed: boolean,
  current: boolean,
  blocked: boolean
): OnboardingTimelineStepStatus {
  if (typeof value === "string" && isTimelineStatus(value)) {
    return value;
  }

  if (blocked) return "blocked";
  if (completed) return "complete";
  if (current) return "current";
  return ONBOARDING_DEFAULT_TIMELINE_STEP_STATUS;
}

function normalizeNextBestActionKind(value: unknown): NextBestActionKind {
  if (typeof value === "string" && isNextBestActionKind(value)) {
    return value;
  }

  return ONBOARDING_DEFAULT_NEXT_BEST_ACTION_KIND;
}

function normalizeSessionResumeStatus(value: unknown, sessionId: string): SessionResumeStatus {
  if (typeof value === "string" && isSessionResumeStatus(value)) {
    return value;
  }

  return sessionId ? "available" : ONBOARDING_DEFAULT_SESSION_RESUME_STATUS;
}

function normalizeAdaptivePromptKind(value: unknown): AdaptivePromptItemViewModel["kind"] {
  if (typeof value === "string" && value in ONBOARDING_ADAPTIVE_PROMPT_KIND_LABELS) {
    return value as AdaptivePromptItemViewModel["kind"];
  }

  return ONBOARDING_DEFAULT_ADAPTIVE_PROMPT_KIND;
}

function normalizeConversationSummaryState(
  value: unknown,
  summary: string,
  highlights: string[],
  messageCount: number
): ConversationSummaryViewModel["state"] {
  if (typeof value === "string" && value in ONBOARDING_CONVERSATION_SUMMARY_STATE_LABELS) {
    return value as ConversationSummaryViewModel["state"];
  }

  if (summary.length === 0 && highlights.length === 0 && messageCount === 0) {
    return ONBOARDING_DEFAULT_CONVERSATION_SUMMARY_STATE;
  }

  if (summary.length > 0 && highlights.length > 0) {
    return "ready";
  }

  return "partial";
}

function normalizeWorkflowCardVariant(value: unknown): ContextualWorkflowCardViewModel["variant"] {
  if (typeof value === "string" && value in ONBOARDING_WORKFLOW_CARD_VARIANT_LABELS) {
    return value as ContextualWorkflowCardViewModel["variant"];
  }

  return ONBOARDING_DEFAULT_WORKFLOW_CARD_VARIANT;
}

function normalizeLabel(value: unknown, fallback: string): string {
  return normalizeText(value, fallback);
}

export function getOnboardingWorkflowStageLabel(stage: OnboardingWorkflowStage): string {
  return ONBOARDING_WORKFLOW_STAGE_LABELS[stage];
}

export function getOnboardingWorkflowStatusLabel(status: OnboardingWorkflowStatus): string {
  return ONBOARDING_WORKFLOW_STATUS_LABELS[status];
}

export function getOnboardingTimelineStatusLabel(status: OnboardingTimelineStepStatus): string {
  return ONBOARDING_TIMELINE_STEP_STATUS_LABELS[status];
}

export function getOnboardingNextBestActionKindLabel(kind: NextBestActionKind): string {
  return ONBOARDING_NEXT_BEST_ACTION_KIND_LABELS[kind];
}

export function getOnboardingSessionResumeStatusLabel(status: SessionResumeStatus): string {
  return ONBOARDING_SESSION_RESUME_STATUS_LABELS[status];
}

export function getOnboardingAdaptivePromptKindLabel(kind: AdaptivePromptItemViewModel["kind"]): string {
  return ONBOARDING_ADAPTIVE_PROMPT_KIND_LABELS[kind];
}

export function getOnboardingConversationSummaryStateLabel(state: ConversationSummaryViewModel["state"]): string {
  return ONBOARDING_CONVERSATION_SUMMARY_STATE_LABELS[state];
}

export function getOnboardingWorkflowCardVariantLabel(variant: ContextualWorkflowCardViewModel["variant"]): string {
  return ONBOARDING_WORKFLOW_CARD_VARIANT_LABELS[variant];
}

export function normalizeOnboardingTimelineStep(
  input: OnboardingTimelineStepInput | null | undefined,
  index = 0,
  fallbackStage: OnboardingWorkflowStage = ONBOARDING_DEFAULT_STAGE
): OnboardingTimelineStepViewModel {
  const stage = normalizeWorkflowStage(input?.stage ?? fallbackStage);
  const completed = normalizeBoolean(input?.completed);
  const current = normalizeBoolean(input?.current);
  const blocked = normalizeBoolean(input?.blocked);
  const status = normalizeTimelineStepStatus(input?.status, completed, current, blocked);

  return {
    id: normalizeText(input?.id, `timeline-step-${index + 1}`),
    title: normalizeLabel(input?.title, `${getOnboardingWorkflowStageLabel(stage)} ${index + 1}`.trim()),
    description: normalizeText(input?.description),
    stage,
    status,
    order: Math.max(0, normalizeInteger(input?.order, index + 1)),
    isCurrent: status === "current",
    isComplete: status === "complete",
    isBlocked: status === "blocked",
    metadata: normalizeMetadata(input?.metadata)
  };
}

export function normalizeOnboardingNextBestAction(
  input: OnboardingNextBestActionInput | null | undefined,
  index = 0
): OnboardingNextBestActionViewModel {
  const kind = normalizeNextBestActionKind(input?.kind);
  return {
    id: normalizeText(input?.id, `next-best-action-${index + 1}`),
    label: normalizeLabel(input?.label, `${getOnboardingNextBestActionKindLabel(kind)} ${index + 1}`),
    description: normalizeText(input?.description),
    kind,
    value: normalizeText(input?.value),
    disabled: normalizeBoolean(input?.disabled),
    priority: normalizeInteger(input?.priority, index),
    isPrimary: kind === "primary",
    metadata: normalizeMetadata(input?.metadata)
  };
}

export function normalizeOnboardingSessionResumeState(
  input: OnboardingSessionResumeStateInput | null | undefined
): OnboardingSessionResumeStateViewModel {
  const sessionId = normalizeText(input?.sessionId);
  const status = normalizeSessionResumeStatus(input?.status, sessionId);

  return {
    sessionId,
    status,
    lastActiveAt: normalizeText(input?.lastActiveAt) || null,
    message: normalizeLabel(input?.message, getOnboardingSessionResumeStatusLabel(status)),
    isAvailable: status !== "unavailable",
    isRecommended: status === "recommended" || status === "required",
    canResume: status === "available" || status === "recommended" || status === "required",
    metadata: normalizeMetadata(input?.metadata)
  };
}

export function normalizeAdaptivePromptItem(
  input: AdaptivePromptItemInput | null | undefined,
  index = 0,
  fallbackStage: OnboardingWorkflowStage = ONBOARDING_DEFAULT_STAGE
): AdaptivePromptItemViewModel {
  const stage = normalizeWorkflowStage(input?.stage ?? fallbackStage);
  const kind = normalizeAdaptivePromptKind(input?.kind);

  return {
    id: normalizeText(input?.id, `adaptive-prompt-${index + 1}`),
    prompt: normalizeLabel(input?.prompt, ONBOARDING_DEFAULT_ADAPTIVE_PROMPT_TEXT),
    kind,
    stage,
    priority: normalizeInteger(input?.priority, index),
    confidence: typeof input?.confidence === "number" && Number.isFinite(input.confidence) ? input.confidence : null,
    metadata: normalizeMetadata(input?.metadata)
  };
}

export function normalizeConversationSummary(
  input: ConversationSummaryInput | null | undefined,
  fallbackStage: OnboardingWorkflowStage = ONBOARDING_DEFAULT_STAGE
): ConversationSummaryViewModel {
  const stage = normalizeWorkflowStage(input?.stage ?? fallbackStage);
  const highlights = Array.isArray(input?.highlights)
    ? input.highlights
        .filter((highlight): highlight is string => typeof highlight === "string" && highlight.trim().length > 0)
        .map((highlight) => highlight.trim())
    : [];
  const summary = normalizeText(input?.summary);
  const messageCount = Math.max(0, normalizeInteger(input?.messageCount));
  const state = normalizeConversationSummaryState(input?.state, summary, highlights, messageCount);

  return {
    id: normalizeText(input?.id, "conversation-summary"),
    title: normalizeLabel(input?.title, ONBOARDING_DEFAULT_CONVERSATION_SUMMARY_TITLE),
    summary,
    highlights,
    stage,
    state,
    messageCount,
    lastUpdatedAt: normalizeText(input?.lastUpdatedAt) || null,
    metadata: normalizeMetadata(input?.metadata)
  };
}

export function normalizeContextualWorkflowCard(
  input: ContextualWorkflowCardInput | null | undefined,
  index = 0,
  fallbackStage: OnboardingWorkflowStage = ONBOARDING_DEFAULT_STAGE
): ContextualWorkflowCardViewModel {
  const stage = normalizeWorkflowStage(input?.stage ?? fallbackStage);

  return {
    id: normalizeText(input?.id, `workflow-card-${index + 1}`),
    title: normalizeLabel(input?.title, `${ONBOARDING_DEFAULT_WORKFLOW_CARD_TITLE} ${index + 1}`),
    body: normalizeText(input?.body),
    variant: normalizeWorkflowCardVariant(input?.variant),
    stage,
    actions: Array.isArray(input?.actions)
      ? input.actions.map((action, actionIndex) => normalizeOnboardingNextBestAction(action, actionIndex))
      : [],
    metadata: normalizeMetadata(input?.metadata)
  };
}

export function normalizeOnboardingWorkflowSnapshot(
  input: OnboardingWorkflowSnapshotInput | null | undefined
): OnboardingWorkflowViewModel {
  const stage = normalizeWorkflowStage(input?.stage);
  const status = normalizeWorkflowStatus(input?.status, stage);
  const timeline = Array.isArray(input?.timeline)
    ? input.timeline.map((step, index) => normalizeOnboardingTimelineStep(step, index, stage))
    : [];
  const nextBestActions = Array.isArray(input?.nextBestActions)
    ? input.nextBestActions.map((action, index) => normalizeOnboardingNextBestAction(action, index))
    : [];
  const sessionResume = normalizeOnboardingSessionResumeState(input?.sessionResume);
  const adaptivePrompts = Array.isArray(input?.adaptivePrompts)
    ? input.adaptivePrompts.map((prompt, index) => normalizeAdaptivePromptItem(prompt, index, stage))
    : [];
  const conversationSummary = input?.conversationSummary
    ? normalizeConversationSummary(input.conversationSummary, stage)
    : null;
  const workflowCards = Array.isArray(input?.workflowCards)
    ? input.workflowCards.map((card, index) => normalizeContextualWorkflowCard(card, index, stage))
    : [];

  return {
    stage,
    status,
    timeline,
    nextBestActions,
    sessionResume,
    adaptivePrompts,
    conversationSummary,
    workflowCards,
    metadata: normalizeMetadata(input?.metadata)
  };
}
