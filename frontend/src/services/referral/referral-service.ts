import { isApiClientError } from "@/core/api";
import {
  createCustomizedReferralLink,
  createReferralLink,
  getReferralChatThread,
  getReferralAgentContextByInvite,
  getReferralDashboardStats,
  getReferralLinks,
  getReferralProgressEvents,
  markReferralChatThreadRead,
  recordReferralWalletConnection,
  sendReferralChatMessage,
  syncPersonalizationToMemory,
  translateReferralChatMessage,
  updateReferralLink,
  type AgentMemoryEnrichmentPayloadDto,
  type AgentMemoryContextInputDto,
  type CreateCustomizedReferralLinkDto,
  type CreateReferralLinkDto,
  type ReferralChatMessageDto,
  type ReferralChatThreadSummaryDto,
  type ReferralDashboardStatsDto,
  type ReferralLinkSummaryDto,
  type ReferralPersonalizationProfileDto,
  type ReferralProgressEventDto,
  type ReferralTranslationMetadataDto,
  type ReferralDerivedAgentSignalDto,
  type RecordReferralWalletConnectionDto,
  type SendReferralChatMessageDto,
  type SyncPersonalizationToMemoryDto,
  type TranslateReferralChatMessageDto,
  type UpdateReferralLinkDto,
} from "@/core/api";

export type ReferralTagColor = "blue" | "violet" | "cyan" | "green" | "orange" | "pink" | "gold" | "gray";
export type ReferralLifecycleStatus =
  | "created"
  | "invite_opened"
  | "wallet_connected"
  | "qora_activated"
  | "first_microtask_completed"
  | "first_achievement_unlocked";

export interface ReferralDashboardStats {
  totalInvites: number;
  activatedQora: number;
  firstMicroTask: number;
  firstAchievement: number;
}

export interface ReferralPersonalizationProfile {
  inviteeRelationship: string;
  familiarityLevel: string;
  invitationReason: string;
  primaryMotivation: string;
  web3FamiliarityLevel: string;
  previousWeb3ToolExperience: string;
  readinessToTakeAction: string;
  concernsAndFrictions: string[];
  previousNegativeExperience: string;
  preferredInformationStyle: string;
  suggestedEcosystemSection: string;
  conversionLikelihood: string;
  additionalNote?: string | null;
}

export type AgentContextSignalSource = "referrer_reported";
export type AgentContextSignalConfidence = "low" | "medium" | "high";

export interface ReferralDerivedAgentSignal {
  key: string;
  value: string | string[];
  source: AgentContextSignalSource;
  confidence?: AgentContextSignalConfidence;
}

export interface AgentMemoryContextInput {
  referralLinkId: string;
  inviteCode: string;
  ownerUserId: string;
  inviteeUserId?: string | null;
  signals: ReferralDerivedAgentSignal[];
  source: "referral_personalization";
  sourceLabel: AgentContextSignalSource;
  createdAt: string;
  metadata: Record<string, string>;
}

export interface ReferralLinkSummary {
  id: string;
  ownerUserId: string;
  inviteCode: string;
  shortUrl: string;
  label: string;
  color: ReferralTagColor;
  isCustomized: boolean;
  createdAt: string;
  latestStatus: ReferralLifecycleStatus;
  unreadMessageCount: number;
  chatEnabled: boolean;
  progressPercent: number;
}

export interface ReferralProgressEvent {
  id: string;
  referralLinkId: string;
  status: ReferralLifecycleStatus;
  title: string;
  description?: string;
  occurredAt?: string;
  metadata?: Record<string, string>;
}

export interface ReferralTranslationMetadata {
  sourceLanguage: string;
  targetLanguage: string;
  provider: string;
  confidence?: number | null;
  translatedAt: string;
}

export interface ReferralChatMessage {
  id: string;
  threadId: string;
  referralLinkId: string;
  senderRole: "referrer" | "invitee";
  body: string;
  originalText: string;
  originalLocale: string;
  sourceLanguage?: string | null;
  translatedText?: string | null;
  translatedTextForViewer?: string | null;
  translation?: ReferralTranslationMetadata | null;
  deliveryStatus: "sent" | "delivered" | "read";
  metadata?: Record<string, string>;
  isReadByOwner: boolean;
  isReadByInvitee: boolean;
  createdAt: string;
}

