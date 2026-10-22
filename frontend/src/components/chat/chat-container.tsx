import { useMemo, useRef, useState } from "react";
import { ChatPanel } from "./chat-panel";
import { ChatErrorBanner } from "./chat-error-banner";
import { sendChatMessage } from "@/core/api";
import type { ChatSubmitStatus } from "@/features/chat";
import type { AgentMessage, SuggestedAction } from "@/types";
import type { WelcomePrompt } from "./suggested-prompt-grid";

function createMessageId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `message-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function ChatContainer() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastAttemptedInput, setLastAttemptedInput] = useState<string | null>(null);
  const [suggestedActions, setSuggestedActions] = useState<SuggestedAction[]>([]);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomAnchorRef = useRef<HTMLDivElement>(null);

  const submitStatus: ChatSubmitStatus = isSubmitting ? "submitting" : "idle";

  const headerStatus = errorMessage ? "error" : isSubmitting ? "sending" : "ready";

  const scrollToBottom = () => {
    window.requestAnimationFrame(() => {
      bottomAnchorRef.current?.scrollIntoView({ behavior: "smooth", block: "end", inline: "nearest" });
    });
  };

  const resolveKnowledgeLabels = (): string[] | undefined => {
    if (typeof window === "undefined") return undefined;
    const raw = window.localStorage.getItem("chatKnowledgeLabels");
    if (!raw) return undefined;
    const labels = raw
      .split(",")
      .map((item) => item.trim().toLowerCase())
      .filter(Boolean);
    return labels.length > 0 ? labels : undefined;
  };

  const resolveMemoryScope = (): string | undefined => {
    if (typeof window === "undefined") return undefined;
    const raw = window.localStorage.getItem("chatMemoryScope");
    const normalized = raw?.trim().toLowerCase();
    return normalized || undefined;
  };

  const handleSubmitMessage = async (text: string, attachments: File[] = []) => {
    const normalized = text.trim();
    if ((!normalized && attachments.length === 0) || isSubmitting) return;

    setErrorMessage(null);
    setLastAttemptedInput(normalized || null);

    const attachmentSummary =
      attachments.length > 0
        ? `\n\nAttached files:\n${attachments.map((file) => `- ${file.name}`).join("\n")}`
        : "";
    const userVisibleText = `${normalized}${attachmentSummary}`.trim();

    const userMessage: AgentMessage = {
      id: createMessageId(),
      role: "user",
      text: userVisibleText,
      createdAt: new Date().toISOString()
    };

    setMessages((previous) => [...previous, userMessage]);
    setIsSubmitting(true);

    try {
      const response = await sendChatMessage({
        message: normalized,
        knowledgeLabels: resolveKnowledgeLabels(),
        memoryScope: resolveMemoryScope(),
        attachments,
      });

      const assistantMessage: AgentMessage = {
        id: createMessageId(),
        role: "agent",
        text: response.message,
        createdAt: response.timestamp ?? new Date().toISOString()
      };

      setMessages((previous) => [...previous, assistantMessage]);
      setSuggestedActions(response.suggestedActions ?? []);
      scrollToBottom();
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Failed to send message.";
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const chatTitle = useMemo(() => {
    if (messages.length === 0) return "New conversation";
    const firstUser = messages.find((message) => message.role === "user");
    if (!firstUser?.text) return "Conversation";
    return firstUser.text.length > 56 ? `${firstUser.text.slice(0, 56)}...` : firstUser.text;
  }, [messages]);

  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-hidden px-3 py-3 sm:px-4 sm:py-4" aria-label="Chat container">
      {errorMessage ? (
        <ChatErrorBanner
          message={errorMessage}
          onDismiss={() => setErrorMessage(null)}
          onRetry={() => {
            if (!lastAttemptedInput) return;
            void handleSubmitMessage(lastAttemptedInput);
          }}
        />
      ) : null}

      <div className="min-h-0 flex-1">
        <ChatPanel
          title={chatTitle}
          subtitle="Workspace assistant"
          headerStatus={headerStatus}
          messages={messages}
          isTyping={false}
          isStreaming={false}
          hasError={Boolean(errorMessage)}
          errorMessage={errorMessage}
          canRetryFailedMessage={Boolean(lastAttemptedInput)}
          submitStatus={submitStatus}
          suggestedActions={suggestedActions}
          onActionSelect={(action) => {
            void handleSubmitMessage(action.label);
          }}
          onPromptSelect={(prompt: WelcomePrompt) => {
            void handleSubmitMessage(prompt.prompt);
          }}
          onRetryFailedMessage={() => {
            if (!lastAttemptedInput) return;
            void handleSubmitMessage(lastAttemptedInput);
          }}
          onSubmit={(text, attachments) => {
            void handleSubmitMessage(text, attachments);
          }}
          scrollContainerRef={scrollContainerRef}
          bottomAnchorRef={bottomAnchorRef}
        />
      </div>
    </section>
  );
}
