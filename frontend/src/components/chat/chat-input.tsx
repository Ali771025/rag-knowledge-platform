
import { useMemo, useState, type FormEvent, type KeyboardEvent } from "react";
import { CHAT_INPUT_MAX_LENGTH, type ChatSubmitStatus } from "@/features/chat";

interface ChatInputProps {
  onSubmit: (text: string) => void;
  status?: ChatSubmitStatus;
  maxLength?: number;
  placeholder?: string;
}

export function ChatInput({
  onSubmit,
  status = "idle",
  maxLength = CHAT_INPUT_MAX_LENGTH,
  placeholder = "Type your message..."
}: ChatInputProps) {
  const [value, setValue] = useState("");

  const isDisabled = status === "submitting" || status === "blocked";
  const trimmedValue = value.trim();
  const canSubmit = !isDisabled && trimmedValue.length > 0;

  const helperText = useMemo(() => {
    return `${value.length}/${maxLength}`;
  }, [maxLength, value.length]);

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit(trimmedValue);
    setValue("");
  };

  const handleFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    if (event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    handleSubmit();
  };

  return (
    <form
      onSubmit={handleFormSubmit}
      className="rounded-2xl border border-border bg-background p-3 shadow-sm"
      aria-label="Chat input"
    >
      <label htmlFor="chat-input" className="sr-only">
        Message
      </label>
      <textarea
        id="chat-input"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        className="min-h-24 w-full resize-none border-0 bg-transparent p-0 text-sm text-foreground outline-none"
        placeholder={placeholder}
        maxLength={maxLength}
        disabled={isDisabled}
        aria-disabled={isDisabled}
        aria-label="Message input"
      />

      <div className="mt-2 flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground" aria-live="polite" aria-atomic="true">
          {helperText}
        </p>
        <button
          type="submit"
          disabled={!canSubmit}
          className="min-h-10 rounded-xl bg-primary px-4 py-1.5 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-45"
          aria-label="Send message"
        >
          Send
        </button>
      </div>
    </form>
  );
}
