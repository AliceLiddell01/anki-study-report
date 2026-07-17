# CI optimization baseline

## 1. Scope and snapshot date

Snapshot date: **2026-07-16**.

The audit branch was created from exact `origin/master` commit:

```text
ecdf2f59eb51841042d968be019de3185c613a36
```

The snapshot covers the three repository-owned workflow files present on that commit:

- `.github/workflows/ci-fast.yml`;
- `.github/workflows/ci-e2e.yml`;
- `.github/workflows/release.yml`.

GitHub-managed CodeQL checks appeared in recent pull-request evidence, but no repository-owned CodeQL workflow file exists in this snapshot, so CodeQL is not treated as an editable contour in this baseline.

The following repository sources were read and compared: `README.md`, `docs/ai-handoff.md`, `docs/ci-cd.md`, `docs/e2e-performance.md`, `docs/docker-e2e.md`, `docs/test-matrix.md`, `docs/verification-run-policy.md`, all three workflow files, `scripts/run_full_check.ps1`, `scripts/run_anki_e2e_docker.ps1`, `scripts/prepare_ci_e2e_artifacts.py`, `scripts/write_ci_fast_summary.ps1`, `docker/anki-e2e/Dockerfile`, `docker/anki-e2e/docker-compose.yml`, `docker/anki-e2e/run-e2e.sh`, and `web-dashboard/package.json`.

Contract tests were located by content and reviewed, including:

- `tests/test_ci_fast_workflow.py`;
- `tests/test_ci_e2e_artifacts.py`;
- `tests/test_e2e_performance.py`;
- `tests/test_full_check_e2e_options.py`;
- `tests/test_release_workflow.py`.

This stage changes no production workflow, script, runtime, frontend, test, dependency, or generated asset. The only tracked change is this document.

### Runs used

Fast CI:

- [29412331138](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29412331138);
- [29418214838](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29418214838);
- [29434970222](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29434970222).

PR release-path comparison:

- [29434970623](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29434970623), paired with Fast CI run `29434970222` on the same pull-request merge commit.

Recent targeted `standard/settings` E2E:

- [29412574154](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29412574154);
- [29418257033](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29418257033);
- [29435269199](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29435269199).

Controlled historical `standard/full` observations from the same performance stage:

- [29214180020](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29214180020);
- [29214315716](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29214315716);
- [29214593730](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29214593730).

Current expanded `standard/full` contour:

- [29412736595](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29412736595).

No new Actions run was dispatched for this audit.

## 2. Executive summary

- **Fast CI bottleneck:** the single `Run canonical fast pipeline` step. Its artifact-measured interval is **89.75–131.31 seconds** across the three recent successful runs. Within the parts exposed by tool output, pytest costs **36.34–57.89 seconds**, Vitest costs **16.91–24.42 seconds**, and Vite build costs **5.88–8.20 seconds**. Exact time for the two TypeScript checks, package operations, dependency installation, and post-job cache save is not currently persisted.
- **Docker E2E bottleneck depends on scope.** In recent targeted `settings` runs, BuildKit/cache/build/load costs **38.37–84.69 seconds**, while inner real-Anki canonical execution remains tightly grouped at **48.37–51.21 seconds**. In the current expanded full run, inner real-Anki execution is the dominant cost at **294.78 seconds**, driven mainly by telemetry restart proof (**140.75 seconds**) and browser capture (**117.85 seconds**); BuildKit costs **38.15 seconds** there.
- **Confirmed duplication:** every pull request to `master` runs both Fast CI and the PR-safe path of `release.yml`. Both install the same Python/frontend dependencies and call `run_full_check.ps1 -SkipDocker`; the release build then packages and validates the add-on again. The paired release build had a runner-start-to-artifact lower bound of about **167 seconds**, in addition to its validation job.
- **Confirmed E2E source rebuild:** ordinary E2E does not consume the Fast CI package. It repeats offline frontend install, frontend build, and package creation. This costs **20.97–21.50 seconds** in the three recent targeted runs and **21.40 seconds** in the current full run.
- **Cache conclusion is intentionally deferred:** the workflow records `gha-enabled`, not a real cache hit/miss state, and the measured Buildx action combines cache import, build, image load, and cache export. Existing evidence proves variance and critical-path cost, but does not prove that removing the cache is the correct solution.
- **Primary data gaps:** exact Fast CI setup/install/cache durations, E2E cache import versus export, current artifact upload duration, redaction/preparation step duration, and complete job `completed_at` values are not preserved in downloaded artifacts.

