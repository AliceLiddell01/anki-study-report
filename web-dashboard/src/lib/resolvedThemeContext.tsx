import { createContext, useContext, type ReactNode } from "react";
import type { ResolvedTheme } from "./theme";

const ResolvedThemeContext = createContext<ResolvedTheme>("light");

export function ResolvedThemeProvider({ value, children }: { value: ResolvedTheme; children: ReactNode }) {
  return <ResolvedThemeContext.Provider value={value}>{children}</ResolvedThemeContext.Provider>;
}

export function useResolvedTheme(): ResolvedTheme {
  return useContext(ResolvedThemeContext);
}
