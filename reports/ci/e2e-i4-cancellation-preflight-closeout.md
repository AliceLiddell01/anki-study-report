# E2E-I4 — Cancellation и preflight: финальный closeout

**Статус:** `COMPLETE`
**Дата:** 2026-07-25
**Ветка:** `platform/e2e-i4-cancellation-preflight`
**Base:** `core`
**Implementation HEAD:** `5e52faee5cd97af8e7760e2c5041c782ce4273fa`
**PR:** `#137`

Актуальный технический контракт:
[`../../docs/e2e-preflight-cancellation.md`](../../docs/e2e-preflight-cancellation.md).

Manual ChatGPT-mode runbook:
[`../../docs/chatgpt-manual-operations.md`](../../docs/chatgpt-manual-operations.md).

## Итог

E2E-I4 завершён. Реализованы и подтверждены:

- fail-closed static/runtime preflight до Docker execution;
- deterministic canonical preflight report;
- отдельный cancellation summary;
- `SIGINT → 130`, `SIGTERM → 143`;
- `phase/cancel → run/cancel`;
- separation cancellation от functional failure;
- scoped process-group signal forwarding;
- bounded escalation и Compose cleanup;
- run-scoped Compose identity;
- split normal/cancellation workflow tail;
- minimal bounded cancellation artifact;
- ownership restoration для bind-mounted evidence;
- сохранение preflight report через inner artifact reset;
- PowerShell parser regression;
- exact package-producing Fast CI;
- controlled same-concurrency A/B cloud acceptance;
- artifact content и sanitizer validation.

## Publication

Implementation commits:

```text
456edc525c808edf467eaf522f093454cefb9911
Preserve cancellation across E2E process layers

8e349ae4cc0a2a5221ee7f74cd8e6fdd548418ed
Add fail-closed E2E preflight validation

608e02773b965e7da140c5fe8b2679aad794ac77
Document partial E2E cancellation and preflight implementation

2420009a53c0015b6549d08020e7a0f8fd85b3df
Integrate cancellation-aware E2E workflow finalization

6b19ccfa4657a7092ee767bed0a59294dbba52f9
Fix cancellation finalization and align E2E contracts

a841a34f3e35d165cd59f3c1fc05513420acb4b0
Fix PowerShell compose error reporting syntax

5e52faee5cd97af8e7760e2c5041c782ce4273fa
Preserve preflight and cancellation evidence ownership
```

Прямых writes в `core` не выполнялось. Merge/release/publication не выполнялись.

## Scope

### Реализовано

```text
.github/workflows/ci-e2e.yml
.github/workflows/ci-fast.yml
docker/anki-e2e/cancellation_protocol.py
docker/anki-e2e/run-e2e-failure-wrapper.sh
docker/anki-e2e/run-e2e.sh
docker/anki-e2e/run_event_*.py
docker/anki-e2e/stop-anki.sh
docker/anki-e2e/docker-compose*.yml
scripts/e2e_preflight*.py
scripts/prepare_ci_e2e_cancellation.py
scripts/run_anki_e2e_docker.ps1
scripts/run_full_check.ps1
tests/<E2E-I4 and affected contracts>
```

### Сохранённые границы

Не изменены:

- product payload/API/UI;
- dashboard security;
- token validation;
- sanitizer/media/action allowlists;
- APKG real-deck foundation;
- release/publication;
- retry/flake policy;
- performance thresholds.

## Preflight

Canonical source:

```text
scripts/e2e_preflight.py
scripts/e2e_preflight_contract.py
scripts/e2e_preflight_checks.py
reports/preflight-report.json
```

Static checks выполняются без Docker. Runtime checks требуют успешный static
report и проверяют exact staged package, Docker/Compose runtime, resolved model,
immutable image source, safe mounts и отсутствие external ports.

Final cloud evidence:

```text
20 checks
status PASS
failedCheckId null
```

Inner artifact reset сохраняет canonical preflight report, поэтому он присутствует
как в cancellation artifact, так и в success manifest.

## Cancellation

Canonical source:

```text
docker/anki-e2e/cancellation_protocol.py
reports/cancellation-summary.json
```

Final signal parity:

```text
SIGINT  → 130
SIGTERM → 143
```

Controlled run A сохранил:

```text
result cancelled
producer docker-e2e
cancellationCode ASR-E2E-CANCELLED
originalSignal SIGTERM
originalExitCode 143
lastSuccessfulPhaseId api-smoke-first
activePhaseId browser-smoke-first
terminal event run/cancel
failure-summary absent
```

## Workflow condition audit

Normal success/failure finalization:

```text
!cancelled()
```

Cancellation-only bounded finalization:

```text
cancelled()
```

Cancellation upload требует существующий artifact path. Heavy normal artifact
preparation не выполняется после cancellation.

## Ownership и cleanup

Проблема root-owned bind mount была устранена следующим порядком:

```text
temporary host log in RUNNER_TEMP
→ bounded exact-project compose down
→ scoped chown e2e-artifacts
→ copy host log
→ prepare cancellation artifact
→ upload
```

Ownership restoration не применяется ко всему workspace или несвязанным paths.

## Локальная проверка

