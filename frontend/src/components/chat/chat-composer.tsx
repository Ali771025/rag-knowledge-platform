import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";
import {
  ArrowUp,
  CircleX,
  File,
  FileArchive,
  FileCode2,
  FileImage,
  FileText,
  Loader2,
  Paperclip,
  Trash2
} from "lucide-react";
import { CHAT_INPUT_MAX_LENGTH, type ChatSubmitStatus } from "@/features/chat";
import { useChatComposerDraftStore } from "@/state";

interface ChatComposerProps {
  status: ChatSubmitStatus;
  onSubmit: (text: string, attachments: File[]) => void;
  onFocus?: () => void;
  hasError?: boolean;
}

function getAttachmentIcon(file: File) {
  const lowerName = file.name.toLowerCase();

  if (file.type.startsWith("image/")) {
    return <FileImage className="h-4 w-4 text-cyan-200/90" aria-hidden="true" />;
  }
  if (file.type.startsWith("text/") || lowerName.endsWith(".txt")) {
    return <FileText className="h-4 w-4 text-emerald-200/90" aria-hidden="true" />;
  }
  if (lowerName.endsWith(".md") || lowerName.endsWith(".markdown")) {
    return <FileCode2 className="h-4 w-4 text-indigo-200/90" aria-hidden="true" />;
  }
  if (lowerName.endsWith(".pdf") || lowerName.endsWith(".doc") || lowerName.endsWith(".docx")) {
    return <FileArchive className="h-4 w-4 text-amber-200/90" aria-hidden="true" />;
  }

  return <File className="h-4 w-4 text-white/80" aria-hidden="true" />;
}

