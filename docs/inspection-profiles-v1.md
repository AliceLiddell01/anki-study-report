# Inspection Profiles v1

## Статус и назначение

**Версия контракта:** 1  
**Этап runtime:** C1.3  
**UI:** реализован в C1.4 по маршруту `#/settings/inspection-profiles`

Inspection Profile — локальный декларативный набор требований к содержимому для одного точного типа заметки Anki. Например, он может определить, что Japanese Vocabulary требует meaning и audio, не применяя это правило к карточкам Programming.

Inspection Profile никогда не:

- выполняет пользовательский код;
- изменяет collection;
- изменяет заметку, карточку, шаблон или media-файл.

Типы заметок Anki владеют упорядоченными полями и шаблонами карточек; одна заметка может создавать несколько карточек. Контракт следует этим нативным границам и не предполагает универсальную форму карточки.

Справочные документы Anki:

- [Getting Started](https://docs.ankiweb.net/getting-started.html);
- [Card Templates](https://docs.ankiweb.net/templates/intro.html);
- [Field Replacements](https://docs.ankiweb.net/templates/fields.html).

## Жизненный цикл

```text
not_configured → suggested → confirmed
                         ↘ needs_review
suggested | confirmed → disabled
```

Сохраняемое состояние:

```text
suggested | confirmed | disabled
```

`not_configured` и `needs_review` вычисляются. Авторитетным является только профиль `confirmed`, fingerprint и точные ссылки которого всё ещё совпадают с актуальным типом заметки.

| Фактическое состояние | Авторитетные причины по содержимому |
| --- | --- |
| `not_configured` | нет |
| `suggested` | нет |
| `confirmed` | да |
| `needs_review` | нет; fail closed |
| `disabled` | нет |

Причины обучения не зависят от профилей и продолжают работать в любом состоянии. Suggestions не могут автоматически подтвердить, изменить или нечётко повторно связать профиль.

## Хранение и восстановление

Документ хранится внутри активного профиля Anki:

```text
<profile>/addon_data/<addon-id>/inspection_profiles.json
```

Он не хранится в:

- collection;
- глобальной конфигурации add-on;
- типах заметок;
- шаблонах.

Это соответствует границам Anki [Configuration and User Files](https://addon-docs.ankiweb.net/addon-config.html) и сохраняет runtime-состояние изолированным для каждого профиля Anki.

Store потокобезопасен и использует детерминированный UTF-8 JSON. Запись выполняется через временный файл в том же каталоге, `flush`, `fsync` и `os.replace`.

Каждая успешная запись увеличивает монотонную `revision`; writer обязан передать текущую `expectedRevision`. Устаревшая revision возвращает конфликт и не перезаписывает более новое состояние.

Поведение восстановления:

- отсутствующий файл — допустимый пустой store с revision 0;
- повреждённый или недопустимый v1 — исходный файл атомарно переименовывается с ограниченным suffix `.corrupt-<UTC>`, источник работает по принципу fail closed;
- будущая `schemaVersion` — файл остаётся побайтно неизменным, запись отклоняется;
- недоступный store — безопасное состояние `unavailable` без утечки исключения или пути.

Пользовательский путь не принимается. Размер документа ограничен 1 МиБ.

## Schema v1

Переносимая schema Draft 2020-12:

[`schemas/inspection-profile-v1.schema.json`](../schemas/inspection-profile-v1.schema.json)

Production-validator Python независимо проверяет те же структуры, а также:

- уникальность между полями;
- ID signed-64-bit;
- связи mappings и checks.

Schema следует:

- [JSON Schema Core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html);
- [Validation 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation.html).

```json
{
  "schemaVersion": 1,
  "revision": 1,
  "profiles": [
    {
      "profileId": "note-type-123",
      "noteTypeId": "123",
      "noteTypeName": "Japanese Vocabulary",
      "storedState": "confirmed",
      "displayName": "Japanese vocabulary",
      "expectedFingerprint": {"algorithm": "sha256", "value": "<64 lowercase hex>"},
      "appliesTo": {"templateOrdinals": []},
      "fieldMappings": [
        {"role": "meaning", "fields": [{"ordinal": 2, "name": "Meaning"}]}
      ],
      "checks": [
        {
          "checkId": "meaning-required",
          "kind": "non_empty",
          "roles": ["meaning"],
          "mode": "any",
          "priority": "high"
        }
      ],
      "confirmedAt": "2026-07-18T00:00:00Z",
      "updatedAt": "2026-07-18T00:00:00Z"
    }
  ]
}
```

V1 разрешает один профиль на `noteTypeId`; ID представлены положительными десятичными строками signed-64-bit. Неизвестные поля отклоняются.

Ограничены:

- ID профилей и проверок;
- роли;
- timestamps;
- массивы;
- числовые параметры.

Документ не содержит значения полей, HTML или CSS шаблона, привязку к колоде, путь, код или query.

## Структуры и fingerprints

Ограниченный каталог читает актуальные metadata моделей Anki внутри сериализованного `QueryOp` в соответствии с Anki [Background Operations](https://addon-docs.ankiweb.net/background-ops.html).

Публичная структура содержит только:

- ID и имя типа заметки и вид `standard | cloze`;
- ordinal и точное имя упорядоченного поля;
- ordinal и имя упорядоченного шаблона и имена полей, на которые ссылаются лицевая и обратная стороны;
- fingerprint SHA-256.

Fingerprint — SHA-256 от канонического JSON, содержащего:

- `noteTypeId`;
- упорядоченные поля;
- идентичности и ссылки шаблонов;
- вид.

Fingerprint меняют:

- добавление, удаление, переименование или изменение порядка поля;
- значимые изменения ссылок шаблона на поля.

Fingerprint не меняют:

- CSS;
- статический текст шаблона;
- время изменения;
- значения выборки;
- назначение колоды.

Подтверждение проверяет и ordinal, и snapshot точного имени поля. Устаревший профиль никогда не связывается нечётко с переименованными полями или другим `noteTypeId`.

Ограниченные коды причин:

```text
field_added
field_removed
field_changed
template_field_usage_changed
note_type_missing
fingerprint_mismatch
unsupported_profile
```

## Роли и suggestions

Стандартные роли:

```text
term reading meaning example audio image part_of_speech pitch
question answer explanation code
```

Ограниченная пользовательская роль может соответствовать regex:

```text
[a-z][a-z0-9_]{0,39}
```

Каждое сопоставленное поле — точная ссылка `{ordinal, name}`. Роли и ссылки на поля не могут дублироваться. Каждая роль, используемая проверкой, должна иметь mapping.

Suggestions переиспользуют детерминированные локальные эвристики note intelligence. Они могут вернуть:

- обнаруженный вид;
- confidence каждого mapping;
- предлагаемые checks;
- предупреждения;
- неразрешённые поля.

Suggestions не используют network, LLM или телеметрию и не сохраняют выборки заметок. Неоднозначность остаётся неразрешённой; suggestion никогда не становится авторитетным автоматически.

## Проверки из allowlist

| Вид | Семантика |
| --- | --- |
| `non_empty` | нормализованный содержательный текст существует в `any` или `all` сопоставленных ссылках; поля только с media считаются пустым текстом |
| `contains_audio` | в объявленных ссылках существует безопасный маркер `[sound:filename]`; существование файла не проверяется |
| `contains_image` | в объявленных ссылках существует безопасная ссылка `<img … src=…>`; media не читается |
| `min_text_length` | нормализованная длина обычного Unicode-текста удовлетворяет диапазону `1..10000` в режиме `any` или `all` |
| `one_of_roles_non_empty` | хотя бы одна целевая роль содержит содержательный текст |
| `all_roles_non_empty` | каждая целевая роль содержит содержательный текст |

Обычный текст использует существующее безопасное извлечение. Tags, невидимая разметка, media-маркеры, NBSP и повторяющиеся пробелы не могут создать ложный текст.

Проверки используют только подтверждённые точные mappings и необязательный scope ordinal шаблона. Полный рендер карточки и JavaScript шаблона не выполняются.

Отклонённые возможности правил:

- произвольные языки regex и substring;
- CSS-selectors;
- Python, JavaScript, SQL или shell;
- imports и callbacks;
- проверка файловой системы или существования media;
- сетевые правила;
- агрегаты между заметками;
- условия по истории повторений.

## Оценка и безопасное подтверждение

Неуспешные проверки создают типизированные внутренние результаты со следующими данными:

- идентичность профиля, типа заметки и проверки;
- вид проверки;
- scope заметки;
- приоритет;
- роли;
- точные идентичности сопоставленных полей;
- revision профиля;
- fingerprint;
- количество sibling-карточек;
- scope шаблона.

Подтверждение может включать ожидаемое условие, фактическую или ожидаемую длину текста либо `markerPresent: false`.

Подтверждение никогда не содержит:

- необработанное содержимое заметки;
- HTML;
- имя audio- или image-файла;
- локальный путь;
- токен;
- исходный код шаблона;
- текст исключения.

Предпросмотр принимает не более 20 явных ID карточек либо ограниченную выборку точного типа заметки и возвращает только безопасное подтверждение неуспешных проверок.

## API runtime

Все endpoints:

- доступны только через loopback-интерфейс;
- требуют текущий токен dashboard;
- принимают `POST application/json`;
- передают ID и документы в body;
- ограничивают body до 64 КиБ;
- возвращают обобщённые машинные ошибки.

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

Операции:

- `query`: `schemaVersion`, `noteTypeIds` (`0..200`), `limit` (`1..500`); возвращает структуры, фактические состояния, сохранённый профиль, suggestions и revision store;
- `validate` v1: строгий черновик и от 0 до 20 точных ID карточек; ничего не сохраняет;
- `validate` v2: строгий черновик и `{mode: "sample", limit: 1..20}`; выбирает детерминированные минимальные ID карточек только для `profile.noteTypeId`, читает не более `limit + 1`, сообщает truncation и ничего не сохраняет;
- `update/save`: `expectedRevision`, явный `targetState`, строгий профиль и проверка актуального fingerprint и references;
- `update/disable`: сохраняет конфигурацию, но отключает авторитетность;
- `update/delete`: удаляет только указанный профиль.

Актуальные чтения моделей и карточек предпросмотра выполняются через сериализованный `QueryOp`.

Единственная запись — локальный для профиля JSON-файл. Она не является Anki `CollectionOp` и не изменяет состояние collection.

## Канонический Triage

Inspection Profiles добавляют в Triage:

- состояние источника проверок профилей;
- общее `contentChecks`;
- стабильный `reasonId`;
- подтверждение вида `profile_check`.

Коды содержимого:

```text
content.required_text_missing
content.audio_missing
content.image_missing
content.text_too_short
content.required_group_missing
```

Идентичность причины:

```text
profile:<profileId>:check:<checkId>
```

Поэтому две проверки одного вида остаются различимыми. Scope содержимого — `note`.

Одна неуспешная заметка показывается один раз на детерминированно выбранной representative card; подтверждение сообщает только количество затронутых sibling-карточек.

Автоматический dataset выбирает минимальный ID карточки-кандидата. Рабочий набор Search выбирает первую явно выбранную применимую sibling-карточку, сохраняет запрошенный порядок и не создаёт невыбранные строки. Независимые причины обучения уровня карточки у siblings остаются отдельными.

Автоматическая оценка использует один общий ограниченный запрос кандидатов revlog, карточек и заметок с лимитом 100 и sentinel truncation, включая кандидатов без проблемы обучения. Рабочий набор Search загружает не более 200 точных ID одним пакетом. Необработанные поля не покидают backend.

Устаревший `attentionCards`, включая эвристические подписи отсутствующих полей, не меняется; эвристики не становятся каноническими причинами содержимого.

Состояние содержимого различает:

```text
available
no_confirmed_profiles
profiles_need_review
disabled
partial
unavailable
```

Отсутствующие профили не считаются ошибкой. Недоступность store или модели никогда не означает устранение проблемы.

## Примеры

Japanese Vocabulary может сопоставить:

```text
meaning → Meaning
audio → Audio
example → Example
```

и подтвердить проверки `non_empty` и `contains_audio`. Отсутствующий маркер audio создаёт `content.audio_missing` только после явного подтверждения.

Programming может сопоставить:

```text
question → Question
answer → Answer
```

и подтвердить две проверки `non_empty` без требования audio. Правило Japanese к нему не применяется, поскольку профили привязаны к точному `noteTypeId` и fingerprint.

## Ограничения, конфиденциальность и совместимость

| Ресурс | Ограничение |
| --- | ---: |
| документ | 1 МиБ |
| профили | 500 |
| mappings и checks на профиль | 32 / 32 |
| references на mapping или check | 16 / 16 |
| поля и шаблоны в структуре | 64 / 32 |
| карточки предпросмотра | 20 |
| автоматические кандидаты | 100 |
| рабочий набор Search | 200 |

Содержимое профиля, mappings полей и checks никогда не отправляются через телеметрию.

Логи содержат только коды операций и ошибок и виды исключений, но не данные профиля, значения заметок, пути или токены.

Не меняются:

- Search;
- Safe Actions;
- Signals;
- Notifications;
- изоляция предпросмотра;
- существующий `CardsPage`;
- устаревший payload отчёта.

C1.4 добавляет локальный editor Settings и строгий client-side-import/export одного профиля, описанный в [`inspection-profiles-ui.md`](inspection-profiles-ui.md). Он не добавляет очередь или Inspector Cards и mutation collection.

## Проекция пошагового editor

UI C1.5R.6 не определяет вторую schema. Созданное только в browser suggestion, элементы управления Basic и Advanced редактируют один точный документ v1.

Созданное происхождение и пользовательское dirty-состояние являются состоянием UI и никогда не сохраняются в профиль. Validate schema v2 и update schema v1 остаются неизменными.
