import type { MessageRole } from "@/types";

export type MessageAlignment = "start" | "end";

export type MessageVisualVariant = "agent" | "user" | "system";

export type ChatSubmitStatus = "idle" | "submitting" | "blocked";

export type ChatRenderMode = "standard" | "streaming";

export interface ChatMessagePresentation {
  role: MessageRole;
  alignment: MessageAlignment;
  variant: MessageVisualVariant;
}
