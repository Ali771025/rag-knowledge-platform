import { requestApi } from "./client";

export interface ReferralDashboardStatsDto {
  total_invites: number;
  activated_qora: number;
  first_microtask: number;
  first_achievement: number;
}

export interface ReferralPersonalizationProfileDto {
  invitee_relationship: string;
  familiarity_level: string;
  invitation_reason: string;
  primary_motivation: string;
  web3_familiarity_level: string;
  previous_web3_tool_experience: string;
  readiness_to_take_action: string;
  concerns_and_frictions: string[];
  previous_negative_experience: string;
  preferred_information_style: string;
  suggested_ecosystem_section: string;
  conversion_likelihood: string;
  additional_note?: string | null;
}

export type AgentContextSignalSourceDto = "referrer_reported";
export type AgentContextSignalConfidenceDto = "low" | "medium" | "high";

export interface ReferralDerivedAgentSignalDto {
  key: string;
  value: string | string[];
  source: AgentContextSignalSourceDto;
  confidence?: AgentContextSignalConfidenceDto;
}

export interface AgentMemoryContextInputDto {
  referral_link_id: string;
  invite_code: string;
  owner_user_id: string;
  invitee_user_id?: string | null;
  signals: ReferralDerivedAgentSignalDto[];
  source: "referral_personalization";
  source_label: AgentContextSignalSourceDto;
  created_at: string;
  metadata: Record<string, string>;
}

export interface ReferralLinkSummaryDto {
  id: string;
  owner_user_id: string;
  invite_code: string;
  short_url: string;
  label: string;
  color: "blue" | "violet" | "cyan" | "green" | "orange" | "pink" | "gold" | "gray";
  is_customized: boolean;
  created_at: string;
  latest_status:
    | "created"
    | "invite_opened"
    | "wallet_connected"
    | "qora_activated"
    | "first_microtask_completed"
    | "first_achievement_unlocked";
  unread_message_count: number;
  chat_enabled: boolean;
  progress_percent: number;
}

export interface ReferralLinksListDto {
  links: ReferralLinkSummaryDto[];
}

export interface CreateReferralLinkDto {
  label: string;
  color: "blue" | "violet" | "cyan" | "green" | "orange" | "pink" | "gold" | "gray";
}

export interface UpdateReferralLinkDto {
  label?: string;
  color?: "blue" | "violet" | "cyan" | "green" | "orange" | "pink" | "gold" | "gray";
}

export interface CreateCustomizedReferralLinkDto extends CreateReferralLinkDto {
  personalization_profile: ReferralPersonalizationProfileDto;
}

export interface ReferralProgressEventDto {
  id: string;
  referral_link_id: string;
  status:
    | "created"
    | "invite_opened"
    | "wallet_connected"
    | "qora_activated"
    | "first_microtask_completed"
    | "first_achievement_unlocked";
  title: string;
  description?: string;
  occurred_at?: string;
  metadata?: Record<string, string>;
}

export interface ReferralProgressEventsDto {
  events: ReferralProgressEventDto[];
}

export interface ReferralTranslationMetadataDto {
  source_language: string;
  target_language: string;
  provider: string;
  confidence?: number | null;
  translated_at: string;
}

export interface ReferralChatMessageDto {
  id: string;
  thread_id: string;
  referral_link_id: string;
  sender_role: "referrer" | "invitee";
  body: string;
  original_text: string;
  original_locale: string;
  source_language?: string | null;
  translated_text?: string | null;
  translated_text_for_viewer?: string | null;
  translation?: ReferralTranslationMetadataDto | null;
  delivery_status: "sent" | "delivered" | "read";
  metadata?: Record<string, string>;
  is_read_by_owner: boolean;
  is_read_by_invitee: boolean;
  created_at: string;
}

export interface ReferralChatThreadSummaryDto {
  id: string;
  referral_link_id: string;
  owner_user_id: string;
  invitee_display_name?: string | null;
  invitee_wallet_address?: string | null;
  latest_message_at?: string | null;
  unread_message_count: number;
  current_user_role: "referrer" | "invitee";
  messages: ReferralChatMessageDto[];
}

export interface SendReferralChatMessageDto {
  message: string;
  sender_role?: "referrer" | "invitee";
  source_language?: string;
  original_locale?: string;
  metadata?: Record<string, string>;
}

export interface RecordReferralWalletConnectionDto {
  wallet_address: string;
  invitee_display_name?: string | null;
}

export interface TranslateReferralChatMessageDto {
  message_id: string;
  target_language: string;
}

export interface TranslateReferralChatMessageResponseDto {
  message_id: string;
  translated_text: string;
  translation: ReferralTranslationMetadataDto;
}

export interface SyncPersonalizationToMemoryDto {
  referral_link_id: string;
  metadata?: Record<string, string>;
}

export interface AgentMemoryEnrichmentPayloadDto {
  referral_link_id: string;
  invite_code: string;
  owner_user_id: string;
  personalization_profile: ReferralPersonalizationProfileDto;
  latest_status:
    | "created"
    | "invite_opened"
    | "wallet_connected"
    | "qora_activated"
    | "first_microtask_completed"
    | "first_achievement_unlocked";
  source: "referral_customization";
  signals: ReferralDerivedAgentSignalDto[];
  agent_context: AgentMemoryContextInputDto;
  enriched_at: string;
  metadata: Record<string, string>;
}

