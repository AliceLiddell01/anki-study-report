# Docker E2E

**Снимок документации:** 2026-07-23.

Подробная техническая инструкция: [`../docker/anki-e2e/README.md`](../docker/anki-e2e/README.md).

Правила запуска: [`verification-run-policy.md`](verification-run-policy.md).

Package/harness reuse: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md).

## Назначение

Docker E2E устанавливает exact add-on package в реальный Anki Desktop 26.05 внутри изолированного Linux-профиля и проверяет runtime-риски, которые не закрываются pytest/Vitest:

- startup hooks и profile lifecycle;
- loopback token-protected dashboard;
- package installation layout;
- native card rendering и Shadow DOM;
- real audio/GIF/image media;
- Cards, Triage, exact recheck и Inspection Profiles;
- Notifications и telemetry lifecycle;
- restart persistence;
- browser console/page/request/network behavior;
- публично безопасный artifact.

Это integration gate, а не обычный цикл разработки.

## Collection content

Единственный источник:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Manifest:

```text
docker/anki-e2e/fixtures/real-decks/manifest.json
```

Каждый run обязан:

1. проверить manifest schema;
2. проверить size/SHA-256 всех packages;
3. импортировать три packages в manifest order;
4. построить inventory;
5. разрешить уникальные anchors;
6. проверить note-type fingerprints/fields/templates/media;
7. доказать zero synthetic content и zero cloning.

Запрещены:

- synthetic notes/cards/note types/templates/media;
- внешний APKG override;
- fallback collection;
- legacy importer/backend fallback;
- cloning для `perf100`;
- content mutations после import.

## Import и scenarios

Collection создаётся пустой. Import:

```text
Collection.import_anki_package(ImportAnkiPackageRequest)
```

После import допускаются только bounded mutations существующих cards:

- scheduling state;
- due/interval/factor/reps/lapses;
- revlog;
- suspended;
- buried.

Количество notes/cards не меняется.

## Lifecycle

Cloud/local canonical lifecycle:

1. Подготовить current E2E harness.
2. Получить exact prebuilt package либо выполнить local source build.
3. Создать empty disposable profile/collection.
4. Проверить и импортировать real decks.
5. Разрешить anchors и применить study-state scenarios.
6. Установить add-on.
7. Для `full/notifications` создать notification lifecycle из real-deck anchors.
8. Запустить Anki и дождаться readiness.
9. Выполнить API/browser smoke.
10. Подготовить offline telemetry queue.
11. При необходимости перезапустить Anki.
12. Проверить persistence/delivery/deletion.
13. Проверить package hash.
14. Сформировать redacted artifact.
15. Восстановить canonical result после upload/cleanup.

## Package sources

### `source-build`

Только local development/diagnostic contour. Контейнер устанавливает frontend dependencies из prepared store, собирает dashboard и package.

### `fast-ci-artifact`

Manual/reusable cloud contour. Получает exact successful Fast CI package.

Package commit и current E2E harness commit могут различаться. В таком случае обязательны ancestry и complete-diff validation с `reuseMode=harness-only`.

Новый Fast CI не нужен, если весь diff разрешён E2E allowlist и package bytes не менялись.

Fallback на source build запрещён.

### `release-artifact`

Release caller передаёт exact current release archive и SHA-256. Harness-only reuse старого Fast CI package не является release proof.

## Modes и scopes

Modes:

```text
standard
perf100
```

Legacy `strict-apkg` cloud input нормализуется в `standard`.

Scopes:

```text
full
global
stats
decks
activity
cards
settings
notifications
```

Scope не отключает real-deck import/checksum/inventory/anchors/scenarios.

`full` автоматически требует restart. Targeted persistent scopes задают `verify_restart=true` по matrix.

## Local commands

```powershell
./scripts/run_anki_e2e_docker.ps1
./scripts/run_full_check.ps1 -DockerOnly
./scripts/run_full_check.ps1 -DockerOnly -CleanDocker
./scripts/run_anki_e2e_docker.ps1 -BuildOnly
./scripts/run_anki_e2e_docker.ps1 -NoBuild
```

