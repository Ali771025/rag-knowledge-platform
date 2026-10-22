import { dsSkeletonClass } from "@/design-system";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return <div className={`${dsSkeletonClass} ${className}`.trim()} aria-hidden="true" />;
}