## 3. Current workflow map

| Workflow | Triggers | Runner/jobs | Timeout and concurrency | Cache | Artifacts | Canonical work and overlap |
| --- | --- | --- | --- | --- | --- | --- |
| Fast CI (`ci-fast.yml`) | `push` to `master`; PR to `master`; manual dispatch | One `windows-2025` job | 20 min; superseded runs for the same PR/ref are cancelled | `setup-python` pip cache; `setup-node` pnpm cache | `ci-fast-<run>-<attempt>`, 14 days | Calls `run_full_check.ps1 -SkipDocker`; overlaps almost completely with release PR build |
| Full Docker / Anki E2E (`ci-e2e.yml`) | reusable `workflow_call`; manual dispatch | One `ubuntu-24.04` job | 90 min; concurrent same ref/mode/scope/worker contour is cancelled | BuildKit `type=gha`, `mode=max`, zstd; one fixed scope | Public redacted E2E evidence, 7 days; Buildx record, observed 14 days | Calls Docker-only canonical contour after a separate Buildx build/load; ordinary runs rebuild frontend/package inside the container |
| Gated Release Delivery (`release.yml`) | PR to `master`; manual dispatch | Validation on Ubuntu; build on Windows; manual-only reusable E2E and publication jobs | 10/25/15/20/10 min by job; publish group is serialized and not cancelled | Build job repeats pip and pnpm caches; publisher also uses pnpm cache | Internal release bundle 2 days; publication reports 7 days; E2E artifact through reusable workflow | PR path repeats Fast CI canonical command; manual path additionally verifies exact artifact in full E2E and performs release gates |

### Trigger documentation drift

`docs/ci-cd.md` says Fast CI runs on pushes to `master` and `codex/**`. The actual `ci-fast.yml` snapshot only declares push to `master`. The current production workflow is the source of truth; this mismatch is a documentation/contract finding, not an optimization applied in this stage.

### Release duplication matrix

| Check or operation | Fast CI | Release on PR | Duplication |
| --- | --- | --- | --- |
| Full-history checkout | Yes | Yes, in validation and build jobs | Confirmed |
| Python setup with pip cache | Yes | Yes | Confirmed |
| pnpm/Node setup with pnpm cache | Yes | Yes | Confirmed |
| Python dependency install | Yes | Yes | Confirmed |
| Frontend dependency install | Yes | Yes | Confirmed |
| Repository hygiene | Through canonical script | Through canonical script | Confirmed |
| Generated changelog check | Through canonical script | Through canonical script | Confirmed |
| Frontend typecheck | Through canonical script | Through canonical script | Confirmed |
| Frontend tests | Through canonical script | Through canonical script | Confirmed |
| Frontend build/copy | Through canonical script | Through canonical script | Confirmed |
| Python tests | Through canonical script | Through canonical script | Confirmed |
| Add-on package build and validation | Through canonical script | Through canonical script | Confirmed |
| Second exact release package/fingerprint | No | Yes, after canonical script | Additional release-only repetition |
| Verification planner and Fast diagnostic summary | Yes | No | Fast-only |
| Release contract validation/bundle metadata | No | Yes | Release-only |

## 4. Measurement methodology

### Source priority

Measurements were accepted in this order:

1. structured JSON/Markdown reports inside artifacts;
2. timestamps in job logs;
3. GitHub job/run metadata exposed by the connector;
4. documented GitHub UI observations in `docs/e2e-performance.md`;
5. no inferred zeroes for missing phases.

`null`, `unknown`, or an explicit lower bound is used when the source does not preserve a duration.

### Time definitions

