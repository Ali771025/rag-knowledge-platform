import { Skeleton } from "./skeleton";

interface LoadingSkeletonProps {
  lines?: number;
}

export function LoadingSkeleton({ lines = 3 }: LoadingSkeletonProps) {
  const safeLines = Math.min(Math.max(lines, 1), 8);

  return (
    <div className="space-y-2" aria-hidden="true">
      {Array.from({ length: safeLines }).map((_, index) => (
        <Skeleton key={`line-${index}`} className={index === safeLines - 1 ? "h-4 w-3/4" : "h-4 w-full"} />
      ))}
    </div>
  );
}

