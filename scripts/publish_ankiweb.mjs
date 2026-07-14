import { createHash } from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";


const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ANKIWEB_ORIGIN = "https://ankiweb.net";
const APPROVED_ARTIFACT_NAME = "anki_study_report.ankiaddon";
const EXPECTED_KEYS = new Set([
  "schema_version", "addon_id", "title", "tags", "support_url",
  "expected_branch_label", "minimum_anki_version", "maximum_anki_version",
  "download_client_version", "repository_url", "releases_url", "donation_url",
]);
const CHALLENGE_TEXT = /captcha|verify you are human|two-factor|2fa|multi-factor|mfa|passkey|security key/i;
const PUBLIC_DESCRIPTION_SELECTOR = "main .shared-item-description";
const PUBLIC_POLL_INTERVALS_MS = [0, 250, 500, 1_000, 2_000, 3_000];
const ARTIFACT_POLL_INTERVALS_MS = [0, 500, 1_000, 2_000];


class PublisherVerificationError extends Error {
  constructor(phase, code, diagnostics = {}) {
    super(code);
    this.phase = phase;
    this.diagnostics = diagnostics;
  }
}


export function normalizeMarkdown(value) {
  return String(value).replace(/\r\n?/g, "\n").trim() + "\n";
}


export function sha256Text(value) {
  return createHash("sha256").update(normalizeMarkdown(value), "utf8").digest("hex");
}


export function parseSimpleYaml(text) {
  const result = {};
  let activeList = null;
  for (const [index, raw] of String(text).split(/\r?\n/).entries()) {
    if (!raw.trim() || raw.trimStart().startsWith("#")) continue;
    if (raw.startsWith("  - ")) {
      if (!activeList) throw new Error(`unexpected-list-item:${index + 1}`);
      result[activeList].push(parseScalar(raw.slice(4)));
      continue;
    }
    if (/^[ \t]/.test(raw) || !raw.includes(":")) throw new Error(`unsupported-yaml:${index + 1}`);
    const separator = raw.indexOf(":");
    const key = raw.slice(0, separator);
    const rawValue = raw.slice(separator + 1).trim();
    if (!/^[a-z][a-z0-9_]*$/.test(key) || Object.hasOwn(result, key)) throw new Error(`invalid-yaml-key:${index + 1}`);
    if (!rawValue) {
      result[key] = [];
      activeList = key;
    } else {
      result[key] = parseScalar(rawValue);
      activeList = null;
    }
  }
  return result;
}


