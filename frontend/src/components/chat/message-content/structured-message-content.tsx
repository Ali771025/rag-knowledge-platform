import type { AgentMessage } from "@/types";
import { PlainTextContent } from "./plain-text-content";
import { MessageCard } from "./message-card";
import { ExpandableSection } from "./expandable-section";
import { QoraStructuredResponse } from "@/features/qora";
import type { QoraAgentResponse } from "@/core/api";

interface StructuredMessageContentProps {
  message: AgentMessage;
}

export function StructuredMessageContent({ message }: StructuredMessageContentProps) {
  const qoraResponse = message.metadata?.qoraResponse as QoraAgentResponse | undefined;
  const hasCards = Boolean(message.cards?.length);
  const hasSections = Boolean(message.expandableSections?.length);

  if (!hasCards && !hasSections) {
    return (
      <div>
        <PlainTextContent text={message.text} />
        {qoraResponse?.request_id ? <QoraStructuredResponse response={qoraResponse} /> : null}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {message.text ? <PlainTextContent text={message.text} /> : null}

      {hasSections ? (
        <div className="space-y-2">
          {message.expandableSections?.map((section) => (
            <ExpandableSection key={section.id} section={section} />
          ))}
        </div>
      ) : null}

      {hasCards ? (
        <div className="space-y-2">
          {message.cards?.map((card) => (
            <MessageCard key={card.id} card={card} />
          ))}
        </div>
      ) : null}
      {qoraResponse?.request_id ? <QoraStructuredResponse response={qoraResponse} /> : null}
    </div>
  );
}
