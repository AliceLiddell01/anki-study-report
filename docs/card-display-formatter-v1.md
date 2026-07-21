# Formatter display identity карточки v1

## Статус

**Этап:** `C1.5R.2 — Complete`  
**Ветка:** `core`  
**Schema:** [`schemas/card-display-formatter-v1.schema.json`](../schemas/card-display-formatter-v1.schema.json)

**Runtime:**

```text
anki_study_report/card_display_formatter_store.py
anki_study_report/card_display_formatter_service.py
anki_study_report/card_display_formatter_runtime.py
```

Card display formatter v1 — независимый локальный configuration contract для изменения compact identity точной пары Anki note type/template.

Он не:

- расширяет Inspection Profile v1;
- меняет полный preview Inspector или expanded preview;
- изменяет collection;
- выполняет пользовательский код.

## Точное назначение

Без configuration сохраняется каноническая identity R1:

```text
【に】（する）
```

Для настроенного Japanese note type, reviewer front которого содержит:

```html
【<b>に</b>】<img src="感.gif"><img src="謝.gif">（<b>する</b>）
```

включённый formatter с `imageMode: stem` может вернуть:

```text
【に】感謝（する）
```

Programming и любые другие note types без formatter, привязанного к точному ID, сохраняют существующую canonical identity.

## Независимое хранение

Документ хранится отдельно для активного Anki profile:

```text
<profile>/addon_data/<addon-id>/card_display_formatters.json
```

Он отделён от:

```text
inspection_profiles.json
config.json
meta.json
collection
note types/templates
```

Store использует:

- deterministic UTF-8 JSON;
- temporary file в той же директории;
- `flush`;
- `os.fsync`;
- `os.replace`.

Каждый успешный save/delete увеличивает monotonic `revision`; caller передаёт `expectedRevision`.

### Recovery states

| State | Поведение |
| --- | --- |
| `missing` | пустой документ revision 0 |
| `corrupt` / invalid v1 | quarantine rename и fallback к canonical display |
| future schema | bytes сохраняются, writes отклоняются, используется canonical display fallback |
| inaccessible | `unavailable`, используется canonical display fallback |

API errors и normal logs не содержат path или document content.

## Document shape и ограничения

Канонический пустой документ:

```json
{
  "schemaVersion": 1,
  "revision": 0,
  "formatters": []
}
```

Formatter entry:

```json
{
  "noteTypeId": "123",
  "noteTypeName": "Japanese Vocabulary",
  "templateOrdinal": null,
  "templateName": null,
  "storedState": "enabled",
  "inputSource": "reviewer_front",
  "textMode": "preserve",
  "imageMode": "stem",
  "audioMode": "omit",
  "maxLines": 1,
  "lineSeparator": " ",
  "maxCharacters": 240,
  "updatedAt": "2026-07-19T00:00:00Z"
}
```

Hard bounds:

```text
document                         1 MiB
formatters                       1000
entries per note type            33
noteTypeName/templateName        160 Unicode characters
templateOrdinal                  null | 0..31
lineSeparator                    0..8 characters, no controls/CR/LF
maxLines                         1..4
maxCharacters                    1..240
noteTypeId                       positive signed-64 decimal string
```

Root и nested objects отклоняют unknown keys. Booleans не считаются integers.

Fail closed обрабатываются:

- duplicate keys `(noteTypeId, templateOrdinal)`;
- incoherent nullable template fields;
- invalid timestamps;
- writes в future schema.

## Identity и resolution

Binding key:

```text
(noteTypeId, templateOrdinal)
```

Names являются только bounded display/diagnostic snapshots. Binding по name, deck, field value или fuzzy similarity отсутствует.

Resolution:

```text
exact enabled  → применить exact formatter
exact disabled → запретить default inheritance и использовать canonical R1 fallback
exact отсутствует + note-type default enabled  → применить default
exact отсутствует + default disabled/absent    → canonical R1 fallback
```

Store читается один раз на Search/Triage request. После этого одна immutable resolver map переиспользуется для всех projected cards.

Отсутствуют:

- per-card file reads;
- HTTP calls;
- collection scans;
- mutable module-global formatter cache.

## Declarative policies

Enums:

```text
storedState: enabled | disabled
inputSource: browser_question | reviewer_front
textMode: preserve | omit
imageMode: omit | filename | stem | marker
audioMode: omit | filename | stem | marker
```

Фиксированные markers:

```text
image: 🖼
audio: 🔊
```

Marker text в v1 не настраивается.

Schema и API не содержат capabilities для:

- JavaScript, Python или SQL;
- shell или regex;
- selector, expression или callback;
- import/module;
- path или URL;
- field value;
- template HTML/CSS;
- remote endpoint.

