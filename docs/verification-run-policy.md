# Политика проверочных запусков

**Статус:** обязательная политика, актуализирована 2026-07-23.

Полный real-Anki E2E — integration gate, а не обычный цикл разработки.

Основной принцип: отдельно определять, изменился ли production package, и отдельно — изменился ли только E2E harness. Exact `.ankiaddon` и текущий E2E checkout являются разными identities.

Подробный контракт: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md).

## Классификация изменения до запуска CI

### Package-impacting

Изменение может повлиять на `.ankiaddon` bytes или production behavior:

```text
focused/local checks
→ commit/push
→ Fast CI на package-impacting head — PASS
→ exact package artifact
→ один targeted real-Anki scope, если его требует риск
→ standard/full только при эскалации matrix/planner
```

Примеры: `anki_study_report/`, `web-dashboard/`, dependencies/lockfiles, package/build scripts, package metadata, add-on manifest/config/changelog и release packaging.

### Harness-only

Изменены только разрешённые Docker E2E/orchestration/artifact/test files, а package bytes неизменны:

```text
focused harness tests
→ commit/push
→ reuse последнего подходящего successful Fast CI package
→ fail-closed ancestry + complete-diff validation
→ один risk-required targeted/full E2E
```

Новый Fast CI в этом режиме **не нужен**. Фактический allowlist находится в `scripts/validate_e2e_harness_reuse.py`.

### Только документация

После уже успешных package/E2E gates:

```text
git diff --check
→ проверить links, paths и code fences
→ без нового Fast CI и Docker E2E
```

Fast CI для docs-only запускается только при отдельном требовании branch protection, workflow или владельца.

## Exact identities

### Package identity

Successful Fast CI публикует:

- diagnostics artifact;
- exact `.ankiaddon` artifact;
- `testedCommitSha`;
- `sourceHeadSha`;
- package SHA-256;
- package size;
- transport digest.

### Harness identity

E2E run фиксирует current workflow/harness SHA отдельно:

- `e2eCheckoutSha`;
- `workflowSourceSha`;
- reuse mode;
- changed paths и их hash.

Разные package/harness SHA допустимы только при validated `harness-only` reuse.

## Real-deck E2E foundation

Docker collection всегда строится из трёх committed рабочих колод:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Manifest:

```text
docker/anki-e2e/fixtures/real-decks/manifest.json
```

Строгий manifest/checksum/import/inventory/anchor/scenario contract является обязательной частью каждого Docker E2E. Synthetic notes/cards/templates/media, external APKG override, cloning и fallback collection запрещены.

`perf100` разрешён только для явной performance-задачи. Он выбирает 100 distinct existing cards.

## Выбор целевого scope

| Изменение | Целевой gate |
| --- | --- |
| Search и Safe Actions | `standard/global` |
| Cards, native preview, media, Triage, Inspection Profiles | `standard/cards`, `verify_restart=true` |
| Statistics и FSRS | `standard/stats` |
| Decks | `standard/decks` |
| Calendar/Activity | `standard/activity` |
| Settings, privacy, telemetry | `standard/settings` |
| Notifications | `standard/notifications`, `verify_restart=true` |
| общий startup/server/package/E2E infrastructure | целевой scope по риску, затем `standard/full` |
| release path | `standard/full` с exact release artifact |

Targeted scope не ослабляет real-deck foundation: все три packages, checksums, inventory, anchors и scenarios остаются обязательными.

## Когда обязателен final `standard/full`

Full gate нужен, когда изменение затрагивает общий contour:

- startup/profile lifecycle;
- shared server/dashboard/package path;
- release artifact;
- notification + telemetry + restart integration;
- общий E2E runner/artifact contract;
- полную замену collection foundation;
- несколько продуктовых scopes одновременно.

Full не запускается после каждого небольшого исправления. После конкретного harness-only fix повторяется только тот gate, который подтверждает исправление и ещё не имеет успешного proof для текущей package/harness пары.

## Fast CI package reuse

Docker consumer обязан:

1. получить явно указанный successful Fast CI run;
2. проверить repository, run status и artifact IDs;
3. проверить diagnostics и package metadata;
4. проверить package bytes/size/SHA-256;
5. проверить ancestry package commit → harness commit;
6. проверить полный changed-path diff;
7. отклонить package-impacting и unrelated paths;
8. запустить current harness без source-build fallback;
9. повторно проверить package SHA после E2E;
10. опубликовать обе SHA и reuse evidence.

Если package artifact истёк, неоднозначен или не соответствует metadata, нужен новый successful Fast CI package. Нельзя обходить ошибку локальной сборкой внутри cloud workflow.

## Release

Release infrastructure, version source, changelog, publisher и AnkiWeb adapter всегда классифицируются как package-impacting/full.

Release caller передаёт exact current release archive через `ANKI_E2E_PREBUILT_ADDON_PATH`. Его SHA-256 проверяется до и после `standard/full`. Harness-only reuse старого Fast CI package не является release proof.

## Stop-loss

После failure сначала изучаются reports, logs, screenshots и root cause.

Разрешён один повтор соответствующего gate после конкретного исправления или подтверждённой infrastructure failure.

Запрещены без отдельной задачи:

- blind rerun;
- warm-cache repeat;
- worker comparison;
- resource benchmark;
- повтор успешного package-producing Fast CI для тех же package bytes;
- повтор успешного targeted/full gate для неизменной package/harness пары;
- локальный full Docker после успешного cloud full;
- source-build fallback при ошибке package handoff;
- `perf100` как обычный acceptance gate.

Вторая одинаковая ошибка прекращает перезапуски.

## Локальный Docker

Допустим, когда:

- диагностируется сам Docker/runtime harness;
- cloud gate ещё не запускался для текущей пары;
- владелец явно выбрал local proof;
- запуск не дублирует successful cloud gate.

Локальный PASS не заменяет обязательный cloud package/harness proof.

## Verification planner

`scripts/plan_verification.py`:

- детерминирован;
- не запускает workflows;
- не хранит state выполненных gates;
- не может понизить package/release/runtime risk;
- может быть повышен человеком или агентом.

Planner recommendation не отменяет package-impact classification и reuse boundary.

## Обязательная фиксация результата

Итоговый отчёт должен содержать:

- package tested commit SHA;
- E2E harness/workflow SHA;
- reuse mode;
- Fast CI run ID/status;
- package artifact name, SHA-256, size и transport digest;
- Docker mode/scope/restart policy;
- PASS/FAIL пяти real-deck reports;
- targeted/full run IDs;
- E2E artifact name/digest;
- sanitizer result;
- что не запускалось;
- причину каждого пропуска/failure;
- подтверждение отсутствия ненужного повторного Fast CI или exact-pair E2E.

Исторический пример: [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md).
