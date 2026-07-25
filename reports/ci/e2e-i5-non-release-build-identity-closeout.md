# E2E-I5 — Non-release build identity closeout

## Status

```text
COMPLETE
implementation and cloud acceptance passed
PR #141 remains unmerged at this snapshot
E2E-I6 not started
```

E2E-I5 is complete at the candidate stage. The implementation, package-producing Fast CI, exact package handoff, one `standard/full` real-Anki E2E and uploaded-artifact inspection all passed on the final implementation tree.

## Baseline and final tree

```text
base branch: core
core baseline: 50c2f0473603fa5979fb4bd46b9f36198f18f85c
working branch: platform/e2e-i5-non-release-build-identity
final candidate HEAD: 92354870970956ed5d2e9216efca5058aa8addf3
PR: #141
previous completed Platform stage: E2E-I4
next planned Platform stage: E2E-I6
```

The stage remained bounded to non-release build identity and its required package/harness/workflow/environment evidence. `core` was not modified directly and no force push was used.

## Implemented

- closed schema v1 and deterministic `identityDigest` over the canonical `identity` object only;
- independent package tested SHA, Fast CI run/attempt, artifact ID/transport digest and inner package hash/size;
- independent harness commit/checkout and workflow source identity;
- exact immutable GHCR reference, digest, platform, environment contract and source revision;
- exact-tree/harness-only reuse mode with changed-file count and changed-path digest;
- execution run/attempt separated from the build digest;
- identity creation after complete material resolution and before canonical Docker E2E;
- raw/public validation and semantic parity enforcement;
- bounded identity staging across inner artifact reset;
- success and functional-failure restoration;
- cancellation preservation only when identity already exists;
- manifest regeneration and public export validation;
- stale identity removal and honest absence before material resolution;
- release-artifact exclusion;
- focused schema, lifecycle, workflow and security tests.

Canonical contract: [`../../docs/non-release-build-identity.md`](../../docs/non-release-build-identity.md).

## Published commits

```text
4d77f37c331250628f9e8e45bb47d711475e78ae  Add canonical non-release build identity
e1653de57992904424b237c03affda1d85e8f907  Bind package, harness, workflow, and environment evidence
df113081f88c2bd476c1e6f3999e2a47f47e76ed  Use exact workflow context for harness checkout
2393c1843c112c12d11757e138991bb833e18d19  Document and verify non-release build identity
92354870970956ed5d2e9216efca5058aa8addf3  Align E2E workflow tests with source identity
```

The final commit corrected two stale string-based workflow tests. Production workflow behavior was not weakened or reverted.

## Local and focused verification

Before cloud acceptance:

```text
python source compile: PASS
initial E2E-I5 focused tests: 47 PASS
workflow YAML parse: PASS
post-fix focused tests: 61 PASS
git diff --check: PASS
```

The first package-producing Fast CI attempt exposed two stale assertions in `tests/test_ci_e2e_workflow.py`:

```text
Fast CI run: 30149006339
result: FAILURE
Python: 1020 passed, 6 skipped, 2 failed
package artifact: not produced
```

The assertions expected trigger-dependent `github.sha` and the removed tested-commit checkout step. Commit `92354870970956ed5d2e9216efca5058aa8addf3` aligned them with `job.workflow_*` and the exact workflow/harness checkout contract. The failed run was not reused or rerun blindly.

## Successful Fast CI package

```text
Fast CI run: 30149481485 / attempt 1
result: PASS
tested commit: 92354870970956ed5d2e9216efca5058aa8addf3
diagnostics artifact ID: 8617175451
diagnostics artifact digest: sha256:568456efdbc5e50aaefe1f19a7adee78d9f7258a425eb0917a3b4e41ae52f070
package artifact ID: 8617175787
package artifact digest: sha256:a3b2357e6b19486c5902d62f4d8433f54374b539e689e2cc7ad138b4caab34c1
inner package SHA-256: 4041ace490b1bba63e340ae8597613db3ce2bf8b12a1cbfb27c776b2c68e0861
inner package size: 750680 bytes
```

The package and diagnostics artifacts were downloaded and validated before E2E dispatch. The complete handoff contract passed with:

