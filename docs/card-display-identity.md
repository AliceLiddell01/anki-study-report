# Display identity карточки

## Статус

**Канонический baseline:** `C1.5R.1 — Complete`  
**Опциональный formatter layer:** `C1.5R.2 — Complete`  
**Ветка:** `core`

**Реализация:**

```text
anki_study_report/card_display_identity.py
anki_study_report/card_display_formatter_store.py
anki_study_report/card_display_formatter_service.py
anki_study_report/card_display_formatter_runtime.py
```

**Публичные контракты:** Search schema v2 и Triage schema v3; C1.5R.2 их не изменяет.

C1.5R.1 установил одну backend-owned identity точной карточки для Search, Triage и текущих Cards surfaces. C1.5R.2 добавил над этим projector опциональный bounded declarative formatter.

При отсутствующем, disabled, corrupt, unsupported или unavailable formatter, а также при пустом formatter output система всегда возвращается к завершённой семантике R1.

Связанные документы:

- [`card-display-formatter-v1.md`](card-display-formatter-v1.md);
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md);
- [`../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md).

## Общая identity точной карточки

Одна compact identity используется в:

- строке результата Search card;
- заголовке Search card Inspector;
- каноническом Triage item;
- item очереди Cards;
- заголовке Cards Inspector.

Search в note mode остаётся note projection и сохраняет `primaryText`. В card rows, card details и Triage items card alias `primaryText` отсутствует.

## Авторитетный projector

`project_card_display_identity(card, formatter=None)` отвечает за одну точную card.

Без active formatter источники используются в таком порядке:

1. native Browser question: `card.question(reload=True, browser=True)`;
2. native reviewer front: `card.question(reload=True, browser=False)`;
3. явное состояние `media_only` или `unavailable`.

При active formatter сначала используется только объявленный `inputSource`.

Request-local resolver выбирает конфигурацию по точной паре:

```text
(noteTypeId, templateOrdinal)
```

Поддерживаются default formatter note type и exact disabled opt-out. Names, decks, fields и fuzzy similarity никогда не участвуют в binding.

При ошибке configured source уже отрендеренные значения переиспользуются, после чего применяется каноническая последовательность fallback. Каждый source рендерится не более одного раза за projection одной card. Projector никогда не вызывает `card.answer()`.

## Упорядоченная compact tokenization

Parser создаёт только tokens:

```text
text
line_break
image
audio
```

Порядок text и media tokens сохраняется. Inline nodes объединяются без выдуманного separator. `<br>` и block boundaries создают новые строки. HTML entities декодируются. Whitespace нормализуется только внутри итоговых строк.

Удаляется содержимое:

- `script`, `style`, `iframe`;
- `object`, `embed`;
- SVG/MathML;
- template/form;
- unsafe media containers.

Malformed blocked nesting fail closed.

Каноническая projection R1 пропускает media tokens и выбирает первую содержательную строку. Поэтому точный Japanese fixture с большим количеством media остаётся:

```text
【に】（する）
```

Включённый reviewer-front formatter с `imageMode: stem` может вернуть:

```text
【に】感謝（する）
```

Safe media handling, policy enums, выбор строк и точная truncation описаны в [`card-display-formatter-v1.md`](card-display-formatter-v1.md). Media file никогда не открывается и не проверяется на существование.

## Wire contract

Card identity остаётся плоским exact fragment:

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

Правила coherence:

- `available`: bounded non-empty text и отрендеренный Browser/reviewer source;
- `media_only`: пустой text, без truncation, rendered source сохраняется;
- `unavailable`: пустой text, source `none`, без truncation.

Formatter state и configuration не копируются в Search/Triage wire data. Публичных fields `formatterApplied`, `formatterId`, aliases, HTML или filename metadata нет.

## Schemas Search и Triage

Search query/inspect остаются strict schema v2. Search metadata остаётся независимым variant schema v1. Triage использует точную schema v3 в этом contract snapshot; дальнейшие additive изменения candidate source описаны отдельно в Triage v4.

`project_card_row()` обслуживает обычный Search, Search inspect и exact-card resolution, который переиспользует Triage. Поэтому все card surfaces используют один resolver и один backend identity path; второй formatter implementation в Triage отсутствует.

Строгие TypeScript parsers отклоняют:

- старые schemas;
- unknown keys;
- card aliases;
- malformed IDs;
- слишком длинный text;
- incoherent display state/source/text.

## Поведение UI

Для `available` backend text отображается без изменений. Frontend локализует только явные fallback states:

| State | RU | EN |
| --- | --- | --- |
| `media_only` | Карточка только с медиа | Card with media only |
| `unavailable` | Текст карточки недоступен | Card text unavailable |

C1.5R.2 не добавляет formatter route, page, hook, Settings navigation, form, live preview или Cards redesign. Guided configuration относится к C1.5R.6, preview semantics — к C1.5R.3.

## Безопасность и приватность

Dashboard остаётся loopback-only и token-protected. Frontend никогда не читает collection. Compact identity и formatter configuration остаются локальными и не копируются в telemetry или normal logs.

Runtime не выполняет:

- JavaScript или Python;
- SQL или shell;
- regex или selectors;
- expressions или callbacks;
- dynamic imports;
- subprocess.

Не логируются raw HTML, значения note fields, содержимое media, absolute paths, renderer exceptions, formatter filenames, сгенерированный `displayText` или tokens.

## Состояние проверки

C1.5R.1 и C1.5R.2 завершены. Для implementation tree C1.5R.2, committed и pushed как `edad09e8ffae443b94e192b266084abb66c37adf`, пройдены:

```text
focused backend: 142 passed
focused frontend: 49 passed
TypeScript typecheck: PASS
package build and validation: PASS
canonical run_full_check.ps1 -SkipDocker: PASS
Git hygiene and origin/core synchronization: PASS
```

Итоговая integrated verification и owner acceptance всего C1.5R зафиксированы в reports C1.5R.7.

## Семантика preview C1.5R.3

См. [`card-preview-semantics.md`](card-preview-semantics.md). Полный preview использует reviewer/native front и answer: Inspector показывает front, развёрнутый dialog — answer, а compact identity не меняется.