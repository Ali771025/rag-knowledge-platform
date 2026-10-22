import { Skeleton } from "@/components/ui";

export function MessageSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-4xl items-start gap-3 px-1">
      <Skeleton className="h-8 w-8 shrink-0 rounded-full" />
      <div className="w-full max-w-2xl space-y-2 rounded-3xl border border-slate-700/60 bg-slate-900/55 p-4">
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
      </div>
    </div>
  );
}