Final candidate:

```text
workflow YAML parse: PASS
run-e2e.sh Bash syntax: PASS
PowerShell AST parser regression: PASS
focused contour: 83 PASS
full Python suite: 981 PASS
git diff --check: PASS
```

## Fast CI

```text
run ID: 30125233072
event: workflow_dispatch
conclusion: success
tested SHA: 5e52faee5cd97af8e7760e2c5041c782ce4273fa
```

Package artifact:

```text
id: 8609019098
name: ci-package-5e52faee5cd97af8e7760e2c5041c782ce4273fa-30125233072-1
size: 745762
digest: sha256:5001e6e1ef480325b1ea9cd214ac8cce157d35f75dbbb9d5a8153acb46fdd882
```

Diagnostics artifact:

```text
id: 8609018407
name: ci-fast-30125233072-1
size: 14358
digest: sha256:9a1d7ab5bf1db8a92fd8c99124e63fffe682a7f072655c2c21855418b3a53fa7
```

Exact inner package SHA-256:

```text
9b3bfcdc019e870579563b2be9eaa75220f6b732ee6b4f8fc6e524288b1c0862
```

## Controlled A/B

Inputs обоих runs:

```text
mode standard
scope full
screenshot_workers 3
resource_telemetry true
verify_restart auto
fast_ci_run_id 30125233072
head SHA 5e52faee5cd97af8e7760e2c5041c782ce4273fa
```

Run B использовал ту же production concurrency identity и автоматически отменил
уже выполнявшийся A. Ручной `gh run cancel` не применялся.

### Run A

```text
run ID: 30126100944
conclusion: cancelled
signal/exit: SIGTERM / 143
code: ASR-E2E-CANCELLED
```

Artifact:

```text
id: 8609322435
name: ci-e2e-cancelled-30126100944-1
size: 26621
digest: sha256:9389b791b41bf6829b499f1dc491bc750725030f682ab7c4a63c7000901edaf1
```

Validated content:

```text
cancellation-artifact.json
reports/cancellation-summary.json
reports/preflight-report.json
reports/run-events.jsonl
diagnostics/cancellation-host.log
```

Validation:

```text
preflight 20/20 PASS
run-event terminal run/cancel
failure-summary absent
permission errors absent
safe text files 5
```

Inner summary сохранил `cleanup=partial` и `artifact=unavailable`, потому что он
фиксируется в момент signal handling. Последующий host tail успешно восстановил
ownership и загрузил GitHub artifact. Оба факта сохранены без переписывания
historical evidence.

### Run B

```text
run ID: 30126228749
conclusion: success
```

Artifact:

```text
id: 8609400578
name: ci-e2e-standard-30126228749-1
size: 6894597
digest: sha256:93133537cb8aff08a792da5475d6c5676fafd314cadf639936a731f8d0ad3dca
```

Validated result:

```text
manifest status success
manifest indexed paths 62
preflight 20/20 PASS
terminal run/pass
browser items 23/23 PASS
screenshots 18/18
telemetry enabled
safe public text files 51
```

Required phases:

```text
api-smoke-first PASS
browser-smoke-first PASS
anki-restart PASS
dashboard-ready-restart PASS
api-smoke-restart PASS
telemetry-restart PASS
```

## Проблемы, найденные при acceptance

В ходе ручного ChatGPT-mode сопровождения были найдены и исправлены реальные
дефекты и process gaps:

- повреждение больших copy-paste blocks;
- неверный parser `git status --porcelain`;
- partial patch из-за brittle anchors;
- неполная Python test environment;
- `.venv` без pip;
- generated `__pycache__`;
- PowerShell `$code:` parser error;
- устаревшие string-based tests;
- `always()` в cancellation path;
- empty artifact под `if-no-files-found: warn`;
- root-owned cancellation evidence;
- удаление preflight report inner cleanup;
- неверное применение byte-canonical validator к sanitized public JSON;
- старый runner с тем же именем в `Downloads`.

Подробный разбор, исправления и prevention:
[`../../docs/chatgpt-manual-operations.md`](../../docs/chatgpt-manual-operations.md).

## Что не запускалось

- `perf100`;
- warm repeat;
- worker comparison;
- visual regression;
- retries/quarantine;
- source-build cloud;
- третий successful full;
- Fast CI/Docker после docs-only closeout.

Причина: эти проверки не входят в E2E-I4 completion criteria; exact production
HEAD уже прошёл required package and controlled A/B gates.

## Security review

Подтверждено:

- cancellation artifact ограничен allowlist;
- package bytes и full screenshots не входят в cancellation artifact;
- source/public evidence валидируется;
- токены/private paths не найдены в public text evidence;
- dashboard/server/security contracts не ослаблены;
- cleanup scoped по process group, Compose project и artifact root;
- cloud source-build fallback не добавлен.

## Final decision

```text
E2E-I4: COMPLETE
required implementation: published
local verification: PASS
Fast CI exact package: PASS
controlled cancellation A: PASS
successful standard/full B: PASS
artifact validation: PASS
documentation: finalized by this closeout
PR: ready for review after docs-only commit
merge: not performed
E2E-I5: not started
```
