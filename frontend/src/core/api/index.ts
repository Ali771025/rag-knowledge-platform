export { apiClient, requestApi } from "./client";
export { ApiClientError, isApiClientError } from "./client";
export {
  CHAT_API_ENDPOINTS,
  createChatSession,
  getSessionSnapshot,
  sendChatMessage
} from "./chat-api";
export { getDashboardCards } from "./dashboard-api";
export { createQoraConversation, recordQoraEvent, sendQoraMessage, startQoraAchievement } from "./qora-api";
export type { QoraAgentResponse, QoraAchievementCard, QoraCTA, QoraLevelCard, QoraSource } from "./qora-api";
export { getUserProfile, updateUserProfile } from "./user-profile-api";
export {
  createCustomizedReferralLink,
  createReferralLink,
  getReferralAgentContextByInvite,
  getReferralChatThread,
  getReferralDashboardStats,
  getReferralLinks,
  getReferralProgressEvents,
  markReferralChatThreadRead,
  recordReferralWalletConnection,
  sendReferralChatMessage,
  syncPersonalizationToMemory,
  translateReferralChatMessage,
  updateReferralLink,
} from "./referral-api";

export type {
  DashboardActivationResponse,
  DashboardCardActionResponse,
  DashboardCardResponse,
  DashboardCardsResponse
} from "./dashboard-api";
export type {
  ChatSessionSnapshotDto,
  ConversationMessageDto,
  CreateChatSessionPayload,
  CreateChatSessionResponse,
  SendChatMessagePayload,
  SendChatMessageResponse,
  SessionSnapshotResponse,
  SuggestedActionDto
} from "./chat-api";
export type { UpdateUserProfilePayload, UserProfileResponse } from "./user-profile-api";
export type {
  AgentMemoryEnrichmentPayloadDto,
  AgentMemoryContextInputDto,
  CreateCustomizedReferralLinkDto,
  CreateReferralLinkDto,
  ReferralChatMessageDto,
  ReferralChatThreadSummaryDto,
  ReferralDashboardStatsDto,
  ReferralLinkSummaryDto,
  ReferralLinksListDto,
  ReferralPersonalizationProfileDto,
  ReferralProgressEventDto,
  ReferralProgressEventsDto,
  ReferralTranslationMetadataDto,
  ReferralDerivedAgentSignalDto,
  RecordReferralWalletConnectionDto,
  SendReferralChatMessageDto,
  SyncPersonalizationToMemoryDto,
  SyncPersonalizationToMemoryResponseDto,
  TranslateReferralChatMessageDto,
  TranslateReferralChatMessageResponseDto,
  UpdateReferralLinkDto,
} from "./referral-api";