- **Fast canonical interval:** `startedAt` to `finishedAt` in `ci-summary.json`. It begins after the workflow has prepared diagnostics and dependencies and ends while writing the summary; it is not the whole job wall.
- **E2E preflight-to-preparation interval:** `workflowDurationSeconds`/`durationSeconds` in `ci-e2e-summary.json`. It starts at runner preflight and ends after public artifact preparation, before upload reporting and final cleanup. It is not the complete job wall.
- **Inner real-Anki canonical wall:** phase `total canonical E2E` from `e2e-phase-timings.json`.
- **Build/cache/load wall:** timer around the complete `docker/build-push-action` step with `load: true`, `cache-from`, and `cache-to`. It is an aggregate, not a split measurement.
- **Runner-start-to-artifact lower bound:** first timestamp in the decoded job log to artifact `created_at`. It excludes any work after artifact creation and therefore cannot be presented as full job wall.
- **Historical GitHub workflow wall:** UI values already recorded in `docs/e2e-performance.md`; these are used only for the controlled historical full runs.

Wall time, summed runner execution, billable minutes, cache/artifact storage, and user wait are different quantities. This document does not infer billing from wall time and does not treat public-repository billing policy as an engineering performance metric.

### Comparison rules

- `settings` is not compared as equal to `full`.
- The current full run is not merged into the controlled Stage 6.6 full triplet because the screenshot/telemetry contour changed materially.
- `standard` is kept separate from `strict-apkg` and `perf100`.
- `cacheState=gha-enabled` means the backend was enabled; it does not prove a cache hit.
- Package and artifact byte sizes are exact metadata values; displayed MB values are rounded decimal MB.
- Variance is reported as a range, with a representative value only where the contour is sufficiently comparable.

### External behavior verified

GitHub's official Actions documentation was used for run history/log semantics, job duration/timestamps, workflow artifacts, and the workflow-runs/jobs REST surfaces. No third-party CI blog was used as a source of truth.

## 5. Fast CI baseline

### Comparable successful runs

All three runs are pull-request runs on `windows-2025-vs2026` image version `20260628.158.1` and concluded successfully.

| Metric | Run 29412331138 | Run 29418214838 | Run 29434970222 | Typical/range | Source |
| --- | ---: | ---: | ---: | ---: | --- |
| Tested PR merge SHA | `1b82321f…` | `a73cc75b…` | `0d34b26e…` | n/a | `ci-summary.json` |
| Head branch SHA | `bed35056…` | `e964249d…` | `811baaf0…` | n/a | artifact metadata |
| Canonical interval | 131.31 s | 89.75 s | 90.17 s | median 90.17 s; 89.75–131.31 s | `ci-summary.json` |
| Vitest reported duration | 24.42 s | 16.91 s | 17.41 s | median 17.41 s | `fast-check.log` |
| Vite build | 8.20 s | 5.88 s | 6.02 s | median 6.02 s | `fast-check.log` |
| pytest | 57.89 s | 36.34 s | 36.63 s | median 36.63 s | `fast-check.log` |
| Runner start to artifact creation | ≥205.86 s | ≥197.81 s | ≥160.38 s | lower-bound range 160.38–205.86 s | job log + artifact metadata |
| Diagnostic ZIP | 581,158 B | 581,757 B | 585,985 B | 0.581–0.586 MB | artifact metadata |
| Embedded `.ankiaddon` | 576,434 B | 577,876 B | 582,365 B | 0.576–0.582 MB | ZIP inventory |
| Complete job wall | unknown | unknown | unknown | unavailable | connector response lacks timestamps and artifact ends before post-job cleanup |

### Most complete phase view: run 29434970222

| Phase | Duration | Precision/source | Notes |
| --- | ---: | --- | --- |
| Runner setup and action download | unknown as a standalone phase | job log timestamps available, but checkout begins immediately after action preparation | Not persisted as structured phase |
| Checkout | unknown as one clean duration | job log | Full-history fetch; no normalized step timing in connector output |
| Python/pnpm/Node setup and cache restore | unknown | job log only | Hit/miss and restore duration are not persisted in Fast artifact |
| Dependency installation | unknown | workflow/log | Python and frontend installs happen before `ci-summary.startedAt` |
| Canonical Fast pipeline | 90.17 s | exact summary timestamps | Critical single workflow step |
| Vitest inside canonical | 17.41 s | tool-reported | Includes test runner transform/setup/collection accounting |
| Vite build inside canonical | 6.02 s | tool-reported | One of the build steps |
| pytest inside canonical | 36.63 s | tool-reported | Largest exposed internal phase |
| Two TypeScript typechecks | unknown | structural code evidence | `test:frontend` and `build:addon` each invoke typecheck |
| Package build/check/check-only | unknown | structural code evidence | Included in the remaining canonical interval |
| Verification planner | unknown | workflow/log | After canonical pipeline |
| Diagnostics/package collection and summary | unknown | workflow/log | Ends at `ci-summary.finishedAt` |
| Artifact upload and post-job cache save | unknown | workflow metadata only | Occur after summary; exact duration unavailable |