```text
reuseAllowed: true
reuseMode: exact-tree
changedFileCount: 0
changedPathsSha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Transport artifact digest and inner `.ankiaddon` digest remained separate identities.

## Successful standard/full E2E

```text
E2E run: 30150971581 / attempt 1
job: Real Anki Desktop (standard / full)
result: PASS
tested commit: 92354870970956ed5d2e9216efca5058aa8addf3
source Fast CI run: 30149481485
E2E artifact ID: 8617629796
E2E artifact name: ci-e2e-standard-30150971581-1
E2E artifact digest: sha256:44d40f58251be7494928a26c151f8505c5a21623ec29d6f1c855314b4d703d7b
E2E artifact size: 6883753 bytes
```

All canonical steps passed, including exact package resolution, diagnostics validation, exact workflow/harness checkout, immutable GHCR verification, identity creation, Docker-only E2E, identity restoration, package hash verification, sanitized evidence publication, public artifact preparation, upload and Docker cleanup.

## Canonical identity evidence

The uploaded public identity contains:

```text
schemaVersion: 1
kind: non-release-build
identityDigest: sha256:d85608e71b0bb927fbd7f400c9b65d436395ff359f467dec6a12f0c63028cbad
repository: AliceLiddell01/anki-study-report
package source run: 30149481485 / attempt 1
package artifact ID: 8617175787
package artifact digest: sha256:a3b2357e6b19486c5902d62f4d8433f54374b539e689e2cc7ad138b4caab34c1
package inner SHA-256: 4041ace490b1bba63e340ae8597613db3ce2bf8b12a1cbfb27c776b2c68e0861
package size: 750680 bytes
package tested SHA: 92354870970956ed5d2e9216efca5058aa8addf3
harness commit/checkout SHA: 92354870970956ed5d2e9216efca5058aa8addf3
workflow source SHA: 92354870970956ed5d2e9216efca5058aa8addf3
workflow path: .github/workflows/ci-e2e.yml
reuse mode: exact-tree
environment image digest: sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
environment platform: linux/amd64
environment contract SHA-256: 8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
```

The execution section separately records E2E run `30150971581`, attempt `1`, trigger SHA and ref. Recomputing SHA-256 over compact sorted UTF-8 JSON of `identity` reproduced the stored `identityDigest`.

## Uploaded artifact inspection

The artifact ZIP was downloaded through the GitHub Actions artifact API and independently inspected outside the repository checkout.

```text
deterministic acceptance checks: 33/33 PASS
uploaded files: 73/73 exact summary inventory
artifact manifest: success
identity present in manifest: yes
identity encoded size: 1847 bytes
browser items: 23/23 PASS
screenshots: 18/18
console events: 0
page errors: 0
failed requests: 0
unexpected external requests: 0
preflight checks: 20/20 PASS
FSRS visual checks: 80 PASS
sanitizer scan: no token, authorization header, private key or token-bearing URL matches
```

Real-deck evidence remained non-synthetic and passed:

```text
committed APKG packages: 3
manifest packages: 3 PASS
runtime imports: 3 PASS
resolved anchors: 11/11
scenario groups: 9 PASS
API smoke: PASS
manual package extraction: false
synthetic fallback: false
```

The workflow-level raw/public identity validation and semantic parity checks passed before upload. In the downloaded public artifact, the identity digest was independently recomputed, the public identity was present in the artifact manifest, the summary inventory matched all 73 uploaded files, and the screenshot manifest matched all 18 PNG files.

## Intentionally not run

- second successful E2E;
- controlled cancellation A/B;
- intentionally failing cloud run;
- `perf100`;
- warm repeat;
- worker comparison;
- visual regression;
- retries;
- docs-only heavy rerun.

These runs were not required after one successful exact-tree `standard/full` acceptance on the final implementation SHA.

## Scope retained

Not implemented:

```text
E2E-I6 canonical final summary/history
release identity/provenance redesign
artifact attestations/SBOM/SLSA/signing
retries/quarantine
visual regression
performance thresholds
source-build cloud fallback
product/API/dashboard changes
```

## Completion decision

All E2E-I5 completion conditions are satisfied:

1. successful package-producing Fast CI on the final implementation commit;
2. successful `standard/full` E2E consuming that exact package;
3. uploaded artifact inspection proving schema/digest, manifest/public evidence, 23 browser items and 18 screenshots;
4. roadmap, handoff, documentation index and report status synchronization.

E2E-I6 is the next planned Platform stage, but this closeout does not start it. Merge remains a separate owner-approved action.