function parseScalar(value) {
  if (value.startsWith('"')) return JSON.parse(value);
  if (value.startsWith("'")) {
    if (!value.endsWith("'")) throw new Error("invalid-quoted-scalar");
    return value.slice(1, -1).replace(/''/g, "'");
  }
  if (/^-?\d+$/.test(value)) return Number(value);
  if (value === "true" || value === "false") return value === "true";
  if (/[#{}\[\]]/.test(value)) throw new Error("yaml-scalar-must-be-quoted");
  return value;
}


export function validateMetadata(metadata) {
  const keys = new Set(Object.keys(metadata));
  const missing = [...EXPECTED_KEYS].filter((key) => !keys.has(key));
  const unknown = [...keys].filter((key) => !EXPECTED_KEYS.has(key));
  if (missing.length || unknown.length) throw new Error(`metadata-keys:m=${missing.join(",")}:u=${unknown.join(",")}`);
  if (metadata.schema_version !== 1 || metadata.addon_id !== 373100400) throw new Error("metadata-identity");
  if (metadata.title !== "Anki Study Report" || metadata.expected_branch_label !== "Branch 1") throw new Error("metadata-target");
  if (!Array.isArray(metadata.tags) || !metadata.tags.length || new Set(metadata.tags).size !== metadata.tags.length) throw new Error("metadata-tags");
  if (!metadata.tags.every((tag) => /^[a-z0-9-]+$/.test(tag))) throw new Error("metadata-tags");
  if (metadata.minimum_anki_version !== "26.05.0" || metadata.maximum_anki_version !== "26.05.0") throw new Error("metadata-branch-versions");
  if (metadata.download_client_version !== 260500) throw new Error("metadata-download-version");
  for (const key of ["support_url", "repository_url", "releases_url", "donation_url"]) {
    if (typeof metadata[key] !== "string" || !metadata[key].startsWith("https://")) throw new Error(`metadata-url:${key}`);
  }
  return metadata;
}


export function sanitizeFailure(error, secrets = []) {
  let message = error instanceof Error ? error.message : String(error);
  for (const value of secrets) {
    if (value) message = message.split(value).join("[REDACTED]");
  }
  const home = os.homedir();
  if (home) message = message.split(home).join("[HOME]");
  message = message
    .replace(/(?:[?&]|&amp;)token=[^\s&]+/gi, "")
    .replace(/\b(?:gh[opusr]_|github_pat_)[A-Za-z0-9_]{12,}/g, "[REDACTED]")
    .slice(0, 300);
  return message || "publisher-failed";
}


export async function pollBounded(probe, options = {}) {
  const intervals = options.intervals ?? PUBLIC_POLL_INTERVALS_MS;
  const sleep = options.sleep ?? ((milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds)));
  const now = options.now ?? (() => Date.now());
  const startedAt = now();
  let lastValue;
  for (let index = 0; index < intervals.length; index += 1) {
    if (intervals[index] > 0) await sleep(intervals[index]);
    lastValue = await probe(index + 1);
    if (lastValue?.done) {
      return { matched: true, value: lastValue, attempts: index + 1, elapsedMs: now() - startedAt };
    }
  }
  return { matched: false, value: lastValue, attempts: intervals.length, elapsedMs: now() - startedAt };
}


export async function pollPublicDescription(container, version, options = {}) {
  const marker = `What's new in ${version}`;
  let containerFound = false;
  let versionMarkerFound = false;
  const result = await pollBounded(async () => {
    const count = await container.count();
    if (count > 1) {
      throw new PublisherVerificationError("public-description", `public-description-container:count=${count}`, {
        publicDescriptionContainerFound: true,
        versionMarkerFound: false,
      });
    }
    const containerPresent = count === 1;
    containerFound ||= containerPresent;
    if (!containerPresent) return { done: false };
    const text = await container.innerText().catch(() => "");
    versionMarkerFound = text.includes(marker);
    return { done: versionMarkerFound };
  }, options);
  const diagnostics = {
    publicDescriptionContainerFound: containerFound,
    versionMarkerFound,
    publicDescriptionAttempts: result.attempts,
    publicDescriptionElapsedMs: result.elapsedMs,
  };
  if (!containerFound) {
    throw new PublisherVerificationError("public-description", "public-description-container-timeout", diagnostics);
  }
  if (!versionMarkerFound) {
    throw new PublisherVerificationError("public-description", "public-description-version-marker-absent", diagnostics);
  }
  return diagnostics;
}


export async function executePublishPlan({ initialState, saveOnce, verifySource, verifyPublic, verifyArtifact }) {
  let mutationCount = 0;
  if (!initialState.metadataMatch || !initialState.descriptionMatch) {
    mutationCount = 1;
    await saveOnce();
  }
  const source = await verifySource();
  if (!source.metadataMatch || !source.descriptionMatch) {
    throw new PublisherVerificationError("authenticated-form", "stored-form-verification-failed", {
      observedDescriptionSha256: source.descriptionSha256 ?? null,
    });
  }
  const publicDescription = await verifyPublic();
  const artifact = await verifyArtifact();
  return {
    mutationCount,
    idempotent: mutationCount === 0,
    source,
    publicDescription,
    artifact,
  };
}


function parseArgs(argv) {
  const args = { mode: null, output: path.join(ROOT, "release-artifacts", "ankiweb-publish-report.json") };
  for (let index = 0; index < argv.length; index += 1) {
    const item = argv[index];
    if (item === "--dry-run" || item === "--publish") {
      if (args.mode) throw new Error("choose-exactly-one-mode");
      args.mode = item.slice(2);
      continue;
    }
    if (!["--version", "--artifact", "--description", "--description-sha256", "--metadata", "--output"].includes(item)) {
      throw new Error(`unknown-argument:${item}`);
    }
    const value = argv[index + 1];
    if (!value) throw new Error(`missing-value:${item}`);
    args[item.slice(2).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = value;
    index += 1;
  }
  if (!args.mode || !args.version || !args.description) throw new Error("mode-version-description-required");
  args.metadata ??= path.join(ROOT, "release", "ankiweb.yml");
  if (args.mode === "publish" && !args.artifact) throw new Error("publish-requires-artifact");
  return args;
}


async function unique(locator, code) {
  const count = await locator.count();
  if (count !== 1) throw new Error(`${code}:count=${count}`);
  return locator;
}


async function assertNoChallenge(page) {
  const text = await page.locator("main").innerText().catch(() => "");
  if (CHALLENGE_TEXT.test(text)) throw new Error("authentication-challenge");
}


async function login(page, email, password) {
  await page.goto(`${ANKIWEB_ORIGIN}/account/login`, { waitUntil: "domcontentloaded" });
  await assertNoChallenge(page);
  const emailField = await unique(page.getByLabel("Email", { exact: true }), "login-email");
  const passwordField = await unique(page.getByLabel("Password", { exact: true }), "login-password");
  const button = await unique(page.getByRole("button", { name: "Log In", exact: true }), "login-button");
  await emailField.fill(email);
  await passwordField.fill(password);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith("/account/login"), { timeout: 20_000 }),
    button.click(),
  ]);
  await assertNoChallenge(page);
  if (page.url().includes("/account/login")) throw new Error("authentication-failed");
}


