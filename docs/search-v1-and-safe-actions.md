# Search и Safe Actions

**Статус:** schema v2 запросов и просмотра Search; schema v1 metadata Search; schema v1 Safe Actions  
**Снимок:** 2026-07-22

## Search

Search доступен по маршруту `#/search`. Запрос выполняется только после явного submit или нажатия `Enter`.

В `sessionStorage` сохраняются:

- query;
- mode;
- filters;
- sort;
- размер страницы.

Результаты, выбор и Inspector после reload не восстанавливаются. Необработанный query не попадает в URL, title, обычные логи или публичные артефакты.

### Режим Cards

Режим Cards показывает:

- каноническую компактную идентичность;
- колоду;
- тип заметки;
- шаблон;
- состояние;
- due;
- interval;
- количество повторений;
- lapses;
- flag.

Идентичность карточки:

```text
displayText
displaySource
displayStatus
displayTruncated
```

Строка Search и Inspector Search используют один backend-projector:

```text
вопрос Browser
→ лицевая сторона reviewer
→ media_only | unavailable
```

Произвольные поля заметки не используются как fallback. Alias карточки `primaryText` отсутствует.

### Режим Notes

Режим Notes сохраняет проекцию заметки:

- `primaryText`;
- тип заметки;
- tags;
- количество карточек;
- колоды.

Фильтры только для карточек очищаются при переходе в Notes. Режим заметок не получает поля отображения карточки.

### Metadata и pagination

Запрос metadata:

```json
{"kind": "metadata", "requestId": "search-metadata-1"}
```

Query v2 использует нативную грамматику Anki, ограниченные структурированные фильтры, размеры страницы `25 | 50 | 100` и жёсткое ограничение 2000.

Inspect v2 загружает одну конкретную сущность после выбора результата.

### Выбор и передача в Browser

Выбор содержит только уникальные положительные десятичные ID, сохраняется между страницами одного fingerprint запроса и ограничен 200 сущностями.

`Open in Anki Browser` передаёт точные mode и ID через действие `open-search-selection` из allowlist. Отображаемый текст никогда не преобразуется в нативный query.

### Строгий parsing и ошибки

Parser frontend проверяет точные ключи, schema, ID, вложенные сводки, metadata pagination и согласованность состояния отображения.

Недопустимый успешный payload:

```text
invalid_search_response
```

Ошибки backend:

```text
invalid_search_request
search_entity_not_found
search_unavailable
search_failed
search_timeout
```

## Safe Actions

Endpoints mutations:

```text
POST /api/entities/cards/actions?token=<token>
POST /api/entities/notes/actions?token=<token>
```

Allowlist карточек:

```text
suspend
unsuspend
set_flag
clear_flag
bury
unbury
move_to_deck
```

Allowlist заметок:

```text
add_tags
remove_tags
```

Отсутствуют generic method invocation, произвольный SQL, delete, bury уровня заметки и move-note.

Запрос валидирует:

- точную структуру JSON;
- уникальные положительные десятичные ID;
- пакет `1..200`;
- ограничение тела 8 КиБ;
- ограниченные tags;
- целевую колоду, разрешённую server.

Один устаревший ID отклоняет весь пакет до mutation. Изменения используют официальные wrappers операций Anki и создают один нативный шаг undo. No-op возвращает `action.no_changes` без mutation.

## Связь Safe Actions с Cards C1.6

Safe Actions остаются единственным путём mutations из Cards. Open in Anki остаётся единственной нативной передачей к редактированию.

Успех действия и `action.no_changes` не являются доказательством устранения.

Жизненный цикл:

```text
Safe Action или Open in Anki
→ Awaiting recheck
→ POST /api/triage/recheck
→ reconciliation причин
```

Только полностью авторитетный recheck конкретной карточки без актуальных причин может удалить элемент из автоматической очереди.

Идентичность Search, отображаемый текст и результат действия не используются для клиентского определения устранения.

Полный контракт:

- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

## Обновление Search после mutations

После успешного действия Search frontend:

1. повторяет текущий query v2;
2. согласует страницу и выбор;
3. повторяет активный inspect v2, если сущность существует.

Такое обновление Search не заменяет жизненный цикл recheck Cards.

## Безопасность и конфиденциальность

Frontend не читает collection напрямую. Сохраняются:

- защита токеном;
- привязка к loopback-интерфейсу;
- allowlist действий;
- sanitizer;
- проверка media;
- изоляция предпросмотра.

Компактная идентичность, queries, ID, имена колод, типов заметок и шаблонов, значения полей и имена media-файлов не добавляются в удалённую телеметрию.
