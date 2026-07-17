# CI optimization Stage 5B: duplicate typecheck removal

## 1. Scope and snapshot

Date: **2026-07-16**.

Repository:

```text
AliceLiddell01/anki-study-report
```

Base `master` SHA:

```text
6255a7d5d10ee95dd24ff8a101e3acd1f8ee51bd
```

Implementation SHA tested by the authorized runtime run:

```text
826c052f9532dc3a15222f4f394f503704fee083
```

Branch:

```text
chatgpt/ci-optimization-stage-5b-remove-duplicate-typecheck
```

Stage 5B changed only the canonical Fast CI orchestration and its contract tests:

```text
scripts/run_full_check.ps1
tests/test_full_check_timing.py
tests/test_ci_fast_timing.py
tests/test_ci_fast_workflow.py
```

It did not change runner selection, checkout depth, dependency installation,
caches, TypeScript configuration, Vitest, Vite, package scripts, Docker E2E, or
release delivery.

## 2. Baseline

Stage 5A runtime baseline:

```text
run: 29501875205
tested SHA: 9746b1cd7b3b4ec63b4dd8111543f4cb3aadc80b
runner: windows-2025
```

Measured duplicate TypeScript work:

| Phase | Duration |
| --- | ---: |
| Typecheck before tests | `8.687 s` |
| Typecheck before build | `8.609 s` |

Both invocations used `pnpm run typecheck`, which maps to `tsc --noEmit`, in the
same `web-dashboard` working directory and against the same `tsconfig.json` and
source graph. The second invocation was therefore selected as the narrow removal
target.

## 3. Implementation

Before:

```text
changelog-check
→ frontend-typecheck-tests
→ frontend-vitest
→ frontend-typecheck-build
→ frontend-vite-build
→ frontend-bundle-check
→ frontend-addon-assets-copy
→ python-pytest
→ package-build-check
→ package-check-only
```

After:

```text
changelog-check
→ frontend-typecheck-tests
→ frontend-vitest
→ frontend-vite-build
→ frontend-bundle-check
→ frontend-addon-assets-copy
→ python-pytest
→ package-build-check
→ package-check-only
```

Only the second canonical `pnpm run typecheck` block was removed from
`scripts/run_full_check.ps1`.

The first canonical typecheck remains before Vitest and Vite. Standalone frontend
build safety also remains unchanged:

```text
"typecheck": "tsc --noEmit"
"build": "pnpm run typecheck && pnpm run build:vite && pnpm run build:check-bundle"
"build:addon": "pnpm run build && pnpm run build:copy-addon"
```

Timing schema compatibility is preserved:

- `schemaVersion` remains `1`;
- historical `frontend-typecheck-build` remains allowlisted;
- new successful runs omit that phase;
- Markdown renders it as `not recorded`;
- no fabricated zero-duration phase is recorded.

## 4. Local verification

Local canonical verification completed successfully on Windows with Python
`3.12.13`.

Commands covered targeted Stage 5B tests and the full non-Docker canonical
contour with timing enabled.

Observed result:

```text
Vitest: 40 files, 245 tests passed
pytest: 548 passed, 3 skipped
Vite build: PASS
bundle guard: PASS
asset synchronization: PASS
package build/check: PASS
package check-only: PASS
Full check completed.
```

All nine expected canonical timing phases completed successfully and
`frontend-typecheck-build` was absent. The local timing document was finalized
and validated successfully. The three skips were environment-specific Windows
symlink tests.

The local top-level timing document duration included the manual delay before
explicit finalization and is not used as a pipeline performance metric.

## 5. Runtime run

Authorized runtime identity:

| Field | Value |
| --- | --- |
| Run ID | `29522295621` |
| Job ID | `87702045336` |
| Workflow | `Fast CI` |
| Job | `Frontend, Python and package` |
| Event | `workflow_dispatch` |
| Ref | `refs/heads/chatgpt/ci-optimization-stage-5b-remove-duplicate-typecheck` |
| Tested SHA | `826c052f9532dc3a15222f4f394f503704fee083` |
| Attempt | `1` |
| Conclusion | `success` |
| Runner label | `windows-2025` |
| Workflow elapsed | `198 s` |
| Job execution | `186 s` |
| Canonical pipeline step | `103 s` |

Every workflow step succeeded, including diagnostics preparation, both dependency
installs, the canonical pipeline, verification planning, timing finalization,
and both artifact uploads.

No rerun was performed.

## 6. Timing artifact

Diagnostics artifact:

```text
ci-fast-29522295621-1
```

Transport metadata:

```text
artifact id: 8385269322
size: 8135 bytes
sha256: e2311e113ea14a8d24fa77db25c75d8123fcbe4eaf3177971467112186cf11b9
```

Contents:

```text
ci-summary.json
ci-summary.md
environment.txt
logs/fast-check.log
timing/fast-ci-timing.json
timing/fast-ci-timing.md
verification-plan/verification-plan.json
verification-plan/verification-plan.md
```

Timing identity and totals:

```text
schemaVersion: 1
result: success
testedCommitSha: 826c052f9532dc3a15222f4f394f503704fee083
internal timed total: 111.437 s
timing document duration: 117.515 s
```

Retained phases:

