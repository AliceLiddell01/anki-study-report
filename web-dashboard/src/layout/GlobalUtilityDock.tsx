import { Moon, Sun } from "lucide-react";
import type { ResolvedTheme } from "../lib/theme";

function GlobalUtilityDock({
  resolvedTheme,
  onThemeChange,
}: {
  resolvedTheme: ResolvedTheme;
  onThemeChange: (theme: ResolvedTheme) => void;
}) {
  const nextTheme: ResolvedTheme = resolvedTheme === "dark" ? "light" : "dark";
  const label = nextTheme === "light" ? "Включить светлую тему" : "Включить тёмную тему";
  const Icon = nextTheme === "light" ? Sun : Moon;

  return (
    <aside className="global-utility-dock" aria-label="Настройки интерфейса" data-testid="global-utility-dock">
      <div className="utility-control-with-tooltip">
        <button
          type="button"
          className="utility-icon-button"
          aria-label={label}
          aria-describedby="theme-toggle-tooltip"
          data-testid="theme-toggle"
          onClick={() => onThemeChange(nextTheme)}
        >
          <Icon size={19} aria-hidden="true" />
        </button>
        <span id="theme-toggle-tooltip" role="tooltip" className="utility-tooltip">
          {label}
        </span>
      </div>
    </aside>
  );
}

export default GlobalUtilityDock;
