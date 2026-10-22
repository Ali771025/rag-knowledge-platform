import { useEffect, type PropsWithChildren } from "react";
import { getPreferredTheme } from "@/design-system";

export function ThemeProvider({ children }: PropsWithChildren) {
  useEffect(() => {
    const root = document.documentElement;
    const nextTheme = getPreferredTheme();

    root.dataset.theme = nextTheme;
    root.classList.toggle("dark", nextTheme === "dark");
  }, []);

  return <>{children}</>;
}
