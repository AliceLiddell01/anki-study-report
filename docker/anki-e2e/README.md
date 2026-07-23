# Docker real-Anki E2E

**Снимок документации:** 2026-07-23

Этот контур запускает собранное расширение в реальном Anki Desktop внутри Docker,
поднимает локальный token-protected dashboard и проверяет API, browser behavior,
нативный рендер карточек, media, restart и публично безопасные артефакты.

Полный Docker E2E — integration gate. Он не предназначен для обычного цикла
разработки и запускается по политике из
[`docs/verification-run-policy.md`](../../docs/verification-run-policy.md).

## Единственный источник collection content

Disposable collection содержит только данные, импортированные из трёх committed
рабочих колод:

```text
fixtures/real-decks/words-n1.apkg
fixtures/real-decks/grammar-n5.apkg
fixtures/real-decks/java-core.apkg
```

Контракт пакетов и сценарных якорей расположен в:

```text
fixtures/real-decks/manifest.json
```

В Docker E2E запрещены:

- synthetic notes, cards, note types, templates и media;
- старый `asr-e2e-render-fixtures.apkg`;
- внешний или local-only APKG override;
- fallback при отсутствии пакета, checksum mismatch или ошибке импорта;
- клонирование notes/cards для performance-сценария;
- конкретные fixture GUID, filenames и field mappings вне manifest.

Пустой системный `Default` deck, который Anki может сохранять как внутреннюю
bootstrap metadata без карточек, не считается test content. Harness не создаёт в
нём notes/cards/templates/media.

## Pipeline

Контейнер выполняет один последовательный lifecycle:

1. копирует checkout в fresh writable build directory;
2. устанавливает frontend dependencies из подготовленного store;
3. собирает frontend и `.ankiaddon`;
4. создаёт пустую disposable collection;
5. валидирует manifest, размеры и SHA-256 всех трёх `.apkg`;
6. импортирует пакеты в manifest order через публичный
   `Collection.import_anki_package(ImportAnkiPackageRequest)`;
7. строит inventory и доказывает, что все notes/cards появились только в ходе
   этих трёх импортов;
8. разрешает manifest anchors по `note GUID + template ordinal` и проверяет
   note-type structure fingerprint, поля, media capabilities и HTML classes;
9. изменяет только scheduling/revlog/due/interval/ease/suspended/buried state
   существующих импортированных карточек;
10. запускает реальный Anki и ждёт readiness;
11. выполняет API smoke и Playwright browser proof;
12. при необходимости проверяет restart;
13. формирует redacted artifact manifest.

Старые имена entrypoints сохранены только как thin orchestration adapters:

```text
seed-collection.py                  empty collection only
import-apkg-fixture.py              mandatory manifest-driven import
mark-apkg-cards-problematic.py      generic study-state scenarios only
```

Они больше не содержат synthetic fixture definitions или card cloning.

## Логирование

Долгие стадии печатают живой прогресс в консоль. Для real-deck preparation
используется префикс:

```text
[real-decks]
```

Ожидаемые сообщения включают:

```text
validating manifest
package 1/3 words: validating checksum
package 1/3 words: checksum PASS
importing package 1/3: words
imported words: ...
resolving anchors
applying scenarios
collection ready
browser smoke PASS
```

При ошибке `real-deck-failure.json` содержит:

- stage;
- subject/package/anchor ID;
- error type и message;
- last completed step;
- traceback.

Никакого fallback после такой ошибки нет.

## Локальный запуск

Из PowerShell:

```powershell
./scripts/run_anki_e2e_docker.ps1
```

Из WSL/Arch с установленным PowerShell Core:

```bash
cd ~/projects/anki-study-report
pwsh -NoProfile -File ./scripts/run_anki_e2e_docker.ps1
```

Только Docker-часть общего check:

```powershell
./scripts/run_full_check.ps1 -DockerOnly
```

Fresh volumes:

```powershell
./scripts/run_full_check.ps1 -DockerOnly -CleanDocker
```

Только build image:

```powershell
./scripts/run_anki_e2e_docker.ps1 -BuildOnly
```

Использовать уже собранный image:

```powershell
./scripts/run_anki_e2e_docker.ps1 -NoBuild
```