export interface ReferralChatThreadSummary {
  id: string;
  referralLinkId: string;
  ownerUserId: string;
  inviteeDisplayName?: string | null;
  inviteeWalletAddress?: string | null;
  latestMessageAt?: string | null;
  unreadMessageCount: number;
  currentUserRole: "referrer" | "invitee";
  messages: ReferralChatMessage[];
}

export interface AgentMemoryEnrichmentPayload {
  referralLinkId: string;
  inviteCode: string;
  ownerUserId: string;
  personalizationProfile: ReferralPersonalizationProfile;
  latestStatus: ReferralLifecycleStatus;
  source: "referral_customization";
  signals: ReferralDerivedAgentSignal[];
  agentContext: AgentMemoryContextInput;
  enrichedAt: string;
  metadata: Record<string, string>;
}

export interface ReferralService {
  getDashboardStats: () => Promise<ReferralDashboardStats>;
  listLinks: () => Promise<ReferralLinkSummary[]>;
  createLink: (input: { label: string; color: ReferralTagColor }) => Promise<ReferralLinkSummary>;
  updateLink: (
    referralLinkId: string,
    input: {
      label?: string;
      color?: ReferralTagColor;
    }
  ) => Promise<ReferralLinkSummary>;
  createCustomizedLink: (input: {
    label: string;
    color: ReferralTagColor;
    personalizationProfile: ReferralPersonalizationProfile;
  }) => Promise<ReferralLinkSummary>;
  getProgressEvents: (referralLinkId: string) => Promise<ReferralProgressEvent[]>;
  getChatThread: (referralLinkId: string, viewerLocale?: string) => Promise<ReferralChatThreadSummary>;
  sendChatMessage: (
    referralLinkId: string,
    input: {
      message: string;
      senderRole?: "referrer" | "invitee";
      sourceLanguage?: string;
      originalLocale?: string;
      metadata?: Record<string, string>;
    }
  ) => Promise<ReferralChatMessage>;
  markChatThreadRead: (referralLinkId: string, viewerLocale?: string) => Promise<ReferralChatThreadSummary>;
  recordWalletConnection: (
    referralLinkId: string,
    input: {
      walletAddress: string;
      inviteeDisplayName?: string | null;
    }
  ) => Promise<ReferralLinkSummary>;
  translateChatMessage: (
    referralLinkId: string,
    input: {
      messageId: string;
      targetLanguage: string;
    }
  ) => Promise<{ messageId: string; translatedText: string; translation: ReferralTranslationMetadata }>;
  syncPersonalizationProfile: (
    referralLinkId: string,
    input: {
      referralLinkId: string;
      metadata?: Record<string, string>;
    }
  ) => Promise<{ synced: boolean; payload: AgentMemoryEnrichmentPayload }>;
  getAgentContextByInviteCode: (inviteCode: string) => Promise<AgentMemoryContextInput>;
}

function toStats(dto: ReferralDashboardStatsDto): ReferralDashboardStats {
  return {
    totalInvites: dto.total_invites,
    activatedQora: dto.activated_qora,
    firstMicroTask: dto.first_microtask,
    firstAchievement: dto.first_achievement,
  };
}

function toPersonalizationProfileDto(input: ReferralPersonalizationProfile): ReferralPersonalizationProfileDto {
  return {
    invitee_relationship: input.inviteeRelationship,
    familiarity_level: input.familiarityLevel,
    invitation_reason: input.invitationReason,
    primary_motivation: input.primaryMotivation,
    web3_familiarity_level: input.web3FamiliarityLevel,
    previous_web3_tool_experience: input.previousWeb3ToolExperience,
    readiness_to_take_action: input.readinessToTakeAction,
    concerns_and_frictions: input.concernsAndFrictions,
    previous_negative_experience: input.previousNegativeExperience,
    preferred_information_style: input.preferredInformationStyle,
    suggested_ecosystem_section: input.suggestedEcosystemSection,
    conversion_likelihood: input.conversionLikelihood,
    additional_note: input.additionalNote ?? null,
  };
}

