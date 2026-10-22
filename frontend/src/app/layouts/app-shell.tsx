import { Outlet, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

export function AppShell() {
  const location = useLocation();

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <motion.div
        key={location.pathname}
        variants={dsMotionVariants.pageEnter}
        initial="hidden"
        animate="visible"
        exit="exit"
      >
        <Outlet />
      </motion.div>
    </div>
  );
}
