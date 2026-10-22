import type { KnowledgeGraphRelationship, PaginatedResult } from "@/types/admin";

interface RelationshipListProps {
  data: PaginatedResult<KnowledgeGraphRelationship> | null;
  isLoading?: boolean;
  onPageChange: (page: number) => void;
}

export function RelationshipList({ data, isLoading = false, onPageChange }: RelationshipListProps) {
  const items = data?.items ?? [];
  const page = data?.page ?? 1;
  const totalPages = Math.max(1, data?.totalPages ?? 1);

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Relationship List</h2>
      <p className="mt-1 text-sm text-muted-foreground">Inspect relationship types and connected entity IDs.</p>

      <div className="mt-3 max-h-[320px] overflow-auto rounded-lg border border-border">
        {isLoading ? <p className="p-3 text-sm text-muted-foreground">Loading relationships...</p> : null}

        {!isLoading && items.length === 0 ? <p className="p-3 text-sm text-muted-foreground">No relationships found.</p> : null}

        {!isLoading && items.length > 0 ? (
          <ul className="divide-y divide-border">
            {items.map((relation) => (
              <li key={relation.id} className="p-3 text-sm">
                <p className="font-medium">{relation.relationshipType}</p>
                <p className="mt-1 text-xs text-muted-foreground break-all">
                  {relation.sourceEntityId} → {relation.targetEntityId}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  label: {relation.label || "-"}
                  {typeof relation.confidence === "number" ? ` | confidence: ${relation.confidence.toFixed(3)}` : ""}
                </p>
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      <div className="mt-3 flex items-center justify-between text-sm">
        <p className="text-muted-foreground">
          Page {page} of {totalPages}
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(Math.max(1, page - 1))}
            className="rounded-md border border-border px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Prev
          </button>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(Math.min(totalPages, page + 1))}
            className="rounded-md border border-border px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