The exposed Vitest, Vite, and pytest durations sum to **60.06 seconds** in run `29434970222`. The remaining **30.11 seconds** of its canonical interval contains the two TypeScript checks, changelog/hygiene work, package build and two validations, copying, process startup, and orchestration. It is not valid to assign all residual time to one component.

## 6. Docker E2E baseline

### 6.1 Recent targeted `standard/settings`

These runs use the same scope and mode. They intentionally skip restart under the targeted-scope policy.

| Metric | Run 29412574154 | Run 29418257033 | Run 29435269199 | Range/representative | Source |
| --- | ---: | ---: | ---: | ---: | --- |
| Preflight to public artifact preparation | 110 s | 100 s | 140 s | 100–140 s; median 110 s | `ci-e2e-summary.json` |
| Build/cache/load/export aggregate | 50.03 s | 38.37 s | 84.69 s | 38.37–84.69 s; median 50.03 s | Buildx timer |
| Inner real-Anki canonical wall | 48.37 s | 51.21 s | 48.65 s | 48.37–51.21 s; median 48.65 s | phase timings |
| Product rebuild inside E2E | 20.97 s | 21.50 s | 21.34 s | 20.97–21.50 s; median 21.34 s | summed phase timings |
| Browser capture | 18.74 s | 21.29 s | 20.19 s | 18.74–21.29 s | phase timings |
| Public E2E ZIP | 6.90 MB | 8.34 MB | 9.06 MB | 6.90–9.06 MB | artifact metadata |
| Public archive entries | 57 | 63 | 60 | 57–63 | ZIP inventory |
| Upload duration | unknown | unknown | unknown | unavailable in artifact | only written to Step Summary after upload |

The stable ~21-second product rebuild consists of workspace copy, offline pnpm install from the image store, `build:addon`, and add-on package creation. BuildKit variance, not inner real-Anki variance, explains most of the targeted total spread.

### 6.2 Controlled historical `standard/full` triplet

These runs are retained because they were deliberately collected as a comparable performance set during the same stage. The first two use the same exact SHA; the final exact-SHA proof removes the temporary bootstrap trigger. They represent the earlier full surface and must not be equated with the current telemetry-expanded full contour.

| Metric | Run 29214180020 | Run 29214315716 | Run 29214593730 | Range | Source |
| --- | ---: | ---: | ---: | ---: | --- |
| Preflight to artifact preparation | 205 s | 190 s | 162 s | 162–205 s | summary artifact |
| GitHub workflow wall | 231 s | 209 s | 184 s | 184–231 s | `docs/e2e-performance.md` UI observations |
| Build/cache/load/export aggregate | 87.70 s | 99.49 s | 48.14 s | 48.14–99.49 s | Buildx timer |
| Inner real-Anki canonical wall | 106.20 s | 81.12 s | 94.14 s | 81.12–106.20 s | `total canonical E2E` phase |
| Product rebuild inside E2E | 18.28 s | 12.86 s | 15.10 s | 12.86–18.28 s | summed phase timings |
| Browser capture phase | 73.33 s | 59.52 s | 66.18 s | 59.52–73.33 s | phase timings |
| Public E2E ZIP | 27.89 MB | 27.91 MB | 24.46 MB | 24.46–27.91 MB | artifact metadata |
| Upload duration | ~2 s | ~2 s | not separately recorded | historical observation only | `docs/e2e-performance.md` |

