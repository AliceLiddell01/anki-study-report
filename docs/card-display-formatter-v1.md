# Formatter идентичности отображения карточки v1

## Статус

**Этап:** `C1.5R.2 — завершено`  
**Ветка:** `core`  
**Schema:** [`schemas/card-display-formatter-v1.schema.json`](../schemas/card-display-formatter-v1.schema.json)

**Runtime:**

```text
anki_study_report/card_display_formatter_store.py
anki_study_report/card_display_formatter_service.py
anki_study_report/card_display_formatter_runtime.py
```

Card display formatter v1 — независимый локальный контракт конфигурации для изменения компактной идентичности точной пары «тип заметки Anki — шаблон».

Он не:

- расширяет Inspection Profile v1;
- меняет полный предпросмотр Inspector или расширенный предпросмотр;
- изменяет collection;
- выполняет пользовательский код.

## Точное назначение

Без конфигурации сохраняется каноническая идентичность R1:

```text
【に】（する）
```

Для настроенного типа заметки Japanese, лицевая сторона reviewer которого содержит:

```html
【<b>に</b>】<img src="感.gif"><img src="謝.gif">（<b>する</b>）
```

включённый formatter с `imageMode: stem` может вернуть:

```text
【に】感謝（する）
```

Programming и любые другие типы заметок без formatter, привязанного к точному ID, сохраняют существующую каноническую идентичность.

## Независимое хранение

Документ хранится отдельно для активного профиля Anki:

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

- детерминированный UTF-8 JSON;
- временный файл в том же каталоге;
- `flush`;
- `os.fsync`;
- `os.replace`.

Каждое успешное сохранение или удаление увеличивает монотонную `revision`; вызывающая сторона передаёт `expectedRevision`.

### Состояния восстановления

| Состояние | Поведение |
| --- | --- |
| `missing` | пустой документ с revision 0 |
| `corrupt` или недопустимый v1 | переименование в quarantine и fallback на каноническое отображение |
| будущая schema | байты сохраняются, запись отклоняется, используется fallback канонического отображения |
| недоступный файл | состояние `unavailable`, используется fallback канонического отображения |

Ошибки API и обычные логи не содержат путь или содержимое документа.

## Структура документа и ограничения

Канонический пустой документ:

```json
{
  "schemaVersion": 1,
  "revision": 0,
  "formatters": []
}
```

Запись formatter:

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

Жёсткие ограничения:

```text
документ                         1 МиБ
formatters                       1000
записей на тип заметки           33
noteTypeName/templateName        160 символов Unicode
templateOrdinal                  null | 0..31
lineSeparator                    0..8 символов, без управляющих символов, CR и LF
maxLines                         1..4
maxCharacters                    1..240
noteTypeId                       положительная десятичная строка signed-64
```

Корневой и вложенные объекты отклоняют неизвестные ключи. Boolean не считается integer.

По принципу fail closed обрабатываются:

- дублирующиеся ключи `(noteTypeId, templateOrdinal)`;
- несогласованные nullable-поля шаблона;
- недопустимые timestamps;
- запись в документ будущей schema.

## Идентичность и разрешение конфигурации

Ключ привязки:

```text
(noteTypeId, templateOrdinal)
```

Имена являются только ограниченными snapshot для отображения и диагностики. Привязка по имени, колоде, значению поля или нечёткому сходству отсутствует.

Порядок разрешения:

```text
точный enabled  → применить точный formatter
точный disabled → запретить наследование стандарта и использовать канонический fallback R1
точный отсутствует + стандарт типа заметки enabled  → применить стандарт
точный отсутствует + стандарт disabled/отсутствует → канонический fallback R1
```

Store читается один раз на запрос Search или Triage. После этого одна неизменяемая map resolver переиспользуется для всех проецируемых карточек.

Отсутствуют:

- чтения файлов для каждой карточки;
- HTTP-вызовы;
- сканирование collection;
- изменяемый глобальный cache formatter на уровне модуля.

## Декларативные политики

Enum:

```text
storedState: enabled | disabled
inputSource: browser_question | reviewer_front
textMode: preserve | omit
imageMode: omit | filename | stem | marker
audioMode: omit | filename | stem | marker
```

Фиксированные маркеры:

```text
image: 🖼
audio: 🔊
```

Текст маркеров в v1 не настраивается.

Schema и API не содержат возможности для:

- JavaScript, Python или SQL;
- shell или regex;
- selector, expression или callback;
- import или module;
- пути или URL;
- значения поля;
- HTML или CSS шаблона;
- удалённого endpoint.

Runtime не использует `eval`, `exec`, динамический import, plugin callback или subprocess.

## Упорядоченный поток токенов

Компактный parser создаёт только:

```text
text
line_break
image
audio
```

