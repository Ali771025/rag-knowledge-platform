import type { EntityMetadata } from "@/types/admin";

interface EntityDetailsPanelProps {
  entity: EntityMetadata | null;
  isLoading?: boolean;
}

export function EntityDetailsPanel({ entity, isLoading = false }: EntityDetailsPanelProps) {
  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Entity Details</h2>

      {isLoading ? <p className="mt-2 text-sm text-muted-foreground">Loading entity details...</p> : null}

      {!isLoading && !entity ? <p className="mt-2 text-sm text-muted-foreground">Select an entity to inspect details.</p> : null}

      {!isLoading && entity ? (
        <div className="mt-3 space-y-2 text-sm">
          <p>
            <span className="font-medium">Name:</span> {entity.name}
          </p>
          <p>
            <span className="font-medium">Type:</span> {entity.type}
          </p>
          <p>
            <span className="font-medium">Label:</span> {entity.label || "-"}
          </p>
          <p>
            <span className="font-medium">Domain:</span> {entity.domain || "-"}
          </p>
          <p>
            <span className="font-medium">Confidence:</span>{" "}
            {typeof entity.confidence === "number" ? entity.confidence.toFixed(3) : "-"}
          </p>
          <p>
            <span className="font-medium">Aliases:</span> {entity.aliases?.join(", ") || "-"}
          </p>
          <p>
            <span className="font-medium">Description:</span> {entity.description || "-"}
          </p>
          {entity.metadata ? (
            <details className="mt-2 rounded-md border border-border bg-muted/40 p-2">
              <summary className="cursor-pointer font-medium">Metadata</summary>
              <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(entity.metadata, null, 2)}</pre>
            </details>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