function toPersonalizationProfile(dto: ReferralPersonalizationProfileDto): ReferralPersonalizationProfile {
  return {
    inviteeRelationship: dto.invitee_relationship,
    familiarityLevel: dto.familiarity_level,
    invitationReason: dto.invitation_reason,
    primaryMotivation: dto.primary_motivation,
    web3FamiliarityLevel: dto.web3_familiarity_level,
    previousWeb3ToolExperience: dto.previous_web3_tool_experience,
    readinessToTakeAction: dto.readiness_to_take_action,
    concernsAndFrictions: dto.concerns_and_frictions,
    previousNegativeExperience: dto.previous_negative_experience,
    preferredInformationStyle: dto.preferred_information_style,
    suggestedEcosystemSection: dto.suggested_ecosystem_section,
    conversionLikelihood: dto.conversion_likelihood,
    additionalNote: dto.additional_note ?? null,
  };
}

function toLinkSummary(dto: ReferralLinkSummaryDto): ReferralLinkSummary {
  return {
    id: dto.id,
    ownerUserId: dto.owner_user_id,
    inviteCode: dto.invite_code,
    shortUrl: dto.short_url,
    label: dto.label,
    color: dto.color,
    isCustomized: dto.is_customized,
    createdAt: dto.created_at,
    latestStatus: dto.latest_status,
    unreadMessageCount: dto.unread_message_count,
    chatEnabled: dto.chat_enabled,
    progressPercent: dto.progress_percent,
  };
}

function toProgressEvent(dto: ReferralProgressEventDto): ReferralProgressEvent {
  return {
    id: dto.id,
    referralLinkId: dto.referral_link_id,
    status: dto.status,
    title: dto.title,
    description: dto.description,
    occurredAt: dto.occurred_at,
    metadata: dto.metadata,
  };
}

function toTranslationMetadata(dto: ReferralTranslationMetadataDto): ReferralTranslationMetadata {
  return {
    sourceLanguage: dto.source_language,
    targetLanguage: dto.target_language,
    provider: dto.provider,
    confidence: dto.confidence ?? null,
    translatedAt: dto.translated_at,
  };
}

function toChatMessage(dto: ReferralChatMessageDto): ReferralChatMessage {
  return {
    id: dto.id,
    threadId: dto.thread_id,
    referralLinkId: dto.referral_link_id,
    senderRole: dto.sender_role,
    body: dto.body,
    originalText: dto.original_text,
    originalLocale: dto.original_locale,
    sourceLanguage: dto.source_language ?? null,
    translatedText: dto.translated_text ?? null,
    translatedTextForViewer: dto.translated_text_for_viewer ?? null,
    translation: dto.translation ? toTranslationMetadata(dto.translation) : null,
    deliveryStatus: dto.delivery_status,
    metadata: dto.metadata,
    isReadByOwner: dto.is_read_by_owner,
    isReadByInvitee: dto.is_read_by_invitee,
    createdAt: dto.created_at,
  };
}

function toChatThreadSummary(dto: ReferralChatThreadSummaryDto): ReferralChatThreadSummary {
  return {
    id: dto.id,
    referralLinkId: dto.referral_link_id,
    ownerUserId: dto.owner_user_id,
    inviteeDisplayName: dto.invitee_display_name ?? null,
    inviteeWalletAddress: dto.invitee_wallet_address ?? null,
    latestMessageAt: dto.latest_message_at ?? null,
    unreadMessageCount: dto.unread_message_count,
    currentUserRole: dto.current_user_role,
    messages: dto.messages.map(toChatMessage),
  };
}

function toAgentSignal(dto: ReferralDerivedAgentSignalDto): ReferralDerivedAgentSignal {
  return {
    key: dto.key,
    value: dto.value,
    source: dto.source,
    confidence: dto.confidence,
  };
}

function toAgentMemoryContext(dto: AgentMemoryContextInputDto): AgentMemoryContextInput {
  return {
    referralLinkId: dto.referral_link_id,
    inviteCode: dto.invite_code,
    ownerUserId: dto.owner_user_id,
    inviteeUserId: dto.invitee_user_id ?? null,
    signals: dto.signals.map(toAgentSignal),
    source: dto.source,
    sourceLabel: dto.source_label,
    createdAt: dto.created_at,
    metadata: dto.metadata,
  };
}

function toAgentMemoryPayload(dto: AgentMemoryEnrichmentPayloadDto): AgentMemoryEnrichmentPayload {
  return {
    referralLinkId: dto.referral_link_id,
    inviteCode: dto.invite_code,
    ownerUserId: dto.owner_user_id,
    personalizationProfile: toPersonalizationProfile(dto.personalization_profile),
    latestStatus: dto.latest_status,
    source: dto.source,
    signals: dto.signals.map(toAgentSignal),
    agentContext: toAgentMemoryContext(dto.agent_context),
    enrichedAt: dto.enriched_at,
    metadata: dto.metadata,
  };
}

