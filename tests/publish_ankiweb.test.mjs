import assert from "node:assert/strict";
import test from "node:test";

import {
  executePublishPlan,
  normalizeMarkdown,
  parseSimpleYaml,
  pollPublicDescription,
  sanitizeFailure,
  sha256Text,
  validateMetadata,
} from "../scripts/publish_ankiweb.mjs";


const VALID_METADATA = `schema_version: 1
addon_id: 373100400
title: "Anki Study Report"
tags:
  - stats
  - report
support_url: "https://example.com/support"
expected_branch_label: "Branch 1"
minimum_anki_version: "26.05.0"
maximum_anki_version: "26.05.0"
download_client_version: 260500
repository_url: "https://example.com/repository"
releases_url: "https://example.com/releases"
donation_url: "https://example.com/donate"
`;


test("metadata parser preserves ordered public tags and rejects unknown keys", () => {
  const metadata = validateMetadata(parseSimpleYaml(VALID_METADATA));
  assert.deepEqual(metadata.tags, ["stats", "report"]);
  assert.throws(() => validateMetadata({ ...metadata, password: "nope" }), /metadata-keys/);
});


test("markdown hashing is deterministic across line endings", () => {
  assert.equal(normalizeMarkdown("hello\r\n"), "hello\n");
  assert.equal(sha256Text("hello\r\n"), sha256Text("hello\n"));
});


test("failure sanitizer removes credentials, home paths and token queries", () => {
  const secret = "publisher-password-value";
  const safe = sanitizeFailure(new Error(`bad ${secret} ${process.env.USERPROFILE || "C:\\Users\\Alice"} ?token=abc`), [secret]);
  assert.doesNotMatch(safe, /publisher-password-value|token=abc/);
});


function fakeContainer(states) {
  let attempt = -1;
  return {
    async count() {
      attempt += 1;
      return states[Math.min(attempt, states.length - 1)].count;
    },
    async innerText() {
      return states[Math.min(attempt, states.length - 1)].text ?? "";
    },
  };
}


function instantPoll() {
  let clock = 0;
  return {
    intervals: [0, 1, 2, 3],
    sleep: async (milliseconds) => { clock += milliseconds; },
    now: () => clock,
  };
}


test("public description may appear after the heading probe would have failed", async () => {
  const container = fakeContainer([
    { count: 0 },
    { count: 1, text: "Anki Study Report" },
    { count: 1, text: "What's new in 1.0.0\nAdded" },
  ]);
  const result = await pollPublicDescription(container, "1.0.0", instantPoll());
  assert.equal(result.publicDescriptionAttempts, 3);
  assert.equal(result.versionMarkerFound, true);
});


test("ordinary text inside the public description satisfies the version marker", async () => {
  const result = await pollPublicDescription(
    fakeContainer([{ count: 1, text: "Release notes: What's new in 1.0.0. Enjoy." }]),
    "1.0.0",
    instantPoll(),
  );
  assert.equal(result.versionMarkerFound, true);
});


