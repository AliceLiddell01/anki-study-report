# API dashboard и контракт payload

**Снимок документации:** 2026-07-22

Dashboard — локальное приложение, которое получает опубликованный payload отчёта и использует несколько узких API. Frontend не читает collection Anki напрямую.

## Модель токена

Все чувствительные endpoints требуют текущий токен dashboard:

```text
?token=<dashboard-token>
```

Dashboard открывается по loopback-URL:

```text
http://127.0.0.1:<port>/?token=<token>#/home
```

Недопустимый токен возвращает `403`. Токен и полный URL с токеном не попадают в обычные логи, DOM-dumps, публичные артефакты или телеметрию.

## Карта endpoints

### Основные GET

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
/api/notifications/summary
/api/notifications
/api/settings/notifications
/api/notifications/toasts
/api/telemetry/status
```

### Основные POST и PUT

```text
/api/cache/rebuild
/api/cache/refresh
/api/server/<action>
/api/logs/clear
/api/dashboard/settings
/api/profile
/api/statistics/query
/api/statistics/fsrs/query
/api/search/query
/api/search/inspect
/api/triage/query
/api/triage/recheck
/api/inspection-profiles/query
/api/inspection-profiles/validate
/api/inspection-profiles/update
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
/api/entities/cards/actions
/api/entities/notes/actions
/api/actions/<action>
/api/notifications/read
/api/notifications/read-all
/api/settings/notifications
/api/notifications/toasts
/api/notifications/toast-delivered
/api/telemetry/events
/api/telemetry/delete
/api/telemetry/check-send
```

Действия server и dashboard остаются allowlist, а не произвольным RPC.

## Запрос и просмотр Search

`POST /api/search/query` и `POST /api/search/inspect`:

- защищены токеном;
- принимают только POST;
- принимают только JSON;
- ограничены телом 8 КиБ.

Обычные query и inspect требуют точное значение `schemaVersion: 2`. Schema v1 не является alias. Query использует нативную грамматику Anki, ограниченные фильтры, размеры страницы `25 | 50 | 100` и жёсткое ограничение 2000. Inspect принимает ровно один десятичный строковый `cardId` или `noteId`.

Строки и подробности карточек v2:

```text
displayText
displaySource      browser_question | reviewer_front | none
displayStatus      available | media_only | unavailable
displayTruncated
```

Alias карточки `primaryText` отсутствует. Строки и подробности заметок сохраняют `primaryText` заметки и не получают поля отображения карточки.

Parser frontend отклоняет старые schema, aliases, неизвестные ключи, повреждённые ID, расхождение количества и несогласованное состояние отображения.

Metadata Search остаётся отдельным вариантом запроса v1:

```json
{"kind": "metadata", "requestId": "search-metadata-1"}
```

Ошибки Search:

```text
400 invalid_search_request
404 search_entity_not_found
503 search_unavailable
503 search_failed
504 search_timeout
```

Полный контракт: [`search-v1-and-safe-actions.md`](search-v1-and-safe-actions.md).

## Запрос Triage v4

`POST /api/triage/query`:

- защищён токеном;
- принимает только POST и JSON;
- ограничен телом 8 КиБ;
- требует точное значение `schemaVersion: 4`.

Автоматический запрос объединяет ограниченные источники обучения за период, текущего содержимого, активных Signals и идентичности Search. Продолжение текущего содержимого запускается вручную и ограничено cursor. Рабочий набор Search принимает от 1 до 200 точных ID карточек и сохраняет порядок первого появления.

Ответ содержит типизированные состояния источников и содержимого, количества, согласованность cursor, стабильные причины и компактную идентичность, принадлежащую Search. Полный предпросмотр и media, необработанный revlog, значения заметок, произвольный query, исключения, токен и runtime-путь отсутствуют.

## Recheck конкретной карточки v1

`POST /api/triage/recheck`:

- защищён токеном;
- принимает только POST и JSON;
- ограничен телом 8 КиБ;
- требует точное значение `schemaVersion: 1`;
- сериализован через `QueryOp`.

Запрос содержит:

```text
cardId
expectedNoteId
reasonIds (1..4)
scope
```

Recheck оценивает только конкретную карточку и переиспользует канонические источники Triage v4. Ответ возвращает типизированное состояние источников, `entityStatus`, `contentChecks` и текущий канонический элемент либо `null`.

Resolved допустим только при полностью авторитетном покрытии и отсутствии актуальных причин. Частичное, недоступное или ошибочное состояние источника, изменение authority профиля, несовпадение идентичности, отсутствующая или изменённая сущность и ошибка collection работают по принципу fail closed.

Полные контракты:

- [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md);
- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

## API formatter отображения карточки

Endpoints:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

Они защищены токеном, принимают только POST, используют точную schema v1 и ограничение тела 64 КиБ.

Состояния store:

```text
empty | available | corrupt | future_schema | unavailable
```

`validate` ничего не сохраняет и не читает collection. `update` принимает только `save` или `delete` с `expectedRevision`. API не раскрывает необработанный HTML, значения заметок, содержимое media, пути, исключения renderer или произвольный язык выражений.

Полный контракт: [`card-display-formatter-v1.md`](card-display-formatter-v1.md).

## API Inspection Profiles

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

Endpoints используют текущий токен, строгий JSON и ограничение 64 КиБ.

Query возвращает ограниченные структуры, fingerprints, состояние жизненного цикла, сохранённый профиль и неавторитетное suggestion. Validation работает только на чтение. Update изменяет локальный store профилей с optimistic-проверками revision и fingerprint.

Причины по содержимому создают только подтверждённые и актуальные профили. Состояния suggested, disabled, needs-review, missing, future, corrupt и unavailable работают по принципу fail closed.

Полный контракт: [`inspection-profiles-v1.md`](inspection-profiles-v1.md).

## API действий над сущностями

```text
POST /api/entities/cards/actions
POST /api/entities/notes/actions
```

Требования: токен, POST, JSON и ограничение тела 8 КиБ.

Allowlist карточек:

```text
suspend | unsuspend | set_flag | clear_flag | bury | unbury | move_to_deck
```

Allowlist заметок:

```text
add_tags | remove_tags
```

Пакет содержит от 1 до 200 точных десятичных ID. Один устаревший ID отклоняет весь пакет. Mutations используют официальные wrappers Anki и один нативный шаг undo.

Успех действия, включая `action.no_changes`, не доказывает устранение проблемы Cards. Оно определяется только явным `/api/triage/recheck`.

## API Settings и Profile

`GET/POST /api/dashboard/settings` публикует нормализованные публичные настройки и принимает только частичные изменения из allowlist.

`GET/POST /api/profile` публикует публичные данные профиля. Доступные для записи поля:

```text
customStudyStartedOn
deckOverviewSort
```

Вычисляемые идентичность и метрики доступны только для чтения.

## Statistics и FSRS

`POST /api/statistics/query` принимает типизированные scope, period, granularity и comparison.

`POST /api/statistics/fsrs/query` принимает документированные read-only-операции FSRS.

Произвольные Search, SQL и необработанные строки revlog, карточек и заметок запрещены.

## Notifications и телеметрия

Endpoints Notification используют ограниченную schema v1 и локальные ID уведомлений. Endpoints телеметрии принимают только ограниченные технические события после явного согласия.

Удалённая телеметрия исключает содержимое collection, имена и значения полей, queries Search, ID карточек, заметок и колод, компактный текст отображения, имена media-файлов и URL с токеном.

## Источники истины payload

Backend:

```text
anki_study_report/dashboard_payload.py
```

Frontend:

```text
web-dashboard/src/types/report.ts
```

Канонический Cards использует `/api/triage/query` и `/api/triage/recheck`. Устаревший `attentionCards` остаётся compatibility-поверхностью для других потребителей.

## Предпросмотр и media

Просмотр Search содержит санитизированный `renderedPreview` рядом с компактной идентичностью. Полный предпросмотр загружается только для активной карточки.

URL media:

```text
/api/media?name=<validated-media-name>&token=<token>
```

Обязательны backend-проверка имени файла, sanitizer, изоляция Shadow DOM и проверка токена. Запрещены `file:`, `javascript:`, iframe и выполнение JavaScript шаблона.

## Текущий статус Core

```text
C1.5R.0–R.7 — завершено; принято владельцем
C1.6 — завершено; принято владельцем; влито в core
C1.6B — условный этап; не начат
Core C1 — завершён
C2 — следующий этап; не начат
```