| Phase | Stage 5B duration |
| --- | ---: |
| Install Python dependencies | `5.313 s` |
| Install frontend dependencies | `3.593 s` |
| Changelog check | `0.344 s` |
| Typecheck before tests | `11.329 s` |
| Vitest | `38.406 s` |
| Vite production build | `14.187 s` |
| Bundle validation | `0.796 s` |
| Asset synchronization | `0.781 s` |
| pytest | `34.375 s` |
| Package build/check | `0.422 s` |
| Package check-only | `0.312 s` |

`frontend-typecheck-build` is absent from JSON and rendered as `not recorded` in
Markdown. No zero-duration replacement phase exists. All recorded phases have
`status: success` and `exitCode: 0`.

The diagnostics files contain no absolute local paths, tokens, authorization
headers, or token-bearing URLs.

## 7. Functional equivalence

Frontend runtime evidence:

```text
40 test files passed
245 tests passed
2243 modules transformed
bundle guard passed
10 JavaScript chunks
```

Python runtime evidence:

```text
551 collected
550 passed
1 skipped
```

The cloud Python count increased relative to the Stage 5A baseline because Stage
5B added contract coverage; no test surface was removed.

Package runtime evidence:

```text
archive entries: 53
missing required entries: []
forbidden entries: []
missing linked dashboard assets: []
empty linked dashboard assets: []
unreferenced dashboard JS/CSS assets: []
dashboard asset graph errors: []
unsafe dashboard asset references: []
zip test result: None
canonical package version: 1.1.0
```

Vite output, bundle validation, asset synchronization, package construction, and
package revalidation all remained successful.

## 8. Before/after timing

| Metric | Stage 5A | Stage 5B | Observed delta | Confidence |
| --- | ---: | ---: | ---: | --- |
| First typecheck | `8.687 s` | `11.329 s` | `+2.642 s` | medium |
| Second typecheck | `8.609 s` | absent | `-8.609 s` direct work | high |
| Vitest | `20.641 s` | `38.406 s` | `+17.765 s` | medium |
| Vite build | `7.437 s` | `14.187 s` | `+6.750 s` | medium |
| Internal timed sum | `126.389 s` | `111.437 s` | `-14.952 s` | medium |
| Internal timing window | `131.906 s` | `117.515 s` | `-14.391 s` | medium |
| Canonical pipeline step | `117 s` | `103 s` | `-14 s` | medium |
| Job execution | `235 s` | `186 s` | `-49 s` | low/medium |
| Workflow elapsed | `246 s` | `198 s` | `-48 s` | low |

The direct removed work is the Stage 5A measured duration of the deleted phase:
`8.609 s`. That value is high-confidence because the phase no longer exists.

The full-run deltas are observational only. Retained phase times varied
substantially between the two single runs, especially Vitest and Vite. Runner
image, action setup, cache state, host load, and process scheduling remain
confounding variables. One after-run does not establish an average saving.

The important technical result is that the duplicated work was removed while the
internal timed total and canonical pipeline step both also decreased in the
observed run.

## 9. Variance and confidence

Confidence classification:

- removal of `8.609 s` baseline duplicate work: **high**;
- schema, command graph, and package contract preservation: **high**;
- internal total improvement in this one comparison: **medium**;
- job/workflow wall-time improvement: **low to medium**;
- average long-term CI saving: **not established by one after-run**.

No retained phase increase is classified as a regression because all functional
checks passed and the comparison consists of one before-run and one after-run on
GitHub-hosted infrastructure.

## 10. Contract preservation

Confirmed unchanged:

- `windows-2025` runner;
- checkout `fetch-depth: 0` and credential behavior;
- setup-python and setup-node cache configuration;
- dependency installation commands;
- canonical command entrypoint;
- standalone frontend build typecheck;
- Vite and bundle validation;
- dashboard asset synchronization;
- pytest and package validation;
- diagnostics upload with `always()`;
- exact package upload as success-only;
- action references pinned to immutable SHAs;
- no Docker or release invocation inside Fast CI.

Exact package artifact:

```text
ci-package-826c052f9532dc3a15222f4f394f503704fee083-29522295621-1
```

Transport metadata:

```text
artifact id: 8385269634
transport size: 580726 bytes
transport sha256: d8175e6b07ee8f96002e5feced183dc916e0c37b3af1716fe0da2206ffb0216d
```

Exact contents:

```text
anki_study_report.ankiaddon
package-metadata.json
```

Inner package verification:

```text
size: 582365 bytes
sha256: 4b5c04a74f920475c44ffc3855f90d4ee7dff5ce7920a9e745db70978673ec54
ZIP integrity: PASS
entries: 53
```

The computed package SHA-256 and size match `package-metadata.json` exactly.
Diagnostics and package artifacts remain separate.

## 11. Result

```text
optimization accepted
```

Stage 5B removed only the duplicate canonical TypeScript typecheck, preserved the
remaining verification surface and standalone type safety, passed local and cloud
verification, produced valid timing diagnostics, and preserved the exact package
contract.

A process-only caveat remains: the GitHub connector used for implementation
created one commit per modified file, so the implementation history contains four
logical commits instead of the originally preferred single implementation commit.
No force-push or history rewrite was performed because preserving the exact tested
SHA and avoiding unsafe branch rewriting took precedence.

## 12. Next decision

Recommended next action:

```text
Prepare a separate integration PR for Stage 5B without rerunning Fast CI.
```

Do not begin the next CI optimization as part of that PR. Any future setup/cache
analysis should be a separate stage with its own scope and measurement plan.
