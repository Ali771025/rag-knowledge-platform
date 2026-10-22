import { useState } from "react";
import type { ExpandableSection as ExpandableSectionType } from "@/types";
import { useAnalytics } from "@/hooks/use-analytics";

interface ExpandableSectionProps {
  section: ExpandableSectionType;
}

export function ExpandableSection({ section }: ExpandableSectionProps) {
  const [isOpen, setIsOpen] = useState(Boolean(section.initiallyExpanded));
  const { trackInfoExpanded } = useAnalytics();
  const contentId = `expandable-section-${section.id}`;

  return (
    <section className="rounded-xl border border-border/80 bg-background/80">
      <button
        type="button"
        onClick={() =>
          setIsOpen((previous) => {
            const next = !previous;
            trackInfoExpanded(section.id, next, "message_section");
            return next;
          })
        }
        className="flex min-h-10 w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs font-semibold text-foreground"
        aria-expanded={isOpen}
        aria-controls={contentId}
      >
        <span>{section.title}</span>
        <span className="text-muted-foreground">{isOpen ? "Hide" : "Show"}</span>
      </button>
      {isOpen ? (
        <p id={contentId} className="border-t border-border/60 px-3 py-2 text-xs text-muted-foreground">
          {section.content}
        </p>
      ) : null}
    </section>
  );
}
