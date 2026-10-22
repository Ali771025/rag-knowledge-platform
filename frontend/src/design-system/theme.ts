export type AppTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "ragai.theme";

export interface ThemeSemanticRoles {
  surface: {
    page: string;
    card: string;
    muted: string;
    elevated: string;
    accent: string;
  };
  text: {
    primary: string;
    secondary: string;
    inverse: string;
  };
  border: {
    default: string;
    strong: string;
  };
  status: {
    success: string;
    warning: string;
    danger: string;
    info: string;
  };
}

export const dsTheme: Record<AppTheme, ThemeSemanticRoles> = {
  light: {
    surface: {
      page: "var(--background)",
      card: "var(--background)",
      muted: "var(--muted)",
      elevated: "var(--surface-3)",
      accent: "var(--accent)"
    },
    text: {
      primary: "var(--foreground)",
      secondary: "var(--muted-foreground)",
      inverse: "#ffffff"
    },
    border: {
      default: "var(--border)",
      strong: "#cbd5e1"
    },
    status: {
      success: "var(--success)",
      warning: "var(--warning)",
      danger: "var(--error)",
      info: "var(--accent)"
    }
  },
  dark: {
    surface: {
      page: "var(--background)",
      card: "var(--background)",
      muted: "var(--muted)",
      elevated: "var(--surface-3)",
      accent: "var(--accent)"
    },
    text: {
      primary: "var(--foreground)",
      secondary: "var(--muted-foreground)",
      inverse: "#020617"
    },
    border: {
      default: "var(--border)",
      strong: "#334155"
    },
    status: {
      success: "var(--success)",
      warning: "var(--warning)",
      danger: "var(--error)",
      info: "var(--accent)"
    }
  }
};

export function getPreferredTheme(): AppTheme {
  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedTheme === "light" || storedTheme === "dark") {
    return storedTheme;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}
