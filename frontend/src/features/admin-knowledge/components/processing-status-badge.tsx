import type { KnowledgeSource } from "@/types/admin";

interface ProcessingStatusBadgeProps {
  status: KnowledgeSource["status"];
}

const STATUS_STYLES: Record<KnowledgeSource["status"], string> = {
  pending: "border-slate-300 bg-slate-100 text-slate-700",
  in_progress: "border-amber-300 bg-amber-100 text-amber-700",
  completed: "border-green-300 bg-green-100 text-green-700",
  failed: "border-rose-300 bg-rose-100 text-rose-700"
};

export function ProcessingStatusBadge({ status }: ProcessingStatusBadgeProps) {
  const label = status.replace("_", " ");
  return <span className={`inline-flex rounded-full border px-2 py-1 text-xs font-medium capitalize ${STATUS_STYLES[status]}`}>{label}</span>;
}
