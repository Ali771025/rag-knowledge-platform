import type { Variants } from "framer-motion";

export type WizardDirection = 1 | -1;

export const dsMotionTiming = {
  instant: 0.08,
  quick: 0.14,
  standard: 0.18,
  soft: 0.24,
  normal: 0.32,
  slow: 0.48
} as const;

export const dsMotionEasing = {
  standard: [0.22, 1, 0.36, 1] as [number, number, number, number],
  decelerate: [0.16, 1, 0.3, 1] as [number, number, number, number],
  accelerate: [0.4, 0, 1, 1] as [number, number, number, number],
  springSoft: [0.2, 0.9, 0.24, 1] as [number, number, number, number],
  linear: "linear"
} as const;

export const dsMotionVariants: {
  fadeIn: Variants;
  subtleSlideUp: Variants;
  pageEnter: Variants;
  card: Variants;
  cardList: Variants;
  listItem: Variants;
  messageEntry: Variants;
  streamingReveal: Variants;
  typingIndicator: Variants;
  panelReveal: Variants;
  modalBackdrop: Variants;
  modalCard: Variants;
  expandable: Variants;
  bottomNav: Variants;
  voiceOrb: Variants;
  voiceProcessingRing: Variants;
  listeningRipple: Variants;
  micState: Variants;
  referralTimelineItem: Variants;
  toast: Variants;
  loadingPulse: Variants;
} = {
  fadeIn: {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  subtleSlideUp: {
    hidden: { opacity: 0, y: 8 },
    visible: { opacity: 1, y: 0, transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, y: -6, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  pageEnter: {
    hidden: { opacity: 0, y: 18, scale: 0.992, filter: "blur(10px)" },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
      filter: "blur(0px)",
      transition: { duration: 0.62, ease: dsMotionEasing.decelerate }
    },
    exit: { opacity: 0, y: -14, scale: 0.992, filter: "blur(8px)", transition: { duration: dsMotionTiming.soft, ease: dsMotionEasing.accelerate } }
  },
  card: {
    hidden: { opacity: 0, y: 18, scale: 0.975, filter: "blur(6px)" },
    visible: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", transition: { duration: 0.42, ease: dsMotionEasing.standard } },
    hover: { y: -8, scale: 1.022, rotateX: 1.2, transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.standard } },
    tap: { scale: 0.972, rotateX: 0, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, y: 8, scale: 0.98, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  cardList: {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.075,
        delayChildren: 0.06
      }
    },
    exit: { transition: { staggerChildren: 0.025, staggerDirection: -1 } }
  },
  listItem: {
    hidden: { opacity: 0, y: 14, scale: 0.98, filter: "blur(5px)" },
    visible: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", transition: { duration: 0.38, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, y: -6, scale: 0.985, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  messageEntry: {
    hidden: { opacity: 0, y: 12, scale: 0.982, filter: "blur(4px)" },
    visible: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", transition: { duration: 0.38, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, y: -6, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  streamingReveal: {
    hidden: { opacity: 0, y: 6, filter: "blur(6px)" },
    visible: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.34, ease: dsMotionEasing.standard } }
  },
  typingIndicator: {
    idle: { opacity: 0.55, y: 0 },
    active: {
      opacity: [0.55, 1, 0.55],
      y: [0, -2, 0],
      transition: { duration: 1.05, repeat: Number.POSITIVE_INFINITY, ease: dsMotionEasing.standard }
    }
  },
  panelReveal: {
    hidden: { opacity: 0, y: 6 },
    visible: { opacity: 1, y: 0, transition: { duration: dsMotionTiming.soft, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, y: -6, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  modalBackdrop: {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { duration: dsMotionTiming.soft, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  modalCard: {
    hidden: { opacity: 0, y: 18, scale: 0.96 },
    visible: { opacity: 1, y: 0, scale: 1, transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.decelerate } },
    exit: { opacity: 0, y: 12, scale: 0.97, transition: { duration: dsMotionTiming.standard, ease: dsMotionEasing.accelerate } }
  },
  expandable: {
    hidden: { opacity: 0, height: 0 },
    visible: { opacity: 1, height: "auto", transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, height: 0, transition: { duration: dsMotionTiming.standard, ease: dsMotionEasing.accelerate } }
  },
  bottomNav: {
    hidden: { opacity: 0, y: 30, scale: 0.96, filter: "blur(8px)" },
    visible: { opacity: 1, y: 0, scale: 1, filter: "blur(0px)", transition: { duration: 0.62, ease: dsMotionEasing.decelerate } },
    exit: { opacity: 0, y: 18, transition: { duration: dsMotionTiming.standard, ease: dsMotionEasing.accelerate } }
  },
  voiceOrb: {
    idle: { scale: 1, opacity: 0.92 },
    listening: {
      scale: [1, 1.035, 1],
      opacity: [0.9, 1, 0.9],
      transition: { duration: 1.6, repeat: Number.POSITIVE_INFINITY, ease: dsMotionEasing.standard }
    },
    speaking: {
      scale: [1, 1.055, 1],
      rotate: [0, 1.5, 0],
      transition: { duration: 1.2, repeat: Number.POSITIVE_INFINITY, ease: dsMotionEasing.standard }
    }
  },
  voiceProcessingRing: {
    idle: { rotate: 0 },
    processing: {
      rotate: 360,
      transition: { duration: 2.6, ease: dsMotionEasing.linear, repeat: Number.POSITIVE_INFINITY }
    }
  },
  listeningRipple: {
    idle: { scale: 0.95, opacity: 0 },
    listening: {
      scale: [0.95, 1.35],
      opacity: [0.45, 0],
      transition: { duration: 1.4, repeat: Number.POSITIVE_INFINITY, ease: dsMotionEasing.standard }
    }
  },
  micState: {
    idle: { scale: 1 },
    listening: { scale: 1.04, transition: { duration: dsMotionTiming.soft, ease: dsMotionEasing.standard } },
    processing: { scale: 0.98, transition: { duration: dsMotionTiming.soft, ease: dsMotionEasing.standard } },
    tap: { scale: 0.96, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.standard } }
  },
  referralTimelineItem: {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0, transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, x: 8, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.accelerate } }
  },
  toast: {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.standard } },
    exit: { opacity: 0, y: -6, transition: { duration: dsMotionTiming.quick, ease: dsMotionEasing.standard } }
  },
  loadingPulse: {
    idle: { opacity: 0.55 },
    active: {
      opacity: [0.45, 0.9, 0.45],
      transition: { duration: 1.2, repeat: Number.POSITIVE_INFINITY, ease: dsMotionEasing.linear }
    }
  }
};

export const wizardStepVariants: Variants = {
  enter: (direction: WizardDirection) => ({
    x: direction > 0 ? 32 : -32,
    opacity: 0,
    scale: 0.98
  }),
  center: {
    x: 0,
    opacity: 1,
    scale: 1,
    transition: { duration: dsMotionTiming.normal, ease: dsMotionEasing.standard }
  },
  exit: (direction: WizardDirection) => ({
    x: direction > 0 ? -32 : 32,
    opacity: 0,
    scale: 0.98,
    transition: { duration: dsMotionTiming.standard, ease: dsMotionEasing.accelerate }
  })
};
