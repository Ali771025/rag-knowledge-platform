export const ONBOARDING_WORKFLOW_STAGES = [
  "idle",
  "welcome",
  "context_capture",
  "recommendation_review",
  "resume_ready",
  "active",
  "paused",
  "completed",
  "error"
] as const;

export const ONBOARDING_WORKFLOW_STATUSES = [
  "not_started",
  "in_progress",
  "ready",
  "blocked",
  "paused",
  "completed",
  "failed"
] as const;

export const ONBOARDING_TIMELINE_STEP_STATUSES = [
  "not_started",
  "current",
  "complete",
  "upcoming",
  "blocked"
] as const;

export const ONBOARDING_NEXT_BEST_ACTION_KINDS = ["primary", "secondary", "link", "system"] as const;

export const ONBOARDING_SESSION_RESUME_STATUSES = ["unavailable", "available", "recommended", "required"] as const;

export const ONBOARDING_ADAPTIVE_PROMPT_KINDS = [
  "goal",
  "clarification",
  "reflection",
  "preference",
  "trust",
  "commitment"
] as const;

export const ONBOARDING_CONVERSATION_SUMMARY_STATES = ["empty", "partial", "ready", "stale"] as const;

export const ONBOARDING_WORKFLOW_CARD_VARIANTS = [
  "summary",
  "next_step",
  "resume",
  "insight",
  "prompt",
  "status"
] as const;

export const ONBOARDING_WORKFLOW_STAGE_LABELS = {
  idle: "Idle",
  welcome: "Welcome",
  context_capture: "Context capture",
  recommendation_review: "Recommendation review",
  resume_ready: "Resume ready",
  active: "Active",
  paused: "Paused",
  completed: "Completed",
  error: "Error"
} as const;

export const ONBOARDING_WORKFLOW_STATUS_LABELS = {
  not_started: "Not started",
  in_progress: "In progress",
  ready: "Ready",
  blocked: "Blocked",
  paused: "Paused",
  completed: "Completed",
  failed: "Failed"
} as const;

export const ONBOARDING_TIMELINE_STEP_STATUS_LABELS = {
  not_started: "Not started",
  current: "Current",
  complete: "Complete",
  upcoming: "Upcoming",
  blocked: "Blocked"
} as const;

export const ONBOARDING_NEXT_BEST_ACTION_KIND_LABELS = {
  primary: "Primary action",
  secondary: "Secondary action",
  link: "Link action",
  system: "System action"
} as const;

export const ONBOARDING_SESSION_RESUME_STATUS_LABELS = {
  unavailable: "Unavailable",
  available: "Available",
  recommended: "Recommended",
  required: "Required"
} as const;

export const ONBOARDING_ADAPTIVE_PROMPT_KIND_LABELS = {
  goal: "Goal prompt",
  clarification: "Clarification prompt",
  reflection: "Reflection prompt",
  preference: "Preference prompt",
  trust: "Trust prompt",
  commitment: "Commitment prompt"
} as const;

export const ONBOARDING_CONVERSATION_SUMMARY_STATE_LABELS = {
  empty: "Empty",
  partial: "Partial",
  ready: "Ready",
  stale: "Stale"
} as const;

export const ONBOARDING_WORKFLOW_CARD_VARIANT_LABELS = {
  summary: "Summary card",
  next_step: "Next step card",
  resume: "Resume card",
  insight: "Insight card",
  prompt: "Prompt card",
  status: "Status card"
} as const;

export const ONBOARDING_DEFAULT_STAGE = "idle" as const;
export const ONBOARDING_DEFAULT_STATUS = "not_started" as const;
export const ONBOARDING_DEFAULT_TIMELINE_STEP_STATUS = "upcoming" as const;
export const ONBOARDING_DEFAULT_NEXT_BEST_ACTION_KIND = "secondary" as const;
export const ONBOARDING_DEFAULT_SESSION_RESUME_STATUS = "unavailable" as const;
export const ONBOARDING_DEFAULT_ADAPTIVE_PROMPT_KIND = "clarification" as const;
export const ONBOARDING_DEFAULT_CONVERSATION_SUMMARY_STATE = "empty" as const;
export const ONBOARDING_DEFAULT_WORKFLOW_CARD_VARIANT = "status" as const;

export const ONBOARDING_EMPTY_TEXT = "";
export const ONBOARDING_DEFAULT_TIMELINE_STEP_TITLE = "Step";
export const ONBOARDING_DEFAULT_NEXT_BEST_ACTION_LABEL = "Next step";
export const ONBOARDING_DEFAULT_ADAPTIVE_PROMPT_TEXT = "Share more context";
export const ONBOARDING_DEFAULT_CONVERSATION_SUMMARY_TITLE = "Conversation summary";
export const ONBOARDING_DEFAULT_WORKFLOW_CARD_TITLE = "Workflow card";
