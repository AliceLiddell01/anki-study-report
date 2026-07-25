# Идентичность отображения карточки

## Статус

**Каноническое исходное состояние:** `C1.5R.1 — завершено`  
**Необязательный слой форматтера:** `C1.5R.2 — завершено`  
**Ветка:** `core`

**Реализация:**

```text
anki_study_report/card_display_identity.py
anki_study_report/card_display_formatter_store.py
anki_study_report/card_display_formatter_service.py
anki_study_report/card_display_formatter_runtime.py
```

**Публичные контракты:** Search schema v2 и Triage schema v3; C1.5R.2 их не изменяет.

C1.5R.1 установил единую идентичность конкретной карточки, формируемую backend, для Search, Triage и актуальных поверхностей Cards. C1.5R.2 добавил поверх этого projector необязательный ограниченный декларативный formatter.

При отсутствующем, отключённом, повреждённом, неподдерживаемом или недоступном formatter, а также при его пустом результате система всегда возвращается к завершённой семантике R1.

Связанные документы:

- [`card-display-formatter-v1.md`](card-display-formatter-v1.md);
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md);
- [`../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md).

## Общая идентичность конкретной карточки

Одна компактная идентичность используется в:

- строке карточки в результатах Search;
- заголовке Inspector карточки Search;
- каноническом элементе Triage;
- элементе очереди Cards;
- заголовке Inspector Cards.

Search в режиме заметок остаётся проекцией заметки и сохраняет `primaryText`. В строках и подробностях карточек и элементах Triage alias карточки `primaryText` отсутствует.

## Авторитетный projector

`project_card_display_identity(card, formatter=None)` отвечает за одну конкретную карточку.

Без активного formatter источники используются в таком порядке:

1. нативный вопрос Browser: `card.question(reload=True, browser=True)`;
2. нативная лицевая сторона reviewer: `card.question(reload=True, browser=False)`;
3. явное состояние `media_only` или `unavailable`.

При активном formatter сначала используется только объявленный `inputSource`.

Локальный для запроса resolver выбирает конфигурацию по точной паре:

```text
(noteTypeId, templateOrdinal)
```

Поддерживаются стандартный formatter типа заметки и точный отключённый opt-out. Имена, колоды, поля и нечёткое сходство никогда не участвуют в binding.

При ошибке настроенного источника уже отрендеренные значения переиспользуются, после чего применяется каноническая последовательность fallback. Каждый источник рендерится не более одного раза за проекцию одной карточки. Projector никогда не вызывает `card.answer()`.

## Упорядоченная компактная tokenization

Parser создаёт только токены:

```text
text
line_break
image
audio
```

Порядок текстовых и media-токенов сохраняется. Соседние inline-узлы объединяются без искусственного разделителя. `<br>` и границы блоков создают новые строки. HTML-entities декодируются. Пробелы нормализуются только внутри итоговых строк.

Удаляется содержимое:

- `script`, `style`, `iframe`;
- `object`, `embed`;
- SVG и MathML;
- template и form;
- небезопасных media-контейнеров.

Повреждённая вложенность запрещённых элементов работает по принципу fail closed.

Каноническая проекция R1 пропускает media-токены и выбирает первую содержательную строку. Поэтому точная японская фикстура с большим количеством media остаётся:

```text
【に】（する）
```

Включённый formatter лицевой стороны reviewer с `imageMode: stem` может вернуть:

```text
【に】感謝（する）
```

Безопасная обработка media, enum политики, выбор строк и точный truncation описаны в [`card-display-formatter-v1.md`](card-display-formatter-v1.md). Media-файл никогда не открывается и не проверяется на существование.

## Wire-контракт

Идентичность карточки остаётся плоским точным fragment:

```json
{
  "displayText": "【に】感謝（する）",
  "displaySource": "reviewer_front",
  "displayStatus": "available",
  "displayTruncated": false
}
```

`displaySource`:

```text
browser_question | reviewer_front | none
```

`displayStatus`:

```text
available | media_only | unavailable
```

Правила согласованности:

- `available`: ограниченный непустой текст и отрендеренный источник Browser или reviewer;
- `media_only`: пустой текст, без truncation, отрендеренный источник сохраняется;
- `unavailable`: пустой текст, источник `none`, без truncation.

Состояние и конфигурация formatter не копируются в wire-данные Search и Triage. Публичных полей `formatterApplied`, `formatterId`, aliases, HTML или metadata имени файла нет.

## Schema Search и Triage

Запросы и просмотр Search остаются на строгой schema v2. Metadata Search остаётся независимым вариантом schema v1. В snapshot этого контракта Triage использует точную schema v3; последующие добавочные изменения источников кандидатов отдельно описаны для Triage v4.

`project_card_row()` обслуживает обычный Search, просмотр Search и определение конкретной карточки, которое переиспользует Triage. Поэтому все поверхности карточек используют один resolver и один путь идентичности backend; второй formatter в Triage отсутствует.

Строгие parsers TypeScript отклоняют:

- старые schema;
- неизвестные ключи;
- aliases карточки;
- повреждённые ID;
- слишком длинный текст;
- несогласованные состояние, источник и текст отображения.

## Поведение UI

Для `available` backend-текст отображается без изменений. Frontend локализует только явные fallback-состояния:

| Состояние | RU | EN |
| --- | --- | --- |
| `media_only` | Карточка только с медиа | Card with media only |
| `unavailable` | Текст карточки недоступен | Card text unavailable |

C1.5R.2 не добавляет маршрут formatter, страницу, hook, навигацию Settings, форму, живой предпросмотр или переработку Cards. Пошаговая настройка относится к C1.5R.6, семантика предпросмотра — к C1.5R.3.

## Безопасность и конфиденциальность

Dashboard остаётся доступным только через loopback-интерфейс и защищённым токеном. Frontend никогда не читает collection. Компактная идентичность и конфигурация formatter остаются локальными и не копируются в телеметрию или обычные логи.

Runtime не выполняет:

- JavaScript или Python;
- SQL или shell;
- regex или selectors;
- expressions или callbacks;
- динамические imports;
- subprocess.

Не логируются необработанный HTML, значения полей заметки, содержимое media, абсолютные пути, исключения renderer, имена файлов formatter, сгенерированный `displayText` или токены.

## Состояние проверки

C1.5R.1 и C1.5R.2 завершены. Для дерева реализации C1.5R.2, закоммиченного и отправленного как `edad09e8ffae443b94e192b266084abb66c37adf`, пройдены:

```text
профильный backend: 142 passed
профильный frontend: 49 passed
TypeScript typecheck: PASS
сборка и проверка пакета: PASS
канонический run_full_check.ps1 -SkipDocker: PASS
гигиена Git и синхронизация origin/core: PASS
```

Финальная комплексная проверка и приёмка владельцем всего C1.5R зафиксированы в отчёте C1.5R.7.

## Семантика предпросмотра C1.5R.3

См. [`card-preview-semantics.md`](card-preview-semantics.md). Полный предпросмотр использует нативные лицевую сторону и ответ reviewer: Inspector показывает лицевую сторону, расширенный диалог — ответ, а компактная идентичность не меняется.
