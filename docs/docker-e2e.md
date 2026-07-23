# Docker E2E

**Снимок документации:** 2026-07-23

Подробная техническая инструкция находится в
[`docker/anki-e2e/README.md`](../docker/anki-e2e/README.md). Эта страница
фиксирует место real-Anki Docker E2E в общем verification process и решения,
которые нельзя случайно откатить.

Для диагностики падений см. [`troubleshooting.md`](troubleshooting.md), а правила
запусков — [`verification-run-policy.md`](verification-run-policy.md).

## Назначение

Docker E2E запускает exact add-on package внутри реального Anki Desktop в
изолированном Linux-профиле. Он нужен для рисков, которые не закрываются только
pytest/Vitest:

- startup hooks и profile lifecycle Anki;
- dashboard readiness, token auth и loopback server;
- public package installation layout;
- native card rendering и Shadow DOM;
- real audio/GIF/image media routes;
- Cards, Triage, exact action/recheck и Inspection Profiles;
- restart persistence;
- browser console/page/request/network behavior;
- redacted structured evidence.

Это integration gate, а не обычный цикл разработки.

## Единственный источник collection content

Disposable collection строится только из committed рабочих колод:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Контракт пакетов и сценарных якорей:

```text
docker/anki-e2e/fixtures/real-decks/manifest.json
```

В каждом mode обязательны:

1. manifest schema validation;
2. размер и SHA-256 каждого package;
3. импорт всех трёх packages в manifest order;
4. inventory notes/cards/note types/decks/media;
5. уникальное разрешение anchors;
6. zero-synthetic и zero-cloning proof.

Запрещены:

- generated synthetic notes/cards/note types/templates/media;
- старый `asr-e2e-render-fixtures.apkg`;
- external/local-only APKG path;
- fallback после missing/checksum/import/anchor failure;
- клонирование content для `perf100`;
- изменение импортированных fields/templates/media при restart.

Пустая системная Anki metadata без cards не считается test content. Harness не
создаёт в ней notes/cards/templates/media.

## Import и scenarios

Harness создаёт empty disposable collection и импортирует packages через
публичный Anki API:

```text
Collection.import_anki_package(ImportAnkiPackageRequest)
```

Concrete GUIDs, field names, structure fingerprints, media requirements и
Inspection Profile mappings находятся только в manifest. Generic scripts
работают с runtime inventory и resolved anchors.

После импорта разрешены только bounded mutations существующих cards:

- scheduling state;
- due/interval/factor/reps/lapses;
- revlog rows;
- suspended state;
- buried state.

Количество notes/cards после import не должно меняться.

## Основные команды

PowerShell:

```powershell
./scripts/run_anki_e2e_docker.ps1
./scripts/run_full_check.ps1 -DockerOnly
./scripts/run_full_check.ps1 -DockerOnly -CleanDocker
```

WSL/Arch с PowerShell Core:

```bash
cd ~/projects/anki-study-report
pwsh -NoProfile -File ./scripts/run_anki_e2e_docker.ps1
```

Только image build:

```powershell
./scripts/run_anki_e2e_docker.ps1 -BuildOnly
```

Уже подготовленный image:

```powershell
./scripts/run_anki_e2e_docker.ps1 -NoBuild
```

Входного параметра для произвольного `.apkg` или media directory нет.

## Mode и scope

Canonical modes:

```text
standard
perf100
```

`standard` — acceptance mode.

`perf100` разрешён только для отдельной performance-задачи. Он выбирает ровно
100 distinct existing imported card IDs и применяет study-state без создания
или клонирования notes/cards.

Legacy cloud input `strict-apkg` временно принимается как compatibility alias и
немедленно нормализуется в `standard`. Он не создаёт отдельный fixture source,
не меняет import contract и не допускает fallback.

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

Scope меняет продуктовые assertions, но никогда не отключает три package imports,
checksums, inventory, anchors и zero-synthetic proof.

## Package source

Docker E2E поддерживает три взаимоисключающих source add-on package:

### `source-build`

Только local/default development contour. Контейнер выполняет offline frontend
install, production build и package validation.

### `fast-ci-artifact`

Cloud consumer получает exact successful Fast CI run, проверяет repository,
tested SHA, artifact identity и внутренний SHA-256, затем устанавливает именно
этот archive. Fallback на source build запрещён.

### `release-artifact`

Release gate получает exact current release archive и обязательный SHA-256.
Release flow не подменяется Fast CI artifact.

