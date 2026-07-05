# Fixtures and test data

Снимок документации: 2026-07-05.

Этот документ разделяет существующие fixtures и рекомендованное покрытие.

## Existing Python fixtures

Dashboard JSON fixtures:

```text
tests/fixtures/dashboard/cache_snapshot.json
tests/fixtures/dashboard/empty_collection.json
tests/fixtures/dashboard/large_collection.json
tests/fixtures/dashboard/minimal_metrics.json
tests/fixtures/dashboard/normal_day.json
```

Они используются Python tests для payload/cache/report behavior.

## Existing frontend mock data

```text
web-dashboard/src/data/mockReport.ts
```

`mockReport` нужен для frontend dev mode и UI tests. Он не является доказательством
работы реального `/api/report`.

## Existing Docker synthetic data

Docker E2E создает synthetic collection через:

```text
docker/anki-e2e/seed-collection.py
```

Существующие synthetic note types/cards включают:

- `E2E Japanese Vocabulary`;
- `E2E Generic Basic`;
- `E2E Custom CSS`;
- `E2E Unsafe Sanitizer`.

Synthetic media allowlist:

```text
要.gif
望.gif
要望.mp3
```

## APKG fixtures

`docker/anki-e2e/README.md` описывает optional APKG path:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

В текущем checkout tracked `.apkg` fixture не обнаружен. Поэтому APKG mode в
этой документации считается рекомендуемым/optional покрытием, а не существующим
inventory.

Local-only APKG можно передать через:

```powershell
$env:ANKI_E2E_APKG_FIXTURE="C:\path\to\asr-e2e-render-fixtures.apkg"
$env:ANKI_E2E_REQUIRE_APKG_FIXTURE="1"
.\scripts\run_anki_e2e_docker.ps1
```

## Какие данные нужны для Cards/rendering/media tests

Существующее и рекомендуемое покрытие:

| Edge case | Сейчас | Где |
| --- | --- | --- |
| custom note CSS | Есть synthetic Docker + unit tests | `seed-collection.py`, `test_note_intelligence.py` |
| audio/image/gif media | Есть synthetic Docker + unit tests | `seed-collection.py`, `test_note_intelligence.py` |
| missing fields | Есть unit coverage | `tests/test_attention_cards.py`, `test_note_intelligence.py` |
| missing audio/image/meaning/example/part of speech | Есть attention/card tests | `tests/test_attention_cards.py` |
| dangerous HTML/CSS | Есть unsafe sanitizer fixture/tests | `seed-collection.py`, `test_note_intelligence.py` |
| large fields | Рекомендуется держать в synthetic/unit coverage | Добавлять как sanitized fixture |
| non-Japanese/general note types | Есть generic basic | `seed-collection.py`, `test_note_intelligence.py` |
| several card templates | Рекомендуется APKG/synthetic coverage | Optional APKG mode или new synthetic fixture |

## Что можно коммитить

- Маленькие synthetic JSON fixtures.
- Sanitized frontend mock data.
- Маленькие synthetic APKG, если они не содержат личных данных и явно
  предназначены для regression tests.
- Generated fixture summaries только если они стабильны и нужны как source
  fixture, не runtime artifact.

## Что нельзя коммитить

- Личную `collection.anki2`.
- Личные decks/APKG без очистки.
- Real profile folders.
- Token-bearing artifacts.
- `e2e-artifacts/`.
- Screenshots/logs/HTML dumps от локального прогона.
- `docker/anki-e2e/local-input/`.

## Как обновлять fixtures безопасно

1. Описать, какой bug/edge case fixture покрывает.
2. Проверить, что данные synthetic или sanitized.
3. Не включать реальные token/paths/profile names.
4. Добавить test, который действительно использует fixture.
5. Для Cards/rendering проверить unit tests и, при необходимости, Docker E2E.
6. Обновить этот документ, если появляется новый tracked fixture.

