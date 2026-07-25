# E2E final summary and bounded history

This document defines the canonical end-of-run evidence contract for the real-Anki
GitHub Actions contour. It completes the E2E observability/build-identity track
without adding performance gates or an external monitoring service.

## Canonical files

The raw producer writes:

```text
reports/final-run-summary.json
```

The public exporter writes the semantically identical sanitized file:

```text
artifacts/reports/final-run-summary.json
```

`final-run-summary.json` is the only canonical final result summary. Existing files
remain during the compatibility period:

```text
ci-e2e-summary.json  derived JSON projection
ci-e2e-summary.md    human rendering
reports/e2e-performance-summary.json  detailed performance evidence
```

The legacy files do not independently infer result, terminal state, compatibility,
or final timings.

The compact history artifact contains only:

```text
reports/final-run-summary.json
reports/e2e-run-history.json
reports/e2e-history-aggregation.json
reports/e2e-regression-observations.json
reports/e2e-regression-observations.md
```

It must not contain logs, screenshots, packages, browser item arrays, failure
stacks, or environment dumps.

## Final summary schema v1

The schema is closed and bounded to 64 KiB. The exact top-level fields are:

```text
schemaVersion
result
finalizationStatus
execution
build
compatibility
terminal
checks
performance
artifactFootprint
evidence
finalState
```

All timestamps are ISO-8601 UTC values ending in `Z`. SHA values are lowercase
40-hex strings. Digests use `sha256:<64 lowercase hex>`. Evidence references use
safe POSIX relative paths. Arbitrary console output, user/card content, tokens,
authorization headers, token-bearing URLs, private absolute paths, complete
stacks, and raw environment data are forbidden.

Serialization is deterministic UTF-8 JSON. Raw and public documents are validated
independently, compared for semantic equality, and the exact public bytes are
hashed.

### Result and finalization

`result` is one of:

```text
success
failure
cancelled
```

`finalizationStatus` is one of:

```text
complete
partial
minimal
unavailable
```

Normal success requires:

```text
result=success
finalizationStatus=complete
terminal.event=run/pass
terminal.failureCode=null
terminal.signal=null
terminal.exitCode=0
finalState.cleanupStatus=success
finalState.artifactPreparationStatus=success
```

A functional failure keeps `failure-summary.json` as detailed evidence. The final
summary stores only a bounded projection of its primary code, active phase/item,
cleanup state, and evidence path. A complete failure is allowed when terminal,
cleanup, public-export, and artifact state were all finalized.

Cancellation keeps immutable signal-time `cancellation-summary.json` evidence.
The final summary adds the post-signal host cleanup result without rewriting the
inner snapshot:

```text
result=cancelled
terminal.event=run/cancel
terminal.failureCode=ASR-E2E-CANCELLED
terminal.exitCode=130|143
terminal.signal=SIGINT|SIGTERM
```

Hard cancellation may produce `partial` or `minimal` evidence.

A setup/preflight failure does not invent build identity. When the package was
not resolved:

```text
build.identityDigest=null
build.status=unresolved
```

The exact failed check or bounded host phase is retained.

## Cross-evidence validation

The builder validates at least these relationships:

| Area | Canonical evidence |
| --- | --- |
| execution | workflow context, artifact manifest, image provenance |
| terminal | `run-events.jsonl` terminal run event |
| failure | `failure-summary.json` primary code and context |
| cancellation | `cancellation-summary.json` code, signal, exit and inner cleanup |
| build | non-release or release identity evidence |
| preflight | `preflight-report.json` status and check counts |
| browser | browser progress counters and operation-only item timing |
| screenshots | expected/actual screenshot counters |
| phase timing | `e2e-phase-timings.json` stable producer timings |
| resources | `resource-summary.json` reference |
| artifact | manifest status, inventory and pre-upload footprint |
| final state | host cleanup and artifact preparation/export result |

Result is never inferred from console text.

## Compatibility schema v1

The compatibility key is:

```text
sha256(
  UTF-8 JSON(
    dimensions,
    sorted keys,
    compact separators,
    no BOM
  )
)
```

Hard dimensions are:

```text
contour
mode
scope
restartExecuted
screenshotWorkers
resourceTelemetry
ankiVersion
packageSourceClass
realDeckWorkloadDigest
browserPlanSchemaVersion
browserReportSchemaVersion
browserItemTimingSemantics
runEventSchemaVersion
phaseTimingSchemaVersion
artifactSchemaVersion
environmentContractDigest
imagePlatform
runnerFamily
```

Cloud and local contours therefore never share a key.

Observed provenance is retained outside the key:

```text
runnerOs
runnerImage
Docker client/server version
Compose version
PowerShell version
workflowSourceSha
harnessSha
```

Changes to observed dimensions add comparison caveats but do not automatically
make otherwise equivalent runs incomparable.