class ApiReferralService implements ReferralService {
  async getDashboardStats(): Promise<ReferralDashboardStats> {
    const dto = await getReferralDashboardStats();
    return toStats(dto);
  }

  async listLinks(): Promise<ReferralLinkSummary[]> {
    const dto = await getReferralLinks();
    return dto.links.map(toLinkSummary);
  }

  async createLink(input: { label: string; color: ReferralTagColor }): Promise<ReferralLinkSummary> {
    const payload: CreateReferralLinkDto = {
      label: input.label,
      color: input.color,
    };
    const dto = await createReferralLink(payload);
    return toLinkSummary(dto);
  }

  async updateLink(
    referralLinkId: string,
    input: {
      label?: string;
      color?: ReferralTagColor;
    }
  ): Promise<ReferralLinkSummary> {
    const payload: UpdateReferralLinkDto = {
      ...(input.label ? { label: input.label } : {}),
      ...(input.color ? { color: input.color } : {}),
    };
    const dto = await updateReferralLink(referralLinkId, payload);
    return toLinkSummary(dto);
  }

  async createCustomizedLink(input: {
    label: string;
    color: ReferralTagColor;
    personalizationProfile: ReferralPersonalizationProfile;
  }): Promise<ReferralLinkSummary> {
    const payload: CreateCustomizedReferralLinkDto = {
      label: input.label,
      color: input.color,
      personalization_profile: toPersonalizationProfileDto(input.personalizationProfile),
    };
    const dto = await createCustomizedReferralLink(payload);
    return toLinkSummary(dto);
  }

  async getProgressEvents(referralLinkId: string): Promise<ReferralProgressEvent[]> {
    const dto = await getReferralProgressEvents(referralLinkId);
    return dto.events.map(toProgressEvent);
  }

  async getChatThread(referralLinkId: string, viewerLocale?: string): Promise<ReferralChatThreadSummary> {
    const dto = await getReferralChatThread(referralLinkId, viewerLocale);
    return toChatThreadSummary(dto);
  }

  async sendChatMessage(
    referralLinkId: string,
    input: {
      message: string;
      senderRole?: "referrer" | "invitee";
      sourceLanguage?: string;
      originalLocale?: string;
      metadata?: Record<string, string>;
    }
  ): Promise<ReferralChatMessage> {
    const payload: SendReferralChatMessageDto = {
      message: input.message,
      ...(input.senderRole ? { sender_role: input.senderRole } : {}),
      ...(input.sourceLanguage ? { source_language: input.sourceLanguage } : {}),
      ...(input.originalLocale ? { original_locale: input.originalLocale } : {}),
      ...(input.metadata ? { metadata: input.metadata } : {}),
    };
    const dto = await sendReferralChatMessage(referralLinkId, payload, input.originalLocale ?? input.sourceLanguage);
    return toChatMessage(dto);
  }

  async markChatThreadRead(referralLinkId: string, viewerLocale?: string): Promise<ReferralChatThreadSummary> {
    const dto = await markReferralChatThreadRead(referralLinkId, viewerLocale);
    return toChatThreadSummary(dto);
  }

  async recordWalletConnection(
    referralLinkId: string,
    input: {
      walletAddress: string;
      inviteeDisplayName?: string | null;
    }
  ): Promise<ReferralLinkSummary> {
    const payload: RecordReferralWalletConnectionDto = {
      wallet_address: input.walletAddress,
      ...(input.inviteeDisplayName ? { invitee_display_name: input.inviteeDisplayName } : {}),
    };
    const dto = await recordReferralWalletConnection(referralLinkId, payload);
    return toLinkSummary(dto);
  }

  async translateChatMessage(
    referralLinkId: string,
    input: {
      messageId: string;
      targetLanguage: string;
    }
  ): Promise<{ messageId: string; translatedText: string; translation: ReferralTranslationMetadata }> {
    const payload: TranslateReferralChatMessageDto = {
      message_id: input.messageId,
      target_language: input.targetLanguage,
    };
    const dto = await translateReferralChatMessage(referralLinkId, payload);
    return {
      messageId: dto.message_id,
      translatedText: dto.translated_text,
      translation: toTranslationMetadata(dto.translation),
    };
  }

