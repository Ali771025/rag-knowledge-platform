import { requestApi } from "./client";

export interface QoraCTA {
  type: string;
  label: string;
  target?: string;
  payload?: Record<string, unknown>;
}

export interface QoraSource {
  source_id: string;
  chunk_id?: string;
  title?: string;
  source_type?: string;
  content_version?: string;
  url?: string;
  claim_ids: string[];
}

export interface QoraLevelCard {
  current_level: number;
  current_points: number;
  next_level?: number;
  next_level_threshold?: number;
  points_needed: number;
  reward_token?: string;
  task_label?: string;
  estimated_points_gain: number;
  progress_percent: number;
  progress_hint: string;
}

export interface QoraAchievementCard {
  achievement_id: string;
  micro_task: { id: string; label: string };
  estimated_points_gain: number;
  level_progress_delta: number;
  expected_reward_hint?: string;
  explanation_style: string;
  cta: QoraCTA;
  reason_codes: string[];
}

export interface QoraAgentResponse {
  request_id: string;
  conversation_id: string;
  message: string;
  response_type: string;
  ui: {
    type: string;
    cards: Array<Record<string, unknown>>;
    options: Array<{ id: string; label: string; value: string }>;
    level_card?: QoraLevelCard;
    achievement_card?: QoraAchievementCard;
  };
  primary_cta?: QoraCTA;
  secondary_cta?: QoraCTA;
  progress: { current_stage: string; step: number; total_steps: number };
  sources: QoraSource[];
  warnings: string[];
  next_best_action?: { type: string; payload?: Record<string, unknown> };
  can_continue: boolean;
}

export async function createQoraConversation(): Promise<string> {
  const response = await requestApi<{ conversation_id: string }, Record<string, never>>({
    method: "POST",
    url: "/v1/agent/conversations",
    data: {}
  });
  return response.conversation_id;
}

export async function sendQoraMessage(input: {
  conversationId: string;
  message: string;
  language: string;
}): Promise<QoraAgentResponse> {
  const requestId = typeof crypto !== "undefined" && crypto.randomUUID
    ? `req_${crypto.randomUUID()}`
    : `req_${Date.now()}`;
  return requestApi<QoraAgentResponse>({
    method: "POST",
    url: `/v1/agent/conversations/${encodeURIComponent(input.conversationId)}/messages`,
    data: {
      request_id: requestId,
      message: input.message,
      page_context: { page: "agent", section: null, product_id: null, language: input.language },
      interaction_events: []
    }
  });
}

export async function recordQoraEvent(input: {
  conversationId: string;
  eventType: string;
  entityType?: string;
  entityId?: string;
  metadata?: Record<string, unknown>;
}): Promise<void> {
  const eventId = typeof crypto !== "undefined" && crypto.randomUUID
    ? `evt_${crypto.randomUUID()}`
    : `evt_${Date.now()}`;
  await requestApi({
    method: "POST",
    url: `/v1/agent/conversations/${encodeURIComponent(input.conversationId)}/events`,
    data: {
      request_id: `req_${eventId}`,
      events: [{
        event_id: eventId,
        event_type: input.eventType,
        entity_type: input.entityType,
        entity_id: input.entityId,
        metadata: input.metadata ?? {},
        occurred_at: new Date().toISOString(),
        idempotency_key: eventId
      }]
    }
  });
}

export async function startQoraAchievement(input: {
  conversationId: string;
  achievementId: string;
}): Promise<void> {
  const requestId = typeof crypto !== "undefined" && crypto.randomUUID
    ? `req_${crypto.randomUUID()}`
    : `req_${Date.now()}`;
  await requestApi({
    method: "POST",
    url: `/v1/agent/conversations/${encodeURIComponent(input.conversationId)}/achievements/${encodeURIComponent(input.achievementId)}/start`,
    params: { request_id: requestId }
  });
}