WSL:

```bash
pwsh -NoProfile -File ./scripts/run_anki_e2e_docker.ps1
```

Произвольный APKG/media input отсутствует.

## Cloud command

```bash
gh workflow run ci-e2e.yml \
  --repo AliceLiddell01/anki-study-report \
  --ref <branch> \
  -f mode=standard \
  -f scope=<scope> \
  -f screenshot_workers=auto \
  -f resource_telemetry=true \
  -f verify_restart=<auto|true|false> \
  -f fast_ci_run_id=<successful-package-producing-run>
```

Перед запуском не нужно создавать новый Fast CI, если изменён только allowlisted E2E harness. Consumer сам проверит reuse boundary.

## Required reports

Успешный artifact manifest обязан индексировать PASS:

```text
reports/real-deck-manifest-report.json
reports/real-deck-import-report.json
reports/collection-inventory.json
reports/anchor-resolution-report.json
reports/scenario-application-report.json
```

Также обязательны API/browser/package/timing reports для выбранного scope.

Inventory:

```text
contentSource = committed-real-apkg-only
syntheticNotes = 0
syntheticCards = 0
syntheticMedia = 0
```

Scenario proof:

```text
notesCreated = 0
cardsCreated = 0
notesOrCardsCloned = 0
```

## Browser evidence

```text
screenshots/pages/<route>/<light|dark>.png
screenshots/cards/real-decks/<preview>/<light|dark>.png
screenshots/states/cards/real-deck-inbox/<light|dark>.png
```

Browser smoke проверяет:

- `renderSource=anki_native`;
- non-empty front/back;
- отсутствие raw AV markers;
- Java `language-java` contour;
- real audio/GIF/image;
- action/recheck и study states;
- no page errors/failed requests/unexpected external requests;
- no document-level horizontal overflow на Cards.

## Notifications

Notification fixture не создаёт synthetic collection content. Он использует resolved real anchors:

```text
cards-action-recheck
cards-low-success
```

Timestamp берётся из scheduler-day evidence. Public proof schema v2 не содержит raw card/deck IDs.

## Telemetry restart

При включённой telemetry E2E проверяются:

- consent/purpose isolation;
- bounded online delivery;
- offline queue минимум 25 events;
- persistence после restart;
- post-restart delivery;
- confirmed deletion;
- credential destruction.

## Package/harness evidence

Для Fast CI handoff artifact содержит:

```text
sourceFastCiRunId
sourceFastCiTestedSha
sourcePackageSha256
e2eCheckoutSha
packageReuseMode
packageReuseChangedFileCount
packageReuseChangedPathsSha256
artifacts/reports/e2e-harness-reuse.json
```

Summary writer повторно валидирует reuse report.

## Security и privacy

- Dashboard слушает только loopback.
- Workspace/package mounts read-only.
- Token и full token-bearing URL не логируются.
- Raw readiness с token не публикуется.
- Media traversal/absolute paths отклоняются.
- Card templates не становятся iframe/JS execution surface.
- Absolute private paths редактируются; безопасные relative paths сохраняются.
- Secret-like text/private keys отклоняются fail closed.
- Runtime profile, collection, logs, screenshots и package outputs не коммитятся.

## Failure contract

Run failed при:

- missing/checksum/import/anchor/fingerprint error;
- synthetic content или content mutation;
- package/harness boundary failure;
- package hash mismatch;
- browser/API/restart/notification/telemetry failure;
- missing/unsafe artifact path;
- sanitizer failure;
- canonical result failure.

После failure нет collection/package fallback.

## Verification sequence

Package-impacting:

```text
focused tests
→ Fast CI package
→ targeted E2E
→ full по риску
```

Harness-only:

```text
focused harness tests
→ reuse existing package
→ targeted/full по риску
```

Docs-only после successful gates:

```text
git diff --check + links
→ без Fast CI/Docker
```

Исторический closeout: [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md).
