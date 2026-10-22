import { forwardRef } from "react";

export const ScrollAnchor = forwardRef<HTMLDivElement>(function ScrollAnchor(_props, ref) {
  return <div ref={ref} aria-hidden="true" className="h-px w-full" />;
});
