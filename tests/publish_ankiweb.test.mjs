import assert from "node:assert/strict";
import test from "node:test";

import {
  normalizeMarkdown,
  parseSimpleYaml,
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
