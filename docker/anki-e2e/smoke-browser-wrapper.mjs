#!/usr/bin/env node

await import("./smoke-browser-core.mjs");

const scope = String(process.env.ANKI_E2E_SCOPE || "full").trim().toLowerCase();
if (scope === "full" || scope === "stats") {
  await import("./fsrs-visual-contract.mjs");
}