async function openUpdateForm(page, metadata) {
  const updateHref = `/shared/upload?id=${metadata.addon_id}`;
  await page.goto(`${ANKIWEB_ORIGIN}${updateHref}`, { waitUntil: "domcontentloaded" });
  await assertNoChallenge(page);
  await unique(page.getByRole("heading", { name: "Update", exact: true }), "update-heading");
  return inspectUpdateForm(page, metadata);
}


async function inspectUpdateForm(page, metadata) {
  const title = await unique(page.getByLabel("Title", { exact: true }), "title-field");
  const tags = await unique(page.getByLabel("Tags", { exact: true }), "tags-field");
  const support = await unique(page.getByLabel("Support Page", { exact: true }), "support-field");
  const branchInputs = page.locator("main input:not([type])");
  if (await branchInputs.count() !== 2) throw new Error(`branch-inputs:count=${await branchInputs.count()}`);
  const branchMin = branchInputs.nth(0);
  const branchMax = branchInputs.nth(1);
  const branchSelect = await unique(page.locator("main select"), "branch-select");
  const options = await branchSelect.locator("option").allTextContents();
  if (options.length !== 1 || options[0].trim() !== metadata.expected_branch_label) throw new Error("unexpected-branches");
  const file = await unique(page.locator('main input[type="file"]'), "release-file-input");
  const description = await unique(page.locator("main textarea"), "description-field");
  const save = await unique(page.getByRole("button", { name: "Save", exact: true }), "save-button");
  await unique(page.getByRole("button", { name: "Add New Branch", exact: true }), "add-branch-button");
  return { title, tags, support, branchMin, branchMax, branchSelect, file, description, save };
}


async function observedState(form, metadata, expectedDescriptionHash) {
  const description = await form.description.inputValue();
  return {
    metadataMatch:
      (await form.title.inputValue()) === metadata.title &&
      (await form.tags.inputValue()) === metadata.tags.join(" ") &&
      (await form.support.inputValue()) === metadata.support_url &&
      (await form.branchMin.inputValue()) === metadata.minimum_anki_version &&
      (await form.branchMax.inputValue()) === metadata.maximum_anki_version &&
      (await form.branchSelect.inputValue()) === "0",
    descriptionMatch: sha256Text(description) === expectedDescriptionHash,
    descriptionSha256: sha256Text(description),
  };
}


async function sha256File(file) {
  return createHash("sha256").update(await fs.readFile(file)).digest("hex");
}


async function downloadPublishedArtifact(context, metadata, destination) {
  const page = await context.newPage();
  try {
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
    await page.goto(
      `${ANKIWEB_ORIGIN}/shared/download/${metadata.addon_id}?v=2.1&p=${metadata.download_client_version}`,
      { waitUntil: "commit" },
    ).catch(() => undefined);
    const download = await downloadPromise;
    const failure = await download.failure();
    if (failure) throw new Error("published-artifact-download-failed");
    await download.saveAs(destination);
    return sha256File(destination);
  } finally {
    await page.close();
  }
}


async function verifyAuthenticatedForm(page, metadata, expectedDescriptionHash) {
  try {
    const form = await openUpdateForm(page, metadata);
    const state = await observedState(form, metadata, expectedDescriptionHash);
    if (!state.metadataMatch || !state.descriptionMatch) {
      throw new PublisherVerificationError("authenticated-form", "stored-form-verification-failed", {
        observedDescriptionSha256: state.descriptionSha256,
      });
    }
    return state;
  } catch (error) {
    if (error instanceof PublisherVerificationError) throw error;
    throw new PublisherVerificationError("authenticated-form", error instanceof Error ? error.message : String(error));
  }
}


