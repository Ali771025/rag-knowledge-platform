import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoadingFallback, NetworkError } from "@/components/ui";
import {
  bulkDeleteKnowledgeSources,
  bulkReprocessKnowledgeSources,
  createKnowledgeSourceFromUrl,
  deleteKnowledgeSource,
  getKnowledgeSource,
  getKnowledgeSourceStatus,
  getKnowledgeSources,
  reprocessKnowledgeSource,
  updateKnowledgeSourceLabel,
  uploadKnowledgeSource
} from "@/services/admin/knowledgeService";
import { SourceUploader } from "./components/source-uploader";
import { UrlIngestionForm } from "./components/url-ingestion-form";
import { SourceTable } from "./components/source-table";
import { SourceDetailsDrawer } from "./components/source-details-drawer";

const DEFAULT_PAGE_SIZE = 10;

export function KnowledgeManagementPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [label, setLabel] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [detailsSourceId, setDetailsSourceId] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const sourceQuery = useQuery({
    queryKey: ["admin-knowledge-sources", page, search, label, statusFilter, typeFilter],
    queryFn: () =>
      getKnowledgeSources({
        page,
        pageSize: DEFAULT_PAGE_SIZE,
        search: search || undefined,
        label: label || undefined,
        status: statusFilter || undefined,
        type: typeFilter || undefined
      })
  });

  const detailsQuery = useQuery({
    queryKey: ["admin-knowledge-source", detailsSourceId],
    queryFn: () => getKnowledgeSource(detailsSourceId as string),
    enabled: Boolean(detailsSourceId)
  });

  const statusQuery = useQuery({
    queryKey: ["admin-knowledge-source-status", detailsSourceId],
    queryFn: () => getKnowledgeSourceStatus(detailsSourceId as string),
    enabled: Boolean(detailsSourceId)
  });

  const uploadMutation = useMutation({
    mutationFn: uploadKnowledgeSource,
    onSuccess: async () => {
      setMutationError(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
    }
  });

  const urlMutation = useMutation({
    mutationFn: createKnowledgeSourceFromUrl,
    onSuccess: async () => {
      setMutationError(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: deleteKnowledgeSource,
    onSuccess: async () => {
      setMutationError(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
      if (detailsSourceId) {
        setDetailsSourceId(null);
      }
    }
  });

  const reprocessMutation = useMutation({
    mutationFn: reprocessKnowledgeSource,
    onSuccess: async () => {
      setMutationError(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
      if (detailsSourceId) {
        await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-source-status", detailsSourceId] });
      }
    }
  });

  const updateLabelMutation = useMutation({
    mutationFn: ({ id, nextLabel }: { id: string; nextLabel: string }) => updateKnowledgeSourceLabel(id, nextLabel),
    onSuccess: async (_, variables) => {
      setMutationError(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-source", variables.id] });
    }
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: bulkDeleteKnowledgeSources,
    onSuccess: async () => {
      setMutationError(null);
      setSelectedIds([]);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
    }
  });

  const bulkReprocessMutation = useMutation({
    mutationFn: bulkReprocessKnowledgeSources,
    onSuccess: async () => {
      setMutationError(null);
      setSelectedIds([]);
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
    }
  });

  const isMutating =
    uploadMutation.isPending ||
    urlMutation.isPending ||
    deleteMutation.isPending ||
    reprocessMutation.isPending ||
    updateLabelMutation.isPending ||
    bulkDeleteMutation.isPending ||
    bulkReprocessMutation.isPending;

  const items = sourceQuery.data?.items ?? [];
  const totalPages = sourceQuery.data?.totalPages ?? 0;

  const detailsSource = useMemo(() => {
    if (detailsQuery.data) return detailsQuery.data;
    if (!detailsSourceId) return null;
    return items.find((item) => item.id === detailsSourceId) ?? null;
  }, [detailsQuery.data, detailsSourceId, items]);

  const toggleSelect = (id: string) => {
    setSelectedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const toggleSelectAll = () => {
    const ids = items.map((item) => item.id);
    const allSelected = ids.length > 0 && ids.every((id) => selectedIds.includes(id));
    setSelectedIds(allSelected ? [] : ids);
  };

  const refreshAll = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-sources"] });
    if (detailsSourceId) {
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-source", detailsSourceId] });
      await queryClient.invalidateQueries({ queryKey: ["admin-knowledge-source-status", detailsSourceId] });
    }
  };

  return (
    <main className="mx-auto w-full max-w-[1200px] space-y-4 p-4 sm:p-6">
      <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Admin Knowledge Management</h1>
        <p className="mt-1 text-sm text-muted-foreground">Upload sources, ingest URLs, monitor processing, and manage labels.</p>
      </section>

      <section className="flex flex-wrap gap-2 text-sm">
        <a href="/admin/knowledge" className="rounded-md border border-border bg-muted px-3 py-1.5 font-medium">
          Knowledge Sources
        </a>
        <a href="/admin/rag" className="rounded-md border border-border px-3 py-1.5">
          RAG Management
        </a>
        <a href="/admin/knowledge-graph" className="rounded-md border border-border px-3 py-1.5">
          Knowledge Graph
        </a>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <SourceUploader
          onSubmit={async (formData) => {
            try {
              await uploadMutation.mutateAsync(formData);
            } catch (error) {
              setMutationError(error instanceof Error ? error.message : "Upload failed.");
            }
          }}
          isSubmitting={uploadMutation.isPending}
        />

        <UrlIngestionForm
          onSubmit={async (payload) => {
            try {
              await urlMutation.mutateAsync(payload);
            } catch (error) {
              setMutationError(error instanceof Error ? error.message : "URL ingestion failed.");
            }
          }}
          isSubmitting={urlMutation.isPending}
        />
      </section>

      <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Search name/domain/label"
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />

          <input
            type="text"
            value={label}
            onChange={(event) => {
              setLabel(event.target.value);
              setPage(1);
            }}
            placeholder="Filter by label"
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />

          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
          </select>

          <select
            value={typeFilter}
            onChange={(event) => {
              setTypeFilter(event.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
          >
            <option value="">All types</option>
            <option value="file">File</option>
            <option value="url">URL</option>
          </select>

          <button
            type="button"
            onClick={() => void refreshAll()}
            disabled={isMutating}
            className="rounded-lg border border-border px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
          >
            Refresh
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            disabled={selectedIds.length === 0 || bulkDeleteMutation.isPending}
            onClick={() => {
              if (!window.confirm(`Delete ${selectedIds.length} selected source(s)? This action cannot be undone.`)) return;
              void bulkDeleteMutation.mutateAsync(selectedIds).catch((error: unknown) => {
                setMutationError(error instanceof Error ? error.message : "Bulk delete failed.");
              });
            }}
            className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Bulk Delete ({selectedIds.length})
          </button>
          <button
            type="button"
            disabled={selectedIds.length === 0 || bulkReprocessMutation.isPending}
            onClick={() => {
              if (!window.confirm(`Reprocess ${selectedIds.length} selected source(s)?`)) return;
              void bulkReprocessMutation.mutateAsync(selectedIds).catch((error: unknown) => {
                setMutationError(error instanceof Error ? error.message : "Bulk reprocess failed.");
              });
            }}
            className="rounded-lg border border-border px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-60"
          >
            Bulk Reprocess ({selectedIds.length})
          </button>
        </div>
      </section>

      {mutationError ? (
        <NetworkError
          title="Action failed"
          message={mutationError}
          retryLabel="Dismiss"
          onRetry={() => {
            setMutationError(null);
          }}
        />
      ) : null}

      {sourceQuery.isLoading ? <LoadingFallback title="Loading sources" /> : null}

      {sourceQuery.isError ? (
        <NetworkError
          title="Failed to load sources"
          message={sourceQuery.error instanceof Error ? sourceQuery.error.message : "Unknown error"}
          onRetry={() => {
            void sourceQuery.refetch();
          }}
        />
      ) : null}

      {!sourceQuery.isLoading && !sourceQuery.isError && items.length === 0 ? (
        <section className="rounded-2xl border border-border bg-background p-8 text-center">
          <p className="text-sm text-muted-foreground">No knowledge sources found for current filters.</p>
        </section>
      ) : null}

      {!sourceQuery.isLoading && !sourceQuery.isError && items.length > 0 ? (
        <>
          <SourceTable
            items={items}
            selectedIds={selectedIds}
            isBusy={isMutating}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onOpenDetails={setDetailsSourceId}
            onDelete={(id) => {
              if (!window.confirm("Delete this source? This action cannot be undone.")) return;
              void deleteMutation.mutateAsync(id).catch((error: unknown) => {
                setMutationError(error instanceof Error ? error.message : "Delete failed.");
              });
            }}
            onReprocess={(id) => {
              if (!window.confirm("Reprocess this source now?")) return;
              void reprocessMutation.mutateAsync(id).catch((error: unknown) => {
                setMutationError(error instanceof Error ? error.message : "Reprocess failed.");
              });
            }}
          />

          <section className="flex items-center justify-between rounded-2xl border border-border bg-background px-4 py-3 text-sm">
            <p className="text-muted-foreground">
              Page {sourceQuery.data?.page ?? 1} of {Math.max(1, totalPages)}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
                disabled={page <= 1}
                className="rounded-md border border-border px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Prev
              </button>
              <button
                type="button"
                onClick={() => setPage((current) => (current < Math.max(1, totalPages) ? current + 1 : current))}
                disabled={page >= Math.max(1, totalPages)}
                className="rounded-md border border-border px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Next
              </button>
            </div>
          </section>
        </>
      ) : null}

      <SourceDetailsDrawer
        source={detailsSource}
        status={statusQuery.data ?? null}
        open={Boolean(detailsSourceId)}
        onClose={() => setDetailsSourceId(null)}
        onRefresh={() => {
          void refreshAll();
        }}
        onDelete={(id) => {
          if (!window.confirm("Delete this source? This action cannot be undone.")) return;
          void deleteMutation.mutateAsync(id).catch((error: unknown) => {
            setMutationError(error instanceof Error ? error.message : "Delete failed.");
          });
        }}
        onReprocess={(id) => {
          if (!window.confirm("Reprocess this source now?")) return;
          void reprocessMutation.mutateAsync(id).catch((error: unknown) => {
            setMutationError(error instanceof Error ? error.message : "Reprocess failed.");
          });
        }}
        onUpdateLabel={async (id, nextLabel) => {
          try {
            await updateLabelMutation.mutateAsync({ id, nextLabel });
          } catch (error) {
            setMutationError(error instanceof Error ? error.message : "Label update failed.");
          }
        }}
        isBusy={isMutating}
      />
    </main>
  );
}
