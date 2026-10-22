import type { PropsWithChildren } from "react";
import { AnimatePresence } from "framer-motion";

interface MotionPresenceProps extends PropsWithChildren {
  initial?: boolean;
  mode?: "sync" | "popLayout" | "wait";
}

export function MotionPresence({ children, initial = false, mode = "sync" }: MotionPresenceProps) {
  return (
    <AnimatePresence initial={initial} mode={mode}>
      {children}
    </AnimatePresence>
  );
}
