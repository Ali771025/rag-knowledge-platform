import type { KnowledgeSource } from "@/types/admin";
import { ProcessingStatusBadge } from "./processing-status-badge";

interface SourceTableProps {
  items: KnowledgeSource[];
  selectedIds: string[];
  isBusy?: boolean;
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: () => void;
  onOpenDetails: (id: string) => void;
  onDelete: (id: string) => void;
  onReprocess: (id: string) => void;
}

export function SourceTable({
  items,
  selectedIds,
  isBusy = false,
  onToggleSelect,
  onToggleSelectAll,
  onOpenDetails,
  onDelete,
  onReprocess
}: SourceTableProps) {
  const allSelected = items.length > 0 && items.every((item) => selectedIds.includes(item.id));

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-background shadow-sm">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-muted text-muted-foreground">
            <tr>
              <th className="px-3 py-2">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onToggleSelectAll}
                  aria-label="Select all sources"
                  disabled={isBusy}
                />
              </th>
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium">Type</th>
              <th className="px-3 py-2 font-medium">Domain</th>
              <th className="px-3 py-2 font-medium">Label</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Chunks</th>
              <th className="px-3 py-2 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-border">
                <td className="px-3 py-2 align-top">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(item.id)}
                    onChange={() => onToggleSelect(item.id)}
                    aria-label={`Select source ${item.name}`}
                    disabled={isBusy}
                  />
                </td>
                <td className="px-3 py-2 align-top">
                  <button
                    type="button"
                    onClick={() => onOpenDetails(item.id)}
                    className="max-w-[260px] truncate text-left font-medium text-foreground underline-offset-2 hover:underline"
                  >
                    {item.name}
                  </button>
                  <p className="mt-0.5 text-xs text-muted-foreground">{new Date(item.createdAt).toLocaleString()}</p>
                </td>
                <td className="px-3 py-2 align-top capitalize">{item.type}</td>
                <td className="px-3 py-2 align-top">{item.domain}</td>
                <td className="px-3 py-2 align-top">{item.label}</td>
                <td className="px-3 py-2 align-top">
                  <ProcessingStatusBadge status={item.status} />
                </td>
                <td className="px-3 py-2 align-top">
                  <span className="font-medium text-foreground">{item.embeddedChunks}</span>
                  <span className="text-muted-foreground">/{item.totalChunks}</span>
                </td>
                <td className="px-3 py-2 align-top">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => onReprocess(item.id)}
                      disabled={isBusy}
                      className="rounded-md border border-border px-2 py-1 text-xs font-medium text-foreground"
                    >
                      Reprocess
                    </button>
                    <button
                      type="button"
                      onClick={() => onDelete(item.id)}
                      disabled={isBusy}
                      className="rounded-md border border-rose-300 bg-rose-50 px-2 py-1 text-xs font-medium text-rose-700"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