test("version text outside the public description does not satisfy verification", async () => {
  const outsidePageText = "What's new in 1.0.0";
  await assert.rejects(
    pollPublicDescription(fakeContainer([{ count: 1, text: "Description without release marker" }]), "1.0.0", instantPoll()),
    (error) => error.phase === "public-description" && error.message === "public-description-version-marker-absent",
  );
  assert.match(outsidePageText, /What's new/);
});


test("missing public description container has a distinct timeout", async () => {
  await assert.rejects(
    pollPublicDescription(fakeContainer([{ count: 0 }]), "1.0.0", instantPoll()),
    (error) => error.message === "public-description-container-timeout" &&
      error.diagnostics.publicDescriptionContainerFound === false,
  );
});


test("present public description without version text has a distinct failure", async () => {
  await assert.rejects(
    pollPublicDescription(fakeContainer([{ count: 1, text: "Older notes" }]), "1.0.0", instantPoll()),
    (error) => error.message === "public-description-version-marker-absent" &&
      error.diagnostics.publicDescriptionContainerFound === true,
  );
});


const MATCHING_STATE = {
  metadataMatch: true,
  descriptionMatch: true,
  descriptionSha256: "description-hash",
};


test("stored source mismatch fails before public or binary evidence can mask it", async () => {
  let publicCalls = 0;
  let artifactCalls = 0;
  await assert.rejects(executePublishPlan({
    initialState: MATCHING_STATE,
    saveOnce: async () => assert.fail("save must not run"),
    verifySource: async () => ({ ...MATCHING_STATE, descriptionMatch: false }),
    verifyPublic: async () => { publicCalls += 1; },
    verifyArtifact: async () => { artifactCalls += 1; },
  }), (error) => error.phase === "authenticated-form");
  assert.equal(publicCalls, 0);
  assert.equal(artifactCalls, 0);
});


test("already-current form and binary complete idempotently with zero mutation", async () => {
  let saves = 0;
  const result = await executePublishPlan({
    initialState: MATCHING_STATE,
    saveOnce: async () => { saves += 1; },
    verifySource: async () => MATCHING_STATE,
    verifyPublic: async () => ({ versionMarkerFound: true }),
    verifyArtifact: async () => ({ observedArtifactSha256: "artifact-hash" }),
  });
  assert.equal(saves, 0);
  assert.equal(result.mutationCount, 0);
  assert.equal(result.idempotent, true);
});


test("mismatched form performs exactly one save before full verification", async () => {
  let saves = 0;
  const result = await executePublishPlan({
    initialState: { ...MATCHING_STATE, metadataMatch: false },
    saveOnce: async () => { saves += 1; },
    verifySource: async () => MATCHING_STATE,
    verifyPublic: async () => ({ versionMarkerFound: true }),
    verifyArtifact: async () => ({ observedArtifactSha256: "artifact-hash" }),
  });
  assert.equal(saves, 1);
  assert.equal(result.mutationCount, 1);
  assert.equal(result.idempotent, false);
});


test("public artifact hash mismatch fails closed", async () => {
  await assert.rejects(executePublishPlan({
    initialState: MATCHING_STATE,
    saveOnce: async () => assert.fail("save must not run"),
    verifySource: async () => MATCHING_STATE,
    verifyPublic: async () => ({ versionMarkerFound: true }),
    verifyArtifact: async () => { throw new Error("published-artifact-hash-mismatch"); },
  }), /published-artifact-hash-mismatch/);
});


test("public polling never repeats form submission", async () => {
  let saves = 0;
  let publicAttempts = 0;
  const result = await executePublishPlan({
    initialState: { ...MATCHING_STATE, descriptionMatch: false },
    saveOnce: async () => { saves += 1; },
    verifySource: async () => MATCHING_STATE,
    verifyPublic: async () => {
      publicAttempts = (await pollPublicDescription(fakeContainer([
        { count: 0 },
        { count: 1, text: "Waiting" },
        { count: 1, text: "What's new in 1.0.0" },
      ]), "1.0.0", instantPoll())).publicDescriptionAttempts;
      return { versionMarkerFound: true };
    },
    verifyArtifact: async () => ({ observedArtifactSha256: "artifact-hash" }),
  });
  assert.equal(saves, 1);
  assert.equal(publicAttempts, 3);
  assert.equal(result.mutationCount, 1);
});


test("sanitized report fields contain no credentials or cookie values", () => {
  const credential = "publisher-password-value";
  const cookie = "session-cookie-value";
  const report = JSON.stringify({
    phase: "authenticated-form",
    error: sanitizeFailure(new Error(`failed ${credential} Cookie: ${cookie}`), [credential, cookie]),
    finalPathname: "/shared/upload",
  });
  assert.doesNotMatch(report, /publisher-password-value|session-cookie-value/);
});
