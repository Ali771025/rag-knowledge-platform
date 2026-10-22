import type { KnowledgeSourceStatus } from "@/types/admin";

interface ProcessingStatusTimelineProps {
  status: KnowledgeSourceStatus;
}

function statusTone(value: KnowledgeSourceStatus["steps"][number]["status"]): string {
  if (value === "completed") return "bg-green-500";
  if (value === "failed") return "bg-rose-500";
  if (value === "in_progress") return "bg-amber-500";
  return "bg-slate-300";
}

export function ProcessingStatusTimeline({ status }: ProcessingStatusTimelineProps) {
  return (
    <div className="space-y-2">
      {status.steps.map((step) => (
        <div key={step.step} className="flex items-start gap-3 rounded-lg border border-border bg-muted/50 px-3 py-2">
          <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${statusTone(step.status)}`} />
          <div className="min-w-0">
            <p className="text-sm font-medium capitalize text-foreground">{step.step.replace("_", " ")}</p>
            <p className="text-xs capitalize text-muted-foreground">{step.status.replace("_", " ")}</p>
            {typeof step.progress === "number" ? <p className="text-xs text-muted-foreground">Progress: {step.progress}%</p> : null}
            {step.message ? <p className="text-xs text-rose-700">{step.message}</p> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