Порядок источника сохраняется. Между соседними inline-токенами текста и media не добавляется искусственный разделитель. HTML-entities декодируются. `<br>` и границы блоков создают переносы строк. Пробелы нормализуются внутри итоговых строк. Повреждённое запрещённое встроенное содержимое работает по принципу fail closed.

Распознаётся безопасное audio:

- `[sound:filename]`;
- безымянный `[anki:play:...]`;
- безопасные отрендеренные ссылки audio и source.

Безымянное audio выводит только фиксированный маркер, когда задано `audioMode: marker`.

## Правила безопасного имени media

Media-токен может содержать только нормализованное плоское локальное имя файла либо `null`.

Разрешённое имя:

- имеет ограниченную длину;
- не содержит scheme;
- не является абсолютным путём;
- не содержит slash или backslash;
- не содержит traversal;
- не содержит управляющих символов.

Validation выполняется после декодирования HTML-entities.

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

Отклонённый или безымянный media-токен всё ещё может вывести фиксированный маркер. Необработанный небезопасный текст наружу не возвращается.

Обработка formatter никогда не:

- открывает media-файл;
- проверяет существование файла;
- разрешает путь файловой системы;
- загружает удалённый ресурс.

## Семантика строк и truncation

Порядок обработки:

```text
tokenize
→ применить режимы text и media
→ построить строки
→ удалить пустые строки
→ выбрать первые maxLines содержательных строк
→ нормализовать пробелы каждой строки
→ объединить через lineSeparator
→ применить maxCharacters
```

Truncation:

- добавляет одно завершающее многоточие;
- никогда не превышает `maxCharacters`;
- точно устанавливает `displayTruncated`.

Допустимый непустой настроенный результат:

```text
displayStatus = available
displaySource = настроенный inputSource
displayText = настроенный результат
displayTruncated = результат truncation formatter
```

Search остаётся на schema v2, Triage — на schema v3 в snapshot этого контракта. В payload Search и Triage не добавляются публичные поля `formatterApplied`, ID formatter, alias или конфигурация formatter.

## Канонический fallback и повторное использование рендера

Без активного formatter:

```text
вопрос Browser → лицевая сторона reviewer → media_only/unavailable
```

При активном formatter сначала используется только выбранный источник.

Следующие состояния возвращают обработку к неизменённому каноническому fallback R1:

- рендер недоступен;
- поток токенов недопустим;
- результат пуст;
- результат полностью удалён политикой.

В рамках проекции одной карточки каждый источник рендерится не более одного раза. Неудачная настроенная попытка кэшируется и переиспользуется fallback. `card.answer()` никогда не вызывается.

## Локальный API dashboard

Защищённые токеном POST-only JSON endpoints:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

Все endpoints используют schema v1, точные ключи и существующее ограничение тела 64 КиБ.

Запрос query:

```json
{"schemaVersion": 1}
```

Ответ query содержит:

```text
schemaVersion
status: empty | available | corrupt | future_schema | unavailable
revision
formatters
errorCode
quarantined
```

`validate` принимает один строгий formatter, ничего не сохраняет и не читает collection. Возвращается нормализованное значение либо ограниченные ошибки полей.

Действия update:

```text
save   expectedRevision + formatter
delete expectedRevision + точный ключ noteTypeId/templateOrdinal
```

Delete не может случайно удалить все formatters типа заметки. Конфликт revision возвращает актуальную revision. Ошибки раскрывают только обобщённые машинные коды.

## Контракт frontend

Строгие types, parser и client:

```text
web-dashboard/src/types/cardDisplayFormatters.ts
web-dashboard/src/lib/cardDisplayFormattersApi.ts
```

Они отклоняют:

- старые и будущие schema;
- неизвестные ключи;
- повреждённые ID и timestamps;
- недопустимые enum и ограничения;
- дублирующиеся ключи;
- несогласованные nullable-поля шаблона;
- повреждённые envelopes ошибок.

C1.5R.2 не добавляет маршрут, страницу, hook, навигацию Settings или форму. Пошаговый UX formatter относится к C1.5R.6.

## Безопасность и конфиденциальность

Сохраняются границы:

```text
server доступен только через loopback-интерфейс
токен dashboard
frontend не имеет доступа к collection
нет выполнения JavaScript шаблона через iframe
нет произвольного кода или языка запросов
нет чтения media-файлов или удалённых загрузок
нет необработанного HTML или полей заметки в store formatter
нет локальных путей или URL с токеном
нет телеметрии и обычных логов для имени файла formatter или displayText
```

Настроенный `displayText` возвращается только локальному dashboard как явный продуктовый результат.

## Отложенная работа

В formatter v1 не входят:

```text
UI Settings и пошаговой настройки
автоматические предложения
API живого предпросмотра formatter
семантика предпросмотра лицевой и обратной стороны
переработка источников кандидатов
переработка очереди Cards
действия, recheck и определение результата C1.6
```
