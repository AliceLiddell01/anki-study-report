import { cp, rm } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(scriptDir, "..");
const repoRoot = resolve(dashboardRoot, "..");
const distDir = resolve(dashboardRoot, "dist");
const addonStaticDir = resolve(repoRoot, "anki_study_report", "web_dashboard");

await rm(addonStaticDir, { force: true, recursive: true });
await cp(distDir, addonStaticDir, { recursive: true });

console.log(`Copied dashboard build to ${addonStaticDir}`);
