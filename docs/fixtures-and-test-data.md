# Fixtures and test data

**Снимок документации:** 2026-07-23.

Этот документ разделяет unit/frontend fixtures, committed real-deck fixtures и runtime artifacts. Ни один тип данных не должен подменять другой.

## Python fixtures

Dashboard JSON fixtures в `tests/fixtures/dashboard/` используются для payload/cache/report tests. Это deterministic synthetic inputs, а не Anki collection и не доказательство real-Anki runtime.

## Frontend mock data

```text
web-dashboard/src/data/mockReport.ts
```

`mockReport` используется только для frontend dev mode/UI tests. Он не доказывает работу `/api/report`, native Anki rendering или media routes.

## Committed real-deck fixtures

Docker real-Anki E2E использует только:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Contract:

```text
docker/anki-e2e/fixtures/real-decks/manifest.json
docker/anki-e2e/fixtures/real-decks/README.md
```

Packages являются owner-provided рабочими колодами, разрешёнными владельцем для публичного хранения и CI этого репозитория. Они не содержат profile token/runtime collection.

| Package | Notes | Cards | Used note types | Media |
| --- | ---: | ---: | ---: | ---: |
| Words N1 | 718 | 718 | 1 | 2 153 |
| Grammar N5 | 133 | 133 | 1 | 0 |
| Java | 70 | 70 | 1 | 0 |

Точные sizes, SHA-256, anchors, expected fields, fingerprints, media capabilities и scenario mutations зафиксированы в manifest.

## Что harness не создаёт

- synthetic decks/note types/fields/templates;
- synthetic notes/cards/media;
- fake profile learning content;
- fallback collection;
- cloned cards для performance.

`seed-collection.py` создаёт только empty disposable collection. Пустой системный `Default` deck без cards не считается fixture content.

Удалённый legacy source:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

Его synthetic 10-card contract больше не поддерживается.

## Import contract

Все три packages обязательны и импортируются через:

```text
Collection.import_anki_package(ImportAnkiPackageRequest)
```

Hard failure:

- missing/duplicate package;
- size/SHA mismatch;
- importer error;
- inventory mismatch;
- missing/ambiguous anchor;
- fingerprint/field/template mismatch;
- missing required media.

External APKG override отсутствует.

`docker/anki-e2e/local-input/` используется только для exact `.ankiaddon` handoff, а не для collection fixtures.

## Scenario data

Разрешены только study-state mutations существующих cards:

- scheduling state;
- revlog;
- due/interval/factor/reps/lapses;
- suspended;
- buried.

Fields/templates/media и note/card counts не меняются.

`perf100` выбирает 100 distinct imported cards.

## Manifest-driven anchors

Generic scripts получают concrete identifiers из manifest/runtime reports.

| Capability | Real source |
| --- | --- |
| Words preview | real Words note |
| Grammar preview | real Grammar note |
| Java preview/`language-java` | real Java note |
| audio/GIF/image | real Words media |
| action/recheck | imported card + study-state |
| low success | imported card + revlog |
| suspended/buried | imported cards |
| Japanese Inspection Profile | real `Слова` note type |
| Programming Inspection Profile | real Java note type |
| Notification lifecycle | `cards-action-recheck` + `cards-low-success` anchors |

Notification fixture не содержит synthetic card/deck IDs и берёт scheduler timestamp из scenario evidence.

## Runtime evidence

Генерируется, но не коммитится:

```text
e2e-artifacts/reports/real-deck-manifest-report.json
e2e-artifacts/reports/real-deck-import-report.json
e2e-artifacts/reports/collection-inventory.json
e2e-artifacts/reports/anchor-resolution-report.json
e2e-artifacts/reports/scenario-application-report.json
e2e-artifacts/reports/notification-fixture-proof.json
e2e-artifacts/screenshots/
```

Runtime evidence не является source fixture.

## Что можно коммитить

- маленькие deterministic unit JSON fixtures;
- sanitized frontend mock data;
- три owner-authorized real APKG;
- manifest/README с checksums/anchors/fingerprints;
- generic tests без embedded content fallback.

## Что нельзя коммитить

- `collection.anki2` или полный profile;
- произвольные личные APKG;
- token-bearing URLs/readiness;
- `e2e-artifacts/`, screenshots, logs, HTML dumps;
- cache/media DB/package outputs/`.ankiaddon`;
- `docker/anki-e2e/local-input/`.

## Обновление working decks

1. Зафиксировать причину и capability.
2. Заменить только нужный `.apkg`.
3. Проверить provenance и отсутствие secrets/profile metadata.
4. Пересчитать size/SHA-256.
5. Повторно получить inventory.
6. Проверить anchors/fingerprints/media.
7. Обновить manifest.
8. Не менять generic runtime ради конкретного content.
9. Выполнить focused contract tests.
10. Выполнить один policy-compliant real-Anki proof.

Изменение только APKG/manifest/E2E harness не требует нового Fast CI package, если `.ankiaddon` не менялся и полный diff проходит `harness-only` allowlist. Package-impacting diff требует новый Fast CI.

Правила: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md).
