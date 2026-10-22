import type { PropsWithChildren } from "react";

interface SectionContainerProps extends PropsWithChildren {
  className?: string;
}

export function SectionContainer({ children, className = "" }: SectionContainerProps) {
  return <section className={`w-full ${className}`.trim()}>{children}</section>;
}

