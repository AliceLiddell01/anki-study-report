import fs from "node:fs/promises";
import path from "node:path";

export function resolveArtifactPaths(root = process.env.ANKI_STUDY_REPORT_E2E_ARTIFACTS || "/e2e/artifacts") {
  const reports = path.join(root, "reports");
  const html = path.join(root, "html");
  const screenshots = path.join(root, "screenshots");
  return {
    root,
    runtime: path.join(root, "runtime"),
    diagnostics: path.join(root, "diagnostics"),
    reports,
    html,
    screenshots,
    package: path.join(root, "package"),
    report(fileName) {
      return path.join(reports, fileName);
    },
    htmlFile(...segments) {
      return path.join(html, ...segments);
    },
    pageScreenshot(pageName, theme) {
      return path.join(screenshots, "pages", pageName, `${theme}.png`);
    },
    navigationScreenshot(theme) {
      return path.join(screenshots, "navigation", `avatar-menu-${theme}.png`);
    },
    cardsScreenshot(fixture, mode, theme) {
      return path.join(screenshots, "cards", fixture, modeDirectory(mode), `${theme}.png`);
    },
    failureScreenshot(fileName) {
      return path.join(screenshots, "failures", fileName);
    },
  };
}

export async function ensureArtifactParent(filePath) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
}

export function relativeArtifactPath(paths, filePath) {
  return path.relative(paths.root, filePath).split(path.sep).join("/");
}

function modeDirectory(mode) {
  return mode === "ankiPreview" ? "anki-preview" : mode;
}