Входного параметра для произвольного APKG нет. Все три committed packages всегда
обязательны.

## Mode и scope

Основной mode:

```text
standard
```

`perf100` — отдельный performance contour. Он выбирает ровно 100 различных
существующих импортированных card IDs и применяет только study-state. Notes и
cards не создаются и не клонируются.

```powershell
./scripts/run_full_check.ps1 -DockerOnly -Perf100
```

Поддерживаемые scope:

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

Пример:

```powershell
./scripts/run_full_check.ps1 -DockerOnly -E2EScope cards -VerifyRestart true
```

Scope не меняет источник collection content: три real APKG импортируются всегда.

## Обязательные real-deck reports

Успешный artifact manifest обязан индексировать:

```text
reports/real-deck-manifest-report.json
reports/real-deck-import-report.json
reports/collection-inventory.json
reports/anchor-resolution-report.json
reports/scenario-application-report.json
```

Дополнительные proof reports:

```text
reports/api-smoke-first.json
reports/browser-smoke-first.json
reports/screenshot-performance.json
reports/screenshot-performance.md
reports/e2e-phase-timings.json
reports/e2e-phase-timings.md
reports/e2e-performance-summary.json
reports/e2e-performance-summary.md
```

`collection-inventory.json` фиксирует:

- totals по notes/cards/used note types/decks/media;
- package ownership импортированных IDs;
- реальные note-type fields/templates/fingerprints;
- `contentSource = committed-real-apkg-only`;
- нулевые synthetic counts.

`scenario-application-report.json` фиксирует before/after study state, revlog IDs,
нулевые content mutations и distinct-card proof для `perf100`.

## Browser evidence

Page screenshots:

```text
screenshots/pages/<route>/<light|dark>.png
```

Нативный expanded front/back proof реальных колод:

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
- непустые front/back HTML;
- отсутствие raw `[sound:...]` и `[anki:play:...]` markers;
- Java `language-java` contour;
- real audio/GIF/image media routes;
- suspended/buried/low-success/action-recheck state;
- отсутствие page errors, console errors, failed requests и внешнего network.

## Failure contract

Run считается failed, если:

- отсутствует manifest или любой пакет;
- размер или SHA-256 не совпал;
- официальный Anki importer вернул ошибку;
- import inventory не совпал с manifest;
- anchor отсутствует, неоднозначен или разрешён вне заявленного пакета;
- fingerprint/fields/template/media contract не совпал;
- scenario пытается применить незаявленный mutation;
- количество notes/cards изменилось после импорта;
- `perf100` не смог выбрать 100 distinct existing cards;
- обязательный report или screenshot отсутствует;
- artifact manifest содержит duplicate, traversal, missing path или token-bearing URL.

## Security и privacy

- Dashboard слушает только loopback внутри disposable environment.
- Token не логируется и не попадает в artifact manifest.
- Полный token-bearing URL не экспортируется.
- Media route проверяется на traversal и абсолютные пути.
- Templates не исполняются как произвольный iframe/JavaScript surface.
- Checkout монтируется read-only; runtime работает в fresh writable copy.
- Collection, logs, screenshots и package outputs остаются runtime artifacts и не
  коммитятся.

## Cloud gate

Cloud Full Docker workflow принимает exact successful Fast CI run для того же SHA
и использует package artifact, уже проверенный Fast CI. Финальный `standard/full`
не повторяется для того же дерева после успешного proof.

Последовательность:

```text
focused tests
→ Fast CI exact SHA
→ один risk-required targeted Docker run
→ один final standard/full, только если его требует риск
```

Warm repeats и worker comparisons выполняются только в отдельной performance-задаче.

## Обновление рабочих колод

Порядок обновления описан рядом с fixtures:

```text
fixtures/real-decks/README.md
```

Минимальный контракт обновления:

1. заменить только соответствующий `.apkg`;
2. пересчитать size и SHA-256;
3. повторно проинспектировать note/card/note-type/media counts;
4. проверить GUID/ordinal anchors, field list и structure fingerprint;
5. обновить manifest;
6. выполнить focused contract tests;
7. выполнить один policy-compliant real-Anki proof.

Нельзя менять generic harness только ради нового содержимого колоды. Новые
конкретные identifiers добавляются в manifest.
