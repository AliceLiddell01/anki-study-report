import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    manifest: "manifest.json",
    rollupOptions: {
      output: {
        manualChunks(id) {
          const moduleId = id.replace(/\\/g, "/");
          if (/\/node_modules\/(react|react-dom|scheduler)\//.test(moduleId)) return "react-runtime";
          if (moduleId.includes("/node_modules/lucide-react/")) return "icons-runtime";
          if (/\/node_modules\/(i18next|react-i18next)\//.test(moduleId)) return "i18n-runtime";
          if (moduleId.includes("/node_modules/recharts/")) return "charts-runtime";
          if (/\/node_modules\/(victory-vendor|decimal\.js-light)\//.test(moduleId)) return "charts-math";
          if (/\/node_modules\/(@reduxjs\/toolkit|react-redux|redux|immer|reselect|use-sync-external-store)\//.test(moduleId)) return "charts-state";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "node",
    globals: true,
    setupFiles: ["./src/testSetup.ts"],
  },
});
