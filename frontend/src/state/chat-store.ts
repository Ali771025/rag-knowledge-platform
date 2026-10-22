import { create } from "zustand";
import type { AgentMessage, MessageRole } from "@/types";

type StreamingMessageUpdate =
  | string
  | Partial<Pick<AgentMessage, "text" | "actions" | "expandableSections" | "cards" | "metadata" | "isStreaming">>;
type StreamingMessageCompletion =
  | string
  | Partial<Pick<AgentMessage, "text" | "actions" | "expandableSections" | "cards" | "metadata">>;

interface StartStreamingMessageInput {
  initialText?: string;
  role?: MessageRole;
  createdAt?: string;
  metadata?: Record<string, unknown>;
}

interface ChatState {
  messages: AgentMessage[];
}

interface ChatActions {
  addMessage: (message: AgentMessage) => void;
  addMessages: (messages: AgentMessage[]) => void;
  setMessages: (messages: AgentMessage[]) => void;
  startStreamingMessage: (messageId: string, input?: StartStreamingMessageInput) => void;
  updateStreamingMessage: (messageId: string, update: StreamingMessageUpdate) => void;
  appendToStreamingMessage: (messageId: string, chunk: string) => void;
  completeStreamingMessage: (messageId: string, finalUpdate?: StreamingMessageCompletion) => void;
  replaceMessage: (messageId: string, nextMessage: AgentMessage) => void;
  removeMessage: (messageId: string) => void;
  clearMessages: () => void;
  getLastMessageByRole: (role: MessageRole) => AgentMessage | undefined;
}

type ChatStore = ChatState & ChatActions;

export type { StartStreamingMessageInput, StreamingMessageCompletion, StreamingMessageUpdate };
export type { ChatState, ChatActions, ChatStore };

export const initialChatState: ChatState = {
  messages: []
};

export const useChatStore = create<ChatStore>((set, get) => ({
  ...initialChatState,
  addMessage: (message) => {
    set((state) => ({
      messages: [...state.messages, message]
    }));
  },
  addMessages: (messages) => {
    if (messages.length === 0) return;

    set((state) => ({
      messages: [...state.messages, ...messages]
    }));
  },
  setMessages: (messages) => {
    set((state) => {
      const hasSameLength = state.messages.length === messages.length;
      const hasSameOrderAndContent =
        hasSameLength &&
        state.messages.every(
          (message, index) =>
            message.id === messages[index]?.id &&
            message.text === messages[index]?.text &&
            message.role === messages[index]?.role &&
            message.isStreaming === messages[index]?.isStreaming
        );

      if (hasSameOrderAndContent) {
        return state;
      }

      return {
        messages: [...messages]
      };
    });
  },
  startStreamingMessage: (messageId, input) => {
    if (!messageId) return;

    set((state) => {
      const index = state.messages.findIndex((message) => message.id === messageId);
      if (index === -1) {
        return {
          messages: [
            ...state.messages,
            {
              id: messageId,
              role: input?.role ?? "agent",
              text: input?.initialText ?? "",
              createdAt: input?.createdAt ?? new Date().toISOString(),
              metadata: input?.metadata,
              isStreaming: true
            }
          ]
        };
      }

      return {
        messages: state.messages.map((message) => {
          if (message.id !== messageId) return message;

          return {
            ...message,
            role: input?.role ?? message.role,
            text: input?.initialText ?? message.text,
            createdAt: input?.createdAt ?? message.createdAt,
            metadata: input?.metadata ?? message.metadata,
            isStreaming: true
          };
        })
      };
    });
  },
  updateStreamingMessage: (messageId, update) => {
    if (!messageId) return;

    set((state) => ({
      // Update by id with a pure map so chunk order remains deterministic in future stream handlers.
      messages:
        state.messages.some((message) => message.id === messageId)
          ? state.messages.map((message) => {
              if (message.id !== messageId) return message;

              if (typeof update === "string") {
                return {
                  ...message,
                  text: update,
                  isStreaming: true
                };
              }

              return {
                ...message,
                ...update
              };
            })
          : [
              ...state.messages,
              {
                id: messageId,
                role: "agent",
                text: typeof update === "string" ? update : update.text ?? "",
                createdAt: new Date().toISOString(),
                metadata: typeof update === "string" ? undefined : update.metadata,
                isStreaming: true
              }
            ]
    }));
  },
  appendToStreamingMessage: (messageId, chunk) => {
    if (!messageId || !chunk) return;

    set((state) => ({
      messages:
        state.messages.some((message) => message.id === messageId)
          ? state.messages.map((message) => {
              if (message.id !== messageId) return message;

              return {
                ...message,
                text: `${message.text}${chunk}`,
                isStreaming: true
              };
            })
          : [
              ...state.messages,
              {
                id: messageId,
                role: "agent",
                text: chunk,
                createdAt: new Date().toISOString(),
                isStreaming: true
              }
            ]
    }));
  },
  completeStreamingMessage: (messageId, finalUpdate) => {
    if (!messageId) return;

    set((state) => {
      const hasMessage = state.messages.some((message) => message.id === messageId);
      if (!hasMessage) {
        if (!finalUpdate) {
          return { messages: state.messages };
        }

        return {
          messages: [
            ...state.messages,
            {
              id: messageId,
              role: "agent",
              text: typeof finalUpdate === "string" ? finalUpdate : finalUpdate.text ?? "",
              createdAt: new Date().toISOString(),
              actions: typeof finalUpdate === "string" ? undefined : finalUpdate.actions,
              expandableSections: typeof finalUpdate === "string" ? undefined : finalUpdate.expandableSections,
              cards: typeof finalUpdate === "string" ? undefined : finalUpdate.cards,
              metadata: typeof finalUpdate === "string" ? undefined : finalUpdate.metadata,
              isStreaming: false
            }
          ]
        };
      }

      return {
        messages: state.messages.map((message) => {
          if (message.id !== messageId) return message;

          if (!finalUpdate) {
            return {
              ...message,
              isStreaming: false
            };
          }

          if (typeof finalUpdate === "string") {
            return {
              ...message,
              text: finalUpdate,
              isStreaming: false
            };
          }

          return {
            ...message,
            ...finalUpdate,
            isStreaming: false
          };
        })
      };
    });
  },
  replaceMessage: (messageId, nextMessage) => {
    set((state) => ({
      messages: state.messages.map((message) => (message.id === messageId ? nextMessage : message))
    }));
  },
  removeMessage: (messageId) => {
    set((state) => ({
      messages: state.messages.filter((message) => message.id !== messageId)
    }));
  },
  clearMessages: () => {
    set({ messages: [] });
  },
  getLastMessageByRole: (role) => {
    const { messages } = get();

    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];
      if (message?.role === role) {
        return message;
      }
    }

    return undefined;
  }
}));
