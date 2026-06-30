import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0f1624",
          900: "#111827",
          850: "#151f2e",
          800: "#1d2a3d",
          700: "#2b3a50",
        },
        report: {
          text: "#e8f0ff",
          muted: "#8fa3bf",
          blue: "#3db4f2",
          purple: "#7c5cff",
          success: "#67d391",
          warning: "#f6c177",
          danger: "#ef6f6c",
        },
      },
      boxShadow: {
        panel: "0 18px 50px rgba(3, 8, 20, 0.22)",
        glow: "0 0 36px rgba(61, 180, 242, 0.12)",
      },
      fontFamily: {
        sans: [
          "Segoe UI Variable Text",
          "Segoe UI",
          "ui-sans-serif",
          "system-ui",
          "Arial",
          "sans-serif",
        ],
        display: [
          "Segoe UI Variable Display",
          "Segoe UI",
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
