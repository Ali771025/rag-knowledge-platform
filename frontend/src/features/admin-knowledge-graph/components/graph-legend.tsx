const legendItems = [
  { type: "person", color: "#ef4444" },
  { type: "organization", color: "#3b82f6" },
  { type: "concept", color: "#22c55e" },
  { type: "technology", color: "#f97316" },
  { type: "location", color: "#14b8a6" },
  { type: "other", color: "#64748b" }
] as const;

export function GraphLegend() {
  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Graph Legend</h2>
      <ul className="mt-3 grid gap-2 sm:grid-cols-2">
        {legendItems.map((item) => (
          <li key={item.type} className="flex items-center gap-2 text-sm">
            <span className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
            <span className="capitalize">{item.type}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
