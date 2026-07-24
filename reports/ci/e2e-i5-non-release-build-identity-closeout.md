# E2E-I5 — Non-release build identity closeout

## Status

```text
PARTIAL
implementation prepared and published for review
cloud acceptance pending
E2E-I6 not started
```

This report is intentionally not a `COMPLETE` closeout. The canonical implementation and focused tests are ready, but the required new package-producing Fast CI and one successful full real-Anki E2E acceptance run were not executable through the available GitHub connector actions.

## Baseline

```text
base branch: core
core baseline: 50c2f0473603fa5979fb4bd46b9f36198f18f85c
working branch: platform/e2e-i5-non-release-build-identity
previous completed Platform stage: E2E-I4
```

No prior E2E-I5 branch, implementation or open PR was present before mutation.

## Implemented

- closed schema v1 and deterministic `identityDigest` over the canonical `identity` object;
- independent package tested SHA, Fast CI run/attempt, artifact ID/transport digest, inner package hash/size;
- independent harness checkout and workflow source identity;
- exact immutable GHCR reference/digest/platform/contract/source revision;
- exact-tree/harness-only mode with changed-file count and changed-path hash;
- execution run/attempt separated from build digest;
- raw/public validation and semantic parity check;
- pre-E2E identity creation, bounded staging across inner artifact reset, manifest regeneration and public export validation;
- success/functional-failure restoration and cancellation allowlist preservation;
- stale identity removal and honest absence before material resolution;
- release-artifact exclusion;
- compact GitHub Step Summary block;
- focused schema, cross-evidence, lifecycle, cancellation and workflow tests.

Canonical contract: `docs/non-release-build-identity.md`.

## Published implementation

```text
4d77f37c331250628f9e8e45bb47d711475e78ae  Add canonical non-release build identity
e1653de57992904424b237c03affda1d85e8f907  Bind package, harness, workflow, and environment evidence
df113081f88c2bd476c1e6f3999e2a47f47e76ed  Use exact workflow context for harness checkout
```

Publication used GitHub tree/commit/ref actions for the primary logical commits and a sequential Contents API correction for the exact workflow-context binding. Branch updates were non-force; `core` was not modified.

## Package decision

The preferred historical Fast CI source was inspected:

```text
Fast CI run: 30125233072 / attempt 1
package artifact ID: 8609019098
package transport digest: sha256:5001e6e1ef480325b1ea9cd214ac8cce157d35f75dbbb9d5a8153acb46fdd882
package tested SHA: 5e52faee5cd97af8e7760e2c5041c782ce4273fa
inner package SHA-256: 9b3bfcdc019e870579563b2be9eaa75220f6b732ee6b4f8fc6e524288b1c0862
inner package size: 750680 bytes
expired: false at inspection time
```

Reuse was rejected fail closed. The package tested SHA is eight commits behind the current core baseline and the complete diff contains many documentation/roadmap/report paths outside the existing harness-only allowlist. The allowlist was not weakened. One new package-producing Fast CI is therefore required from the implementation branch.

## Verification performed

```text
python compile: PASS
focused identity and E2E-I5 contract tests: 46 PASS
isolated repository-integration assertion: 1 SKIP because unchanged repository files were not mounted in the isolated fixture
YAML parse: PASS
```

The checks ran in an isolated execution sandbox, not in the owner's WSL or local clone. PowerShell/actionlint and the full repository suite were not available in that environment and are not claimed.

## Cloud acceptance blocker

The connected GitHub action surface supports repository writes, PR operations, workflow/artifact reads and reruns, but does not expose workflow dispatch. The E2E workflow has only `workflow_call` and `workflow_dispatch`; publishing the branch or opening a PR to `core` does not automatically start the required package-producing Fast CI or full E2E gate.

Consequently, these required completion proofs remain pending:

```text
new Fast CI package run
exact package artifact ID/digest
one standard/full E2E run after final implementation fix
canonical build identity digest from the cloud artifact
manifest/public parity from the uploaded artifact
browser items 23/23
screenshots 18/18
```

No attempt was made to bypass this by weakening reuse, adding a temporary dispatch workflow, changing the PR base, using source-build fallback or re-running an unrelated historical workflow.

## Not run

- second successful E2E;
- controlled cancellation A/B;
- intentionally failing cloud run;
- perf100;
- warm repeat;
- worker comparison;
- visual regression;
- retries;
- docs-only heavy rerun.

## Scope retained

Not implemented:

```text
E2E-I6 canonical final summary/history
release identity/provenance redesign
artifact attestations/SBOM/SLSA/signing
retries/quarantine
visual regression
performance thresholds
product/API/dashboard changes
```

## Completion condition

E2E-I5 may be changed from `PARTIAL` to `COMPLETE` only after:

1. one new successful package-producing Fast CI on the final implementation commit;
2. one successful `standard/full` E2E consuming that exact package;
3. inspection of the uploaded artifact proving identity schema/digest, manifest/public parity and the unchanged 23-item/18-screenshot browser contract;
4. documentation/roadmap status sync using the resulting immutable run and artifact evidence.

The next planned stage remains E2E-I6, but it must not start before this acceptance closes.
