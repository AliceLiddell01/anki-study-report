# Fixtures and test data

**Снимок документации:** 2026-07-23

Этот документ разделяет unit/frontend fixtures, committed real-deck fixtures и
runtime artifacts. Ни один тип данных не должен подменять другой.

## Python fixtures

Dashboard JSON fixtures:

```text
tests/fixtures/dashboard/cache_snapshot.json
tests/fixtures/dashboard/empty_collection.json
tests/fixtures/dashboard/large_collection.json
tests/fixtures/dashboard/minimal_metrics.json
tests/fixtures/dashboard/normal_day.json
```

Они используются Python tests для payload, cache и report behavior. Это
синтетические deterministic inputs, а не Anki collection и не доказательство
работы реального Anki runtime.

## Frontend mock data

```text
web-dashboard/src/data/mockReport.ts
```

`mockReport` используется только для frontend dev mode и UI tests. Он не является
доказательством работы `/api/report`, Anki rendering или media routes.

Frontend mock data может содержать synthetic profiles, decks, history, Statistics,
Activity, Cards и Notifications states. Эти данные не импортируются в Docker Anki
collection.

## Committed real-deck fixtures

Docker real-Anki E2E использует только:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Контракт:

```text
docker/anki-e2e/fixtures/real-decks/manifest.json
docker/anki-e2e/fixtures/real-decks/README.md
```

Пакеты являются owner-provided рабочими колодами, разрешёнными владельцем для
публичного хранения и использования в tests/CI этого репозитория. Они не содержат
profile token или runtime collection.

Текущий inventory source:

| Package | Notes | Cards | Used note types | Media |
| --- | ---: | ---: | ---: | ---: |
| Words N1 | 718 | 718 | 1 | 2,153 |
| Grammar N5 | 133 | 133 | 1 | 0 |
| Java | 70 | 70 | 1 | 0 |

Точные sizes, SHA-256, note GUID anchors, template ordinals, expected fields,
structure fingerprints, media capabilities и разрешённые scenario mutations
зафиксированы только в `manifest.json`.

## Что real-Anki harness не создаёт

После перехода на committed working decks harness не создаёт:

- synthetic decks;
- synthetic note types;
- synthetic fields/templates;
- synthetic notes/cards;
- synthetic media;
- fake profile learning content;
- fallback collection content.

`seed-collection.py` создаёт только пустую disposable collection. Возможная пустая
системная metadata Anki (`Default` deck без карточек) не является test fixture и
не учитывается как collection content.

Старый файл удалён:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

Его 10-card regression contract, фиксированные media names и synthetic deck
hierarchy больше не поддерживаются.

## Import contract

Все три пакета обязательны и импортируются в manifest order через публичный Anki
API:

```text
Collection.import_anki_package(ImportAnkiPackageRequest)
```

Hard failure возникает при:

- missing package;
- duplicate package ID/path;
- size mismatch;
- checksum mismatch;
- importer error;
- unexpected note/card/note-type/media count;
- missing или ambiguous anchor;
- fingerprint/fields/template mismatch;
- missing required real media.

Внешнего APKG override и local-input mount нет.

## Scenario data

После импорта разрешено менять только study-state существующих импортированных
cards:

- scheduling state;
- revlog rows;
- due/interval/factor/reps/lapses;
- suspended state;
- buried state.

Запрещено менять содержимое fields/templates/media или создавать notes/cards.

`perf100` выбирает 100 различных существующих импортированных card IDs. Он не
клонирует notes или cards.

## Manifest-driven anchors

Generic scripts не содержат конкретных слов, GUID, filenames или field mappings.
Они получают их из manifest и записывают resolved IDs в runtime report.

Основные capabilities:

| Capability | Manifest anchor source |
| --- | --- |
| Words native front/back | real Words note |
| Grammar native front/back | real Grammar note |
| Java native front/back и `language-java` | real Java note |
| audio | real Words media reference |
| GIF и static image | real Words media references |
| action/recheck | existing imported Words card + study-state |
| low success | existing imported Words card + revlog |
| suspended/buried | existing imported Words cards |
| Japanese Inspection Profile | real `Слова` fields/fingerprint |
| Programming Inspection Profile | real Java fields/fingerprint |

## Runtime evidence

Docker run генерирует, но не коммитит:

```text
e2e-artifacts/reports/real-deck-manifest-report.json
e2e-artifacts/reports/real-deck-import-report.json
e2e-artifacts/reports/collection-inventory.json
e2e-artifacts/reports/anchor-resolution-report.json
e2e-artifacts/reports/scenario-application-report.json
```

Browser evidence:

```text
e2e-artifacts/screenshots/pages/
e2e-artifacts/screenshots/cards/real-decks/
e2e-artifacts/screenshots/states/cards/real-deck-inbox/
```

Runtime evidence не является source fixture.

## Что можно коммитить

- Маленькие deterministic JSON fixtures для unit tests.
- Sanitized frontend mock data.
- Три owner-authorized real APKG из manifest contract.
- Fixture README и manifest с checksums/anchors/fingerprints.
- Generic tests, которые не встраивают содержимое колод в runtime code.

## Что нельзя коммитить

- `collection.anki2` или полный Anki profile.
- Произвольные личные APKG без явного provenance/authorization.
- Token-bearing URLs и readiness files.
- `e2e-artifacts/`, screenshots, logs, HTML dumps и reports локального run.
- Cache, media DB, package outputs и `.ankiaddon`.
- `docker/anki-e2e/local-input/` или другой внешний fixture staging directory.

## Как обновлять fixtures

1. Зафиксировать причину обновления и затрагиваемую capability.
2. Заменить только соответствующий `.apkg`.
3. Проверить provenance и отсутствие секретов/profile metadata.
4. Пересчитать size и SHA-256.
5. Повторно получить note/card/note-type/media inventory.
6. Проверить все manifest anchors и note-type structure fingerprints.
7. Не менять generic runtime code ради нового слова или filename.
8. Запустить focused contract tests.
9. После exact-head Fast CI выполнить один policy-compliant real-Anki proof.

Если anchor больше не уникален, его нужно заменить на другой реальный устойчивый
anchor в manifest. Нельзя добавлять fallback selector или synthetic replacement.
