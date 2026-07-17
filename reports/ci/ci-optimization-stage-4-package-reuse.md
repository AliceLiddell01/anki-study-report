# CI optimization Stage 4: Fast package reuse measurement

## 1. Scope and snapshot

Дата измерения: **2026-07-16**.

Repository:

```text
AliceLiddell01/anki-study-report
```

Base и measurement SHA:

```text
8d87c40b4ba397b2840212122637d67adeb0e6d7
```

Measurement branch:

```text
chatgpt/ci-optimization-stage-4-package-reuse-measurement
```

До cloud runs ветка была идентична `master`: ahead `0`, behind `0`, commits `0`.
Production code, workflows, scripts, Docker image contract и tests в Stage 4 не
менялись.

Stage 4 сравнивает ровно один `standard/settings` run на каждый package source:

```text
fast-ci-artifact
source-build
```

Порядок был фиксирован: artifact mode первым, source build вторым. Не
выполнялись `full`, `strict-apkg`, `perf100`, resource telemetry, restart proof,
warm-cache repeats или дополнительные повторы.

GitHub различает workflow run, job и steps. REST Jobs API публикует
`started_at`/`completed_at` для job и steps, поэтому workflow elapsed, queue wait
и job execution ниже считаются отдельно:

- <https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2022-11-28>
- <https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2022-11-28>

Значения из округлённого UI не использовались, когда были доступны structured
timestamps или reports.

## 2. Inputs and run IDs