The key intentionally excludes:

```text
run ID and attempt
timestamps
branch and PR title
artifact name
build identity digest
package commit
harness commit
workflow display name
```

Exact build identity remains provenance and participates in the candidate key,
not the compatibility key.

## Candidate and first-run pass rate

For non-release runs:

```text
candidateKey = sha256({
  identityKind,
  buildIdentityDigest,
  compatibilityKey
})
```

Release candidates use the existing exact release artifact identity with the same
compatibility key. Release and non-release candidates are not mixed.

A first-attempt candidate is eligible only when:

```text
runPurpose=acceptance
contour=cloud
mode!=perf100
candidateKey is valid
runAttempt=1
finalizationStatus=complete
result=success|failure
```

Controlled, measurement, cancelled, local, partial/minimal, rerun-attempt, and
repeated execution of an already-seen candidate are counted with explicit
exclusion reasons.

For the earliest eligible execution of each candidate:

```text
success -> pass
functional failure -> fail
```

The rate is informational and never a merge or workflow gate.

## Bounded history schema v1

The canonical history file is:

```text
reports/e2e-run-history.json
```

Limits are fixed by schema v1:

```text
maxAgeDays=90
maxEntries=120
maxEntriesPerCompatibilityKey=30
```

Entries are deduplicated by `(runId, runAttempt)`, sorted by start time/run/attempt,
trimmed by age, then per-key count, then total count. Each entry contains compact
facts only:

```text
run and attempt
candidate/result/purpose/compatibility/build identity
final summary digest
timestamps
selected stable metrics
selected stable phase/item durations
main artifact ID/digest/size/expiry
first-attempt eligibility/outcome
observed environment dimensions
```

Previous history is discovered through the GitHub Actions API. An artifact name is
only a candidate selector: repository/run metadata, expiry, schema, bounds, and
entry digests still require validation.

Missing or expired history produces `continuity=bootstrap`. Invalid or incompatible
history produces `continuity=reset` with a bounded reason. Neither case changes the
functional E2E result. The newly generated history artifact must still validate.

Generated history is not committed to the repository and GitHub cache is not a
canonical history store.

## Aggregation and percentiles

Only complete successful `acceptance` entries from the exact same compatibility
key and cloud contour contribute performance samples. Failed, cancelled,
controlled, measurement, incompatible, and missing values are excluded. Missing
metrics are never replaced by zero.

Percentiles use:

```python
statistics.quantiles(values, n=100, method="inclusive")
```

Minimum samples:

```text
p50: 3
p95: 20
```

Below the minimum, the value is `null` and status is
`insufficient-history`.

Aggregated stable metrics include workflow/canonical/preflight/image/browser/
artifact-preparation/cleanup durations, pre-upload artifact bytes, uploaded main
artifact bytes, run-event producer calls/duration, and selected stable phase and
browser item IDs.

## Artifact footprint

The canonical main summary records the pre-upload footprint:

```text
fileCount
totalUncompressedBytes
category counts and bytes
bounded largestFiles
screenshot/report/diagnostic/package/runtime counts and bytes
artifact manifest size and SHA-256
```

Categories are derived from stable relative prefixes. The summary size is included
through a deterministic fixed-point calculation. Upload-generated metadata is not
embedded in the uploaded main artifact.

After upload, numeric artifact ID, digest, uploaded size, and expiry are written to
the compact history entry and GitHub Step Summary. The already-uploaded artifact is
never rewritten.

## Observational regression report

Files:

```text
reports/e2e-regression-observations.json
reports/e2e-regression-observations.md
```

Statuses are:

```text
insufficient-history
within-history
above-p50
above-p95
improved
not-comparable
```

The report includes current value, compatible p50/p95, absolute and percentage
delta, sample count, continuity, and observed environment caveats.

Classification is strictly observational. It must not change `result`, emit
`::error`, prevent upload, block merge, or create a duration/size threshold.

## Run purpose

The workflow accepts only:

```text
acceptance
controlled
measurement
```

Default is `acceptance`. `perf100` is always normalized to `measurement`.
Purpose never changes the functional result.

## Retention and continuity

The heavy E2E artifact keeps its existing short retention. The compact history
artifact uses a separate retention of up to 90 days, within repository policy.
Artifact expiry or deletion is expected and is represented honestly by bootstrap
or reset continuity.

## Security boundary

The canonical producer and public exporter reject:

```text
credentials and authorization headers
token-bearing URLs
private absolute paths
control characters
user/card HTML or content
full stacks and logs
raw environment dumps
artifact download URLs
actor email
```

Allowed values are stable IDs, bounded enums, public SHAs/digests, numeric run and
artifact IDs, durations/counts, safe relative paths, and sanitized bounded
summaries.
