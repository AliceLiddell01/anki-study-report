# Non-release build identity

Status: implementation candidate for E2E-I5; cloud acceptance is required before the stage may be marked complete.

## Purpose

A non-release real-Anki E2E run consumes several independently versioned materials. Human labels such as workflow names, artifact names, branch names, job names and timestamps do not uniquely identify that combination. The canonical document binds the immutable package, harness, workflow, environment and reuse boundary into one deterministic identity while keeping the E2E execution instance separate.

Canonical raw path:

```text
reports/non-release-build-identity.json
```

Canonical public path:

```text
artifacts/reports/non-release-build-identity.json
```

The document is emitted only for `fast-ci-artifact`. `release-artifact` retains its existing release identity contract and must not emit `kind=non-release-build`.

## Identity map

| Value | Producer / raw source | Validator | Public evidence | Immutable | Independent recheck |
| --- | --- | --- | --- | --- | --- |
| Package tested SHA | Fast CI package metadata and diagnostics | Fast CI handoff validator + identity cross-evidence validator | `fast-ci-handoff.json`, canonical identity | yes | compare exact 40-hex SHA |
| Source Fast CI run/attempt | GitHub Actions run metadata | Fast CI run resolver | canonical identity | yes | GitHub Actions run API |
| Package artifact ID | GitHub artifact metadata | exact artifact resolver | canonical identity | yes | GitHub Actions artifact API |
| Package transport digest | GitHub artifact metadata | exact artifact resolver | canonical identity | yes | GitHub Actions artifact API |
| Inner package SHA-256/size | exact `.ankiaddon` bytes | package metadata validator + independent byte rehash | canonical identity | yes | hash and size exact file bytes |
| Harness SHA / checkout SHA | validated E2E checkout | harness reuse validator + identity validator | canonical identity | yes | `git rev-parse HEAD` and ancestry/diff validation |
| Workflow repository/path/SHA | `job.workflow_repository`, `job.workflow_file_path`, `job.workflow_sha` | workflow static tests + identity validator | canonical identity | yes | GitHub workflow identity contexts |
| Reuse mode/count/hash | complete package-to-harness diff | harness reuse validator | `e2e-harness-reuse.json`, canonical identity | yes | recompute sorted changed-path hash |
| GHCR reference/digest/platform | immutable consumer lock and pulled image | environment consumer validator + `RepoDigests`/platform checks | canonical identity and environment provenance | yes | image inspect and lock validation |
| Environment contract/source commit | environment lock and OCI labels | environment consumer validator + identity cross-check | canonical identity | yes | lock/label parity |
| E2E run ID/attempt/ref/trigger SHA | current workflow execution | identity schema validator | `execution` object | yes per execution | GitHub run metadata |

Artifact names, workflow display names and timestamps remain informational labels and are not identity fields.

## Schema v1

The document has an exact, closed field set:

```json
{
  "schemaVersion": 1,
  "kind": "non-release-build",
  "identityDigest": "sha256:<64 lowercase hex>",
  "identity": {
    "repository": "AliceLiddell01/anki-study-report",
    "package": {
      "source": "fast-ci-artifact",
      "testedCommitSha": "<40 lowercase hex>",
      "sourceRunId": 123,
      "sourceRunAttempt": 1,
      "artifactId": 456,
      "artifactDigest": "sha256:<64 lowercase hex>",
      "innerSha256": "<64 lowercase hex>",
      "sizeBytes": 750680
    },
    "harness": {
      "commitSha": "<40 lowercase hex>",
      "checkoutSha": "<40 lowercase hex>"
    },
    "workflow": {
      "repository": "AliceLiddell01/anki-study-report",
      "filePath": ".github/workflows/ci-e2e.yml",
      "sourceSha": "<40 lowercase hex>"
    },
    "environment": {
      "imageReference": "ghcr.io/...@sha256:<64 lowercase hex>",
      "imageDigest": "sha256:<64 lowercase hex>",
      "platform": "linux/amd64",
      "contractSha256": "<64 lowercase hex>",
      "publishedFromCommitSha": "<40 lowercase hex>"
    },
    "reuse": {
      "mode": "exact-tree",
      "changedFileCount": 0,
      "changedPathsSha256": "<64 lowercase hex>"
    }
  },
  "execution": {
    "runId": 789,
    "runAttempt": 1,
    "triggerSha": "<40 lowercase hex>",
    "ref": "refs/heads/platform/e2e-i5-non-release-build-identity"
  }
}
```

