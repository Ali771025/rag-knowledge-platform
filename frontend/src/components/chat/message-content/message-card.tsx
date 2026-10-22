import type { MessageCard as MessageCardType } from "@/types";

interface MessageCardProps {
  card: MessageCardType;
}

export function MessageCard({ card }: MessageCardProps) {
  return (
    <article className="rounded-xl border border-border/80 bg-background/80 p-3">
      <h4 className="text-xs font-semibold text-foreground">{card.title}</h4>
      {card.description ? <p className="mt-1 text-xs text-muted-foreground">{card.description}</p> : null}
      {card.ctaLabel ? (
        <button type="button" className="mt-2 rounded-full border border-border px-3 py-1 text-xs font-medium text-foreground">
          {card.ctaLabel}
        </button>
      ) : null}
    </article>
  );
}
