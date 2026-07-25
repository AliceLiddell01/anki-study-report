import { readFile, stat } from "node:fs/promises";
import { resolve } from "node:path";
import { gzipSync } from "node:zlib";

const dashboardRoot = resolve(import.meta.dirname, "..");
const distRoot = resolve(dashboardRoot, "dist");
const manifestPath = resolve(distRoot, "manifest.json");
const manifest = JSON.parse(await readFile(manifestPath, "utf8"));
const entries = Object.entries(manifest);
const entry = entries.find(([, value]) => value.isEntry);

if (!entry) fail("Vite manifest has no production entry.");

const jsFiles = [...new Set(entries.map(([, value]) => value.file).filter((file) => file?.endsWith(".js")))];
if (jsFiles.length < 3) fail(`Expected a split build, found only ${jsFiles.length} JavaScript chunk(s).`);

const sizes = await Promise.all(jsFiles.map(async (file) => {
  const contents = await readFile(resolve(distRoot, file));
  return { file, bytes: (await stat(resolve(distRoot, file))).size, gzipBytes: gzipSync(contents).byteLength };
}));
const oversized = sizes.filter(({ bytes }) => bytes > 500_000);
if (oversized.length) {
  fail(`JavaScript chunks exceed 500 kB: ${oversized.map(({ file, bytes }) => `${file} (${bytes} bytes)`).join(", ")}`);
}

const reachableKeys = new Set();
const visit = (key) => {
  if (reachableKeys.has(key)) return;
  const chunk = manifest[key];
  if (!chunk) fail(`Manifest references missing chunk key: ${key}`);
  reachableKeys.add(key);
  for (const dependency of [...(chunk.imports || []), ...(chunk.dynamicImports || [])]) visit(dependency);
};
visit(entry[0]);

for (const expected of ["StatisticsPage.tsx", "FsrsStatisticsPage.tsx", "InspectionProfilesSettingsPage.tsx"]) {
  const chunk = entries.find(([key, value]) => key.endsWith(expected) || value.src?.endsWith(expected));
  if (!chunk) fail(`Expected lazy route is missing from manifest: ${expected}`);
  if (!reachableKeys.has(chunk[0])) fail(`Expected lazy route is not reachable from the entry: ${expected}`);
  if (!chunk[1].isDynamicEntry) fail(`Expected route is no longer a dynamic entry: ${expected}`);
}

const entrySize = sizes.find(({ file }) => file === entry[1].file)?.bytes;
const largest = sizes.reduce((current, item) => item.bytes > current.bytes ? item : current, sizes[0]);
const total = sizes.reduce((sum, item) => sum + item.bytes, 0);
const totalGzip = sizes.reduce((sum, item) => sum + item.gzipBytes, 0);
console.log(`Bundle guard passed: ${jsFiles.length} JS chunks, entry ${entrySize} bytes, largest ${largest.file} ${largest.bytes} bytes, total ${total} bytes (${totalGzip} bytes gzip).`);

function fail(message) {
  throw new Error(`Bundle regression guard: ${message}`);
}