async function verifyPublicRendering(page, metadata, version) {
  try {
    await page.goto(`${ANKIWEB_ORIGIN}/shared/info/${metadata.addon_id}`, { waitUntil: "domcontentloaded" });
    await assertNoChallenge(page);
    const publicTitles = page.getByRole("heading", { name: metadata.title, exact: true });
    await publicTitles.first().waitFor({ state: "visible", timeout: 10_000 });
    await unique(publicTitles, "post-save-public-title");
    const updateHref = `/shared/upload?id=${metadata.addon_id}`;
    const updateLink = page.locator(`a[href="${updateHref}"]`);
    await updateLink.waitFor({ state: "visible", timeout: 10_000 });
    await unique(updateLink, "post-save-update-link");
    if ((await updateLink.innerText()).trim() !== "Update") {
      throw new Error("post-save-update-link-label");
    }
    return await pollPublicDescription(page.locator(PUBLIC_DESCRIPTION_SELECTOR), version);
  } catch (error) {
    if (error instanceof PublisherVerificationError) throw error;
    throw new PublisherVerificationError("public-description", error instanceof Error ? error.message : String(error));
  }
}


async function verifyPublicArtifact(context, metadata, expectedArtifactHash, tempDir) {
  let observedArtifactSha256 = null;
  let lastDownloadError = null;
  const result = await pollBounded(async (attempt) => {
    const destination = path.join(tempDir, `public-${attempt}-${APPROVED_ARTIFACT_NAME}`);
    try {
      observedArtifactSha256 = await downloadPublishedArtifact(context, metadata, destination);
      lastDownloadError = null;
      return { done: observedArtifactSha256 === expectedArtifactHash };
    } catch (error) {
      lastDownloadError = error;
      return { done: false };
    }
  }, { intervals: ARTIFACT_POLL_INTERVALS_MS });
  const diagnostics = {
    observedArtifactSha256,
    artifactAttempts: result.attempts,
    artifactElapsedMs: result.elapsedMs,
  };
  if (!observedArtifactSha256) {
    throw new PublisherVerificationError(
      "public-download",
      lastDownloadError instanceof Error ? lastDownloadError.message : "published-artifact-download-failed",
      diagnostics,
    );
  }
  if (observedArtifactSha256 !== expectedArtifactHash) {
    throw new PublisherVerificationError("artifact-hash", "published-artifact-hash-mismatch", diagnostics);
  }
  return diagnostics;
}


async function writeReport(output, report) {
  await fs.mkdir(path.dirname(output), { recursive: true });
  await fs.writeFile(output, JSON.stringify(report, null, 2) + "\n", { encoding: "utf8", mode: 0o600 });
}


