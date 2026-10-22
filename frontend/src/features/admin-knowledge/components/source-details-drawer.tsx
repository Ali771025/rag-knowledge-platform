import { useState } from "react";
import type { KnowledgeSource, KnowledgeSourceStatus } from "@/types/admin";
import { ProcessingStatusBadge } from "./processing-status-badge";
import { ProcessingStatusTimeline } from "./processing-status-timeline";

interface SourceDetailsDrawerProps {
  source: KnowledgeSource | null;
  status: KnowledgeSourceStatus | null;
  open: boolean;
  onClose: () => void;
  onRefresh: () => void;
  onDelete: (id: string) => void;
  onReprocess: (id: string) => void;
  onUpdateLabel: (id: string, label: string) => Promise<void>;
  isBusy?: boolean;
}

export function SourceDetailsDrawer({
  source,
  status,
  open,
  onClose,
  onRefresh,
  onDelete,
  onReprocess,
  onUpdateLabel,
  isBusy = false
}: SourceDetailsDrawerProps) {
  const [labelDrafts, setLabelDrafts] = useState<Record<string, string>>({});

  if (!open || !source) return null;
  const nextLabel = labelDrafts[source.id] ?? source.label;

  return (
    <div className="fixed inset-0 z-40 flex">
      <button type="button" className="h-full flex-1 bg-black/35" onClick={onClose} aria-label="Close details" />
      <aside className="h-full w-full max-w-lg overflow-y-auto border-l border-border bg-background p-4 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Source Details</h3>
            <p className="mt-1 text-sm text-muted-foreground break-all">{source.name}</p>
          </div>
          <button type="button" onClick={onClose} className="rounded-md border border-border px-2 py-1 text-sm">
            Close
          </button>
        </div>

        <div className="mt-4 space-y-3 text-sm">
          <div className="rounded-lg border border-border p-3">
            <p>
              <span className="font-medium">Type:</span> {source.type}
            </p>
            <p>
              <span className="font-medium">Domain:</span> {source.domain}
            </p>
            <p>
              <span className="font-medium">Label:</span> {source.label}
            </p>
            <p>
              <span className="font-medium">Status:</span> <ProcessingStatusBadge status={source.status} />
            </p>
            <p>
              <span className="font-medium">Chunks:</span> {source.embeddedChunks}/{source.totalChunks}
            </p>
            <p>
              <span className="font-medium">Tags:</span> {source.tags.join(", ") || "-"}
            </p>
          </div>

          <div className="rounded-lg border border-border p-3">
            <p className="mb-2 text-sm font-medium">Update Label</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={nextLabel}
                onChange={(event) => {
                  const value = event.target.value;
                  setLabelDrafts((current) => ({ ...current, [source.id]: value }));
                }}
                className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
                disabled={isBusy}
              />
              <button
                type="button"
                onClick={async () => {
                  await onUpdateLabel(source.id, nextLabel);
                  setLabelDrafts((current) => ({ ...current, [source.id]: nextLabel.trim() }));
                }}
                disabled={isBusy || !nextLabel.trim()}
                className="rounded-md border border-border px-3 py-1.5 text-sm font-medium"
              >
                Save
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-border p-3">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-sm font-medium">Processing Timeline</p>
              <button type="button" onClick={onRefresh} className="rounded-md border border-border px-2 py-1 text-xs">
                Refresh
              </button>
            </div>
            {status ? <ProcessingStatusTimeline status={status} /> : <p className="text-sm text-muted-foreground">Loading status...</p>}
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => onReprocess(source.id)}
              disabled={isBusy}
              className="rounded-md border border-border px-3 py-2 text-sm font-medium"
            >
              Reprocess
            </button>
            <button
              type="button"
              onClick={() => onDelete(source.id)}
              disabled={isBusy}
              className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700"
            >
              Delete Source
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
