# CI optimization Stage 5A: Fast CI timing baseline

## 1. Scope and snapshot

Дата baseline: **2026-07-16**.

Repository:

```text
AliceLiddell01/anki-study-report
```

Base `master` SHA:

```text
4d197c1037fd66401735e654c6697791364518a4
```

Instrumentation commit tested by the runtime run:

```text
9746b1cd7b3b4ec63b4dd8111543f4cb3aadc80b
```

Branch:

```text
chatgpt/ci-optimization-stage-5a-fast-ci-instrumentation
```

Stage 5A added observational instrumentation only. It did **not** remove work,
change caches, change the runner, change checkout depth, change dependency
commands, change test coverage, or implement a Fast CI optimization.

Formal closure status is **PARTIAL** despite the successful cloud run because the
required pre-dispatch local `run_full_check.ps1 -SkipDocker` PASS was not supplied,
and the available GitHub connector exposed the Jobs API step inventory but omitted
the run/job/step timestamp fields. No second run is needed to close those evidence
gaps.

## 2. Run identity

| Field | Value |
| --- | --- |
| Run ID | `29501875205` |
| Workflow | `Fast CI` |
| Job | `Frontend, Python and package` (`fast`) |
| Job ID | `87632586181` |
| Event | `workflow_dispatch` |
| Ref | `refs/heads/chatgpt/ci-optimization-stage-5a-fast-ci-instrumentation` |
| Tested SHA | `9746b1cd7b3b4ec63b4dd8111543f4cb3aadc80b` |
| Attempt | `1` |
| Conclusion | `success` |
| Runner label | `windows-2025` |
| Runner image | `windows-2025-vs2026` |
| Runner image version | `20260714.173.1` |
| Runner version | `2.335.1` |
| Hosted compute image provisioner | `20260707.563` |
| OS | Windows Server 2025, `10.0.26100` |
| Python | `3.11.9` |
| Node.js | `20.20.2` |
| pnpm | `9.15.9` |

Run URL:

```text
https://github.com/AliceLiddell01/anki-study-report/actions/runs/29501875205
```

The job and all repository-owned steps concluded successfully. No Docker E2E or
release workflow was started.

## 3. Measurement model

The baseline separates two clocks.

### Internal high-resolution timing

`scripts/ci_fast_timing.py` uses a monotonic clock for `durationMs` and UTC wall
timestamps for audit. The structured result is stored in:

```text
timing/fast-ci-timing.json
timing/fast-ci-timing.md
```

The JSON is schema v1, atomically written, allowlisted by stable phase IDs and
contains no absolute paths, tokens, authorization headers or token-bearing URLs.

### GitHub action/job timing

GitHub's Jobs API represents a job and its steps with `started_at` and
`completed_at`. Those timestamps have coarser granularity than the internal
monotonic timers and include action setup/post work that repository scripts cannot
measure.

Official references:

- https://docs.github.com/en/rest/actions/workflow-jobs
- https://docs.github.com/en/rest/actions/workflow-runs
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
- https://github.com/actions/setup-node
- https://github.com/actions/setup-python

For this run, the connector returned the complete successful step inventory and
the decoded job log, but its normalized job/step response omitted timestamp
fields and only the initial log segment was available to the analysis surface.
Consequently external timings below are exact where an artifact/log boundary
exists, lower bounds where post-job work continues, and `unavailable` where a
value would otherwise be fabricated.

## 4. Top-level timing

| Metric | Duration | Evidence | Confidence |
| --- | ---: | --- | --- |
| Queue wait | unavailable | Run-level `created_at` was not exposed | none |
| Runner log start → internal timer start | `92.640 s` | Job log `13:22:04.4573863Z` → timing JSON `13:23:37.097Z` | high for aggregate |
| Internal instrumented window | `131.906 s` | timing JSON | high |
| Sum of completed internal phases | `126.389 s` | timing JSON | high |
| Internal orchestration/gap remainder | `5.517 s` | instrumented window − phase sum | high |
| Runner log start → diagnostics artifact created | `225.543 s` | job log → artifact API | high lower bound |
| Runner log start → package artifact created | `226.543 s` | job log → artifact API | high lower bound |
| Complete job execution | `>226.543 s` | package upload was followed by package summary and post actions | high lower bound |
| Workflow elapsed | unavailable | Run-level created/completed timestamps were not exposed | none |

