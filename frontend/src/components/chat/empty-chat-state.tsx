export function EmptyChatState() {
  const suggestions = [
    "Help me build an onboarding plan",
    "Summarize this user problem in 3 bullets",
    "Draft a follow-up message for this lead"
  ];

  return (
    <section className="rounded-3xl border border-dashed border-border bg-muted/60 px-5 py-8 text-center sm:px-8 sm:py-10">
      <h2 className="text-base font-semibold text-foreground sm:text-lg">Welcome to your onboarding assistant</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Share your goal, ask a question, or choose a suggested action to begin.
      </p>

      <div className="mt-5 grid gap-2 sm:grid-cols-3">
        {suggestions.map((suggestion) => (
          <div key={suggestion} className="rounded-xl border border-border bg-background px-3 py-2 text-left text-xs text-muted-foreground">
            {suggestion}
          </div>
        ))}
      </div>
    </section>
  );
}
