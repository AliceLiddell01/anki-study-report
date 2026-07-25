# Канонический API Cards v2 Triage

## Текущие schema

```text
POST /api/triage/query    schemaVersion 4
POST /api/triage/recheck  schemaVersion 1
```

Оба endpoints:

- доступны только через loopback-интерфейс;
- защищены токеном dashboard;
- принимают `POST application/json`;
- ограничены телом 8 КиБ;
- сериализованы через Anki `QueryOp`.

Запросы принимают только строгие ограниченные ID, scope и поля schema. Язык запросов, SQL, HTML, значения заметок и произвольный ввод действий запрещены.

## Query v4

### Автоматическая очередь

```json
{
  "schemaVersion": 4,
  "dataset": "automatic",
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": []
  },
  "limit": 100,
  "contentCursor": null
}
```

### Рабочий набор Search

```json
{
  "schemaVersion": 4,
  "dataset": "search_workset",
  "cardIds": ["123", "456"],
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": ["10"]
  },
  "limit": 200
}
```

Автоматический результат объединяет независимые ограниченные источники:

- кандидатов обучения за выбранный период;
- кандидатов по текущему содержимому;
- активные Signals;
- идентичность Search.

Pagination текущего содержимого является явной и ограниченной. Client никогда не запускает автоматический цикл cursor. Рабочий набор Search сохраняет явный порядок первого появления карточек.

Ответ публикует:

- типизированное общее состояние и состояния источников и проверок содержимого;
- количества;
- согласованность cursor;
- до четырёх стабильных причин на элемент.

Идентичность очереди использует ту же компактную проекцию, принадлежащую Search, что строки Search и Inspectors. Полный HTML предпросмотра и media не входят в Triage; просмотр Search вызывается только для активной карточки.

Стабильные ID причин:

```text
learning:<code>
profile:<profileId>:check:<checkId>
```

Подтверждение ограничено и исключает необработанные значения заметок, HTML, имена файлов, исходный код шаблона, пути файловой системы, токены и исключения.

## Recheck конкретной карточки v1

Запрос:

```json
{
  "schemaVersion": 1,
  "cardId": "123",
  "expectedNoteId": "456",
  "reasonIds": ["learning:learning.repeated_again"],
  "scope": {
    "periodStartMs": 1700000000000,
    "periodEndMs": 1700604800000,
    "deckIds": []
  }
}
```

`reasonIds` содержит от одного до четырёх уникальных ограниченных канонических ID причин текущего элемента. Это позволяет server работать по принципу fail closed, когда прежнюю авторитетную причину профиля больше нельзя проверить. Это не список причин, которые нужно скрыть.

Сокращённая структура ответа:

```json
{
  "schemaVersion": 1,
  "cardId": "123",
  "expectedNoteId": "456",
  "status": "available",
  "entityStatus": "available",
  "generatedAtMs": 1721000000000,
  "sourceStatus": {
    "learningCandidates": {
      "status": "available",
      "itemCount": 1,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    },
    "signals": {
      "status": "empty",
      "itemCount": 0,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    },
    "searchResolver": {
      "status": "available",
      "itemCount": 1,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    },
    "profileChecks": {
      "status": "empty",
      "itemCount": 0,
      "skippedCount": 0,
      "truncated": false,
      "errorCode": null
    }
  },
  "contentChecks": {
    "status": "no_confirmed_profiles"
  },
  "item": {}
}
```

Настоящий ответ содержит полный строгий объект `contentChecks` и либо полный элемент Triage, либо `null`.

`entityStatus`:

```text
available | missing | changed | unavailable
```

Состояние верхнего уровня:

```text
available | partial | unavailable
```

Устранение допустимо только тогда, когда:

- состояние сущности авторитетно;
- все обязательные источники авторитетны;
- возвращённый доступный элемент содержит ноль причин.

Частичное, недоступное или ошибочное состояние источника, изменение authority профиля, несовпадение идентичности и ошибка collection не могут дать результат Resolved.

## Parser и поведение HTTP

Parsers TypeScript требуют:

- точные верхнеуровневые и вложенные ключи;
- конечные ограниченные числа;
- десятичные строки ID;
- допустимые значения enum;
- согласованную идентичность элемента;
- отсутствие будущих полей.

Автоматические элементы Query v4 должны иметь хотя бы одну причину. Только Recheck v1 может вернуть доступный точный элемент с нулём причин как авторитетное подтверждение.

Поведение HTTP:

```text
GET                                      → 405
missing/invalid token                    → 403
wrong content type                       → 415
invalid JSON/schema/fields               → 400
runtime unavailable/failure              → 503
timeout                                  → 504
```

Публичные ошибки остаются обобщёнными и не раскрывают значения collection, queries, пути или исключения.

## Контракт UI

Жизненный цикл C1.6 и reconciliation причин описаны в:

- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md).

Ограничение автоматической очереди в 100 элементов является только ограничением представления. Оно никогда не доказывает, что проблема устранена.