export function ChatComposer({ status, onSubmit, onFocus, hasError = false }: ChatComposerProps) {
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isFocused, setIsFocused] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const draft = useChatComposerDraftStore((state) => state.draft);
  const clearDraft = useChatComposerDraftStore((state) => state.clearDraft);

  const trimmed = value.trim();
  const isSubmitting = status === "submitting";
  const isStreaming = status === "blocked";
  const isDisabled = isSubmitting || isStreaming;
  const canSubmit = !isDisabled && (trimmed.length > 0 || attachments.length > 0);

  const containerClassName = useMemo(() => {
    if (hasError) {
      return "border-rose-400/65";
    }

    if (isFocused) {
      return "border-white/25";
    }

    return "border-white/10";
  }, [hasError, isFocused]);

  const attachmentPreviewUrls = useMemo(() => {
    return attachments.map((file) =>
      file.type.startsWith("image/")
        ? {
            key: `${file.name}-${file.size}-${file.lastModified}`,
            url: URL.createObjectURL(file)
          }
        : null
    );
  }, [attachments]);

  useEffect(() => {
    return () => {
      attachmentPreviewUrls.forEach((item) => {
        if (item?.url) {
          URL.revokeObjectURL(item.url);
        }
      });
    };
  }, [attachmentPreviewUrls]);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const minHeight = 44;
    const maxHeight = 180;
    textarea.style.height = `${minHeight}px`;
    const nextHeight = Math.min(maxHeight, Math.max(minHeight, textarea.scrollHeight));
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [value]);

  useEffect(() => {
    if (!draft.trim()) return;
    setValue(draft);
    clearDraft();
    textareaRef.current?.focus();
  }, [clearDraft, draft]);

  const handleSubmit = () => {
    if (!canSubmit) return;
    onSubmit(trimmed, attachments);
    setValue("");
    setAttachments([]);
  };

  const handleFormSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    handleSubmit();
  };

  const handleFilesSelected = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFiles = Array.from(event.target.files ?? []);
    if (nextFiles.length === 0) return;

    const allowedExtensions = new Set([".txt", ".md", ".markdown", ".pdf", ".doc", ".docx"]);
    const filtered = nextFiles.filter((file) => {
      if (file.type.startsWith("image/") || file.type.startsWith("text/")) return true;
      const lowerName = file.name.toLowerCase();
      return Array.from(allowedExtensions).some((extension) => lowerName.endsWith(extension));
    });

    setAttachments((previous) => {
      const merged = [...previous];
      filtered.forEach((file) => {
        const duplicate = merged.some(
          (item) => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified
        );
        if (!duplicate) {
          merged.push(file);
        }
      });
      return merged.slice(0, 6);
    });
    event.target.value = "";
  };

  const handleTextareaKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    if (event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    handleSubmit();
  };

  const hasAnyAttachment = attachments.length > 0;

  return (
    <form
      onSubmit={handleFormSubmit}
      className={`w-full max-w-[900px] rounded-[24px] border bg-[#2f2f2f] px-2.5 py-2.5 shadow-lg sm:rounded-[28px] sm:px-3 sm:py-3 ${containerClassName}`}
      aria-label="Chat composer"
      aria-busy={isSubmitting || isStreaming}
      aria-disabled={isDisabled}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,.txt,.md,.markdown,.pdf,.doc,.docx"
        multiple
        className="hidden"
        onChange={handleFilesSelected}
      />

      {hasAnyAttachment ? (
        <div className="-mx-0.5 mb-2 flex gap-2 overflow-x-auto px-0.5 pb-1">
          {attachments.map((file) => {
            const key = `${file.name}-${file.size}-${file.lastModified}`;
            const previewUrl = attachmentPreviewUrls.find((item) => item?.key === key)?.url ?? null;
            return (
              <div
                key={key}
                className="relative h-14 w-14 shrink-0 overflow-hidden rounded-xl border border-white/10 bg-black/20"
              >
                {previewUrl ? (
                  <img src={previewUrl} alt={file.name} className="h-14 w-14 object-cover" />
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-white/[0.03]">
                    {getAttachmentIcon(file)}
                  </div>
                )}

                {previewUrl ? (
                  <div className="pointer-events-none absolute bottom-1 left-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-black/55">
                    <FileImage className="h-3 w-3 text-cyan-200/90" aria-hidden="true" />
                  </div>
                ) : (
                  <div className="pointer-events-none absolute bottom-1 left-1 inline-flex rounded-full bg-black/45 px-1.5 py-0.5 text-[8px] font-medium uppercase tracking-wide text-white/80">
                    {file.name.split(".").pop()?.slice(0, 4) ?? "FILE"}
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => {
                    setAttachments((previous) =>
                      previous.filter(
                        (item) =>
                          !(
                            item.name === file.name &&
                            item.size === file.size &&
                            item.lastModified === file.lastModified
                          )
                      )
                    );
                  }}
                  className="absolute right-1 top-1 inline-flex h-5 w-5 items-center justify-center rounded-full bg-black/55 text-white/80 transition hover:bg-black/75 hover:text-white"
                  aria-label={`Remove ${file.name}`}
                >
                  <CircleX className="h-3.5 w-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      ) : null}

      <div
        onFocus={() => setIsFocused(true)}
        onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
            setIsFocused(false);
          }
        }}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleTextareaKeyDown}
          onFocus={onFocus}
          disabled={isDisabled}
          maxLength={CHAT_INPUT_MAX_LENGTH}
          placeholder="Ask anything..."
          className="min-h-[44px] max-h-[180px] w-full resize-none bg-transparent px-2 text-[15px] leading-6 text-white placeholder-white/45 outline-none sm:text-base"
          aria-label="Message input"
        />
      </div>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-y-2">
        <div className="flex items-center gap-1.5 sm:gap-2">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isDisabled}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label={hasAnyAttachment ? `Files (${attachments.length})` : "Attach files"}
          >
            <Paperclip className="h-4 w-4" />
          </button>
          {hasAnyAttachment ? (
            <button
              type="button"
              onClick={() => setAttachments([])}
              disabled={isDisabled}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full text-white transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-40"
              aria-label="Clear attachments"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        <div className="ml-auto flex items-center gap-2 pl-2">
          <p className="text-[11px] tabular-nums text-white/55 sm:text-xs">
            {value.length}/{CHAT_INPUT_MAX_LENGTH}
          </p>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`inline-flex h-9 w-9 items-center justify-center rounded-full transition disabled:cursor-not-allowed ${
              canSubmit
                ? "bg-white text-black hover:bg-white/90"
                : "bg-white/10 text-white/40"
            }`}
            aria-label="Send message"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <ArrowUp className="h-4 w-4" aria-hidden="true" />
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