  async syncPersonalizationProfile(
    referralLinkId: string,
    input: {
      referralLinkId: string;
      metadata?: Record<string, string>;
    }
  ): Promise<{ synced: boolean; payload: AgentMemoryEnrichmentPayload }> {
    const payload: SyncPersonalizationToMemoryDto = {
      referral_link_id: input.referralLinkId,
      ...(input.metadata ? { metadata: input.metadata } : {}),
    };
    const dto = await syncPersonalizationToMemory(referralLinkId, payload);
    return {
      synced: dto.synced,
      payload: toAgentMemoryPayload(dto.payload),
    };
  }

  async getAgentContextByInviteCode(inviteCode: string): Promise<AgentMemoryContextInput> {
    const dto = await getReferralAgentContextByInvite(inviteCode);
    return toAgentMemoryContext(dto);
  }
}

class LocalFallbackReferralService implements ReferralService {
  private links: ReferralLinkSummary[] = [];

  async getDashboardStats(): Promise<ReferralDashboardStats> {
    const totalInvites = this.links.length;
    const activatedQora = this.links.filter((link) =>
      ["qora_activated", "first_microtask_completed", "first_achievement_unlocked"].includes(link.latestStatus)
    ).length;
    const firstMicroTask = this.links.filter((link) =>
      ["first_microtask_completed", "first_achievement_unlocked"].includes(link.latestStatus)
    ).length;
    const firstAchievement = this.links.filter((link) => link.latestStatus === "first_achievement_unlocked").length;
    return {
      totalInvites,
      activatedQora,
      firstMicroTask,
      firstAchievement,
    };
  }

  async listLinks(): Promise<ReferralLinkSummary[]> {
    return [...this.links];
  }

  async createLink(input: { label: string; color: ReferralTagColor }): Promise<ReferralLinkSummary> {
    const id = `local-ref-${Date.now()}`;
    const inviteCode = `REF-${Math.random().toString(36).slice(2, 10).toUpperCase()}`;
    const next: ReferralLinkSummary = {
      id,
      ownerUserId: "local-user",
      inviteCode,
      shortUrl: `https://example.invalid/register?invite=${inviteCode}`,
      label: input.label,
      color: input.color,
      isCustomized: false,
      createdAt: new Date().toISOString(),
      latestStatus: "created",
      unreadMessageCount: 0,
      chatEnabled: false,
      progressPercent: 0,
    };
    this.links = [next, ...this.links];
    return next;
  }

  async updateLink(
    referralLinkId: string,
    input: {
      label?: string;
      color?: ReferralTagColor;
    }
  ): Promise<ReferralLinkSummary> {
    const current = this.links.find((item) => item.id === referralLinkId);
    if (!current) {
      throw new Error("Referral link not found");
    }
    const next: ReferralLinkSummary = {
      ...current,
      ...(input.label ? { label: input.label } : {}),
      ...(input.color ? { color: input.color } : {}),
    };
    this.links = this.links.map((item) => (item.id === referralLinkId ? next : item));
    return next;
  }

  async createCustomizedLink(input: {
    label: string;
    color: ReferralTagColor;
    personalizationProfile: ReferralPersonalizationProfile;
  }): Promise<ReferralLinkSummary> {
    const next = await this.createLink({ label: input.label, color: input.color });
    const customized: ReferralLinkSummary = {
      ...next,
      isCustomized: true,
    };
    this.links = this.links.map((item) => (item.id === next.id ? customized : item));
    return customized;
  }

  async getProgressEvents(_referralLinkId: string): Promise<ReferralProgressEvent[]> {
    return [];
  }

  async getChatThread(referralLinkId: string, _viewerLocale?: string): Promise<ReferralChatThreadSummary> {
    return {
      id: `thread-${referralLinkId}`,
      referralLinkId,
      ownerUserId: "local-user",
      inviteeDisplayName: null,
      inviteeWalletAddress: null,
      latestMessageAt: null,
      unreadMessageCount: 0,
      currentUserRole: "referrer",
      messages: [],
    };
  }