export interface SyncPersonalizationToMemoryResponseDto {
  synced: boolean;
  payload: AgentMemoryEnrichmentPayloadDto;
}

const REFERRAL_API_ENDPOINTS = {
  dashboardStats: "/v1/referrals/dashboard-stats",
  links: "/v1/referrals/links",
  link: (referralLinkId: string) => `/v1/referrals/links/${encodeURIComponent(referralLinkId)}`,
  createCustomized: "/v1/referrals/links/customized",
  progressEvents: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/progress-events`,
  chatThread: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/chat-thread`,
  chatMessages: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/chat-thread/messages`,
  markChatRead: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/chat-thread/read`,
  walletConnection: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/wallet-connection`,
  translateMessage: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/chat-thread/translate`,
  syncPersonalization: (referralLinkId: string) =>
    `/v1/referrals/links/${encodeURIComponent(referralLinkId)}/sync-personalization`,
  agentContextByInvite: (inviteCode: string) =>
    `/v1/referrals/agent-context/by-invite/${encodeURIComponent(inviteCode)}`,
} as const;

export async function getReferralDashboardStats(): Promise<ReferralDashboardStatsDto> {
  return requestApi<ReferralDashboardStatsDto>({
    method: "GET",
    url: REFERRAL_API_ENDPOINTS.dashboardStats,
  });
}

export async function getReferralLinks(): Promise<ReferralLinksListDto> {
  return requestApi<ReferralLinksListDto>({
    method: "GET",
    url: REFERRAL_API_ENDPOINTS.links,
  });
}

export async function createReferralLink(payload: CreateReferralLinkDto): Promise<ReferralLinkSummaryDto> {
  return requestApi<ReferralLinkSummaryDto, CreateReferralLinkDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.links,
    data: payload,
  });
}

export async function updateReferralLink(
  referralLinkId: string,
  payload: UpdateReferralLinkDto
): Promise<ReferralLinkSummaryDto> {
  return requestApi<ReferralLinkSummaryDto, UpdateReferralLinkDto>({
    method: "PATCH",
    url: REFERRAL_API_ENDPOINTS.link(referralLinkId),
    data: payload,
  });
}

export async function createCustomizedReferralLink(
  payload: CreateCustomizedReferralLinkDto
): Promise<ReferralLinkSummaryDto> {
  return requestApi<ReferralLinkSummaryDto, CreateCustomizedReferralLinkDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.createCustomized,
    data: payload,
  });
}

export async function getReferralProgressEvents(referralLinkId: string): Promise<ReferralProgressEventsDto> {
  return requestApi<ReferralProgressEventsDto>({
    method: "GET",
    url: REFERRAL_API_ENDPOINTS.progressEvents(referralLinkId),
  });
}

export async function getReferralChatThread(
  referralLinkId: string,
  viewerLocale?: string
): Promise<ReferralChatThreadSummaryDto> {
  return requestApi<ReferralChatThreadSummaryDto>({
    method: "GET",
    url: REFERRAL_API_ENDPOINTS.chatThread(referralLinkId),
    params: viewerLocale ? { viewer_locale: viewerLocale } : undefined,
  });
}

export async function sendReferralChatMessage(
  referralLinkId: string,
  payload: SendReferralChatMessageDto,
  viewerLocale?: string
): Promise<ReferralChatMessageDto> {
  return requestApi<ReferralChatMessageDto, SendReferralChatMessageDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.chatMessages(referralLinkId),
    params: viewerLocale ? { viewer_locale: viewerLocale } : undefined,
    data: payload,
  });
}

export async function markReferralChatThreadRead(
  referralLinkId: string,
  viewerLocale?: string
): Promise<ReferralChatThreadSummaryDto> {
  return requestApi<ReferralChatThreadSummaryDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.markChatRead(referralLinkId),
    params: viewerLocale ? { viewer_locale: viewerLocale } : undefined,
  });
}

export async function recordReferralWalletConnection(
  referralLinkId: string,
  payload: RecordReferralWalletConnectionDto
): Promise<ReferralLinkSummaryDto> {
  return requestApi<ReferralLinkSummaryDto, RecordReferralWalletConnectionDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.walletConnection(referralLinkId),
    data: payload,
  });
}

export async function translateReferralChatMessage(
  referralLinkId: string,
  payload: TranslateReferralChatMessageDto
): Promise<TranslateReferralChatMessageResponseDto> {
  return requestApi<TranslateReferralChatMessageResponseDto, TranslateReferralChatMessageDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.translateMessage(referralLinkId),
    data: payload,
  });
}

export async function syncPersonalizationToMemory(
  referralLinkId: string,
  payload: SyncPersonalizationToMemoryDto
): Promise<SyncPersonalizationToMemoryResponseDto> {
  return requestApi<SyncPersonalizationToMemoryResponseDto, SyncPersonalizationToMemoryDto>({
    method: "POST",
    url: REFERRAL_API_ENDPOINTS.syncPersonalization(referralLinkId),
    data: payload,
  });
}

export async function getReferralAgentContextByInvite(inviteCode: string): Promise<AgentMemoryContextInputDto> {
  return requestApi<AgentMemoryContextInputDto>({
    method: "GET",
    url: REFERRAL_API_ENDPOINTS.agentContextByInvite(inviteCode),
  });
}