The `92.640 s` pre-internal aggregate includes runner/action preparation,
checkout, setup-python, setup-pnpm, setup-node/cache work and diagnostics
initialization. It must not be attributed entirely to cache restore or checkout.

## 5. Action/setup phases

| Phase | Duration | Evidence | Confidence |
| --- | ---: | --- | --- |
| Runner/action preparation before checkout | `1.729 s` | runner log start → checkout group start | medium |
| Checkout start → repository fetch completion | `8.644 s` | decoded job log | high lower bound |
| Checkout completion + Python/pnpm/Node setup/cache + diagnostics initialization | `82.266 s` | fetch completion → internal timer start | high aggregate, low attribution |
| Setup Python | unavailable separately | Jobs step success; no surfaced step timestamps | none |
| Setup pnpm | unavailable separately | Jobs step success; no surfaced step timestamps | none |
| Setup Node.js/pnpm cache | unavailable separately | Jobs step success; no surfaced step timestamps | none |
| Post setup-node | unavailable | Successful post step inventory | none |
| Post setup-pnpm | unavailable | Successful post step inventory | none |
| Post setup-python | unavailable | Successful post step inventory | none |
| Post checkout | unavailable | Successful post step inventory | none |

All action references remained pinned to full commit SHAs. Checkout remained
`persist-credentials: false` with `fetch-depth: 0`.

## 6. Dependency phases

| Phase | Duration | Share of internal window | Evidence | Confidence |
| --- | ---: | ---: | --- | --- |
| Python dependency install | `7.594 s` | `5.76%` | monotonic phase | high |
| Frontend dependency install | `2.609 s` | `1.98%` | monotonic phase | high |
| Combined dependency commands | `10.203 s` | `7.74%` | phase sum | high |

These values measure the install commands after setup/cache restore. They do not
include setup-python or setup-node cache work.

## 7. Frontend phases

| Phase | Duration | Share of internal window | Evidence | Confidence |
| --- | ---: | ---: | --- | --- |
| Typecheck before tests | `8.687 s` | `6.59%` | monotonic phase | high |
| Vitest | `20.641 s` | `15.65%` | monotonic phase | high |
| Typecheck before build | `8.609 s` | `6.53%` | monotonic phase | high |
| Vite production build | `7.437 s` | `5.64%` | monotonic phase | high |
| Bundle validation | `0.688 s` | `0.52%` | monotonic phase | high |
| Dashboard asset synchronization | `0.703 s` | `0.53%` | monotonic phase | high |
| Frontend total | `46.765 s` | `35.45%` | phase sum | high |

Vitest reported `40` test files and `245` tests passed. Its own runner summary
reported `19.26 s`; the enclosing monotonic phase was `20.641 s`, which also
includes process startup/teardown and orchestration.

The Vite log reported `2243` transformed modules and a `6.40 s` inner build;
the enclosing phase was `7.437 s`.

## 8. Python/package phases

| Phase | Duration | Share of internal window | Evidence | Confidence |
| --- | ---: | ---: | --- | --- |
| Changelog generated-output check | `0.250 s` | `0.19%` | monotonic phase | high |
| pytest | `67.047 s` | `50.83%` | monotonic phase | high |
| Package build and validation | `0.390 s` | `0.30%` | monotonic phase | high |
| Package check-only revalidation | `0.281 s` | `0.21%` | monotonic phase | high |
| Python/package total | `67.968 s` | `51.53%` | phase sum | high |

pytest collected `550` tests and finished with `549 passed, 1 skipped` in
`66.40 s`. The enclosing phase was `67.047 s`.

Both package validations passed with:

```text
Archive entries: 53
Missing required entries: []
Forbidden entries: []
Zip test result: None
Canonical package version: 1.1.0
```

## 9. CI finalization