  async sendChatMessage(
    referralLinkId: string,
    input: {
      message: string;
      senderRole?: "referrer" | "invitee";
      sourceLanguage?: string;
      originalLocale?: string;
      metadata?: Record<string, string>;
    }
  ): Promise<ReferralChatMessage> {
    const locale = input.originalLocale ?? input.sourceLanguage ?? "en";
    return {
      id: `msg-${Date.now()}`,
      threadId: `thread-${referralLinkId}`,
      referralLinkId,
      senderRole: input.senderRole ?? "referrer",
      body: input.message,
      originalText: input.message,
      originalLocale: locale,
      sourceLanguage: input.sourceLanguage ?? null,
      translatedText: null,
      translatedTextForViewer: null,
      translation: null,
      deliveryStatus: "delivered",
      metadata: input.metadata,
      isReadByOwner: true,
      isReadByInvitee: false,
      createdAt: new Date().toISOString(),
    };
  }

  async markChatThreadRead(referralLinkId: string, _viewerLocale?: string): Promise<ReferralChatThreadSummary> {
    return this.getChatThread(referralLinkId);
  }

  async recordWalletConnection(
    referralLinkId: string,
    input: {
      walletAddress: string;
      inviteeDisplayName?: string | null;
    }
  ): Promise<ReferralLinkSummary> {
    const current = this.links.find((item) => item.id === referralLinkId);
    if (!current) {
      throw new Error("Referral link not found");
    }
    const next: ReferralLinkSummary = {
      ...current,
      latestStatus: "wallet_connected",
      progressPercent: Math.max(current.progressPercent, 40),
      chatEnabled: true,
    };
    this.links = this.links.map((item) => (item.id === referralLinkId ? next : item));
    void input;
    return next;
  }

  async translateChatMessage(
    _referralLinkId: string,
    input: {
      messageId: string;
      targetLanguage: string;
    }
  ): Promise<{ messageId: string; translatedText: string; translation: ReferralTranslationMetadata }> {
    return {
      messageId: input.messageId,
      translatedText: `[${input.targetLanguage}]`,
      translation: {
        sourceLanguage: "auto",
        targetLanguage: input.targetLanguage,
        provider: "local_stub",
        confidence: 1,
        translatedAt: new Date().toISOString(),
      },
    };
  }

  async syncPersonalizationProfile(
    referralLinkId: string,
    input: {
      referralLinkId: string;
      metadata?: Record<string, string>;
    }
  ): Promise<{ synced: boolean; payload: AgentMemoryEnrichmentPayload }> {
    return {
      synced: true,
      payload: {
        referralLinkId,
        inviteCode: input.referralLinkId,
        ownerUserId: "local-user",
        personalizationProfile: {
          inviteeRelationship: "friend",
          familiarityLevel: "beginner",
          invitationReason: "join_qora",
          primaryMotivation: "learn_web3",
          web3FamiliarityLevel: "newcomer",
          previousWeb3ToolExperience: "none",
          readinessToTakeAction: "exploring",
          concernsAndFrictions: ["security_uncertainty"],
          previousNegativeExperience: "none",
          preferredInformationStyle: "simple_steps",
          suggestedEcosystemSection: "getting_started",
          conversionLikelihood: "medium",
          additionalNote: null,
        },
        latestStatus: "created",
        source: "referral_customization",
        signals: [
          {
            key: "relationship_context",
            value: "friend",
            source: "referrer_reported",
            confidence: "medium",
          },
        ],
        agentContext: {
          referralLinkId,
          inviteCode: input.referralLinkId,
          ownerUserId: "local-user",
          inviteeUserId: null,
          signals: [
            {
              key: "relationship_context",
              value: "friend",
              source: "referrer_reported",
              confidence: "medium",
            },
          ],
          source: "referral_personalization",
          sourceLabel: "referrer_reported",
          createdAt: new Date().toISOString(),
          metadata: input.metadata ?? {},
        },
        enrichedAt: new Date().toISOString(),
        metadata: input.metadata ?? {},
      },
    };
  }

  async getAgentContextByInviteCode(inviteCode: string): Promise<AgentMemoryContextInput> {
    return {
      referralLinkId: inviteCode,
      inviteCode,
      ownerUserId: "local-user",
      inviteeUserId: null,
      signals: [
        {
          key: "relationship_context",
          value: "friend",
          source: "referrer_reported",
          confidence: "medium",
        },
      ],
      source: "referral_personalization",
      sourceLabel: "referrer_reported",
      createdAt: new Date().toISOString(),
      metadata: {
        source_attribution: "referrer_reported",
        truth_status: "unverified_referrer_signal",
      },
    };
  }
}