Cloud image берётся по exact GHCR digest. Mutable `latest`, fallback build и
неоднозначный artifact запрещены.

## Ключевые пути контейнера

```text
/workspace                                      read-only source checkout
/e2e/workspace-build                            writable copied build tree
/e2e/anki-data                                  disposable Anki base
/e2e/anki-data/prefs21.db                       profile metadata
/e2e/anki-data/E2E                              disposable profile
/e2e/anki-data/addons21/anki_study_report_e2e   installed add-on
/e2e/artifacts                                  runtime evidence
```

Add-on устанавливается на base-level path:

```text
/e2e/anki-data/addons21/anki_study_report_e2e
```

Не переносить его в profile-level `E2E/addons21/`.

## Live progress и failure diagnostics

Долгие package стадии выводят сообщения с префиксом:

```text
[real-decks]
```

Пример ожидаемой последовательности:

```text
validating manifest
package 1/3 words: checksum PASS
importing package 1/3: words
imported words: ...
resolving anchors
applying scenarios
collection ready
browser smoke PASS
```

При ошибке создаётся `reports/real-deck-failure.json` с:

- stage;
- package/anchor/subject ID;
- error type и message;
- last completed step;
- traceback.

После ошибки нет fallback collection.

## Обязательные evidence reports

Успешный artifact manifest обязан индексировать PASS:

```text
reports/real-deck-manifest-report.json
reports/real-deck-import-report.json
reports/collection-inventory.json
reports/anchor-resolution-report.json
reports/scenario-application-report.json
```

Дополнительно обязательны API/browser/timing/package reports, перечисленные в
техническом README.

`collection-inventory.json` должен содержать:

```text
contentSource = committed-real-apkg-only
syntheticNotes = 0
syntheticCards = 0
syntheticMedia = 0
```

`scenario-application-report.json` должен показывать:

```text
notesCreated = 0
cardsCreated = 0
notesOrCardsCloned = 0
```

## Browser evidence

Canonical page proof:

```text
screenshots/pages/<route>/<light|dark>.png
```

Real native front/back proof:

```text
screenshots/cards/real-decks/words-preview/<light|dark>.png
screenshots/cards/real-decks/grammar-preview/<light|dark>.png
screenshots/cards/real-decks/java-preview/<light|dark>.png
```

Cards state proof:

```text
screenshots/states/cards/real-deck-inbox/<light|dark>.png
```

Browser smoke проверяет:

- `renderSource = anki_native`;
- непустой front/back HTML;
- отсутствие raw `[sound:...]` и `[anki:play:...]`;
- Java `language-java` contour;
- real audio/GIF/image media;
- action/recheck, low-success, suspended и buried states;
- отсутствие console/page/request errors;
- отсутствие unexpected external requests;
- отсутствие document-level horizontal overflow на Cards route.

Screenshots после cloud run нужно просмотреть содержательно; одного manifest/count
недостаточно.

## Readiness и startup markers

Runtime files:

```text
runtime/dashboard-ready.json
runtime/addon-e2e-events.jsonl
```

Ожидаемая цепочка events включает import, hook, collection availability, report
build, server start, publish и readiness write. Token может находиться в
readiness file внутри artifact archive, но не должен попадать в logs, screenshots,
DOM dumps или artifact manifest.

## Restart

`full` автоматически требует restart. Targeted Cards/Inspection Profiles proof
задаёт `verify_restart=true`.

Restart только останавливает и повторно запускает Anki. Он не изменяет real note
types, fields, templates или media. После restart повторяется API smoke и
проверяется persistence stored profiles/state.

## Security и privacy

- Dashboard слушает только loopback внутри disposable environment.
- Checkout монтируется read-only; build выполняется в writable copy.
- Token не логируется и не индексируется.
- Media traversal и absolute paths отклоняются.
- Templates не превращаются в произвольный iframe/JavaScript execution surface.
- Runtime collection/profile/media/logs/screenshots/reports не коммитятся.
- Artifact manifest принимает только существующие relative unique paths и
  отклоняет traversal, missing files, duplicates и token-bearing URL.

## Verification sequence

```text
focused tests
→ Fast CI exact SHA
→ один risk-required targeted Docker run
→ один final standard/full только при matrix/policy escalation
```

Для полной замены collection foundation обязательны:

1. focused contract tests;
2. Fast CI exact head;
3. один `standard/cards` с restart;
4. один final `standard/full` exact tree.

Успешный exact-tree gate не повторяется. После одинакового второго падения
слепые reruns прекращаются; сначала анализируется первопричина и evidence.
