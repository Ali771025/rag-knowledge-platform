export const dsColors = {
  background: "var(--background)",
  foreground: "var(--foreground)",
  muted: "var(--muted)",
  mutedForeground: "var(--muted-foreground)",
  surface1: "var(--surface-1)",
  surface2: "var(--surface-2)",
  surface3: "var(--surface-3)",
  accent: "var(--accent)",
  primary: "var(--primary)",
  border: "var(--border)",
  ring: "var(--ring)",
  card: "var(--background)",
  danger: "var(--error)",
  warning: "var(--warning)",
  success: "var(--success)"
} as const;

export const dsRadius = {
  sm: "0.5rem",
  md: "0.75rem",
  lg: "1rem",
  xl: "1.25rem",
  full: "9999px"
} as const;

export const dsShadows = {
  sm: "0 1px 2px rgb(2 6 23 / 0.08)",
  md: "0 4px 10px rgb(2 6 23 / 0.08)",
  lg: "0 10px 20px rgb(2 6 23 / 0.12)"
} as const;

export const dsZIndex = {
  base: 0,
  sticky: 20,
  overlay: 40,
  modal: 50,
  toast: 60
} as const;

export const dsSurfaces = {
  page: "background",
  card: "card",
  subtle: "surface2",
  elevated: "surface3",
  emphasis: "primary"
} as const;