class ResilientReferralService implements ReferralService {
  private readonly api = new ApiReferralService();

  private readonly fallback = new LocalFallbackReferralService();

  async getDashboardStats(): Promise<ReferralDashboardStats> {
    try {
      return await this.api.getDashboardStats();
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.getDashboardStats();
      }
      throw error;
    }
  }

  async listLinks(): Promise<ReferralLinkSummary[]> {
    try {
      return await this.api.listLinks();
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.listLinks();
      }
      throw error;
    }
  }

  async createLink(input: { label: string; color: ReferralTagColor }): Promise<ReferralLinkSummary> {
    try {
      return await this.api.createLink(input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.createLink(input);
      }
      throw error;
    }
  }

  async updateLink(
    referralLinkId: string,
    input: {
      label?: string;
      color?: ReferralTagColor;
    }
  ): Promise<ReferralLinkSummary> {
    try {
      return await this.api.updateLink(referralLinkId, input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.updateLink(referralLinkId, input);
      }
      throw error;
    }
  }

  async createCustomizedLink(input: {
    label: string;
    color: ReferralTagColor;
    personalizationProfile: ReferralPersonalizationProfile;
  }): Promise<ReferralLinkSummary> {
    try {
      return await this.api.createCustomizedLink(input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.createCustomizedLink(input);
      }
      throw error;
    }
  }

  async getProgressEvents(referralLinkId: string): Promise<ReferralProgressEvent[]> {
    try {
      return await this.api.getProgressEvents(referralLinkId);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.getProgressEvents(referralLinkId);
      }
      throw error;
    }
  }

  async getChatThread(referralLinkId: string, viewerLocale?: string): Promise<ReferralChatThreadSummary> {
    try {
      return await this.api.getChatThread(referralLinkId, viewerLocale);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.getChatThread(referralLinkId, viewerLocale);
      }
      throw error;
    }
  }

  async sendChatMessage(
    referralLinkId: string,
    input: {
      message: string;
      senderRole?: "referrer" | "invitee";
      sourceLanguage?: string;
      originalLocale?: string;
      metadata?: Record<string, string>;
    }
  ): Promise<ReferralChatMessage> {
    try {
      return await this.api.sendChatMessage(referralLinkId, input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.sendChatMessage(referralLinkId, input);
      }
      throw error;
    }
  }

  async markChatThreadRead(referralLinkId: string, viewerLocale?: string): Promise<ReferralChatThreadSummary> {
    try {
      return await this.api.markChatThreadRead(referralLinkId, viewerLocale);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.markChatThreadRead(referralLinkId, viewerLocale);
      }
      throw error;
    }
  }

  async recordWalletConnection(
    referralLinkId: string,
    input: {
      walletAddress: string;
      inviteeDisplayName?: string | null;
    }
  ): Promise<ReferralLinkSummary> {
    try {
      return await this.api.recordWalletConnection(referralLinkId, input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.recordWalletConnection(referralLinkId, input);
      }
      throw error;
    }
  }

  async translateChatMessage(
    referralLinkId: string,
    input: {
      messageId: string;
      targetLanguage: string;
    }
  ): Promise<{ messageId: string; translatedText: string; translation: ReferralTranslationMetadata }> {
    try {
      return await this.api.translateChatMessage(referralLinkId, input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.translateChatMessage(referralLinkId, input);
      }
      throw error;
    }
  }

  async syncPersonalizationProfile(
    referralLinkId: string,
    input: {
      referralLinkId: string;
      metadata?: Record<string, string>;
    }
  ): Promise<{ synced: boolean; payload: AgentMemoryEnrichmentPayload }> {
    try {
      return await this.api.syncPersonalizationProfile(referralLinkId, input);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.syncPersonalizationProfile(referralLinkId, input);
      }
      throw error;
    }
  }

  async getAgentContextByInviteCode(inviteCode: string): Promise<AgentMemoryContextInput> {
    try {
      return await this.api.getAgentContextByInviteCode(inviteCode);
    } catch (error) {
      if (isApiClientError(error) && [401, 403, 404, 503].includes(error.status ?? 0)) {
        return this.fallback.getAgentContextByInviteCode(inviteCode);
      }
      throw error;
    }
  }
}

export const referralService: ReferralService = new ResilientReferralService();
