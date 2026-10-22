type AsyncStatus = "idle" | "loading" | "success" | "error";

interface AsyncStatusBadgeProps {
  status: AsyncStatus;
}

const statusClassMap: Record<AsyncStatus, string> = {
  idle: "border-border bg-muted/40 text-muted-foreground",
  loading: "border-accent/35 bg-accent/10 text-foreground",
  success: "border-success/35 bg-success/10 text-success",
  error: "border-error/35 bg-error/10 text-error"
};

const statusLabelMap: Record<AsyncStatus, string> = {
  idle: "Idle",
  loading: "Loading",
  success: "Success",
  error: "Error"
};

export function AsyncStatusBadge({ status }: AsyncStatusBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${statusClassMap[status]}`}>
      {statusLabelMap[status]}
    </span>
  );
}

