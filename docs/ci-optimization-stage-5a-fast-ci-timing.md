# CI optimization Stage 5A: Fast CI timing baseline

## 1. Scope and closure status

Дата baseline и closure: **2026-07-16**.

Repository:

```text
AliceLiddell01/anki-study-report
```

Base `master` SHA:

```text
4d197c1037fd66401735e654c6697791364518a4
```

Instrumentation commit tested by the authorized runtime run:

```text
9746b1cd7b3b4ec63b4dd8111543f4cb3aadc80b
```

Stage 5A branch before this closure update:

```text
chatgpt/ci-optimization-stage-5a-fast-ci-instrumentation
bdc15ae25076bdc884f0c045351c37852aa05164
```

Formal closure status is **COMPLETE**.

The initial baseline document was intentionally marked `PARTIAL` because the
local canonical PASS and raw GitHub REST timestamps were not yet available to the
report author. Both gaps were subsequently closed:

- the user supplied a successful local `run_full_check.ps1 -SkipDocker` result
  with a clean working tree;
- raw workflow, job and step REST timestamps were supplied for the single
  authorized cloud baseline.

Stage 5A remains observational only. It did **not** remove work, change caches,
change the runner, change checkout depth, change dependency commands, change test
coverage or implement a Fast CI optimization.

## 2. Runtime run identity

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

The job and every repository-owned, upload and post-job step concluded
successfully. No Docker E2E, release dispatch or production deployment was
started.

## 3. Local canonical verification

Local canonical verification: **PASS**.