Runtime не использует `eval`, `exec`, dynamic import, plugin callback или subprocess.

## Упорядоченный token stream

Compact parser создаёт только:

```text
text
line_break
image
audio
```

Source order сохраняется. Между соседними inline text/media tokens не добавляется выдуманный separator. HTML entities декодируются. `<br>` и block boundaries создают line breaks. Whitespace нормализуется внутри итоговых строк. Malformed blocked embedded content fail closed.

Распознаётся безопасное audio:

- `[sound:filename]`;
- unnamed `[anki:play:...]`;
- безопасные rendered audio/source references.

Unnamed audio выдаёт только фиксированный marker, когда `audioMode: marker`.

## Правила безопасного имени media

Media token может содержать только normalized flat local filename либо `null`.

Разрешённое имя:

- bounded;
- без scheme;
- без absolute path;
- без slash/backslash;
- без traversal;
- без control characters.

Validation выполняется после HTML entity decoding.

Примеры отклоняемых ссылок:

```text
../x.png
folder/x.png
folder\x.png
C:x.png
http://...
https://...
data:...
file:...
```

Отклонённый или unnamed media token всё ещё может вывести фиксированный marker. Raw unsafe text наружу не возвращается.

Formatter processing никогда не:

- открывает media file;
- проверяет существование file;
- разрешает filesystem path;
- загружает remote resource.

## Семантика строк и truncation

Порядок обработки:

```text
tokenize
→ применить text/media modes
→ построить lines
→ удалить empty lines
→ выбрать первые maxLines meaningful lines
→ нормализовать whitespace каждой line
→ объединить через lineSeparator
→ применить maxCharacters
```

Truncation:

- добавляет один terminal ellipsis;
- никогда не превышает `maxCharacters`;
- точно устанавливает `displayTruncated`.

Валидный non-empty configured result:

```text
displayStatus = available
displaySource = configured inputSource
displayText = configured output
displayTruncated = formatter truncation
```

Search остаётся schema v2, Triage — schema v3 в этом contract snapshot. В Search/Triage payload не добавляются публичные fields `formatterApplied`, formatter ID, alias или formatter configuration.

## Canonical fallback и повторное использование render

Без active formatter:

```text
Browser question → reviewer front → media_only/unavailable
```

При active formatter сначала используется только выбранный source.

Следующие состояния возвращают обработку к неизменённому canonical fallback R1:

- render unavailable;
- invalid token stream;
- empty output;
- output, полностью удалённый policy.

В рамках projection одной card каждый source рендерится не более одного раза. Неудачный configured attempt кэшируется и переиспользуется fallback. `card.answer()` никогда не вызывается.

## Локальный dashboard API

Token-protected POST-only JSON endpoints:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

Все endpoints используют schema v1, exact keys и существующий body cap 64 KiB.

Query request:

```json
{"schemaVersion": 1}
```

Query response содержит:

```text
schemaVersion
status: empty | available | corrupt | future_schema | unavailable
revision
formatters
errorCode
quarantined
```

`validate` принимает один strict formatter, ничего не сохраняет и не читает collection. Возвращается normalized value либо bounded field errors.

Update actions:

```text
save   expectedRevision + formatter
delete expectedRevision + exact noteTypeId/templateOrdinal key
```

Delete не может случайно удалить все formatters note type. Revision conflict возвращает current revision. Errors раскрывают только generic machine codes.

## Frontend contract

Strict types/parser/client:

```text
web-dashboard/src/types/cardDisplayFormatters.ts
web-dashboard/src/lib/cardDisplayFormattersApi.ts
```

Они отклоняют:

- old/future schemas;
- unknown keys;
- malformed IDs и timestamps;
- invalid enums/limits;
- duplicate keys;
- incoherent nullable template fields;
- malformed error envelopes.

C1.5R.2 не добавляет route, page, hook, Settings navigation или form. Guided formatter UX относится к C1.5R.6.

## Безопасность и приватность

Сохраняются границы:

```text
loopback-only server
dashboard token
frontend не имеет доступа к collection
нет iframe/template JavaScript execution
нет arbitrary code или query language
нет чтения media files или remote loads
нет raw HTML/note fields в formatter store
нет local paths или token-bearing URLs
нет telemetry/normal logs для formatter filename или displayText
```

Configured `displayText` возвращается только локальному dashboard как явный product output.

## Отложенная работа

В formatter v1 не входят:

```text
Settings/guided UI
automatic suggestions
live formatter preview API
front/back preview semantics
candidate-source redesign
Cards inbox redesign
C1.6 actions/recheck/resolution
```