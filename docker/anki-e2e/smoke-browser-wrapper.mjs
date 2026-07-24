#!/usr/bin/env node

import path from "node:path";
import { normalizeBrowserArtifacts } from "./browser-report-contract.mjs";

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const value = process.argv[index];
  if (value.startsWith("--")) {
    args.set(value.slice(2), process.argv[index + 1] && !process.argv[index + 1].startsWith("--") ? process.argv[++index] : "1");
  }
}
const label = args.get("label") || "first";
const root = process.env.ANKI_STUDY_REPORT_E2E_ARTIFACTS || "/e2e/artifacts";
let originalError = null;
try {
  await import("./smoke-browser-core.mjs");
} catch (error) {
  originalError = error;
} finally {
  try {
    await normalizeBrowserArtifacts({ root: path.resolve(root), label });
  } catch (normalizationError) {
    if (!originalError) throw normalizationError;
    console.error(`[BROWSER] secondary report normalization failure: ${normalizationError?.message || normalizationError}`);
  }
}
if (originalError) throw originalError;

const scope = String(process.env.ANKI_E2E_SCOPE || "full").trim().toLowerCase();
if (scope === "full" || scope === "stats") {
  await import("./fsrs-visual-contract.mjs");
}
