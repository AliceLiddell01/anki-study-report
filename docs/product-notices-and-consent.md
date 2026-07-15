# Product notices и consent foundation

Снимок контракта: 2026-07-15. Реализация полностью локальна: этот слой не
создаёт telemetry events и не выполняет внешние HTTP-запросы.

## Назначение

Product-notice слой хранит факт первого/последнего запуска и последней
просмотренной версии, показывает локализованную историю релизов и сохраняет
granular privacy choice для текущего Anki-профиля. Закрытие What’s New означает
только просмотр текущей версии. Оно не меняет privacy choice и не удаляет
историю. Consent — отдельный modal и отдельное решение.

## Per-profile storage

Source of truth находится вне установленного add-on:

```text
<profile>/addon_data/<addon_id>/product_notices.json
<profile>/addon_data/<addon_id>/privacy.json
```

Если Anki profile runtime действительно недоступен, действует общий runtime
fallback `anki_study_report/user_files/`; этот каталог исключён из package и
Git. Оба store используют UTF-8, normalized JSON, `RLock`, временный файл,
`flush` + `fsync` и atomic `os.replace`. Неизвестные ключи и более новая
`schemaVersion` сохраняются. Повреждённый документ перемещается в соседний
`*.corrupt-<UTC timestamp>`, после чего чтение возвращает безопасное значение.

`product_notices.json` schema v1:

```json
{
  "schemaVersion": 1,
  "firstObservedVersion": "1.1.0",
  "lastStartedVersion": "1.1.0",
  "lastSeenReleaseVersion": null
}
```

`privacy.json` schema v1 содержит `status`, обе цели, версии consent/notice,
время решения и `deletionPending`. Версия приложения не используется как
версия storage schema.

## Startup и modal coordinator

При загрузке Python entrypoint синхронно записывает `lastStartedVersion`, но не
обращается к сети. React coordinator допускает только один modal:

1. consent/re-consent, если требуется решение;
2. What’s New, если текущая версия ещё не просмотрена;
3. обычный dashboard.

На первом запуске What’s New раскрывает текущую версию. После обновления
раскрываются все версии новее `lastSeenReleaseVersion`; более старые остаются
доступны свёрнутыми. X, Escape и «Понятно» записывают текущую версию как
просмотренную. Ручное открытие из profile menu или `#/settings/privacy` не
переоткрывает consent.

Если runtime state API недоступен, bundled changelog всё ещё открывается,
effective purposes остаются `false`, а выбор не считается принятым.

## Consent semantics

Доступны две необязательные цели:

```text
reliabilityDiagnostics
featureUsage
```

Обе изначально `false`. Пустой сохранённый выбор, X и Escape записывают
`declined`; хотя бы одна выбранная цель записывает `accepted`. Отказ не меняет
ни одной функции add-on. Решение применяется только к текущему профилю.

Повторное решение требуется только при изменении `consentSchemaVersion` или
материальном изменении `privacyNoticeVersion`. Пока новое решение не принято,
`effectivePurposes` принудительно равны `false`, даже если старый документ был
`accepted`.

## Accessibility contract

`AccessibleModal` предоставляет `role="dialog"`, `aria-modal="true"`, видимый
локализованный title, начальный фокус на heading, focus trap, Escape, возврат
фокуса invoker, scrollable content и inert/`aria-hidden` для App Shell. Release
accordion управляется кнопками с `aria-expanded`. Компоненты поддерживают
RU/EN, light/dark и `prefers-reduced-motion`.

## Local API

Все endpoints доступны только на loopback dashboard server и требуют
`?token=<dashboard-token>`:

```text
GET  /api/product-notices
POST /api/product-notices/seen   body: {}
GET  /api/privacy
POST /api/privacy                body: {"purposes": {...}}
```

POST принимает только два boolean purpose и отклоняет unknown/missing fields.
React вызывает только relative `/api/...` URL и не получает remote credentials.

## Канонический changelog

`release/changelog.json` — единственный редактируемый source of truth.
`scripts/generate_changelog.py` детерминированно создаёт:

```text
CHANGELOG.md
anki_study_report/changelog.json
web-dashboard/src/data/changelog.generated.ts
```

Validator требует RU/EN parity, stable item IDs, newest-first SemVer, уникальные
version/item ID, корректные даты и bounded plain text без HTML/Markdown links.
Текущая package version обязана присутствовать. `prepare_release.py` переносит
structured `unreleased.sections` в новый release и повторно генерирует outputs.
GitHub Release и AnkiWeb renderers получают current English section через
существующий `release_common.py`; отдельного release pipeline нет.

Package validator требует bundled `changelog.json`, но runtime JSON state в
archive не входит.

## Проверки

Основные regression suites:

```text
tests/test_product_notices.py
tests/test_changelog.py
tests/test_dashboard_server.py
tests/test_package_build.py
tests/test_release_automation.py
web-dashboard/src/components/ProductNoticeCoordinator.test.tsx
web-dashboard/src/lib/productNoticesApi.test.ts
```

Real-Anki smoke сохраняет consent, What’s New и Privacy screenshots и проверяет
first-run decline, modal order, no-repeat и manual reopen.
