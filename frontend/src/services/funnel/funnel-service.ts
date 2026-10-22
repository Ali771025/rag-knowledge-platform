import type { FunnelStage } from "@/types";

export interface FunnelDiscoveryItem {
  id: string;
  label: string;
  confidence: number;
}

export interface FunnelDiscoveryInput {
  assistantMessage: string;
  funnelStage?: FunnelStage | string;
}

export interface FunnelService {
  discoverItems: (input: FunnelDiscoveryInput) => Promise<FunnelDiscoveryItem[]>;
}

const stageHints: Record<FunnelStage, string[]> = {
  ENTRY: ["intent capture", "context baseline"],
  EXPLORATION: ["need discovery", "problem framing"],
  TRUST: ["credibility signals", "risk reduction"],
  OPPORTUNITY: ["value alignment", "solution matching"],
  MICRO_COMMITMENT: ["small next action", "commitment prompt"],
  ECONOMIC_ACTION: ["conversion readiness", "action confirmation"]
};

function toId(value: string, index: number): string {
  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized ? `funnel-${normalized}-${index}` : `funnel-item-${index}`;
}

function scoreByIndex(index: number): number {
  return Math.max(0.45, Math.min(0.95, 0.9 - index * 0.08));
}

function collectKeywords(text: string): string[] {
  const words = text
    .split(/[\s,.;:!?()\n]+/)
    .map((word) => word.trim().toLowerCase())
    .filter((word) => word.length >= 5);

  const unique: string[] = [];
  const seen = new Set<string>();

  for (const word of words) {
    if (seen.has(word)) continue;
    seen.add(word);
    unique.push(word);
    if (unique.length >= 4) break;
  }

  return unique.map((word) => word.replace(/[-_]+/g, " "));
}

class MockFunnelService implements FunnelService {
  async discoverItems(input: FunnelDiscoveryInput): Promise<FunnelDiscoveryItem[]> {
    const sourceText = input.assistantMessage.trim();
    const extracted = collectKeywords(sourceText);

    let labels = extracted;
    const normalizedStage = (input.funnelStage ?? "").toString().trim().toUpperCase() as FunnelStage;
    if (labels.length === 0 && normalizedStage in stageHints) {
      labels = stageHints[normalizedStage];
    }
    if (labels.length === 0) {
      labels = ["conversation signal", "user objective"];
    }

    return labels.map((label, index) => ({
      id: toId(label, index),
      label,
      confidence: scoreByIndex(index)
    }));
  }
}

export const funnelService: FunnelService = new MockFunnelService();
