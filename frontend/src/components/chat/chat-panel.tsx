import type { RefObject } from "react";
import type { AgentMessage, SuggestedAction } from "@/types";
import type { ChatSubmitStatus } from "@/features/chat";
import { ChatComposerDock } from "./chat-composer-dock";
import { ChatComposer } from "./chat-composer";
import { ChatHeader } from "./chat-header";
import { ChatWelcomeState } from "./chat-welcome-state";
import { ChatScrollArea } from "./chat-scroll-area";
import { ChatMessageList } from "./chat-message-list";
import { FailedMessageState } from "./failed-message-state";
import { MessageSkeleton } from "./message-skeleton";
import { SuggestedActions } from "./suggested-actions";
import { ThinkingIndicator } from "./thinking-indicator";
import type { WelcomePrompt } from "./suggested-prompt-grid";

interface ChatPanelProps {
  title: string;
  subtitle: string;
  headerStatus?: "ready" | "thinking" | "streaming" | "sending" | "error";
  messages: AgentMessage[];
  isTyping: boolean;
  isStreaming: boolean;
  hasError?: boolean;
  errorMessage?: string | null;
  canRetryFailedMessage?: boolean;
  submitStatus: ChatSubmitStatus;
  suggestedActions: SuggestedAction[];
  onActionSelect: (action: SuggestedAction, position: number) => void;
  onPromptSelect: (prompt: WelcomePrompt) => void;
  onRetryFailedMessage?: () => void;
  onSubmit: (text: string, attachments: File[]) => void;
  onComposerFocus?: () => void;
  scrollContainerRef: RefObject<HTMLDivElement>;
  bottomAnchorRef: RefObject<HTMLDivElement>;
}

export function ChatPanel({
  title,
  subtitle,
  headerStatus = "ready",
  messages,
  isTyping,
  isStreaming,
  hasError = false,
  errorMessage = null,
  canRetryFailedMessage = false,
  submitStatus,
  suggestedActions,
  onActionSelect,
  onPromptSelect,
  onRetryFailedMessage,
  onSubmit,
  onComposerFocus,
  scrollContainerRef,
  bottomAnchorRef
}: ChatPanelProps) {
  const fallbackPrompts: WelcomePrompt[] = [
    {
      id: "welcome-plan",
      title: "Build a plan",
      description: "Get a structured onboarding outline.",
      prompt: "Create a step-by-step onboarding plan for a new enterprise customer."
    },
    {
      id: "welcome-summary",
      title: "Summarize context",
      description: "Turn raw notes into concise highlights.",
      prompt: "Summarize this user problem in 3 concise bullets and suggest a next action."
    },
    {
      id: "welcome-reply",
      title: "Draft a reply",
      description: "Generate a clear follow-up message.",
      prompt: "Draft a professional follow-up message for a customer who paused onboarding."
    },
    {
      id: "welcome-risks",
      title: "Identify risks",
      description: "Find blockers before they escalate.",
      prompt: "List the top onboarding risks in this scenario and how to mitigate each one."
    }
  ];

  const promptsFromActions: WelcomePrompt[] = suggestedActions.slice(0, 6).map((action, index) => ({
    id: action.id || `suggested-${index}`,
    title: `Suggested prompt ${index + 1}`,
    prompt: action.label,
    description: action.reason
  }));
  const welcomePrompts = promptsFromActions.length > 0 ? promptsFromActions : fallbackPrompts;

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-none border border-transparent bg-background shadow-[0_16px_40px_rgba(2,6,23,0.18)] sm:rounded-2xl">
      <ChatHeader title={title} subtitle={subtitle} status={headerStatus} />

      <ChatScrollArea scrollContainerRef={scrollContainerRef}>
        {messages.length === 0 ? (
          <ChatWelcomeState prompts={welcomePrompts} disabled={submitStatus !== "idle"} onSelectPrompt={onPromptSelect} />
        ) : (
          <ChatMessageList messages={messages} bottomAnchorRef={bottomAnchorRef} />
        )}

        {isStreaming && messages.length === 0 ? (
          <MessageSkeleton />
        ) : null}

        <ThinkingIndicator visible={isTyping && !isStreaming} />

        {hasError && errorMessage ? (
          <div className="mt-3">
            <FailedMessageState
              message={errorMessage}
              canRetry={canRetryFailedMessage}
              onRetry={() => {
                onRetryFailedMessage?.();
              }}
            />
          </div>
        ) : null}

        {suggestedActions.length > 0 ? (
          <div className="mx-auto mb-4 w-full max-w-3xl px-1">
            <SuggestedActions actions={suggestedActions} onActionSelect={onActionSelect} />
          </div>
        ) : null}
      </ChatScrollArea>

      <ChatComposerDock>
        <ChatComposer status={submitStatus} onSubmit={onSubmit} onFocus={onComposerFocus} hasError={hasError} />
      </ChatComposerDock>
    </section>
  );
}
