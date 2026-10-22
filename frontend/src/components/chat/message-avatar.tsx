import type { MessageRole } from "@/types";

interface MessageAvatarProps {
  role: MessageRole;
}

function UserGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <circle cx="12" cy="8" r="3.25" stroke="currentColor" strokeWidth="1.8" />
      <path d="M5 19c1.5-3 4-4.5 7-4.5s5.5 1.5 7 4.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function AssistantGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden="true">
      <rect x="5" y="6" width="14" height="12" rx="4" stroke="currentColor" strokeWidth="1.8" />
      <circle cx="9.5" cy="12" r="1.1" fill="currentColor" />
      <circle cx="14.5" cy="12" r="1.1" fill="currentColor" />
      <path d="M12 3v3M4 12h1M19 12h1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function MessageAvatar({ role }: MessageAvatarProps) {
  const isUser = role === "user";
  const label = isUser ? "User" : "Assistant";
  const toneClass = isUser
    ? "border-slate-600/70 bg-slate-800 text-slate-200"
    : "border-cyan-400/25 bg-cyan-500/15 text-cyan-200";

  return (
    <span
      className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${toneClass}`}
      aria-label={`${label} avatar`}
      title={label}
    >
      {isUser ? <UserGlyph /> : <AssistantGlyph />}
    </span>
  );
}
