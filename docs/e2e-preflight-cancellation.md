# E2E preflight и cancellation contract

**Статус:** implementation in progress; acceptance не завершён  
**Дата:** 2026-07-24  
**Ветка:** `platform/e2e-i4-cancellation-preflight`

Этот документ описывает уже опубликованную часть E2E-I4. До cloud verification и workflow-level integration он не заменяет финальный closeout и не означает `COMPLETE`.

## Цель

E2E lifecycle должен различать четыре состояния:

```text
preflight PASS  → execution starts
preflight FAIL  → no pull/build/run; validation evidence
functional fail → failure-summary.json + run/fail
cancellation    → cancellation-summary.json + run/cancel + 130/143
```

Cancellation не является functional failure и не должна создавать `failure-summary.json`.

## Lifecycle map

Опубликованный контур:

```text
GitHub workflow step
→ PowerShell run_full_check.ps1
→ PowerShell run_anki_e2e_docker.ps1
→ docker compose run
→ container bootstrap
→ run-e2e-failure-wrapper.sh
→ owned process group for run-e2e.sh
→ Anki/Xvfb/telemetry/resource sampler children
→ bounded cancellation cleanup
→ cancellation-summary.json + run/cancel
```

Ключевые точки владения:

- PowerShell сохраняет native exit `130`/`143` и не превращает его в generic `1`;
- Compose project name включает `github.run_id` и `github.run_attempt`;
- outer wrapper запускает core runner через `setsid`;
- signal пересылается только owned process group;
- bounded escalation: original signal, затем `SIGTERM`, затем `SIGKILL` только для owned group;
- functional non-zero остаётся functional failure.

## Canonical preflight

CLI:

```text
scripts/e2e_preflight.py
```

Importable modules:

```text
scripts/e2e_preflight_contract.py
scripts/e2e_preflight_checks.py
```

Report:

```text
reports/preflight-report.json
```

Schema v1:

```json
{
  "schemaVersion": 1,
  "status": "PASS",
  "producer": "docker-e2e",
  "executionContext": "github-actions",
  "startedAtUtc": "2026-07-24T00:00:00.000Z",
  "finishedAtUtc": "2026-07-24T00:00:01.000Z",
  "durationMs": 1000,
  "checks": [],
  "failedCheckId": null
}
```

Properties:

- deterministic field and check order;
- first failure stops the validator;
- stable non-user-derived IDs;
- bounded public-safe summaries;
- no tokens, control characters or private absolute paths;
- UTF-8 without BOM, LF, deterministic serialization;
- atomic report replacement.

### Static checks

```text
inputs.mode-scope
inputs.workers
inputs.restart
package.source-exclusivity
repository.required-files
filesystem.artifact-root
environment-lock.syntax
environment-lock.consistency
environment-lock.exact-reference
compose.files
```

Static checks do not invoke Docker. Cloud `source-build`, non-exclusive package inputs, unsafe artifact roots, missing files, mutable/non-exact image references and lock/spec mismatches fail before runtime checks.

### Runtime checks

```text
package.staged-artifact
docker-cli.available
compose-cli.available
docker-daemon.reachable
docker-daemon.platform
compose.resolved-model
compose.expected-service
compose.image-source
compose.safe-mounts
compose.no-external-ports
```

Runtime validation uses:

```text
docker compose config --quiet
docker compose config --format json
```

The resolved model must contain only `anki-e2e`, use the expected immutable image source, keep the workspace read-only, avoid Docker socket/root mounts and expose no external ports.

## Cancellation summary

Protocol:

```text
docker/anki-e2e/cancellation_protocol.py
```

Canonical path:

```text
reports/cancellation-summary.json
```

Schema v1 records:

```text
schemaVersion
result=cancelled
producer
cancellationCode
observedAtUtc
elapsedMs
originalExitCode
originalSignal
context
cleanup
artifact
evidencePaths
```

Stable codes:

```text
docker-e2e → ASR-E2E-CANCELLED
fast-ci    → ASR-FAST-CANCELLED
```

Signal parity:

```text
SIGINT  → 130
SIGTERM → 143
unknown signal → null with exit 130 or 143
```

The document is bounded, atomically written, immutable after creation and cannot coexist with `failure-summary.json`.

## Run-event parity

The current schema-v2 runtime supports:

```text
active phase → phase/cancel
run          → run/cancel
failureCode  → cancellation code
message      → exact exit/signal pair
```

Validation rejects:

- cancellation with `failure-summary.json`;
- cancellation without `cancellation-summary.json`;
- different producer/code/exit/signal;
- multiple phase/cancel events;
- active phase mismatch;
- later `run/fail` or `run/pass`.

Historical schema v1 and existing success/failure behavior remain accepted by their existing contracts.

## Cleanup and artifacts

Cancellation cleanup is:

- idempotent;
- bounded;
- valid after partial startup;
- scoped to current process group and Compose project;
- tolerant of already absent processes/resources.

Cancellation artifact policy:

```text
best-effort-minimal
```

Allowlisted evidence:

```text
reports/cancellation-summary.json
reports/preflight-report.json
reports/run-events.jsonl
diagnostics/cancellation-host.log
```

Full screenshots, package bytes and unbounded raw Docker logs are excluded from the minimal cancellation artifact.

## Verification performed for published code

```text
python -m pytest -q \
  tests/test_e2e_i4_contracts.py \
  tests/test_e2e_process_supervision.py

python -m py_compile <published Python modules>
bash -n docker/anki-e2e/run-e2e-failure-wrapper.sh
bash -n docker/anki-e2e/stop-anki.sh
```

Published-head focused result:

```text
13 PASS
Python compile PASS
Bash syntax PASS
```

A broader local candidate contour, including workflow and inner runner changes that were not published, produced `89 PASS`. It is not a remote/cloud proof.

## Acceptance gaps

The following are not yet proven or published on the branch:

- `.github/workflows/ci-e2e.yml` `always()` audit and cancellation-only steps;
- `.github/workflows/ci-fast.yml` cancellation finalization;
- inner `run-e2e.sh` cancellation trap changes;
- PowerShell execution on a Windows runner;
- Fast CI package-producing PASS for the final diff;
- controlled concurrency run A with GitHub conclusion `cancelled`;
- successful `standard/full` successor run B;
- artifact IDs/digests and orphan-resource proof.

Therefore E2E-I4 remains `PARTIAL`; roadmap completion must not be marked until those gates exist.
