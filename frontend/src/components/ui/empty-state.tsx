interface EmptyStateProps {
  title: string;
  description?: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <section className="w-full rounded-xl border border-border bg-muted/40 px-4 py-5 text-center" role="status" aria-live="polite">
      <h3 className="font-heading text-sm font-semibold text-foreground">{title}</h3>
      {description ? <p className="font-body mt-1 text-sm text-muted-foreground">{description}</p> : null}
    </section>
  );
}
