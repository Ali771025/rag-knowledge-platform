import { motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface ReferralLinkProgressProps {
  progressPercent: number;
  statusLabel: string;
}

export function ReferralLinkProgress({ progressPercent, statusLabel }: ReferralLinkProgressProps) {
  return (
    <div className="space-y-1">
      <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 transition-all"
          initial="hidden"
          animate="visible"
          variants={dsMotionVariants.referralTimelineItem}
          style={{ width: `${Math.max(0, Math.min(100, progressPercent))}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs text-[color:var(--color-text-muted)]">
        <span>{statusLabel}</span>
        <span>{progressPercent}%</span>
      </div>
    </div>
  );
}

export const ReferralLinkProgressBar = ReferralLinkProgress;