| Phase | Duration | Evidence | Confidence |
| --- | ---: | --- | --- |
| Verification planner | `0.157 s` | monotonic phase | high |
| Fast CI summary preparation | `0.875 s` | monotonic phase | high |
| Exact package metadata write | `0.140 s` | monotonic phase | high |
| Staged exact package validation | `0.156 s` | monotonic phase | high |
| Exact package metadata verify | `0.125 s` | monotonic phase | high |
| Internal finalization total | `1.453 s` | phase sum | high |
| Timing end → diagnostics artifact created | approximately `1.002 s` | timing completion and artifact API, second-rounded | medium |
| Timing end → package artifact created | approximately `2.002 s` | timing completion and artifact API, second-rounded | medium |
| Package summary/post-job work | unavailable | Occurs after package artifact creation | none |

The upload duration cannot be written precisely into the artifact being uploaded.
Artifact API creation timestamps therefore provide only an external
second-granularity boundary.

## 10. Coverage accounting

```text
internal timing window                 131906 ms
sum of allowlisted completed phases    126389 ms
internal orchestration/gaps              5517 ms
phase coverage                           95.82%
```

Logical internal groups:

| Group | Duration | Share |
| --- | ---: | ---: |
| Dependency preparation | `10.203 s` | `7.74%` |
| Frontend canonical work | `46.765 s` | `35.45%` |
| Python/package work | `67.968 s` | `51.53%` |
| CI-only finalization | `1.453 s` | `1.10%` |
| Internal orchestration/gaps | `5.517 s` | `4.18%` |

The complete job cannot be reconciled to milliseconds because the runner log,
internal monotonic timer, artifact API and unavailable Jobs API timestamps are
different measurement surfaces.

## 11. Cache evidence

### setup-python pip cache

| Field | Value |
| --- | --- |
| Action | `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1` (`v6.3.0`) |
| Cache configuration | `cache: pip`, `cache-dependency-path: requirements-dev.txt` |
| Cached data semantics | global pip cache directory |
| Setup duration | unavailable separately |
| Post duration | unavailable separately |
| Install duration | `7.594 s` |
| Classification | `enabled-unknown` |
| Reason | Cache was configured and setup/post steps succeeded, but no exact-hit output or restore-key log was preserved in the uploaded diagnostics or exposed connector segment |

### setup-node pnpm cache

| Field | Value |
| --- | --- |
| Action | `actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e` (`v6.4.0`) |
| Cache configuration | `cache: pnpm`, `cache-dependency-path: web-dashboard/pnpm-lock.yaml` |
| Cached data semantics | pnpm global package-manager data; not `node_modules` |
| Setup duration | unavailable separately |
| Post duration | unavailable separately |
| Install duration | `2.609 s` |
| Classification | `enabled-unknown` |
| Reason | Cache was configured and setup/post steps succeeded, but no exact-hit output or restore-key log was preserved in the uploaded diagnostics or exposed connector segment |

GitHub defines an exact key match as a cache hit; a partial restore or absent
exact match is not an exact hit. This report therefore does not infer cache
effectiveness from `cache:` being enabled.

## 12. Duplicate TypeScript typecheck analysis

1. First typecheck: **`8.687 s`**.
2. Second typecheck: **`8.609 s`**.
3. Both invoke the same atomic command:

   ```text
   pnpm run typecheck
   → tsc --noEmit
   ```

4. Both use the same `web-dashboard/tsconfig.json`, whose input graph is
   `include: ["src"]`.
5. The only canonical operation between them is `vitest run`. The current command
   graph does not declare generated TypeScript source output from Vitest.
6. The second typecheck runs **before** Vite/assets generation, so it is not a
   validation of generated bundle assets. Bundle validation and asset copy have
   separate measured phases.
7. Safe upper-bound saving from removing only the duplicate invocation is the
   observed second phase: **`8.609 s`**, plus negligible shell/process overhead.
8. This is `6.53%` of the internal timing window and approximately `3.80%` of the
   observed runner-start-to-package lower bound.
9. The two measurements differ by only `78 ms` (`0.90%`), which is consistent with
   the same command and input graph in this one run.

The report does not implement the removal.

## 13. Ranked bottlenecks

