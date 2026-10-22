export const MESSAGE_ROLES = ["agent", "user", "system"] as const;
export type MessageRole = (typeof MESSAGE_ROLES)[number];

export const PERSONA_TYPES = ["SAVER", "HUNTER", "PLAYER", "ARCHITECT", "UNKNOWN"] as const;
export type PersonaType = (typeof PERSONA_TYPES)[number];

export const FUNNEL_STAGES = [
  "ENTRY",
  "EXPLORATION",
  "TRUST",
  "OPPORTUNITY",
  "MICRO_COMMITMENT",
  "ECONOMIC_ACTION"
] as const;
export type FunnelStage = (typeof FUNNEL_STAGES)[number];

export interface SuggestedAction {
  id: string;
  label: string;
  kind: "primary" | "secondary" | "link" | "system";
  value?: string;
  disabled?: boolean;
  reason?: string;
  metadata?: Record<string, unknown>;
}

export interface ExpandableSection {
  id: string;
  title: string;
  content: string;
  initiallyExpanded?: boolean;
}

export interface MessageCard {
  id: string;
  title: string;
  description?: string;
  ctaLabel?: string;
  ctaValue?: string;
  metadata?: Record<string, unknown>;
}

export interface AgentMessage {
  id: string;
  role: MessageRole;
  text: string;
  createdAt: string;
  actions?: SuggestedAction[];
  expandableSections?: ExpandableSection[];
  cards?: MessageCard[];
  metadata?: Record<string, unknown>;
  isStreaming?: boolean;
}

export interface SessionStateSnapshot {
  sessionId: string | null;
  persona: PersonaType;
  confidence: number | null;
  trustScore: number | null;
  funnelStage: FunnelStage;
  suggestedActions: SuggestedAction[];
  metadata?: Record<string, unknown>;
}
