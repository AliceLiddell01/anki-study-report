import type { Config } from "tailwindcss";

const colorVar = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: colorVar("--color-bg"),
          900: colorVar("--color-bg-elevated"),
          850: colorVar("--color-surface-1"),
          800: colorVar("--color-surface-2"),
          700: colorVar("--color-border-subtle"),
        },
        report: {
          text: colorVar("--color-text-primary"),
          secondary: colorVar("--color-text-secondary"),
          muted: colorVar("--color-text-muted"),
          blue: colorVar("--color-accent"),
          purple: colorVar("--color-purple"),
          success: colorVar("--color-good"),
          warning: colorVar("--color-warning"),
          danger: colorVar("--color-danger"),
        },
      },
      boxShadow: {
        panel: "var(--shadow-card)",
        glow: "var(--shadow-glow)",
      },
      fontFamily: {
        sans: [
          "Inter",
          "Segoe UI",
          "Noto Sans",
          "Yu Gothic UI",
          "Meiryo",
          "ui-sans-serif",
          "system-ui",
          "Arial",
          "sans-serif",
        ],
        display: [
          "Inter",
          "Segoe UI",
          "Noto Sans",
          "Yu Gothic UI",
          "Meiryo",
          "ui-sans-serif",
          "system-ui",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