| Rank | Phase/group | Duration | Share | Confidence | Candidate |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | pytest | `67.047 s` | `50.83%` internal | high | possible future test-performance investigation; broad risk |
| 2 | Pre-internal action/setup aggregate | `92.640 s` aggregate | not comparable to internal share | high aggregate / low attribution | cache/setup investigation requires complete step/cache evidence |
| 3 | Vitest | `20.641 s` | `15.65%` internal | high | possible future frontend test optimization |
| 4 | Duplicate second TypeScript typecheck | `8.609 s` | `6.53%` internal | high | **recommended Stage 5B candidate** |
| 5 | Python dependency install | `7.594 s` | `5.76%` internal | high | lower priority without cache evidence |
| 6 | Vite production build | `7.437 s` | `5.64%` internal | high | lower priority; required production artifact work |

Although pytest is the largest measured phase, changing test selection,
parallelism or architecture has materially higher correctness and maintenance
risk. The pre-internal setup aggregate is larger still, but current evidence
cannot attribute it safely to a specific cache or action.

## 14. Stage 5B decision

Selected primary candidate:

```text
duplicate TypeScript typecheck
```

Evidence:

- measured duration: `8.609 s`;
- frequency: every Fast CI run and every local canonical non-Docker check;
- safe upper-bound saving: approximately `8.609 s` per run;
- semantic duplication: same `tsc --noEmit`, same working directory, same
  `tsconfig.json`, same `src` input graph;
- no generated TypeScript input is introduced between the two invocations;
- bundle/assets have independent validations;
- implementation scope can remain local to canonical orchestration and package
  scripts without changing TypeScript options or coverage.

Required Stage 5B verification:

1. Preserve one full `tsc --noEmit` before Vitest/build.
2. Preserve exact Vitest, Vite, bundle-check and asset-copy commands/order.
3. Preserve ordinary `pnpm run build` behavior unless a versioned script contract
   is intentionally introduced.
4. Update workflow/script contract tests.
5. Run focused tests and `run_full_check.ps1 -SkipDocker`.
6. Perform a separately authorized exact-SHA Fast CI before/after comparison.

Alternatives are lower priority for Stage 5B because:

- pytest is larger but requires a dedicated test architecture/performance study;
- cache/setup work lacks exact hit/partial/miss and per-action duration evidence;
- package revalidation costs only `0.281 s`;
- Vite is required production work and is slightly cheaper than the duplicate
  typecheck.

No Stage 5B implementation is included in Stage 5A.

## 15. Artifacts, out of scope and caveats

### Diagnostics artifact

```text
name: ci-fast-29501875205-1
artifact ID: 8376876963
transport digest:
sha256:ce206b70d2beaf6986125c073c344cf71db44543ea757f9a46356c2725b1d6ba
size: 7841 bytes
retention: 14 days
```

Inventory:

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

### Exact package artifact

```text
name:
ci-package-9746b1cd7b3b4ec63b4dd8111543f4cb3aadc80b-29501875205-1

artifact ID: 8376877644
transport digest:
sha256:b960f5b27c657c0cbeff38f557ccf39429d19fca8f6a3d3ebe56aab8756addce
downloaded ZIP size: 580722 bytes
retention: 7 days
```

The artifact contains exactly:

```text
anki_study_report.ankiaddon
package-metadata.json
```

Inner package:

```text
SHA-256:
d8833b71473e7ebfbab3c0d26611e7322b9009ad12dbc300c19025867241b71b

size:
582365 bytes

archive entries:
53

zip integrity:
PASS
```

The metadata identity, package size and inner SHA-256 match the downloaded bytes.

### Not performed

- no Fast CI optimization;
- no second cloud run;
- no warm/cold cache pair;
- no Docker E2E;
- no release workflow;
- no Pull Request;
- no merge/rebase into `master`;
- no runner/cache/checkout change;
- no Stage 5B implementation.

### Caveats

- one runtime observation does not establish an average;
- queue wait and exact complete job wall were not exposed;
- per-action cache restore/save durations were not exposed;
- cache state remains `enabled-unknown`;
- the required pre-run local canonical PASS was not supplied;
- the runtime tested the instrumentation commit before this docs-only baseline
  commit; no second Fast CI run should be made for the docs-only commit.