The user ran the Stage 5A branch through:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
git status --short
```

Observed result:

```text
Vitest: 40 files, 245 tests passed
pytest: 547 passed, 3 skipped
package build/check: PASS
package check-only: PASS
Full check completed.
git status --short: empty
```

The three local skips are Windows symlink-capability tests:

```text
tests/test_fast_ci_e2e_handoff.py
tests/test_security_boundaries.py
tests/test_trusted_media_selector.py
```

Local Python was `3.12.13`; cloud Python was `3.11.9`. The local run establishes
correctness and repository cleanliness. Its duration is not used as a direct
performance comparison with the GitHub-hosted runner.

## 4. Measurement model

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

### GitHub workflow, job and step timing

GitHub REST workflow and Jobs APIs provide second-granularity lifecycle and step
timestamps. They include action setup, cache restore/save, artifact upload and
post-job work that repository-owned monotonic timers cannot measure.

Official references:

- https://docs.github.com/en/rest/actions/workflow-jobs
- https://docs.github.com/en/rest/actions/workflow-runs
- https://docs.github.com/en/rest/actions/artifacts
- https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching
- https://github.com/actions/setup-node
- https://github.com/actions/setup-python

Internal monotonic values and REST wall-clock values are therefore reported
separately. A zero difference between second-granularity step timestamps is
rendered as `<1 s`, not as a proven zero-duration step.

## 5. Top-level timing

Raw lifecycle timestamps:

```text
workflow created_at:      2026-07-16T13:21:51Z
workflow run_started_at:  2026-07-16T13:21:51Z
workflow updated_at:      2026-07-16T13:25:57Z
job created_at:           2026-07-16T13:21:53Z
job started_at:           2026-07-16T13:22:01Z
job completed_at:         2026-07-16T13:25:56Z
```

| Metric | Duration | Source |
| --- | ---: | --- |
| Workflow elapsed | `246 s` | workflow REST timestamps |
| Workflow creation → job start | `10 s` | workflow/job REST timestamps |
| Job queue after job creation | `8 s` | job REST timestamps |
| Job execution | `235 s` | job REST timestamps |
| Visible step sum | approximately `230 s` | step timestamp differences |
| Step gaps/rounding/orchestration remainder | approximately `5 s` | job execution − visible step sum |
| Internal instrumented window | `131.906 s` | timing JSON |
| Sum of completed internal phases | `126.389 s` | timing JSON |
| Internal orchestration/gap remainder | `5.517 s` | internal window − phase sum |
| Internal phase coverage | `95.82%` | timing JSON |

The REST step sum is approximate because every step boundary has only
second-level precision. It must not be reconciled to internal milliseconds as if
both clocks had the same granularity or coverage.

## 6. GitHub action and setup phases

| Step | Duration | Interpretation |
| --- | ---: | --- |
| Set up job | `2 s` | runner job initialization |
| Check out repository | `11 s` | full action step wall time |
| Set up Python | `6 s` | action wall time, including any pip-cache work |
| Set up pnpm | `38 s` | pnpm action wall time; not a pure cache duration |
| Set up Node.js | `24 s` | action wall time, including pnpm-cache handling |
| Prepare diagnostics | `12 s` | timing initialization plus runtime/version output |
| Post Set up Node.js | `<1 s` | second-granularity timestamps |
| Post Set up pnpm | `<1 s` | second-granularity timestamps |
| Post Set up Python | `<1 s` | second-granularity timestamps |
| Post Check out repository | `2 s` | checkout cleanup wall time |
| Complete job | `<1 s` | second-granularity timestamps |

All action references remained pinned to full commit SHAs. Checkout remained
`persist-credentials: false` with `fetch-depth: 0`.

Action wall time is not equivalent to cache overhead. In particular, the `38 s`
pnpm setup and `24 s` Node setup measurements cannot be decomposed into download,
runtime setup, restore and orchestration without dedicated log/output evidence.

## 7. Dependency phases

| Phase | Internal duration | REST step wall | Share of internal window |
| --- | ---: | ---: | ---: |
| Python dependency install | `7.594 s` | `8 s` | `5.76%` |
| Frontend dependency install | `2.609 s` | `3 s` | `1.98%` |
| Combined dependency commands | `10.203 s` | approximately `11 s` | `7.74%` |

Internal values measure the install commands after setup/cache restore. They do
not include setup-python or setup-node action work.

## 8. Frontend phases

| Phase | Duration | Share of internal window |
| --- | ---: | ---: |
| Typecheck before tests | `8.687 s` | `6.59%` |
| Vitest | `20.641 s` | `15.65%` |
| Typecheck before build | `8.609 s` | `6.53%` |
| Vite production build | `7.437 s` | `5.64%` |
| Bundle validation | `0.688 s` | `0.52%` |
| Dashboard asset synchronization | `0.703 s` | `0.53%` |
| Frontend total | `46.765 s` | `35.45%` |

Vitest reported `40` test files and `245` tests passed. Its own runner summary
reported `19.26 s`; the enclosing monotonic phase was `20.641 s`, which includes
process startup, teardown and orchestration.

The Vite log reported `2243` transformed modules and a `6.40 s` inner build; the
enclosing phase was `7.437 s`.

The complete canonical pipeline step had a REST wall duration of `117 s`. This
step wraps frontend, pytest and package work and must not replace the more precise
internal breakdown.

## 9. Python and package phases

| Phase | Duration | Share of internal window |
| --- | ---: | ---: |
| Changelog generated-output check | `0.250 s` | `0.19%` |
| pytest | `67.047 s` | `50.83%` |
| Package build and validation | `0.390 s` | `0.30%` |
| Package check-only revalidation | `0.281 s` | `0.21%` |
| Python/package total | `67.968 s` | `51.53%` |

Cloud pytest collected `550` tests and finished with `549 passed, 1 skipped` in
`66.40 s`; the enclosing phase was `67.047 s`.

Both cloud package validations passed with:

```text
Archive entries: 53
Missing required entries: []
Forbidden entries: []
Zip test result: None
Canonical package version: 1.1.0
```

## 10. CI finalization

Internal subphase timing:

| Internal subphase | Duration |
| --- | ---: |
| Verification planner | `0.157 s` |
| Fast CI summary preparation | `0.875 s` |
| Exact package metadata write | `0.140 s` |
| Staged exact package validation | `0.156 s` |
| Exact package metadata verify | `0.125 s` |
| Internal finalization total | `1.453 s` |

GitHub step wall timing:

| Step | Duration |
| --- | ---: |
| Publish verification plan | `1 s` |
| Write CI summary | `1 s` |
| Prepare exact Fast CI package | `1 s` |
| Finalize structured timing | `1 s` |
| Upload Fast CI diagnostics | `1 s` |
| Upload exact Fast CI package | `1 s` |
| Summarize exact Fast CI package | `1 s` |

The internal values isolate repository-owned subcommands with monotonic
millisecond precision. REST values represent whole step wall time with
second-level granularity, including shell/action orchestration.

## 11. Coverage accounting

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

The full `235 s` job includes runner/action work outside the internal timer.
Internal coverage therefore describes the `131.906 s` instrumented window, not
the complete job.

## 12. Cache evidence

### setup-python pip cache

| Field | Value |
| --- | --- |
| Action | `actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1` (`v6.3.0`) |
| Configuration | `cache: pip`, `cache-dependency-path: requirements-dev.txt` |
| Setup action wall | `6 s` |
| Post action wall | `<1 s` |
| Install command | `7.594 s` internal / `8 s` REST step |
| Classification | `enabled-unknown` |

### setup-node pnpm cache

| Field | Value |
| --- | --- |
| Action | `actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e` (`v6.4.0`) |
| Configuration | `cache: pnpm`, `cache-dependency-path: web-dashboard/pnpm-lock.yaml` |
| Cached data semantics | pnpm global package-manager data; not `node_modules` |
| Setup Node.js action wall | `24 s` |
| Post setup-node wall | `<1 s` |
| Frontend install command | `2.609 s` internal / `3 s` REST step |
| Classification | `enabled-unknown` |

`Set up pnpm` separately took `38 s`; that action installs/configures pnpm and is
not itself proof of a setup-node cache hit or miss.

Neither REST timestamps nor the preserved diagnostics prove `exact-hit`,
`partial-hit` or `miss`. Cache classification therefore remains
`enabled-unknown`; no cache effectiveness claim is made from configuration or
action duration alone.

## 13. Duplicate TypeScript typecheck analysis

1. First typecheck: **`8.687 s`**.
2. Second typecheck: **`8.609 s`**.
3. Both invoke the same atomic command:

   ```text
   pnpm run typecheck
   → tsc --noEmit
   ```

4. Both use the same `web-dashboard/tsconfig.json`, whose input graph is
   `include: ["src"]`.
5. The only canonical operation between them is `vitest run`; the current command
   graph does not declare generated TypeScript source output from Vitest.
6. The second typecheck runs **before** Vite/assets generation, so it is not a
   validation of generated bundle assets. Bundle validation and asset copy have
   separate phases.
7. The safe observed upper-bound saving from removing only the duplicate
   invocation is **`8.609 s`**, plus negligible shell/process overhead.
8. The two measurements differ by `78 ms` (`0.90%`), consistent with the same
   command and input graph in this observation.

Stage 5A records this evidence but does not implement the removal.

## 14. Ranked bottlenecks

| Rank | Phase/action | Duration | Evidence quality | Stage 5B suitability |
| ---: | --- | ---: | --- | --- |
| 1 | pytest | `67.047 s` | high, internal monotonic | largest phase, but broad correctness and architecture risk |
| 2 | Set up pnpm | `38 s` action wall | high wall time, low attribution | needs dedicated setup analysis |
| 3 | Set up Node.js | `24 s` action wall | high wall time, cache state unknown | needs hit/miss evidence and controlled experiment |
| 4 | Vitest | `20.641 s` | high, internal monotonic | requires frontend test-performance analysis |
| 5 | Duplicate second typecheck | `8.609 s` | high, bounded semantic duplication | **selected low-risk candidate** |
| 6 | Python dependency install | `7.594 s` | high, internal monotonic | lower priority without cache experiment |
| 7 | Vite production build | `7.437 s` | high, internal monotonic | required production artifact work |

The largest measured phase is not automatically the best optimization candidate.
Removing or restructuring pytest/Vitest work can change coverage and maintenance
cost. Setup action walls are large but cannot be attributed to cache or one
suboperation. The duplicate typecheck has a smaller but directly measured,
bounded and low-risk opportunity.

## 15. Stage 5B decision

Selected primary candidate:

```text
duplicate TypeScript typecheck
```

Evidence:

- measured second invocation: `8.609 s`;
- frequency: every Fast CI run and local canonical non-Docker check;
- same `tsc --noEmit`, working directory, `tsconfig.json` and `src` input graph;
- no generated TypeScript input is introduced between invocations;
- bundle and copied assets have independent validations;
- lower behavioral risk than test architecture or cache redesign.

Stage 5B must preserve one full typecheck, Vitest, Vite, bundle validation, asset
copy, pytest and package checks. It requires a separate authorization and
before/after verification. No Stage 5B implementation is included here.

## 16. Artifacts

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
Diagnostics and exact-package artifacts remain separate.

## 17. Boundaries and caveats

Not performed in Stage 5A:

- no Fast CI optimization;
- no second manual cloud run or warm/cold pair;
- no Docker E2E;
- no release dispatch or production deployment;
- no runner/cache/checkout change;
- no Stage 5B implementation.

Remaining evidence limitations:

- this is one cloud observation, not an average or distribution;
- cache state remains `enabled-unknown`;
- no controlled warm/cold cache pair was performed;
- action wall durations are not pure cache overhead;
- the baseline runtime tested instrumentation commit `9746b1c…`, before the
  docs-only baseline and closure commits;
- the synthetic PR merge ref has not yet been tested at the time of this closure
  commit and belongs to the integration draft PR verification.
