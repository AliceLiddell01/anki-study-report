# Dashboard API и payload-контракт

Снимок документации: 2026-07-05.

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
/api/actions/<action>
```

Server actions и dashboard actions должны оставаться небольшим allowlist-слоем,
а не произвольным RPC в Anki.

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

## Правило изменения контракта

Если меняется форма payload:

1. Обновить `dashboard_payload.py`.
2. Обновить `web-dashboard/src/types/report.ts`.
3. Обновить Python tests на точную форму payload.
4. Обновить frontend normalization/tests.
5. Обновить этот документ.
6. Прогнать минимум payload tests + frontend typecheck/tests.
