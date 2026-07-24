# E2E preflight и cancellation contract

**Статус:** `COMPLETE` и cloud-accepted
**Дата:** 2026-07-25
**Implementation HEAD:** `5e52faee5cd97af8e7760e2c5041c782ce4273fa`
**Ветка:** `platform/e2e-i4-cancellation-preflight`

Этот документ является актуальным техническим контрактом E2E-I4. Историческое
подтверждение находится в
[`../reports/ci/e2e-i4-cancellation-preflight-closeout.md`](../reports/ci/e2e-i4-cancellation-preflight-closeout.md).

## Цель

E2E lifecycle различает:

```text
preflight PASS  → execution starts
preflight FAIL  → Docker pull/build/run не начинается; validation evidence
functional fail → failure-summary.json + run/fail
cancellation    → cancellation-summary.json + run/cancel + 130/143
success         → run/pass + success manifest
```

Cancellation не является functional failure и не создаёт
`failure-summary.json`.

## Canonical preflight

### Files

```text
scripts/e2e_preflight.py
scripts/e2e_preflight_contract.py
scripts/e2e_preflight_checks.py
reports/preflight-report.json
```

### Schema v1

```text
schemaVersion
status
producer
executionContext
startedAtUtc
finishedAtUtc
durationMs
checks
failedCheckId
```

Source report:

- UTF-8 без BOM;
- LF;
- deterministic field/check order;
- atomic replacement;
- bounded size;
- first failure stops execution;
- safe summaries без secrets, control characters и private absolute paths;
- byte-canonical serialization.

Public sanitized copy сохраняет schema semantics, но может быть pretty-printed
после redaction. Поэтому source copy проходит byte+semantic validation, public
copy — semantic+sanitizer validation.

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

Static layer не вызывает Docker. Invalid inputs, non-exclusive package source,
missing files, unsafe artifact root и mutable/inconsistent environment identity
завершаются до registry login/pull/build/run.

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

Runtime layer требует успешный canonical static report и использует resolved
Compose model. Cloud environment обязан быть exact immutable GHCR digest.

### Preservation

Host workflow создаёт `reports/preflight-report.json` до container execution.
Inner artifact reset сохраняет только этот canonical report и удаляет остальные
stale outputs. Success manifest и cancellation artifact обязаны включать
preflight evidence.

## Cancellation protocol

### Files

```text
docker/anki-e2e/cancellation_protocol.py
docker/anki-e2e/run-e2e-failure-wrapper.sh
docker/anki-e2e/run_event_runtime.py
docker/anki-e2e/run_event_validate.py
scripts/prepare_ci_e2e_cancellation.py
reports/cancellation-summary.json
```

### Stable codes

```text
docker-e2e → ASR-E2E-CANCELLED
fast-ci    → ASR-FAST-CANCELLED
```

`ASR-E2E-UNKNOWN` остаётся fail-closed fallback только когда functional failure
произошёл до persistence известного failure path. Он не используется как
нормальная cancellation category.

### Signal parity

```text
SIGINT  → originalExitCode=130, originalSignal=SIGINT
SIGTERM → originalExitCode=143, originalSignal=SIGTERM
unknown signal → originalSignal=null при exit 130 или 143
```

### Summary schema v1

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

Summary:

- atomic;
- immutable после создания;
- bounded;
- public-safe;
- не может сосуществовать с `failure-summary.json`.

## Process ownership и signal forwarding

Outer wrapper:

1. запускает core runner в owned process group через `setsid`;
2. хранит child PID/process-group identity;
3. пересылает исходный signal только owned group;
4. ждёт bounded grace;
5. выполняет scoped TERM/KILL escalation только внутри owned group;
6. сохраняет cancellation summary и run events;
7. возвращает исходный `130/143`.

Unrelated процессы не завершаются. Compose project изолирован:

```text
asr-e2e-<github.run_id>-<github.run_attempt>
```

## Run-event parity

Cancellation lifecycle:

```text
active phase → phase/cancel
run          → run/cancel
failureCode  → producer cancellation code
message      → exact exit/signal pair
```

Validator запрещает:

- cancellation без cancellation summary;
- cancellation вместе с failure summary;
- code/producer/exit/signal mismatch;
- больше одного `phase/cancel`;
- active phase mismatch;
- последующий `run/fail` или `run/pass`.

## Workflow condition policy

Normal success/failure finalization использует:

```yaml
if: ${{ !cancelled() }}
```

Cancellation-only bounded tail использует:

```yaml
if: ${{ cancelled() }}
```

Heavy public artifact preparation не выполняется после cancellation.

Fast CI также сохраняет `run/cancel`, а normal package/diagnostic finalization не
должна превращать cancellation в generic failure.

## Cancellation cleanup и ownership

Порядок host cancellation tail:

