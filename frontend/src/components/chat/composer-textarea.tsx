import { useLayoutEffect, useRef, type KeyboardEvent } from "react";

interface ComposerTextareaProps {
  value: string;
  onValueChange: (value: string) => void;
  onSubmit: () => void;
  onFocus?: () => void;
  placeholder: string;
  disabled?: boolean;
  maxLength: number;
  minHeight?: number;
  maxHeight?: number;
}

export function ComposerTextarea({
  value,
  onValueChange,
  onSubmit,
  onFocus,
  placeholder,
  disabled = false,
  maxLength,
  minHeight = 88,
  maxHeight = 240
}: ComposerTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = `${minHeight}px`;
    const nextHeight = Math.min(maxHeight, Math.max(minHeight, textarea.scrollHeight));
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [maxHeight, minHeight, value]);

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }

    if (event.nativeEvent.isComposing) {
      return;
    }

    event.preventDefault();
    onSubmit();
  };

  return (
    <textarea
      ref={textareaRef}
      value={value}
      onChange={(event) => onValueChange(event.target.value)}
      onKeyDown={handleKeyDown}
      onFocus={onFocus}
      disabled={disabled}
      maxLength={maxLength}
      placeholder={placeholder}
      className="w-full resize-none border-0 bg-transparent px-0 py-0 text-[15px] leading-7 text-slate-100 placeholder:text-slate-500 outline-none"
      aria-label="Message input"
    />
  );
}
