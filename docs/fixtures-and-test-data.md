# Fixtures and test data

Снимок документации: 2026-07-06.

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

Profile fixtures в `mockReport` синтетические: identity `E2E`, normal history,
несколько deterministic decks и revlog-estimate time. `ProfilePage.test.tsx`
также строит empty/missing-time/custom-date variants; реальные имена и runtime
`profile.json` не коммитятся.

Stage 4 mock добавляет bounded `activityHub`: 90-day active/inactive pattern,
unavailable early range, seven daily decks, milestone/return/record и two
completed weeks. Docker synthetic collection распределяет revlog по нескольким
дням/неделям и добавляет safe Activity fixture decks; APKG fixture не меняется.

Stage 5 mock добавляет normalized `deckHub`: multiple roots, direct parent,
danger descendant под stable aggregate, attention/preliminary, duplicate short
names, long/Unicode names и filtered excluded count. Pure tests отдельно строят
161-node и malformed/cyclic fixtures.

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

Decks v2 synthetic data также создаёт `E2E Decks`, `E2E Grammar`, шестой
уровень `E2E Deep`, duplicate `N3` и пустую filtered deck
`E2E Filtered Health Excluded`. Review patterns детерминированно дают healthy,
attention, danger и preliminary states.

## APKG fixtures

Tracked APKG fixture:

```text
docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg
```

Это owner-authored, sanitized и owner-authorized regression deck для Cards
rendering preview. В fixture сейчас:

- 10 cards;
- 10 notes;
- 4 note types;
- 13 media entries.

Cards, fields, templates и deck structure созданы и многократно переработаны
владельцем с AI assistance. Все 13 media entries созданы владельцем: нарисованы,
записаны либо сгенерированы под его управлением. Владелец разрешает публичное
распространение этой fixture как части repository, tests, Docker E2E и CI
artifacts. Это разрешение относится только к fixture и не задаёт лицензию для
остального репозитория. Provenance рядом с файлом зафиксирован в
`docker/anki-e2e/fixtures/README.md`.

Не путать эту owner-authored APKG с generated synthetic Docker collection из
`docker/anki-e2e/seed-collection.py`.

Default Docker E2E сначала создает synthetic collection, затем importer
автоматически добавляет tracked APKG fixture, если файл есть в checkout. Strict
APKG mode делает отсутствие или неудачный import ошибкой:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture
```

Perf100 smoke использует эту же tracked APKG fixture и не создает новую APKG.
Docker E2E импортирует fixture, затем клонирует импортированные notes/cards в
изолированной collection до 100 problematic cards:

```powershell
.\scripts\run_full_check.ps1 -DockerOnly -RequireApkgFixture -Perf100
```

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
| several card templates | Есть owner-authorized tracked APKG + synthetic coverage | `docker/anki-e2e/fixtures/asr-e2e-render-fixtures.apkg`, `seed-collection.py` |

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

Runtime screenshots организованы под `e2e-artifacts/screenshots/cards/` по
fixture (`synthetic`/`apkg`), mode (`table`/`tiles`/`anki-preview`) и theme.
Это generated proof, а не source fixture.

## Как обновлять fixtures безопасно

1. Описать, какой bug/edge case fixture покрывает.
2. Проверить, что данные synthetic или sanitized.
3. Не включать реальные token/paths/profile names.
4. Добавить test, который действительно использует fixture.
5. Для Cards/rendering проверить unit tests и, при необходимости, Docker E2E.
6. Обновить этот документ, если появляется новый tracked fixture.
