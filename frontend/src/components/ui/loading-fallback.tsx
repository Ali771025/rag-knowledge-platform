import { LoadingDots } from "./loading-dots";
import { Skeleton } from "./skeleton";

interface LoadingFallbackProps {
  title?: string;
  description?: string;
  showSkeleton?: boolean;
}

export function LoadingFallback({
  title = "Loading",
  description = "Please wait a moment while we prepare your workspace.",
  showSkeleton = true
}: LoadingFallbackProps) {
  return (
    <section
      className="mx-auto mt-8 w-full max-w-sm rounded-2xl border border-border bg-background p-4 shadow-sm"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        <LoadingDots label={title} />
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>

      {showSkeleton ? (
        <div className="mt-4 space-y-2" aria-hidden="true">
          <Skeleton className="h-4 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      ) : null}
    </section>
  );
}