```text
write host log to RUNNER_TEMP
→ bounded docker compose down for exact project
→ scoped ownership restoration for e2e-artifacts
→ copy bounded host log into artifact tree
→ prepare minimal cancellation artifact
→ upload required artifact
```

Нельзя писать host log непосредственно в root-owned bind-mounted tree до
ownership restoration.

Required cancellation upload использует:

```yaml
if-no-files-found: error
```

`continue-on-error` допустим для diagnostics step, чтобы overall GitHub
conclusion оставался `cancelled`, но отсутствие required evidence не выглядело
успехом.

## Artifact policy

### Cancellation

Policy:

```text
best-effort-minimal
```

Allowlist:

```text
reports/cancellation-summary.json
reports/preflight-report.json
reports/run-events.jsonl
diagnostics/cancellation-host.log
```

Запрещены full screenshots, package bytes, readiness token, unbounded raw logs и
private paths.

Inner summary фиксирует состояние в момент signal handling. Host workflow может
позже завершить cleanup и опубликовать artifact. Поэтому
`artifact.status=unavailable` внутри historical inner summary не противоречит
последующему существованию GitHub artifact.

### Success

Success artifact содержит:

- `artifact-manifest.json` со status `success`;
- source-derived sanitized preflight report;
- valid `run-events.jsonl` с terminal `run/pass`;
- browser/API/restart/telemetry evidence;
- package/harness identities;
- redacted readiness;
- no `failure-summary.json`;
- no `cancellation-summary.json`.

## Package identity

Cloud manual E2E принимает exact successful Fast CI artifact. Если complete diff
не проходит fail-closed harness reuse allowlist, allowlist не расширяется ради
текущей задачи: создаётся новый package-producing Fast CI.

E2E summary фиксирует независимо:

```text
source Fast CI run ID
source tested commit SHA
inner package SHA-256
current E2E checkout/harness SHA
environment image digest
```

## Cloud acceptance

### Fast CI

```text
run: 30125233072
conclusion: success
tested SHA: 5e52faee5cd97af8e7760e2c5041c782ce4273fa

package artifact:
id: 8609019098
name: ci-package-5e52faee5cd97af8e7760e2c5041c782ce4273fa-30125233072-1
digest: sha256:5001e6e1ef480325b1ea9cd214ac8cce157d35f75dbbb9d5a8153acb46fdd882

diagnostics artifact:
id: 8609018407
name: ci-fast-30125233072-1
digest: sha256:9a1d7ab5bf1db8a92fd8c99124e63fffe682a7f072655c2c21855418b3a53fa7
```

### Controlled run A

```text
run: 30126100944
conclusion: cancelled
signal/exit: SIGTERM / 143
code: ASR-E2E-CANCELLED
active phase: browser-smoke-first
last successful phase: api-smoke-first
preflight: 20/20 PASS

artifact:
id: 8609322435
name: ci-e2e-cancelled-30126100944-1
digest: sha256:9389b791b41bf6829b499f1dc491bc750725030f682ab7c4a63c7000901edaf1
```

### Controlled run B

```text
run: 30126228749
conclusion: success
manifest: success, 62 indexed paths
preflight: 20/20 PASS
browser items: 23/23 PASS
screenshots: 18/18
API/restart/readiness/telemetry phases: PASS
terminal event: run/pass

artifact:
id: 8609400578
name: ci-e2e-standard-30126228749-1
digest: sha256:93133537cb8aff08a792da5475d6c5676fafd314cadf639936a731f8d0ad3dca

inner package SHA-256:
9b3bfcdc019e870579563b2be9eaa75220f6b732ee6b4f8fc6e524288b1c0862
```

B был запущен с той же concurrency identity после входа A в canonical Docker
step. Он автоматически отменил A; ручной cancel не использовался.

## Verification

Final implementation candidate:

```text
focused contour: 83 PASS
full Python suite: 981 PASS
PowerShell parser regression: PASS
workflow YAML parse: PASS
Bash syntax: PASS
git diff --check: PASS
Fast CI: PASS
controlled A/B: PASS
```

## Не запускалось

- `perf100`;
- warm repeat;
- worker comparison;
- visual regression;
- retries/quarantine;
- source-build cloud fallback;
- третий successful full;
- docs-only Fast CI/Docker rerun.

Эти проверки не входят в completion criteria E2E-I4.

## Out of scope

- E2E-I5 non-release build identity;
- E2E-I6 canonical summary/history;
- retries/quarantine;
- visual regression;
- performance thresholds;
- product/API/UI behavior;
- release/publication.

Завершение E2E-I4 не означает автоматический старт E2E-I5.

## Operations

Пошаговый manual ChatGPT-mode runbook:
[`chatgpt-manual-operations.md`](chatgpt-manual-operations.md).
