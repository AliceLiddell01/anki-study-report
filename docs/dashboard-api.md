# Dashboard API и payload-контракт

Снимок документации: 2026-07-12.

Dashboard - это локальное приложение, которое получает один опубликованный
report payload и несколько служебных API. Оно не читает Anki collection
напрямую.

## Token model

Все чувствительные endpoint-ы вызываются с query parameter:

```text
?token=<dashboard-token>
```

Frontend берет token из URL:

```text
http://127.0.0.1:8766/?token=<token>#/home
```

Если token неверный, `/api/report` возвращает `403`, и frontend показывает
состояние forbidden. В dev mode mockReport подставляется только для не-403
ошибок.

## Основные GET endpoints

```text
/api/status
/api/health
/api/server/status
/api/report
/api/media
/api/cache/status
/api/dashboard/settings
/api/profile
/api/logs/status
/api/logs/recent
/api/logs/download
/api/integrations/status
```

## Основные POST endpoints

```text
/api/cache/rebuild
/api/cache/refresh
/api/server/<action>
/api/logs/clear
/api/dashboard/settings
/api/profile
/api/statistics/query
/api/actions/<action>
```

Server actions и dashboard actions должны оставаться небольшим allowlist-слоем,
а не произвольным RPC в Anki.

## Settings API

`GET /api/dashboard/settings` возвращает normalized public settings и
`deckOptions`. `POST` принимает partial nested patch только для allowlisted
sections `dashboard`, `report`, `data`, `server`. Unknown/internal fields и
invalid enum/type/range получают `400`:

```json
{
  "error": "invalid_settings",
  "fieldErrors": {"server.port": "..."},
  "message": "Проверьте значения настроек.",
  "ok": false
}
```

Успешный ответ возвращает фактически сохранённое normalized state. Полный
contract: `docs/settings-hub.md`.

## Profile API

`GET /api/profile` возвращает public `ProfileModel`; `POST` принимает только
`customStudyStartedOn` и `deckOverviewSort`. Computed metrics, identity и
unknown fields не writable. Invalid values получают `400` и `fieldErrors`.
Source of truth — per-profile runtime `profile.json`; public ответ не содержит
token или runtime path. Полный contract: `docs/profile-mvp.md`.

## Payload source of truth

Backend builder:

```text
anki_study_report/dashboard_payload.py
```

Frontend type contract:

```text
web-dashboard/src/types/report.ts
```

Payload tests:

```text
tests/test_dashboard_payload.py
tests/test_attention_cards.py
web-dashboard/src/lib/cardAttention.test.ts
web-dashboard/src/pages/CardsPage.test.tsx
```

## Top-level StudyReport shape

Текущая frontend модель `StudyReport` содержит:

```text
dataSource?
metadata
summary
kpis
answerDistribution
activity
comparison?
decks
attentionCards?
attentionCardsStatus?
noteTypeCatalog?
forecast
fsrs
recommendations
cache?
cacheDebug?
performance?
today?
profile?
activityHub?
deckHub?
statisticsHub?
```

Backend сейчас строит основной contract через:

```python
build_dashboard_report_payload(metrics, metadata, cache_summary=None)
```

Ключи, которые должны оставаться стабильными для dashboard:

```text
metadata
summary
kpis
answerDistribution
activity
comparison
decks
attentionCards
attentionCardsStatus
noteTypeCatalog
forecast
fsrs
recommendations
cache
```

## Today slice

Optional `today` содержит Home-only current-day view:

```text
metadata, summary, kpis, answerDistribution, activity,
comparison, decks, recommendations
```

Он строится строго для `metadata.todayDate`. Top-level historical report не
урезается и остаётся source для Calendar, Decks и Cards. `#/home` использует
`today`, когда slice присутствует; fallback на top-level нужен только для
старого payload/dev fixture.

## Profile slice

Optional `profile` содержит `identity`, `studyHistory`, `activity`, `decks` и
`preferences`. В runtime Stage 3 он публикуется всегда и строится из исходного
all-collection cache snapshot независимо от dashboard scope. Optional type
сохраняет совместимость frontend с legacy fixtures/старым report.