`cacheState` is `gha-enabled` for all three; it does not identify which layers were hits or how much time was spent importing versus exporting. Therefore the labels historically used for first/warm observations are not treated as measured cache-hit facts in this document.

### 6.3 Current expanded `standard/full`: run 29412736595

Run metadata:

- head SHA: `bed35056e8f1fa78f9a32863d8e77084af957ddd`;
- event: manual workflow dispatch;
- runner: Ubuntu 24.04, image `20260714.240.1`;
- scope/mode: `full` / `standard`;
- screenshot workers: `auto` resolved to 3;
- resource telemetry input: false;
- restart policy: auto, therefore enabled for full;
- result: success;
- artifact: `ci-e2e-standard-29412736595-1`, **37,827,664 bytes**;
- Buildx record: **31,215 bytes**.

| Phase | Duration | Share of inner canonical | Source |
| --- | ---: | ---: | --- |
| Runner preflight to public artifact preparation | 351.00 s | n/a | `ci-e2e-summary.json` |
| Build/cache/load/export aggregate | 38.15 s | outside inner canonical | Buildx timer |
| Inner real-Anki canonical wall | 294.78 s | 100% | phase timings |
| Telemetry restart persistence and deletion | 140.75 s | 47.7% | phase timings |
| Browser serial and parallel capture | 117.85 s | 40.0% | phase timings |
| Product rebuild inside E2E | 21.40 s | 7.3% | summed phase timings |
| Workspace copy | 0.09 s | <0.1% | phase timings |
| Offline frontend dependency install | 5.33 s | 1.8% | phase timings |
| Frontend build | 15.82 s | 5.4% | phase timings |
| Add-on package | 0.16 s | <0.1% | phase timings |
| Runner start to artifact creation | ≥355.31 s | n/a | job log + artifact metadata |
| Artifact upload | unknown | n/a | not persisted in public artifact |
| Complete job wall | unknown | n/a | post-upload cleanup/action finalization not exposed as timestamped job metadata |

For the current full contour, removing or tuning BuildKit alone cannot address the majority of elapsed time. The two largest inner phases account for about **87.7%** of inner canonical wall.

### 6.4 Docker phase ownership

| Phase | Workflow or container owner | Current observability |
| --- | --- | --- |
| Checkout/preflight/containerd restart/Buildx setup | GitHub workflow | Log timestamps only; not exported as structured durations |
| Cache import/build/image load/cache export | `docker/build-push-action` | One aggregate duration; no split |
| Workspace copy | `run-e2e.sh` | Structured phase |
| Offline frontend install | `run-e2e.sh` | Structured phase |
| Frontend build | `run-e2e.sh` | Structured phase |
| `.ankiaddon` package build/validation | `run-e2e.sh` | Structured phase |
| Fixture/profile preparation | `run-e2e.sh` | Structured phase |
| Anki starts/readiness/API/browser/restart | `run-e2e.sh` | Structured phases |
| Manifest generation/validation | container cleanup trap | Structured phase |
| Public redaction/export | `prepare_ci_e2e_artifacts.py` workflow step | No separately persisted step duration |
| Artifact upload | `upload-artifact` | Duration only in GitHub Step Summary, not inside downloaded artifact |
| Docker cleanup and post actions | workflow | Logs only |

## 7. Duplicate work inventory

### Fast CI versus release PR path

This is the largest confirmed cross-workflow duplication. A pull request to `master` triggers both workflows independently. They do not share a tested result, dependency installation, or package artifact.

For the paired exact PR merge commit:

- Fast CI run `29434970222`: canonical interval **90.17 seconds**; runner start to diagnostic artifact **at least 160.38 seconds**.
- Release run `29434970623`: separate validation job plus build job; build job runner start to release artifact **at least 167.01 seconds**.
- Release production jobs were correctly skipped on the PR, but the duplicated canonical verification and second packaging still ran.

The exact end-to-end PR delay cannot be calculated from artifact timestamps alone because complete job/run completion timestamps are missing. The duplicated runner work is nevertheless structurally and operationally confirmed.

### Repeated typecheck inside one canonical pipeline

`web-dashboard/package.json` defines:

```text
test:frontend -> typecheck + Vitest
build:addon   -> build -> typecheck + Vite build + bundle check
```

