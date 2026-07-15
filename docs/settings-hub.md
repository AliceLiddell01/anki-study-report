# Settings Hub

Статус: **Accepted / Complete**. Stage 2, 2026-07-10.

## Scope Stage 2

Settings Hub объединяет реальные настройки add-on и технические страницы в
одной desktop-first оболочке. Этап также переносит редактирование dashboard
scope из Profile, фиксирует семантику «Сегодня» и сохраняет диагностику как
read-only surface.

Не реализованы Profile MVP, accounts, achievements, Activity Feed, Statistics,
Search, Notifications, Cards v2, external integrations и mobile drawer.

## Settings IA и canonical routes

```text
Отчёт
  Отчёт             #/settings
Данные
  Данные            #/settings/data
Система
  Сервер            #/settings/server
Диагностика
  Источники данных  #/settings/sources
  Логи              #/settings/logs
```

Sidebar постоянен на всех settings routes, использует обычный `<nav
aria-label="Настройки">`, показывает active item и остаётся keyboard-usable.

Compatibility redirects:

```text
#/integrations -> #/settings/sources
#/logs         -> #/settings/logs
```

Старые hashes нормализуются в canonical URL через `history.replaceState`; две
копии page state не создаются. Unknown hash по-прежнему безопасно открывает
`#/home`.

## Public settings model

Token-protected `GET/POST /api/dashboard/settings` работает с четырьмя
allowlisted sections:

```text
dashboard
  scope, selectedDeckIds, selectedDeckNames, includeChildDecks
report
  defaultPeriod, customStartDate, customEndDate, scope,
  selectedDeckIds, includeChildDecks, detailLevel, answerMode
data
  trackReviewerSessions, sessionIdleTimeoutSeconds, sessionGapCapSeconds,
  useStudyTimeStats, useStatsCacheForReport
server
  autoStart, port, idleTimeoutSeconds
```

GET также возвращает `deckOptions` из Anki collection через Python backend.
Frontend не читает collection напрямую. IDs являются identity; names — только
presentation data. Stale IDs остаются видимыми как недоступные и не ломают
форму.

Unknown sections/fields, неверные enum, types и ranges отклоняются с
`invalid_settings` и `fieldErrors`. API не публикует token, runtime paths,
cache schema, package identity, E2E variables, `last_report_ts` или custom
profile internals.

## Ownership и persistence

Source of truth — штатный Anki add-on config:

```text
config.json defaults
-> config_service.py normalization
-> user overrides
-> mw.addonManager.writeConfig(...)
```

Runtime не редактирует shipped `config.json`. Partial update делает один
read/normalize/merge/write под re-entrant lock и сохраняет неизвестные/internal
keys, включая неизвестные nested keys в `web_dashboard` и
`dashboard_display`.

`dashboard_display.period` сохранён только как deprecated migration data. Он
не публикуется в Settings Hub и больше не влияет на dashboard.

## Save model

Report, Data и Server используют одинаковый pattern:

```text
loaded normalized state
-> editable draft
-> dirty state
-> Сохранить изменения / Отменить изменения
-> normalized saved response
```

Save disabled без изменений и во время request. Backend errors сохраняют draft;
field errors показываются рядом с controls. Inline live region сообщает
success/error. `beforeunload` и settings route links предупреждают о
несохранённых изменениях.

## Runtime actions

Operational actions не смешиваются с form submit:

- Data: обновить или после подтверждения полностью перестроить cache;
- Server: открыть, скопировать существующую ссылку, перезапустить или
  остановить;
- Logs: скачать или после подтверждения очистить.

Port и idle timeout применяются к текущему server process только после явного
restart. Restart/stop могут сменить token; UI не обещает, что старая ссылка
останется рабочей.

## Today semantics

`StudyReport.today` — отдельный Home-only payload slice. Он строится из stats
cache строго для текущего `today_key`, содержит current-day summary/KPI/answer
distribution/activity/decks/recommendations и historical comparison baselines.

Calendar, Decks и Cards продолжают использовать исторический top-level report.
Поэтому Home не является переименованным all-time report и другие страницы не
теряют диапазон данных.

Stage 5 сохраняет тот же scope для `deckHub`: selected IDs и
`includeChildDecks` применяются backend-side, а необходимые ancestors
публикуются только как structural context без данных исключённых веток.

С Home удалены крупные blocks «Период статистики» и «Статистика по». Для
default «Все колоды» дополнительный indicator не показывается. Для selected
scope рядом с heading появляется компактная ссылка в `#/settings`.

## Profile boundary after Stage 3

`#/profile` больше не transitional settings surface. Profile MVP показывает
отдельный all-collection lifetime slice и сохраняет только дату начала/сортировку
через `/api/profile`. Dashboard/report scope по-прежнему принадлежит Settings
Hub и не влияет на Profile. См. `docs/profile-mvp.md`.

## Diagnostics boundaries

`#/settings/sources` остаётся read-only диагностикой локальных источников.
`#/settings/logs` показывает redacted local log и token-protected download.
Никакие external providers, login или generic RPC не добавлены.

## Security rules

- Все settings/status/action endpoints требуют текущий dashboard token.
- Server слушает только `127.0.0.1`.
- Public settings имеют явный nested allowlist.
- Token и полный token-bearing URL не возвращаются settings model.
- Server/cache/log actions остаются отдельным allowlist.
- Media sanitizer, Cards Shadow DOM и action allowlists не менялись.

## Future settings not implemented

В Hub нет placeholder controls для Statistics, FSRS page, accounts, cloud sync,
external services, arbitrary themes или plugin/DLC system. Новые sections
добавляются только вместе с реальным backend contract и persistence.

## Privacy

`#/settings/privacy` — реальный Data-group route. Он показывает сохранённый
per-profile status, две granular purpose toggles, версии/время решения, точные
allowed/never-collected категории и action «Открыть What’s New». Страница не
содержит фиктивного remote delete: такая кнопка появится только вместе с
работающим client/server deletion contract.
