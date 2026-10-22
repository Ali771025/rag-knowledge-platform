interface GraphFiltersValue {
  search: string;
  label: string;
  type: string;
  relationshipType: string;
  depth: number;
}

interface GraphFiltersProps {
  value: GraphFiltersValue;
  onChange: (next: GraphFiltersValue) => void;
  onRefresh: () => void;
}

export function GraphFilters({ value, onChange, onRefresh }: GraphFiltersProps) {
  const set = <K extends keyof GraphFiltersValue>(key: K, nextValue: GraphFiltersValue[K]) => {
    onChange({ ...value, [key]: nextValue });
  };

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Graph Filters</h2>
      <p className="mt-1 text-sm text-muted-foreground">Filter entities, relationships, and graph neighborhood.</p>

      <div className="mt-3 grid gap-3 md:grid-cols-2 lg:grid-cols-6">
        <input
          type="search"
          value={value.search}
          onChange={(event) => set("search", event.target.value)}
          placeholder="Search entities"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />

        <input
          type="text"
          value={value.label}
          onChange={(event) => set("label", event.target.value)}
          placeholder="Source label"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />

        <select
          value={value.type}
          onChange={(event) => set("type", event.target.value)}
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        >
          <option value="">All entity types</option>
          <option value="person">Person</option>
          <option value="organization">Organization</option>
          <option value="concept">Concept</option>
          <option value="technology">Technology</option>
          <option value="location">Location</option>
          <option value="other">Other</option>
        </select>

        <input
          type="text"
          value={value.relationshipType}
          onChange={(event) => set("relationshipType", event.target.value.toUpperCase())}
          placeholder="Relationship type"
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        />

        <select
          value={value.depth}
          onChange={(event) => set("depth", Number(event.target.value))}
          className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
        >
          <option value={1}>Depth 1</option>
          <option value={2}>Depth 2</option>
          <option value={3}>Depth 3</option>
        </select>

        <button
          type="button"
          onClick={onRefresh}
          className="rounded-lg border border-border px-3 py-2 text-sm font-medium"
        >
          Refresh
        </button>
      </div>
    </section>
  );
}
