# Unified live run event protocol

**Status:** E2E-I1 contract, schema v1  
**Producers:** `fast-ci`, `docker-e2e`

Fast CI and real-Anki Docker E2E expose the same phase lifecycle in two forms:

1. an immediate stable console line;
2. one deterministic JSON object per line in `run-events.jsonl`.

The stream supplements existing Fast CI timing, E2E phase/resource telemetry, raw logs, screenshots and artifact manifests. It does not replace them.

## Evidence paths

```text
Fast CI:   ci-fast/run-events.jsonl
Docker E2E: reports/run-events.jsonl
Public E2E artifact: artifacts/reports/run-events.jsonl
```

The Fast CI path is included in the existing `ci-fast/` diagnostics artifact. The Docker path is indexed by the existing artifact manifest because it lives under `reports/`. Public E2E preparation validates the source stream before sanitization/copy and validates the copied stream again.

## Schema v1

Every line contains exactly these fields in this order:

```json
{"schemaVersion":1,"timestampUtc":"2026-07-24T00:00:00.000Z","elapsedMs":0,"producer":"fast-ci","phaseId":"run","eventKind":"run","status":"start","durationMs":null,"current":null,"total":null,"message":"pipeline=canonical","failureCode":null}
```

| Field | Contract |
| --- | --- |
| `schemaVersion` | integer `1` |
| `timestampUtc` | UTC ISO-8601 with millisecond precision and trailing `Z` |
| `elapsedMs` | non-negative integer from run initialization |
| `producer` | `fast-ci` or `docker-e2e` |
| `phaseId` | producer-specific stable ID from the reviewed registry |
| `eventKind` | `run`, `phase`, or `message` |
| `status` | closed lifecycle value described below |
| `durationMs` | non-negative integer for completed lifecycle events, otherwise `null` |
| `current`, `total` | paired bounded progress counters reserved for later item-level progress |
| `message` | optional trimmed public-safe single-line UTF-8 text, at most 512 bytes |
| `failureCode` | reserved for E2E-I3 and therefore `null` in E2E-I1 |

Lifecycle values:

```text
run:     start | pass | fail | cancel
phase:   start | pass | fail | skip | cancel
message: info
```

A finalized stream starts with exactly one `run/start` event and ends with exactly one final run event. Elapsed values are non-decreasing. Serialization is compact and deterministic UTF-8 without BOM; every event ends with `\n`.

## Console form

```text
[00:37.842] [E2E] [browser-smoke-first] START
[01:10.995] [E2E] [browser-smoke-first] PASS duration=33153ms
```

Fast CI uses `[FAST]`; Docker E2E uses `[E2E]`. ANSI is not part of the contract. Messages are appended only after validation, and a line can never begin with a GitHub workflow-command marker.

## Safety and append guarantees

The validator rejects:

- unknown schema versions, producers, event kinds, statuses and phase IDs;
- negative or inconsistent timing/progress values;
- control characters, multiline values and NUL;
- token-bearing URLs, authorization/private-key material and common secret forms;
- Windows, UNC and private Linux absolute paths in public-safe messages;
- messages above 512 UTF-8 bytes and event lines above 2048 bytes;
- BOM, partial lines, malformed JSON and non-deterministic serialization.

Writers use a cross-platform exclusive lock plus append-only UTF-8 writes and `fsync`. This preserves completed lines when several short-lived Python, PowerShell or Bash producers append concurrently.

## Stable phase registries

Fast CI IDs are the existing IDs from `scripts/ci_fast_timing.py`. Integration fails at import time if the timing and run-event registries diverge.

Docker E2E v1 IDs:

```text
workspace-copy
exact-package-validation
frontend-dependency-install
frontend-build
addon-package
profile-bootstrap
collection-bootstrap
real-deck-import
scenario-preparation
addon-install
anki-start-first
dashboard-ready-first
api-smoke-first
browser-smoke-first
anki-restart
dashboard-ready-restart
api-smoke-restart
telemetry-restart
artifact-manifest
```

E2E-I1 deliberately reports browser smoke as one phase-level operation. Route/theme/preview item progress remains E2E-I2.

## Compose output in CI

`run_anki_e2e_docker.ps1` uses deterministic non-interactive Compose presentation in CI:

```text
COMPOSE_ANSI=never
COMPOSE_PROGRESS=plain
COMPOSE_MENU=0
COMPOSE_STATUS_STDOUT=1
docker compose --ansi never --progress plain run --no-TTY ...
```

Local interactive output is unchanged unless the process explicitly sets CI mode or those Compose variables.
