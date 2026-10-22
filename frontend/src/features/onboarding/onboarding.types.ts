import type { FunnelStage } from "@/types";

export type OnboardingWorkflowStage =
  | "idle"
  | "welcome"
  | "context_capture"
  | "recommendation_review"
  | "resume_ready"
  | "active"
  | "paused"
  | "completed"
  | "error";

export type OnboardingWorkflowStatus =
  | "not_started"
  | "in_progress"
  | "ready"
  | "blocked"
  | "paused"
  | "completed"
  | "failed";

export type OnboardingTimelineStepStatus = "not_started" | "current" | "complete" | "upcoming" | "blocked";

export type NextBestActionKind = "primary" | "secondary" | "link" | "system";

export type SessionResumeStatus = "unavailable" | "available" | "recommended" | "required";

export type AdaptivePromptKind = "goal" | "clarification" | "reflection" | "preference" | "trust" | "commitment";

export type ConversationSummaryState = "empty" | "partial" | "ready" | "stale";

export type ContextualWorkflowCardVariant = "summary" | "next_step" | "resume" | "insight" | "prompt" | "status";

export interface OnboardingTimelineStepInput {
  id?: string | null;
  title?: string | null;
  description?: string | null;
  stage?: OnboardingWorkflowStage | FunnelStage | string | null;
  status?: OnboardingTimelineStepStatus | string | null;
  order?: number | null;
  completed?: boolean | null;
  current?: boolean | null;
  blocked?: boolean | null;
  metadata?: Record<string, unknown> | null;
}

export interface OnboardingNextBestActionInput {
  id?: string | null;
  label?: string | null;
  description?: string | null;
  kind?: NextBestActionKind | string | null;
  value?: string | null;
  disabled?: boolean | null;
  priority?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface OnboardingSessionResumeStateInput {
  sessionId?: string | null;
  status?: SessionResumeStatus | string | null;
  lastActiveAt?: string | null;
  message?: string | null;
  resumeToken?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface AdaptivePromptItemInput {
  id?: string | null;
  prompt?: string | null;
  kind?: AdaptivePromptKind | string | null;
  stage?: OnboardingWorkflowStage | FunnelStage | string | null;
  priority?: number | null;
  confidence?: number | null;
  metadata?: Record<string, unknown> | null;
}

export interface ConversationSummaryInput {
  id?: string | null;
  title?: string | null;
  summary?: string | null;
  highlights?: Array<string | null | undefined> | null;
  stage?: OnboardingWorkflowStage | FunnelStage | string | null;
  state?: ConversationSummaryState | string | null;
  messageCount?: number | null;
  lastUpdatedAt?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ContextualWorkflowCardInput {
  id?: string | null;
  title?: string | null;
  body?: string | null;
  variant?: ContextualWorkflowCardVariant | string | null;
  stage?: OnboardingWorkflowStage | FunnelStage | string | null;
  actions?: Array<OnboardingNextBestActionInput | null | undefined> | null;
  metadata?: Record<string, unknown> | null;
}

export interface OnboardingWorkflowSnapshotInput {
  stage?: OnboardingWorkflowStage | FunnelStage | string | null;
  status?: OnboardingWorkflowStatus | string | null;
  timeline?: Array<OnboardingTimelineStepInput | null | undefined> | null;
  nextBestActions?: Array<OnboardingNextBestActionInput | null | undefined> | null;
  sessionResume?: OnboardingSessionResumeStateInput | null;
  adaptivePrompts?: Array<AdaptivePromptItemInput | null | undefined> | null;
  conversationSummary?: ConversationSummaryInput | null;
  workflowCards?: Array<ContextualWorkflowCardInput | null | undefined> | null;
  metadata?: Record<string, unknown> | null;
}