`run_full_check.ps1` invokes both. Therefore TypeScript typecheck executes twice in each Fast CI canonical run and twice again in the duplicated release PR canonical run.

### Fast package versus ordinary E2E source rebuild

Fast CI creates a non-release `.ankiaddon` and uploads it. Ordinary source-driven E2E does not download or validate that package; it mounts source code and runs frontend install/build/package again inside Docker. The current repeated cost is about **21.3 seconds per E2E run**.

The release manual path is intentionally different: it passes the exact prebuilt release artifact into reusable E2E and verifies its fingerprint. That exact-artifact security contract must not be weakened by a future optimization.

### Repeated packaging

- Fast canonical: package `--check`, then package `--check-only`.
- Release PR canonical: same operations through `run_full_check.ps1`.
- Release bundle step: package `--check`, package `--check-only`, then release bundle generation.
- Ordinary E2E: another package `--check` from source.

Some checks are deliberate validation layers. The baseline only records repetition; it does not decide which validation is redundant.

### Cache transfer/export

`cache-to: type=gha,mode=max` is enabled on every ordinary E2E build action. Its export is part of the same critical-path step as import/build/load. The existing summary cannot assign a separate export cost, so no defensible savings estimate can yet be attached to removing it.

### Artifact overlap

- Fast artifact and release bundle both contain an add-on package built from the same PR commit, but byte identity was not compared in this audit.
- E2E evidence also includes an `.ankiaddon`, plus screenshots/logs/reports.
- A separate Docker build record artifact is created for each E2E run.

## 8. Artifact and cache inventory

### Caches

| Contour | Backend/keying | Save behavior | Measured state | Gap |
| --- | --- | --- | --- | --- |
| Fast Python | `setup-python` pip cache keyed by `requirements-dev.txt` | action-managed restore/save | enabled | Hit state and restore/save duration not in Fast artifact |
| Fast frontend | `setup-node` pnpm cache keyed by lockfile | action-managed restore/save | enabled | Hit state and restore/save duration not in Fast artifact |
| Release build | same pip and pnpm mechanisms as Fast | action-managed | enabled | Duplicates dependency setup on PR |
| E2E image | BuildKit GHA cache, fixed scope, `mode=max`, zstd compression level 0 | `cache-to` on every run | only `gha-enabled` | No hit/miss, imported bytes, exported bytes, import duration, or export duration |
| E2E pnpm store | Docker image layer populated by `pnpm fetch` | reused only through image/layer cache | indirectly covered by BuildKit | Layer-level contribution not persisted |

### Artifacts

| Producer | Name | Retention | Observed compressed size | Main contents |
| --- | --- | ---: | ---: | --- |
| Fast CI | `ci-fast-<run>-<attempt>` | 14 days | 0.581–0.586 MB | summary, environment, canonical log, verification plan, non-release `.ankiaddon` |
| E2E public evidence | `ci-e2e-<mode>-<run>-<attempt>` | 7 days | settings 6.90–9.06 MB; controlled full 24.46–27.91 MB; current full 37.83 MB | redacted runtime evidence, diagnostics, JSON/Markdown reports, HTML, screenshots, `.ankiaddon` |
| E2E Buildx | automatic `*.dockerbuild` | observed 14 days | 27.7–32.4 KB | Docker build record |
| Release PR/manual build | `release-bundle-<run>-<attempt>` | 2 days | 0.585 MB in paired run | exact `.ankiaddon`, release manifest and public release inputs |
| Release publication jobs | per-job sanitized report names | 7 days | not sampled | draft/publisher/finalization reports |

Public E2E export has a strict allowlist, token/path redaction, manifest validation, and secret-like text rejection. Optimization of artifact preparation must preserve those safety properties.

## 9. Confirmed findings

### Finding 1 — PR release workflow duplicates Fast CI

**Evidence:** both `ci-fast.yml` and the PR build job in `release.yml` independently set up runtimes/caches, install dependencies, and invoke `run_full_check.ps1 -SkipDocker`. Paired runs `29434970222` and `29434970623` executed on the same PR merge SHA.
**Impact:** duplicated Windows runner execution, dependency/cache traffic, tests, frontend build, Python tests, packaging, and additional PR wait.
**Confidence:** high.
**Potential next-stage experiment:** redesign the PR-safe release contour to consume or depend on the exact Fast CI result while preserving independent manual release build and exact-artifact gates; compare runner wall and required-check behavior on one authorized PR.

