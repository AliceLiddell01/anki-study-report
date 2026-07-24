# E2E-I4 — Cancellation и preflight: промежуточный closeout

**Статус:** `PARTIAL`  
**Дата:** 2026-07-24  
**Ветка:** `platform/e2e-i4-cancellation-preflight`  
**Base:** `core`  
**Base / merge base:** `bf51ae29d6f8a0414bbd6d893b27594b8b95acaa`  
**Implementation HEAD:** `8e349ae4cc0a2a5221ee7f74cd8e6fdd548418ed`

## Итог

Опубликована рабочая foundation-часть E2E-I4:

- fail-closed canonical preflight schema и validator;
- deterministic static/runtime check order;
- separate canonical `cancellation-summary.json`;
- `SIGINT → 130`, `SIGTERM → 143` parity;
- cancellation separation from `failure-summary.json`;
- `phase/cancel → run/cancel` runtime/validator support;
- owned process-group supervision в outer Docker wrapper;
- bounded cancellation escalation и cleanup;
- native cancellation exit preservation в PowerShell;
- run-scoped Compose project identity;
- best-effort minimal cancellation artifact preparer;
- focused schema, fail-fast и process-tree tests.

Этап не может быть закрыт как `COMPLETE`: workflow-level integration и обязательные cloud proofs отсутствуют.

## Publication

Published commits:

```text
456edc525c808edf467eaf522f093454cefb9911  Preserve cancellation across E2E process layers
8e349ae4cc0a2a5221ee7f74cd8e6fdd548418ed  Add fail-closed E2E preflight validation
```

Publication method:

```text
one logical file set
→ one Git tree
→ one commit
→ commit/tree/diff verification
→ non-force fast-forward ref update
```

Verified after publication:

```text
branch ahead of core: 2
branch behind core: 0
merge base: bf51ae29d6f8a0414bbd6d893b27594b8b95acaa
force update: no
```

No direct writes were made to `core`.

## Preflight

Canonical files:

```text
scripts/e2e_preflight.py
scripts/e2e_preflight_contract.py
scripts/e2e_preflight_checks.py
reports/preflight-report.json
```

Static checks:

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

Runtime checks:

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

Focused fake-runner tests prove that an invalid mode/source and a missing staged package fail before any Docker `pull`, `build` or `run` command.

## Cancellation

Canonical files:

```text
docker/anki-e2e/cancellation_protocol.py
docker/anki-e2e/run_event_runtime.py
docker/anki-e2e/run_event_validate.py
docker/anki-e2e/run-e2e-failure-wrapper.sh
scripts/prepare_ci_e2e_cancellation.py
```

Implemented semantics:

```text
SIGINT  → originalExitCode=130, originalSignal=SIGINT
SIGTERM → originalExitCode=143, originalSignal=SIGTERM

cancellation-summary.json
→ phase/cancel when a phase is active
→ run/cancel
→ no failure-summary.json
→ no later run/fail or run/pass
```

The outer wrapper uses `setsid`, stores the owned child PID/process group, forwards only to that group, waits a bounded grace period and escalates only within the owned group. A synthetic child/grandchild test verifies that unrelated processes remain alive.

## PowerShell and Compose

Published changes:

- `$LASTEXITCODE` `130/143` is returned instead of being converted by `throw` to `1`;
- environment restoration remains in `finally`;
- normal full artifact assertion is skipped after cancellation;
- `COMPOSE_PROJECT_NAME=asr-e2e-<run>-<attempt>` isolates concurrent resources;
- Compose receives `init: true` and bounded stop grace period;
- the GHCR override starts the shared cancellation/failure wrapper.

PowerShell execution was not run locally because `pwsh` was unavailable in the execution environment. Windows-runner proof is still required.

## Tests

Published-head focused contour:

```text
python -m pytest -q \
  tests/test_e2e_i4_contracts.py \
  tests/test_e2e_process_supervision.py

13 PASS
```

Additional static checks:

```text
published Python compile: PASS
published Bash syntax: PASS
```

A broader local candidate contour that also contained unpublished workflow and inner-runner changes:

```text
89 PASS
workflow YAML parse: PASS
run-e2e.sh bash syntax: PASS
```

The broader local result is development evidence only and is not attributed to the remote branch HEAD.

## Package decision

The complete branch diff is **not accepted** by the current fail-closed harness reuse validator because it includes new/changed paths outside the existing allowlist, including:

```text
scripts/e2e_preflight.py
scripts/e2e_preflight_contract.py
scripts/e2e_preflight_checks.py
scripts/run_full_check.ps1
scripts/run_anki_e2e_docker.ps1
scripts/prepare_ci_e2e_cancellation.py
tests/test_e2e_i4_contracts.py
tests/test_e2e_process_supervision.py
```

The allowlist was not weakened. A new package-producing Fast CI is therefore required before cloud E2E acceptance.

## Cloud verification

No workflow run exists for implementation HEAD `8e349ae4cc0a2a5221ee7f74cd8e6fdd548418ed`.

Not available through the active GitHub connector:

- workflow dispatch;
- force-cancel/cancel run API;
- local authenticated `gh` fallback.

Consequently the following required proofs were not performed:

```text
Fast CI package-producing PASS
controlled run A cancelled by same concurrency group
run A conclusion=cancelled
run A bounded cancellation evidence
run A no-orphan proof
successful standard/full run B
23/23 browser items
18/18 screenshots
API/restart/telemetry PASS
artifact IDs and digests
```

No run IDs, artifact identities or package hashes are claimed for E2E-I4.

## Workflow integration gap

Local candidate changes for these files were inspected and tested but were not published:

```text
.github/workflows/ci-e2e.yml
.github/workflows/ci-fast.yml
docker/anki-e2e/run-e2e.sh
```

Therefore the remote branch does not yet prove:

- full `always()` audit;
- heavy success/failure artifact steps skipped on cancellation;
- cancellation-only bounded upload/cleanup steps;
- Fast CI cancellation finalization;
- inner core-runner trap behavior.

This gap is blocking for `COMPLETE`.

## Что не запускалось

- third full;
- `perf100`;
- warm repeat;
- worker comparison;
- visual regression;
- retries;
- source-build cloud fallback;
- docs-only rerun;
- any cloud Fast CI/E2E run for this branch.

## Out of scope preserved

- E2E-I5 build identity;
- E2E-I6 final summary/history;
- retries/quarantine;
- visual regression;
- performance thresholds;
- product payload/API/UI;
- release/publish behavior.

## Required continuation before COMPLETE

```text
publish exact workflow and inner-runner integration
→ run package-producing Fast CI
→ inspect jobs/steps/artifacts
→ run controlled same-group A/B standard/full pair
→ prove A=cancelled and B=PASS
→ update docs/roadmap/final closeout
→ mark PR ready only after evidence
```

E2E-I5 must not begin before this sequence closes E2E-I4.