## Activity Hub slice

Optional `activityHub` — canonical Stage 4 source для `#/calendar`: scoped
one-year `days`, exact period bounds, availability, day-deck details и derived
daily/weekly feed. Runtime публикует slice всегда; optional TS field сохраняет
совместимость со старыми fixtures. Contract не содержит raw revlog/card data и
не добавляет endpoint. См. `docs/activity-calendar-v2.md`.

## Deck Hub slice

Optional `deckHub` — canonical Stage 5 source для `#/decks`. Runtime публикует
его из current normal-deck catalog и scoped direct rows. Shape normalized:
`scope`, compact `summary`, `nodes` map и `rootIds`; каждый node разделяет
`directMetrics`/`subtreeMetrics`, `aggregateHealth`, `dataConfidence` и
`descendantIssues`. Filtered decks отсутствуют в nodes. Legacy `decks`
сохранён для Home/Cards/compatibility. См. `docs/decks-v2.md`.

Deck Browser использует token-protected `POST /api/actions/open-deck-browser`
с body `{deckId, mode: subtree|direct}`. Backend разрешает current canonical
name и не принимает arbitrary query через этот action.

## Statistics Hub и query

Runtime `statisticsHub` содержит default 90d dashboard query и
`initialResult`, coverage/capabilities и compact normal-deck options.
`POST /api/statistics/query` принимает только typed
`scope/period/granularity/comparison` и возвращает тот же result type.
Endpoint требует token, ограничен 8 KiB, отклоняет arbitrary search/SQL/unknown
fields и не публикует raw revlog/card/note data. Secondary empty-body action:
`POST /api/actions/open-native-stats`. Полный contract:
`docs/statistics-v1.md`.

## Card-level contract

Карточки внимания приходят в canonical ключе:

```text
attentionCards
```

Backend должен отдавать актуальный `attentionCards` плюс
`attentionCardsStatus`; frontend больше не fallback-ит к legacy top-level
aliases. Top-level `problemCards` больше не является supported payload alias
после Stage 9; top-level `cardIssues` удален после Stage 10; top-level `cards`
удален после Stage 11.

Важные поля карточки:

```text
cardId
noteId
deckName
frontPreview/front
preview
renderedPreview
issues
riskScore
againCount
lapses
averageAnswerSeconds
passRate
lastReviewedAt/lastReviewed
searchQuery/browserSearch
```

`renderedPreview` может содержать:

```text
frontHtml
backHtml
frontPlainText
backPlainText
css
mediaRefs
cardOrd
cardId
renderSource
renderStatus
fallbackReason/reason
```

HTML/CSS/media должны проходить sanitizer. Нельзя отдавать произвольные
`file:`, `javascript:` или опасные inline styles в dashboard.

## Media preview

Карточки используют ссылки вида:

```text
/api/media?name=<media-name>&token=<token>
```

Media name должен проходить safe filename validation на backend. Frontend может
добавлять token к уже нормализованным media refs.

## Cache summary

`cache` описывает состояние SQLite cache:

```text
status
dataSource
usedFor
version
createdAt/updatedAt
lastRevlogId
cachedDays
cachedDeckDays
isBuilding
error/lastError
fallbackReason
limitations
periodSummary
cacheDeckSummary
performance
```

Cache может быть source для части dashboard, но не должен менять публичный
frontend contract.

Когда report строится через cache adapter, summary сохраняет status diagnostics
(`version`, `isBuilding`, `error`, `lastError`) вместе с `fallbackReason`.
`mixed` overlay ограничен cache-backed sections; card-level поля остаются за
canonical live payload (`attentionCards` / `attentionCardsStatus`).

## Правило изменения контракта

Если меняется форма payload:

1. Обновить `dashboard_payload.py`.
2. Обновить `web-dashboard/src/types/report.ts`.
3. Обновить Python tests на точную форму payload.
4. Обновить frontend normalization/tests.
5. Обновить этот документ.
6. Прогнать минимум payload tests + frontend typecheck/tests.