### Finding 2 — canonical frontend typecheck runs twice

**Evidence:** `test:frontend` invokes typecheck and `build:addon` invokes `build`, which invokes typecheck again; both scripts run in the canonical pipeline.
**Impact:** repeated TypeScript compilation in every Fast CI and release PR canonical run. Exact seconds are unknown because typecheck output is not timestamped.
**Confidence:** high.
**Potential next-stage experiment:** add lightweight command timing or restructure only the aggregate canonical invocation so standalone scripts keep their safety; measure one exact-SHA run before deciding.

### Finding 3 — ordinary E2E repeats product build and packaging

**Evidence:** `run-e2e.sh` performs offline install, `build:addon`, and package creation when no prebuilt release artifact is supplied. Recent targeted runs measure **20.97–21.50 seconds**; current full measures **21.40 seconds**.
**Impact:** a stable ~21-second fixed cost per ordinary E2E run, plus duplicated package content.
**Confidence:** high.
**Potential next-stage experiment:** test an exact-SHA package handoff from Fast CI to non-release E2E while retaining source-driven fallback and the stricter manual-release fingerprint contract.

### Finding 4 — BuildKit cost is variable and insufficiently decomposed

**Evidence:** build/cache/load/export aggregate ranges **38.37–84.69 seconds** in recent targeted runs and **48.14–99.49 seconds** in the controlled historical full triplet. All summaries only report `gha-enabled`.
**Impact:** material variance and critical-path time, but no evidence assigning cost to cache import, actual build, load, or export.
**Confidence:** high for the variance/observability finding; low for any proposed cache policy.
**Potential next-stage experiment:** first persist Buildx cache hit information and split import/build/load/export timings; only then run a narrowly authorized cache-policy comparison.

### Finding 5 — current full E2E is dominated by inner lifecycle, not BuildKit

**Evidence:** run `29412736595` has **294.78 seconds** inner canonical wall versus **38.15 seconds** BuildKit aggregate. Telemetry restart proof and browser capture consume **258.59 seconds** combined.
**Impact:** a Docker-cache-only optimization would leave most current full wall untouched.
**Confidence:** high for this run and current contour; broader stability requires more current full samples.
**Potential next-stage experiment:** collect one or two future naturally required full runs with the same telemetry/screenshot contract and compare phase stability before considering scope/risk-based lifecycle separation.

### Finding 6 — Fast CI critical path is under-instrumented

**Evidence:** the structured artifact exposes only the aggregate canonical interval. Dependency setup, two typechecks, package phases, artifact upload, and post-job cache save lack structured durations.
**Impact:** the aggregate range is known, but the best intra-Fast optimization cannot yet be ranked confidently.
**Confidence:** high.
**Potential next-stage experiment:** add non-invasive phase timing to the canonical script or summary without changing test behavior.

### Finding 7 — workflow/document trigger contract has drifted

**Evidence:** current `ci-fast.yml` pushes only on `master`, while `docs/ci-cd.md` still says `master` and `codex/**`.
**Impact:** operators and future agents may infer duplicate feature-branch runs that no longer exist or plan around an obsolete trigger.
**Confidence:** high.
**Potential next-stage experiment:** decide whether code or documentation represents intended policy, then correct only the stale side in a separate scoped change.

## 10. Unknowns and measurement gaps

