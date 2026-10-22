import type { MessagesSchema } from "@/i18n/messages";
import type { ReferralChatThreadSummary, ReferralLinkSummary, ReferralProgressEvent, ReferralTagColor } from "@/services/referral";
import { MotionList, MotionListItem } from "@/components/ui";
import { ReferralLinkCard } from "./referral-link-card";

interface ReferralLinkListProps {
  links: ReferralLinkSummary[];
  locale: string;
  messages: MessagesSchema;
  expandedStatusByLinkId: Record<string, boolean>;
  expandedChatByLinkId: Record<string, boolean>;
  statusEventsByLinkId: Record<string, ReferralProgressEvent[]>;
  chatThreadByLinkId: Record<string, ReferralChatThreadSummary>;
  chatStatusByLinkId: Record<string, "idle" | "loading" | "success" | "error">;
  chatSendingByLinkId: Record<string, boolean>;
  canUseChat: (link: ReferralLinkSummary) => boolean;
  onToggleStatus: (linkId: string) => void;
  onToggleChat: (linkId: string) => void;
  onRetryChat: (linkId: string) => void;
  onSendChatMessage: (linkId: string, message: string) => void;
  onCommitLabel: (linkId: string, label: string) => void;
  onCommitColor: (linkId: string, color: ReferralTagColor) => void;
  onCopySuccess: () => void;
  onCopyError: () => void;
  onShareSuccess: () => void;
  onShareUnavailable: () => void;
  onShareError: () => void;
}

export function ReferralLinkList({
  links,
  locale,
  messages,
  expandedStatusByLinkId,
  expandedChatByLinkId,
  statusEventsByLinkId,
  chatThreadByLinkId,
  chatStatusByLinkId,
  chatSendingByLinkId,
  canUseChat,
  onToggleStatus,
  onToggleChat,
  onRetryChat,
  onSendChatMessage,
  onCommitLabel,
  onCommitColor,
  onCopySuccess,
  onCopyError,
  onShareSuccess,
  onShareUnavailable,
  onShareError,
}: ReferralLinkListProps) {
  return (
    <MotionList className="space-y-3">
      {links.map((link) => (
        <MotionListItem key={link.id}>
          <ReferralLinkCard
            link={link}
            locale={locale}
            messages={messages}
            canUseChat={canUseChat(link)}
            isStatusExpanded={Boolean(expandedStatusByLinkId[link.id])}
            isChatExpanded={Boolean(expandedChatByLinkId[link.id])}
            statusEvents={statusEventsByLinkId[link.id] ?? []}
            chatThread={chatThreadByLinkId[link.id] ?? null}
            chatStatus={chatStatusByLinkId[link.id] ?? "idle"}
            chatSending={Boolean(chatSendingByLinkId[link.id])}
            onToggleStatus={() => onToggleStatus(link.id)}
            onToggleChat={() => onToggleChat(link.id)}
            onRetryChat={() => onRetryChat(link.id)}
            onSendChatMessage={(message) => onSendChatMessage(link.id, message)}
            onCommitLabel={(label) => onCommitLabel(link.id, label)}
            onCommitColor={(color) => onCommitColor(link.id, color)}
            onCopySuccess={onCopySuccess}
            onCopyError={onCopyError}
            onShareSuccess={onShareSuccess}
            onShareUnavailable={onShareUnavailable}
            onShareError={onShareError}
          />
        </MotionListItem>
      ))}
    </MotionList>
  );
}
