import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LoadingFallback, NetworkError } from "@/components/ui";
import { AdminApiError } from "@/services/admin/httpClient";
import { getEntities, getEntityById, getGraph, getRelationships } from "@/services/admin/knowledgeGraphService";
import { EntityDetailsPanel } from "./components/entity-details-panel";
import { EntityExplorer } from "./components/entity-explorer";
import { GraphCanvas } from "./components/graph-canvas";
import { GraphFilters } from "./components/graph-filters";
import { GraphLegend } from "./components/graph-legend";
import { RelationshipList } from "./components/relationship-list";

const PAGE_SIZE = 12;

export function KnowledgeGraphPage() {
  const queryClient = useQueryClient();
  const [entityPage, setEntityPage] = useState(1);
  const [relationshipPage, setRelationshipPage] = useState(1);
  const [selectedEntityId, setSelectedEntityId] = useState<string | undefined>(undefined);
  const [filters, setFilters] = useState({
    search: "",
    label: "",
    type: "",
    relationshipType: "",
    depth: 2
  });

  const entityQuery = useQuery({
    queryKey: ["admin-graph-entities", entityPage, filters.search, filters.label, filters.type],
    queryFn: () =>
      getEntities({
        page: entityPage,
        pageSize: PAGE_SIZE,
        search: filters.search || undefined,
        label: filters.label || undefined,
        type: filters.type || undefined
      })
  });

  const relationshipQuery = useQuery({
    queryKey: ["admin-graph-relationships", relationshipPage, filters.search, filters.label, filters.relationshipType],
    queryFn: () =>
      getRelationships({
        page: relationshipPage,
        pageSize: PAGE_SIZE,
        search: filters.search || undefined,
        label: filters.label || undefined,
        type: filters.type || undefined,
        relationshipType: filters.relationshipType || undefined
      })
  });

  const graphQuery = useQuery({
    queryKey: [
      "admin-graph-visualize",
      filters.search,
      filters.label,
      filters.type,
      filters.relationshipType,
      filters.depth,
      selectedEntityId
    ],
    queryFn: () =>
      getGraph({
        search: filters.search || undefined,
        label: filters.label || undefined,
        type: filters.type || undefined,
        relationshipType: filters.relationshipType || undefined,
        depth: filters.depth,
        centerEntityId: selectedEntityId,
        limit: 180
      })
  });

  const selectedEntityQuery = useQuery({
    queryKey: ["admin-graph-entity", selectedEntityId],
    queryFn: () => getEntityById(selectedEntityId as string),
    enabled: Boolean(selectedEntityId) && graphQuery.data?.graphBackendAvailable !== false
  });

  const isUnavailableByError = useMemo(() => {
    const errors = [entityQuery.error, relationshipQuery.error, graphQuery.error, selectedEntityQuery.error];
    return errors.some((error) => error instanceof AdminApiError && error.status === 503);
  }, [entityQuery.error, relationshipQuery.error, graphQuery.error, selectedEntityQuery.error]);

  const isUnavailableByMetadata = graphQuery.data?.graphBackendAvailable === false;
  const isUnavailable = isUnavailableByError || isUnavailableByMetadata;
  const unavailableReason =
    graphQuery.data?.graphBackendReason ??
    "Neo4j/graph service is not configured or currently unreachable for this environment.";

  const refreshAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-graph-entities"] });
    await queryClient.invalidateQueries({ queryKey: ["admin-graph-relationships"] });
    await queryClient.invalidateQueries({ queryKey: ["admin-graph-visualize"] });
    if (selectedEntityId) {
      await queryClient.invalidateQueries({ queryKey: ["admin-graph-entity", selectedEntityId] });
    }
  };

  return (
    <main className="mx-auto w-full max-w-[1280px] space-y-4 p-4 sm:p-6">
      <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Admin Knowledge Graph</h1>
        <p className="mt-1 text-sm text-muted-foreground">Explore entities, relationships, and local graph neighborhoods.</p>
      </section>

      <section className="flex flex-wrap gap-2 text-sm">
        <a href="/admin/knowledge" className="rounded-md border border-border px-3 py-1.5">
          Knowledge Sources
        </a>
        <a href="/admin/rag" className="rounded-md border border-border px-3 py-1.5">
          RAG Management
        </a>
        <a href="/admin/knowledge-graph" className="rounded-md border border-border bg-muted px-3 py-1.5 font-medium">
          Knowledge Graph
        </a>
      </section>

      <GraphFilters
        value={filters}
        onChange={(next) => {
          setFilters(next);
          setEntityPage(1);
          setRelationshipPage(1);
        }}
        onRefresh={() => {
          void refreshAll();
        }}
      />

      {entityQuery.isLoading || relationshipQuery.isLoading || graphQuery.isLoading ? (
        <LoadingFallback title="Loading knowledge graph" />
      ) : null}

      {isUnavailable ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 shadow-sm">
          <p className="font-medium">Knowledge graph backend is unavailable.</p>
          <p className="mt-1">{unavailableReason}</p>
          <button
            type="button"
            onClick={() => {
              void refreshAll();
            }}
            className="mt-3 rounded-md border border-amber-300 bg-white px-3 py-1.5 text-sm font-medium"
          >
            Retry
          </button>
        </section>
      ) : null}

      {!isUnavailable && (entityQuery.isError || relationshipQuery.isError || graphQuery.isError) ? (
        <NetworkError
          title="Failed to load graph data"
          message={
            entityQuery.error instanceof Error
              ? entityQuery.error.message
              : relationshipQuery.error instanceof Error
                ? relationshipQuery.error.message
                : graphQuery.error instanceof Error
                  ? graphQuery.error.message
                  : "Unknown graph loading error"
          }
          onRetry={() => {
            void refreshAll();
          }}
        />
      ) : null}

      {!isUnavailable && !entityQuery.isError && !relationshipQuery.isError && !graphQuery.isError ? (
        <>
          <section className="grid gap-4 lg:grid-cols-3">
            <EntityExplorer
              data={entityQuery.data ?? null}
              selectedEntityId={selectedEntityId}
              isLoading={entityQuery.isLoading}
              onSelectEntity={(entityId) => {
                setSelectedEntityId(entityId);
              }}
              onPageChange={setEntityPage}
            />

            <EntityDetailsPanel entity={selectedEntityQuery.data ?? null} isLoading={selectedEntityQuery.isLoading} />

            <GraphLegend />
          </section>

          <GraphCanvas
            nodes={graphQuery.data?.nodes ?? []}
            edges={graphQuery.data?.edges ?? []}
            selectedNodeId={selectedEntityId}
            onSelectNode={(nodeId) => {
              setSelectedEntityId(nodeId);
            }}
          />

          <RelationshipList
            data={relationshipQuery.data ?? null}
            isLoading={relationshipQuery.isLoading}
            onPageChange={setRelationshipPage}
          />
        </>
      ) : null}
    </main>
  );
}