1. **Fast setup/install/cache split:** no exact durations for checkout, setup Python, setup pnpm, setup Node, pip restore/save, pnpm restore/save, Python install, or frontend install.
2. **Fast typecheck/package split:** no command timestamps for either typecheck or package `--check`/`--check-only`.
3. **Complete Fast job wall:** connector job responses expose step state but not `started_at`/`completed_at`; artifacts are created before post-job actions complete.
4. **Release workflow end-to-end wall:** paired build lower bound is known, but validation/build dependency wait and final completion are not reconstructed exactly.
5. **BuildKit decomposition:** cache import, cache export, actual layer build, image load, and Buildx setup are not separately measured.
6. **Cache efficacy:** `gha-enabled` is not a hit/miss state. No defensible byte-transfer or avoided-build calculation is available.
7. **Current full variance:** only one fully comparable run exists after the telemetry/screenshot expansion; historical full runs are not equivalent.
8. **Redaction/preparation duration:** `prepare_ci_e2e_artifacts.py` duration is not persisted as a structured metric.
9. **Current artifact upload duration:** only the GitHub Step Summary receives it after upload; the downloaded artifact intentionally contains `null`.
10. **Artifact storage accumulation:** sampled artifact sizes and retention are known, but repository-wide active storage at the snapshot date was not enumerated.
11. **Package byte identity across contours:** package presence is confirmed; exact cross-artifact hash equality was not required and not measured.
12. **Billable minutes:** not analyzed. Engineering delay and runner consumption are reported independently of account billing treatment.

Minimal future measurement needed before changing cache policy:

- Buildx import/build/load/export split;
- actual cache hit/miss and transferred bytes;
- two otherwise comparable naturally required runs, with explicit permission if an extra run would be needed.

No expensive run should be created solely to fill these gaps without a separate user decision.

## 11. Baseline table for subsequent stages

| Contour | Current range | Representative value | Main cost center | Confidence |
| --- | ---: | ---: | --- | --- |
| Fast CI canonical interval | 89.75–131.31 s | 90.17 s median | Canonical pipeline; pytest is largest exposed internal phase | High for aggregate, medium for internal attribution |
| Fast runner start to artifact | ≥160.38–205.86 s | lower bound only | Setup/install + canonical + diagnostics/upload start | Medium |
| Targeted `standard/settings` E2E to preparation | 100–140 s | 110 s median | Build/cache/load variance plus ~49 s inner contour | High |
| Targeted inner real-Anki | 48.37–51.21 s | 48.65 s median | Product rebuild and browser capture | High |
| Controlled historical full workflow wall | 184–231 s | 209 s middle observation | Build/cache/load plus 81–106 s inner contour | High for historical contour |
| Current expanded full to preparation | 351 s | 351 s | Inner telemetry restart and browser capture | High for one run; low for variance |
| Current expanded full inner real-Anki | 294.78 s | 294.78 s | Telemetry restart proof + browser capture | High for one run |
| Build/cache/load/export aggregate | 38.15–99.49 s across sampled standard runs | ~50 s recent targeted median | Undecomposed Buildx action | Medium |
| Product rebuild inside current E2E | 20.97–21.50 s targeted; 21.40 s full | 21.34 s targeted median | Offline install + frontend build | High |
| Artifact preparation/upload | preparation unknown; historical upload ~2 s | unknown | Redaction/export and upload | Low |

## 12. Acceptance decision for Stage 1

### Is the baseline sufficient?

**Yes, for a narrowly scoped Stage 1 addressing PR-level duplication between Fast CI and `release.yml`.** The duplication is proven structurally and by paired successful runs on the same PR merge commit. It occurs on every PR to `master`, and removing it from the PR path can be designed without changing the manual production release exact-artifact chain.

The baseline is **not sufficient to choose a Docker cache policy**. BuildKit is expensive and variable, but current telemetry cannot distinguish import, build, load, and export or identify real hit/miss state. Removing `cache-to` now would be a guess rather than an evidence-based optimization.

### Data the user should review before Stage 1

- Whether `Gated Release Delivery` must remain a separate required PR check by name, or may become a lightweight release-contract-only check dependent on Fast CI.
- Whether branch protection currently requires both Fast CI and the release workflow's build job.
- Whether the intended Fast push policy is only `master` or also `codex/**`, because documentation and workflow differ.

### Recommended next stage

Prepare Stage 1 around **eliminating the duplicate canonical non-Docker verification from the PR path of `release.yml` while preserving release-contract validation, exact manual release build, reusable full real-Anki gate, artifact fingerprinting, protected AnkiWeb publication, and GitHub Release finalization**.

Cache redesign, E2E lifecycle splitting, and artifact-retention changes should remain separate later stages with their own evidence and acceptance criteria.