| Role | Workflow | Run ID | Event | SHA | Result |
| --- | --- | ---: | --- | --- | --- |
| Exact producer | Fast CI | [29492253514](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29492253514) | `push` on `master` | `8d87c40b…` | success |
| Run A | Full Docker / Anki E2E | [29494116783](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29494116783) | `workflow_dispatch` | `8d87c40b…` | success |
| Run B | Full Docker / Anki E2E | [29495144612](https://github.com/AliceLiddell01/anki-study-report/actions/runs/29495144612) | `workflow_dispatch` | `8d87c40b…` | success |

Fast producer использован повторно; новый Fast CI для Stage 4 не запускался.

Run A inputs:

```text
mode=standard
scope=settings
screenshot_workers=auto → 3
resource_telemetry=false
verify_restart=false
fast_ci_run_id=29492253514
```

Run B inputs отличались только отсутствующим `fast_ci_run_id`, что выбирало
`source-build`.

Exact Fast package:

```text
artifact:
ci-package-8d87c40b4ba397b2840212122637d67adeb0e6d7-29492253514-1

package SHA-256:
7e86d0df87e0aa2abe7521be3fcb31b149c97490fa0e1073a8b7c5d149c9c690

package size:
582365 bytes
```

Producer metadata связало `testedCommitSha`, `sourceHeadSha`, run ID, artifact
name, internal package SHA-256 и size с exact measurement SHA.

## 3. Comparability checklist

| Property | Artifact mode | Source build | Match |
| --- | --- | --- | --- |
| Repository SHA | `8d87c40b…` | `8d87c40b…` | yes |
| Branch/ref | Stage 4 branch | Stage 4 branch | yes |
| Workflow path | `.github/workflows/ci-e2e.yml` | same | yes |
| Workflow blob SHA | `9cccb8dd…` | `9cccb8dd…` | yes |
| Mode | `standard` | `standard` | yes |
| Scope | `settings` | `settings` | yes |
| Screenshot workers | `3` | `3` | yes |
| Resource telemetry | false | false | yes |
| Restart | false | false | yes |
| Anki version | `26.05` | `26.05` | yes |
| Runner label | `ubuntu-24.04` | `ubuntu-24.04` | yes |
| Runner image version | `20260714.240.1` | `20260705.232.1` | **no** |
| Dockerfile Git blob | `2edce63f…` | `2edce63f…` | yes |
| Built image size | `1501807210 B` | `1501807210 B` | yes |
| Image manifest/config | same | same | yes |
| Screenshot count | `23` | `23` | yes |
| Screenshot path set/dimensions | 23 expected paths | same 23 paths | yes |
| Functional conclusion | success | success | yes |

Это paired exact-SHA comparison с одинаковым project/workflow contour, но не
полностью controlled infrastructure experiment: GitHub назначил разные
`ubuntu-24.04` image versions. Поэтому:

- structured inner product phases имеют **high confidence**;
- total job/workflow delta имеет **medium confidence**;
- Docker delta не приписывается package source.

## 4. Functional equivalence

Functional equivalence: **PASS** для targeted `standard/settings`.

Оба run подтвердили:

- `artifactManifestStatus=success`;
- одинаковые 23 screenshot paths и dimensions;
- 12 page screenshots, product-notice/localization states и один 125% proof;
- `consoleErrors=[]`;
- `requestFailures=[]`;
- API/browser/settings contour без functional failure;
- Anki `26.05`;
- один и тот же source commit;
- один и тот же installed add-on manifest contract.

Run A дополнительно подтвердил:

- `packageSource=fast-ci-artifact`;
- source run `29492253514`;
- tested/workflow/checkout SHA = measurement SHA;
- exact package SHA-256 совпал до и после real-Anki E2E;
- `fast-ci-handoff.json` опубликован;
- source frontend install/build/package phases имеют status `absent`;
- exact prebuilt validation/extraction имеет status `success`.

Run B подтвердил:

- `packageSource=source-build`;
- Fast handoff steps получили `skipped`;
- offline dependency install, frontend build и add-on package были выполнены;
- тот же real-Anki/settings/browser contour завершился успешно.

Packages между режимами намеренно не byte-identical: Fast package собран на
Windows, source package — внутри Linux E2E. Их 53-file inventory совпадает;
различия почти полностью сводятся к CRLF/LF, а generated `index.html` имеет ещё
одну пустую строку. `manifest.json` и bundled asset names совпадают. Stage 4
сравнивает способы подготовки package, а не заявляет cross-OS reproducible ZIP.

Визуальный просмотр contact sheets не выявил пустых, обрезанных или явно
сломанных settings screenshots.

## 5. Top-level timing table

| Metric | Artifact mode | Source build | Source − artifact |
| --- | ---: | ---: | ---: |
| `workflowCreatedAt` | `11:21:19Z` | `11:38:13Z` | n/a |
| `workflowCompletedAt` | `11:23:12Z` | `11:40:33Z` | n/a |
| `jobStartedAt` | `11:21:25Z` | `11:38:17Z` | n/a |
| `jobCompletedAt` | `11:23:11Z` | `11:40:33Z` | n/a |
| Queue wait | 6000 ms | 4000 ms | -2000 ms |
| Workflow elapsed | 113000 ms | 140000 ms | **27000 ms** |
| Job execution | 106000 ms | 136000 ms | **30000 ms** |
| Summary preflight→preparation interval | 92000 ms | 119000 ms | **27000 ms** |
| Docker build/cache/load | 39035 ms | 48560 ms | 9525 ms |
| Inner canonical E2E | 28824 ms | 51969 ms | 23145 ms |

`observedJobDeltaMs = 30000 ms`.

Это наблюдаемая разница, а не чистый causal effect. Она включает runner image,
BuildKit restore/unpack/export и обычную lifecycle variance.

Fast producer для контекста:

| Metric | Value |
| --- | ---: |
| Queue wait | 3000 ms |
| Job execution | 161000 ms |
| Workflow elapsed | 165000 ms |
| Structured canonical interval | 88342 ms |

## 6. Step breakdown

Jobs API timestamps имеют секундную granularity. Значения меньше секунды
отображаются как `<1 s`, а не как `0 ms`.

### Common startup

| Step group | Artifact mode | Source build |
| --- | ---: | ---: |
| Initial checkout | ~1 s | ~1 s |
| Source input validation | ~5 s | ~6 s |
| Runner/Docker preflight | ~7 s | ~7 s |
| Compose validation | ~1 s | ~1 s |
| Containerd restart | ~1 s | ~1 s |
| Buildx setup | ~1 s | ~1 s |
| Build timer setup | ~1 s | ~1 s |

### Artifact-only preparation

Run A steps from source-run resolution through package validation/staging took
approximately **8 s** by Jobs API timestamps. Because step timestamps are
second-rounded, this is reported as a **7–9 s range**, not fake millisecond
precision.

Included:

- source-run and artifact-ID resolution;
- diagnostics download and validation;
- exact tested commit checkout and verification;
- package download;
- metadata/hash/size validation and staging.

### Docker preparation

| Phase | Artifact mode | Source build |
| --- | ---: | ---: |
| Build/cache/load aggregate | 39035 ms | 48560 ms |
| Built image size | 1501807210 B | 1501807210 B |
| Explicit `CACHED` build steps in log | 6 | 9 |
| Cache manifest import | performed | performed |
| Cache export | performed | performed |

### Inner E2E

| Phase | Artifact mode | Source build |
| --- | ---: | ---: |
| Workspace copy | 96 ms | 97 ms |
| Frontend dependency install | absent | 4926 ms |
| Frontend build | absent | 16634 ms |
| Add-on package/validation | absent | 165 ms |
| Exact prebuilt validation/extraction | 140 ms | absent |
| Fixture/profile preparation | 916 ms | 932 ms |
| First Anki start | 2301 ms | 2512 ms |
| Readiness wait | 2099 ms | 2107 ms |
| API smoke | 149 ms | 164 ms |
| Browser serial/parallel capture | 20661 ms | 22437 ms |
| Manifest generation/validation | 72 ms | 74 ms |
| Total canonical E2E | 28824 ms | 51969 ms |

Run A parallel screenshot capture:

```text
12 tasks
3 workers
5676 ms capture wall
2.85× speedup
95.0% efficiency
0 failures
```

Run B:

```text
12 tasks
3 workers
5810 ms capture wall
2.49× speedup
83.1% efficiency
0 failures
```

### Finalization

Оба run потратили примерно 6 секунд от завершения canonical E2E до job post
cleanup. Artifact mode дополнительно проверил tested package SHA и скопировал
sanitized handoff evidence; source build корректно отметил эти steps как
`skipped`. E2E artifact upload занял около 1 секунды по Jobs API.

## 7. Product preparation comparison

Structured source preparation:

```text
sourceProductPreparationMs
= dependency install
+ frontend build
+ add-on package/validation
= 4926 + 16634 + 165
= 21725 ms
```

Inner saving after retaining prebuilt validation:

```text
innerProductPreparationSavedMs
= sourceProductPreparationMs
- prebuiltValidationExtractionMs
= 21725 - 140
= 21585 ms
```

Artifact handoff overhead:

```text
artifactHandoffPreparationMs ≈ 7000–9000 ms
```

Net preparation improvement:

```text
netPreparationDeltaMs
= sourceProductPreparationMs
- artifactHandoffPreparationMs
- prebuiltValidationExtractionMs
≈ 12585–14585 ms
```

Best central estimate:

```text
≈ 13585 ms
```

Confidence:

- product phases: **high**, direct structured telemetry;
- prebuilt validation: **high**, direct structured telemetry;
- handoff aggregate: **medium**, Jobs API second granularity;
- net range: **medium-high**;
- observed 30 s job delta: **medium**, because Docker/runner variance contributes.

Fast package reuse therefore removed the stable ~21.7 s inner product rebuild,
but cross-run resolution/download/exact checkout consumed about 7–9 s. The
defensible direct benefit is approximately **12.6–14.6 s per targeted E2E run**,
not the full observed 30 s job difference.

## 8. Cache variance

Both summaries say `cacheState=gha-enabled`. This means the GHA backend was
configured; it is not itself a hit/miss proof.

Official GitHub cache documentation distinguishes exact and partial restore:
when no exact match exists, the most recent partial restore-key match may be
used. Consequently cache-enabled runs are not automatically equivalent:

<https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching>

Observed Buildx evidence:

- both runs imported a GHA cache manifest;
- artifact mode logged 6 explicit cached Dockerfile steps;
- source build logged 9;
- both produced the same image manifest/config and image size;
- artifact mode Build/cache/load: 39.035 s;
- source build Build/cache/load: 48.560 s;
- source build spent 42.6 s unpacking the image into Docker;
- artifact mode reported 0.0 s for the equivalent unpack;
- runner image versions differed.

The source run had more explicit cached steps but a slower aggregate. This is
strong evidence that transfer/unpack/export and runner variance dominate the
difference; it is not evidence that package source changed Docker build time.

Historical ranges:

| Evidence | Build/cache/load | Inner canonical |
| --- | ---: | ---: |
| Stage 0 recent targeted source-build range | 38.37–84.69 s | 48.37–51.21 s |
| Historical source run `29435269199` | 84.691 s | 48.649 s |
| Stage 3 artifact run `29488238700` | 40.790 s | 28.183 s |
| Stage 4 artifact run | 39.035 s | 28.824 s |
| Stage 4 source run | 48.560 s | 51.969 s |

Stage 4 source/product phase timings remain consistent with the historical
~21 s source rebuild. Docker timing remains variable.

## 9. Artifact/storage cost

Artifact API supplies immutable IDs, compressed sizes, expiry and SHA-256
digest metadata:

<https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28>

### Fast producer

| Artifact | ID | Compressed bytes | Expiry |
| --- | ---: | ---: | --- |
| `ci-fast-29492253514-1` | `8372951553` | 5887 | 2026-07-30 |
| exact Fast package | `8372952135` | 580686 | 2026-07-23 |

Fast producer total: **586573 B**.

### Artifact-mode E2E

| Artifact | ID | Compressed bytes | Expiry |
| --- | ---: | ---: | --- |
| `ci-e2e-standard-29494116783-1` | `8373674745` | 9069586 | 2026-07-23 |
| Buildx record | `8373675558` | 31870 | 2026-07-30 |

Run A total: **9101456 B**.

### Source-build E2E

| Artifact | ID | Compressed bytes | Expiry |
| --- | ---: | ---: | --- |
| `ci-e2e-standard-29495144612-1` | `8374095693` | 9069747 | 2026-07-23 |
| Buildx record | `8374096728` | 31578 | 2026-07-30 |

Run B total: **9101325 B**.

Total active artifact footprint created or reused for this measurement set:

```text
18789354 B ≈ 18.79 MB
```

The artifact E2E public payload has one extra report
`fast-ci-handoff.json`; otherwise storage is effectively identical. Package
reuse changes runner work, not screenshot-heavy E2E storage.

GitHub states that standard GitHub-hosted runners are free for public
repositories, but wall time, runner work, artifact storage and cache storage are
separate engineering/resource metrics. Storage is still accounted independently:

<https://docs.github.com/en/billing/concepts/product-billing/github-actions>

## 10. What package reuse achieved

Confirmed:

1. The exact Fast-tested `.ankiaddon` reached real Anki without a product rebuild.
2. Source install/build/package phases changed from `success` to `absent`.
3. Exact package validation/extraction retained safety for 140 ms.
4. The source-run package hash was revalidated after real-Anki execution.
5. Functional settings coverage, screenshots, errors and manifest remained equivalent.
6. Inner product preparation saved 21.585 s.
7. After handoff overhead, direct net preparation saving is about 12.6–14.6 s.
8. E2E artifact/storage cost remained effectively unchanged.

Not established:

- that package reuse accelerated Docker build;
- that the 30 s observed job delta is entirely causal;
- that GHCR or cache policy would produce a particular saving;
- full-contour performance;
- warm-cache average or variance distribution.

## 11. Remaining bottlenecks ranked

### 1. Mandatory Fast CI / PR wait

Current exact producer:

```text
job execution: 161 s
workflow elapsed: 165 s
canonical structured interval: 88.342 s
```

Fast CI runs on each PR and on `master`, while Docker E2E remains a rare manual
risk gate. Its setup/install/cache/typecheck/package split is still
under-instrumented. Frequency-weighted user wait is therefore the highest
priority even though it is outside the paired E2E job.

### 2. Docker build/cache/load in E2E

After package reuse, Run A spent **39.035 s** in Docker build/cache/load versus
**28.824 s** in the complete inner E2E. It is the largest single Stage 4 E2E
phase and has the largest infrastructure variance.

### 3. Browser/lifecycle

Artifact-mode browser serial/parallel capture used **20.661 s** and dominates
the remaining inner E2E. The parallel read-only subset itself was only 5.676 s;
serial persistence/notices/lifecycle work makes up most of the rest.

### 4. Cross-run handoff

The security and identity checks cost approximately 7–9 s. This overhead is
material but justified: removing exact checkout, dual hash validation or
artifact-ID binding would weaken the Stage 3 contract.

## 12. Decision matrix A/B/C/D

| Option | Evidence | Expected benefit | Complexity | Security/maintenance risk | Priority |
| --- | --- | --- | --- | --- | --- |
| A — GHCR/prebuilt E2E environment image | Docker aggregate is 39–49 s and variable | potentially material per E2E, but not yet quantified | high | registry lifecycle, digest/provenance, invalidation, access and storage | second |
| B — browser/lifecycle optimization | browser phase 20.7–22.4 s; parallel subset already efficient | bounded; coverage cannot be removed | medium-high | flaky timing, weakened screenshot/persistence proof | third |
| C — Fast CI optimization | mandatory producer job is 161 s; canonical 88.3 s; every PR/master | highest frequency-weighted reduction in developer wait | medium | low if measurement-first and canonical semantics preserved | **selected** |
| D — stop infrastructure optimization | package reuse already yields 12.6–14.6 s net | avoids maintenance | low | leaves mandatory 161 s gate under-instrumented | not yet |

## 13. Recommended next stage

Choose **C — Fast CI optimization**.

Recommended Stage 5 scope:

1. add non-invasive structured timing around Fast checkout/setup/cache restore,
   dependency installs, both TypeScript checks, Vitest, Vite build, pytest,
   package checks, artifact upload and post-job cache save;
2. confirm whether the second TypeScript typecheck is materially duplicated;
3. optimize only the largest proven repeated phase while preserving standalone
   scripts and `run_full_check.ps1 -SkipDocker` semantics;
4. measure one exact-SHA Fast CI before/after pair;
5. do not add Docker, release or E2E work to this stage.

Why C before A:

- Fast CI is the ordinary PR gate; Docker E2E is manual and rare.
- The current Fast job is longer than either Stage 4 E2E job.
- A GHCR environment image would add substantial supply-chain and lifecycle
  complexity before BuildKit import/load/export is fully decomposed.
- Even a modest Fast reduction repeated on every PR/master is more valuable than
  a similar saving in occasional targeted E2E.

Why B is lower:

- screenshot parallelism already succeeds with 3 workers and no failures;
- serial product-notice/settings proofs are safety coverage, not obvious waste;
- browser work is smaller than the Docker aggregate and less frequent than Fast CI.

Why D is lower:

- the mandatory 161 s Fast job still has a large unmeasured setup/canonical gap;
- stopping now would leave an evidence-backed optimization opportunity unexplored.

## 14. Unknowns and caveats

1. Only one paired run per mode was allowed; no distribution or confidence
   interval from repeats exists.
2. Runner image versions differ, so total-wall comparison is not fully controlled.
3. No `full` contour was run; conclusions apply to targeted `standard/settings`.
4. No warm repeat was run; exact cache reuse was not averaged.
5. `gha-enabled` is not a hit/miss classification.
6. Buildx import, image unpack/load and export are visible in logs but not yet
   persisted as separate structured fields.
7. Artifact handoff timing is second-rounded by Jobs API; the report uses a
   7–9 s range.
8. Source and Fast packages are functionally equivalent but not byte-identical
   cross-platform ZIPs.
9. Public-repository standard runner minutes are free under current GitHub
   policy, but storage and engineering wait remain separate concerns.
10. Production CI was not modified by Stage 4.
11. The report does not start or implement Stage 5.