Maximum encoded document size is 32 KiB. Unknown fields, missing fields, wrong JSON types, unsafe paths/refs, uppercase or malformed hashes, mutable image references and inconsistent exact-tree/harness-only boundaries fail closed.

## Digest semantics

`identityDigest` is SHA-256 over only the canonical `identity` object:

```text
UTF-8
sorted JSON keys
compact separators (, and :)
no BOM
no trailing newline in hashed bytes
```

Included:

- exact Fast CI source run and attempt;
- exact package artifact ID and transport digest;
- package tested commit;
- inner `.ankiaddon` SHA-256 and size;
- harness and actual checkout SHA;
- workflow repository, file path and source SHA;
- immutable environment reference, digest, platform, contract and publication source commit;
- reuse mode, changed-file count and changed-path hash.

Excluded:

- `identityDigest` itself;
- E2E run ID and attempt;
- trigger ref/SHA;
- timestamps;
- artifact, workflow and job display names;
- branch/PR titles and URLs;
- human summaries.

A re-run of the same exact build therefore retains the same digest while the `execution` object changes. Mutation of any component identity or reuse-boundary field changes the digest.

## Boundaries

### Artifact transport digest versus inner package hash

The GitHub artifact digest identifies the uploaded transport archive. `innerSha256` identifies the exact `.ankiaddon` bytes tested by Anki. They are intentionally separate and neither substitutes for the other.

### Package commit versus harness commit

`package.testedCommitSha` identifies the source tree that produced package bytes. `harness.commitSha` identifies the E2E harness used to test them. A docs-only or allowlisted harness commit does not become the package-tested commit.

### Harness commit versus workflow source commit

The harness is the exact checked-out repository tree used by E2E. The workflow source is obtained from the workflow identity context (`job.workflow_sha` and related fields), not from the trigger SHA. Current Fast CI artifact consumption validates the explicit relation through the existing reuse contract.

### Build identity versus execution

`identity` describes the exact build combination. `execution` identifies one run/attempt that exercised it and is deliberately excluded from `identityDigest`.

### Non-release versus release

The contract is consumer-side evidence for Fast CI artifacts. It does not redesign release provenance, signing or publication.

## Lifecycle

1. Resolve and validate the exact successful Fast CI run and artifact IDs.
2. Validate diagnostics, package metadata and exact package bytes.
3. Validate package-to-harness ancestry and complete changed-path boundary.
4. Resolve workflow identity from the workflow/job context.
5. Validate the immutable GHCR lock, pull the exact digest and verify `RepoDigests`, platform and labels.
6. Build and cross-validate the canonical identity before Docker E2E.
7. Keep a bounded staging copy outside the inner artifact reset and restore the canonical reports path after the reset.
8. Rebuild the artifact manifest so the report is indexed.
9. Preserve the same validated document for success, functional failure and cancellation when material resolution completed.
10. Validate raw and public copies independently and require semantic equality.

If failure or cancellation occurs before all required materials are resolved, no partial identity is created. Empty strings, `unknown` placeholders and mutable tags are forbidden.

## CLI

```text
python scripts/non_release_build_identity.py build ...
python scripts/non_release_build_identity.py validate --input <path>
python scripts/non_release_build_identity.py validate-cross-evidence ...
python scripts/non_release_build_identity.py validate-pair --raw <path> --public <path>
python scripts/non_release_build_identity.py render-summary --input <path> [--output <summary>]
```

The pure schema/digest validator performs no network calls and uses only the Python standard library. GitHub API resolution remains in the existing handoff workflow.

## Security boundary

The schema does not permit tokens, authorization headers, artifact download URLs, private filesystem paths, actor email, event payloads, arbitrary environment values, command lines, package contents or display titles. Raw and public documents are validated before and after the existing sanitizer boundary.

Artifact attestations, Sigstore, SLSA, SBOM and signing are intentionally outside E2E-I5. They are separate supply-chain capabilities and would require an independently approved permissions and provenance design.
