import type { EntityMetadata, PaginatedResult } from "@/types/admin";

interface EntityExplorerProps {
  data: PaginatedResult<EntityMetadata> | null;
  selectedEntityId?: string;
  isLoading?: boolean;
  onSelectEntity: (entityId: string) => void;
  onPageChange: (page: number) => void;
}

export function EntityExplorer({
  data,
  selectedEntityId,
  isLoading = false,
  onSelectEntity,
  onPageChange
}: EntityExplorerProps) {
  const items = data?.items ?? [];
  const page = data?.page ?? 1;
  const totalPages = Math.max(1, data?.totalPages ?? 1);

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Entity Explorer</h2>
      <p className="mt-1 text-sm text-muted-foreground">Browse entities and select one to center the graph view.</p>

      <div className="mt-3 max-h-[320px] overflow-auto rounded-lg border border-border">
        {isLoading ? <p className="p-3 text-sm text-muted-foreground">Loading entities...</p> : null}

        {!isLoading && items.length === 0 ? <p className="p-3 text-sm text-muted-foreground">No entities found.</p> : null}

        {!isLoading && items.length > 0 ? (
          <ul className="divide-y divide-border">
            {items.map((entity) => {
              const selected = entity.id === selectedEntityId;
              return (
                <li key={entity.id}>
                  <button
                    type="button"
                    onClick={() => onSelectEntity(entity.id)}
                    className={`w-full px-3 py-2 text-left text-sm transition ${
                      selected ? "bg-muted text-foreground" : "hover:bg-muted/50"
                    }`}
                  >
                    <p className="font-medium">{entity.name}</p>
                    <p className="text-xs text-muted-foreground">
                      type: {entity.type} | label: {entity.label || "-"}
                    </p>
                  </button>
                </li>
              );
            })}
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