async function run() {
  const startedAt = new Date().toISOString();
  let args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`AnkiWeb publisher rejected its arguments: ${sanitizeFailure(error)}\n`);
    return 2;
  }
  const email = process.env.ANKIWEB_EMAIL || "";
  const password = process.env.ANKIWEB_PASSWORD || "";
  const secretValues = [email, password];
  const baseReport = {
    schemaVersion: 2,
    mode: args.mode,
    version: args.version,
    addonId: 373100400,
    branch: "Branch 1",
    startedAt,
    finishedAt: null,
    status: "failure",
    phase: null,
    mutationCount: 0,
    descriptionSha256: null,
    artifactSha256: null,
    expectedDescriptionSha256: null,
    observedDescriptionSha256: null,
    expectedArtifactSha256: null,
    observedArtifactSha256: null,
    publicDescriptionContainerFound: false,
    versionMarkerFound: false,
    publicDescriptionAttempts: 0,
    publicDescriptionElapsedMs: 0,
    artifactAttempts: 0,
    artifactElapsedMs: 0,
    finalPathname: null,
    idempotent: false,
  };
  let browser;
  let tempDir;
  let page;
  try {
    if (!email || !password) throw new Error("missing-ankiweb-credentials");
    const metadataText = await fs.readFile(path.resolve(args.metadata), "utf8");
    const metadata = validateMetadata(parseSimpleYaml(metadataText));
    const description = normalizeMarkdown(await fs.readFile(path.resolve(args.description), "utf8"));
    const descriptionHash = sha256Text(description);
    baseReport.expectedDescriptionSha256 = descriptionHash;
    if (args.descriptionSha256) {
      const supplied = (await fs.readFile(path.resolve(args.descriptionSha256), "utf8")).trim();
      if (supplied !== descriptionHash) throw new Error("description-hash-input-mismatch");
    }
    let artifactHash = null;
    let artifactPath = null;
    if (args.artifact) {
      artifactPath = path.resolve(args.artifact);
      if (path.basename(artifactPath) !== APPROVED_ARTIFACT_NAME) throw new Error("unexpected-artifact-name");
      artifactHash = await sha256File(artifactPath);
      baseReport.expectedArtifactSha256 = artifactHash;
    }
    const publisherTempRoot = process.env.RUNNER_TEMP || os.tmpdir();
    tempDir = await fs.mkdtemp(path.join(publisherTempRoot, "asr-ankiweb-"));
    const require = createRequire(path.join(ROOT, "web-dashboard", "package.json"));
    const { chromium } = require("playwright");
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ acceptDownloads: true });
    page = await context.newPage();
    await login(page, email, password);
    const form = await openUpdateForm(page, metadata);
    const before = await observedState(form, metadata, descriptionHash);
    baseReport.observedDescriptionSha256 = before.descriptionSha256;
    if (args.mode === "dry-run") {
      await writeReport(args.output, {
        ...baseReport,
        status: "success",
        finishedAt: new Date().toISOString(),
        descriptionSha256: descriptionHash,
        formContractValid: true,
        metadataAlreadyCurrent: before.metadataMatch,
        descriptionAlreadyCurrent: before.descriptionMatch,
      });
      return 0;
    }
    if (!artifactPath || !artifactHash) throw new Error("publish-artifact-missing");
    baseReport.idempotent = before.metadataMatch && before.descriptionMatch;
    const verified = await executePublishPlan({
      initialState: before,
      saveOnce: async () => {
        baseReport.mutationCount = 1;
        baseReport.idempotent = false;
        try {
          await form.title.fill(metadata.title);
          await form.tags.fill(metadata.tags.join(" "));
          await form.support.fill(metadata.support_url);
          await form.branchMin.fill(metadata.minimum_anki_version);
          await form.branchMax.fill(metadata.maximum_anki_version);
          await form.branchSelect.selectOption({ label: metadata.expected_branch_label });
          await form.file.setInputFiles(artifactPath);
          await form.description.fill(description);
          const ready = await observedState(form, metadata, descriptionHash);
          if (!ready.metadataMatch || !ready.descriptionMatch) throw new Error("pre-save-form-verification-failed");
          await Promise.all([
            page.waitForURL((url) => !url.pathname.startsWith("/shared/upload"), { timeout: 30_000 }),
            form.save.click(),
          ]);
          await assertNoChallenge(page);
        } catch (error) {
          throw new PublisherVerificationError("authenticated-form", error instanceof Error ? error.message : String(error));
        }
      },
      verifySource: async () => {
        const state = await verifyAuthenticatedForm(page, metadata, descriptionHash);
        baseReport.observedDescriptionSha256 = state.descriptionSha256;
        return state;
      },
      verifyPublic: async () => {
        const diagnostics = await verifyPublicRendering(page, metadata, args.version);
        Object.assign(baseReport, diagnostics);
        return diagnostics;
      },
      verifyArtifact: async () => {
        const diagnostics = await verifyPublicArtifact(context, metadata, artifactHash, tempDir);
        Object.assign(baseReport, diagnostics);
        return diagnostics;
      },
    });
    baseReport.mutationCount = verified.mutationCount;
    await writeReport(args.output, {
      ...baseReport,
      status: "success",
      finishedAt: new Date().toISOString(),
      phase: null,
      descriptionSha256: verified.source.descriptionSha256,
      artifactSha256: verified.artifact.observedArtifactSha256,
      observedDescriptionSha256: verified.source.descriptionSha256,
      observedArtifactSha256: verified.artifact.observedArtifactSha256,
      ...verified.publicDescription,
      artifactAttempts: verified.artifact.artifactAttempts,
      artifactElapsedMs: verified.artifact.artifactElapsedMs,
      formContractValid: true,
      postSaveVerified: true,
      idempotent: verified.idempotent,
      finalPathname: new URL(page.url()).pathname,
    });
    return 0;
  } catch (error) {
    const safeMessage = sanitizeFailure(error, secretValues);
    const diagnostics = error instanceof PublisherVerificationError ? error.diagnostics : {};
    const finalPathname = page ? (() => {
      try { return new URL(page.url()).pathname; } catch { return null; }
    })() : null;
    await writeReport(args.output, {
      ...baseReport,
      ...diagnostics,
      phase: error instanceof PublisherVerificationError ? error.phase : baseReport.phase,
      finishedAt: new Date().toISOString(),
      finalPathname,
      error: safeMessage,
    });
    process.stderr.write(`AnkiWeb publisher failed: ${safeMessage}\n`);
    return 1;
  } finally {
    if (browser) await browser.close().catch(() => undefined);
    if (tempDir) await fs.rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  }
}


if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await run();
}
