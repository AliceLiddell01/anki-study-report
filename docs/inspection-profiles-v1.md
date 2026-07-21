# Inspection Profiles v1

## Статус и назначение

**Версия контракта:** 1  
**Runtime stage:** C1.3  
**UI:** реализован в C1.4 по маршруту `#/settings/inspection-profiles`

Inspection Profile — локальный declarative набор требований к содержимому для одного точного Anki note type. Например, он может определить, что «Japanese Vocabulary требует meaning и audio», не применяя это правило к карточкам Programming.

Inspection Profile никогда не:

- выполняет пользовательский код;
- изменяет collection;
- изменяет note, card, template или media file.

Anki note types владеют упорядоченными fields и card templates; одна note может создавать несколько cards. Контракт следует этим нативным границам и не предполагает универсальную форму карточки.

Справочные документы Anki:

- [Getting Started](https://docs.ankiweb.net/getting-started.html);
- [Card Templates](https://docs.ankiweb.net/templates/intro.html);
- [Field Replacements](https://docs.ankiweb.net/templates/fields.html).

## Lifecycle

```text
not_configured → suggested → confirmed
                         ↘ needs_review
suggested | confirmed → disabled
```

Persisted state:

```text
suggested | confirmed | disabled
```

`not_configured` и `needs_review` вычисляются. Авторитетным является только `confirmed` profile, у которого fingerprint и exact references всё ещё совпадают с текущим note type.

| Effective state | Авторитетные content reasons |
| --- | --- |
| `not_configured` | нет |
| `suggested` | нет |
| `confirmed` | да |
| `needs_review` | нет; fail closed |
| `disabled` | нет |

Learning reasons не зависят от profiles и продолжают работать в любом состоянии. Suggestions не могут автоматически подтвердить, изменить или fuzzy-rebind profile.

## Хранение и recovery

Документ хранится внутри активного Anki profile:

```text
<profile>/addon_data/<addon-id>/inspection_profiles.json
```

Он не хранится в:

- collection;
- глобальном config add-on;
- note types;
- templates.

Это соответствует границам Anki [Configuration and User Files](https://addon-docs.ankiweb.net/addon-config.html) и сохраняет runtime state изолированным для каждого Anki profile.

Store thread-safe и использует deterministic UTF-8 JSON. Writes выполняются через temporary file в той же директории, `flush`, `fsync` и `os.replace`.

Каждая успешная write увеличивает monotonic `revision`; writer обязан передать текущий `expectedRevision`. Stale revision возвращает conflict и не перезаписывает более новое состояние.

Recovery behavior:

- missing file — валидный empty store, revision 0;
- corrupt/invalid v1 — исходный файл атомарно переименовывается с bounded suffix `.corrupt-<UTC>`, source fail closed;
- future `schemaVersion` — файл остаётся byte-for-byte неизменным, writes отклоняются;
- inaccessible store — безопасный status `unavailable`, без утечки exception/path.

Пользовательский path не принимается. Размер документа ограничен 1 MiB.

## Schema v1

Portable schema Draft 2020-12:

[`schemas/inspection-profile-v1.schema.json`](../schemas/inspection-profile-v1.schema.json)

Production Python validator независимо проверяет те же shapes, а также:

- cross-field uniqueness;
- signed-64-bit IDs;
- relationships mappings/checks.

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

V1 разрешает один profile на `noteTypeId`; IDs представлены positive signed-64-bit decimal strings. Unknown fields отклоняются.

Bounded:

- profile/check IDs;
- roles;
- timestamps;
- arrays;
- numeric parameters.

Документ не содержит field values, template HTML/CSS, deck binding, path, code или query.

## Structures и fingerprints

Bounded catalog читает current Anki model metadata внутри serialized `QueryOp` в соответствии с Anki [Background Operations](https://addon-docs.ankiweb.net/background-ops.html).

Public structure содержит только:

- note type ID, name и kind `standard | cloze`;
- ordered field ordinal и exact name;
- ordered template ordinal/name и referenced field names для front/back;
- SHA-256 fingerprint.

Fingerprint — SHA-256 от canonical JSON, содержащего:

- `noteTypeId`;
- ordered fields;
- template identities/references;
- kind.

Fingerprint инвалидируют:

- add/remove/rename/reorder field;
- релевантные изменения template field references.

Fingerprint не изменяют:

- CSS;
- static template text;
- mod time;
- sample values;
- deck assignment.

Confirmation проверяет и ordinal, и exact field-name snapshot. Stale profile никогда не fuzzy-match-ится к renamed fields или другому `noteTypeId`.

Bounded reason codes:

```text
field_added
field_removed
field_changed
template_field_usage_changed
note_type_missing
fingerprint_mismatch
unsupported_profile
```

## Roles и suggestions

Стандартные roles:

```text
term reading meaning example audio image part_of_speech pitch
question answer explanation code
```

Bounded custom role может соответствовать regex:

```text
[a-z][a-z0-9_]{0,39}
```

Каждый mapped field — точная reference `{ordinal, name}`. Roles и field references не могут дублироваться. Каждый role, используемый check, должен иметь mapping.

Suggestions переиспользуют детерминированные локальные heuristics note intelligence. Они могут вернуть:

- detected kind;
- confidence каждого mapping;
- proposed checks;
- warnings;
- unresolved fields.

Suggestions не используют network, LLM или telemetry и не сохраняют note samples. Ambiguity остаётся unresolved; suggestion никогда не становится authority автоматически.

## Allowlisted checks

| Kind | Семантика |
| --- | --- |
| `non_empty` | normalized meaningful text существует в `any`/`all` mapped refs; media-only fields считаются empty text |
| `contains_audio` | в declared refs существует безопасный marker `[sound:filename]`; существование file не проверяется |
| `contains_image` | в declared refs существует безопасная reference `<img … src=…>`; media не читается |
| `min_text_length` | normalized plain-text Unicode length удовлетворяет `1..10000` в mode `any`/`all` |
| `one_of_roles_non_empty` | хотя бы один target role содержит meaningful text |
| `all_roles_non_empty` | каждый target role содержит meaningful text |

Plain text использует существующее безопасное extraction. Tags, invisible markup, media markers, NBSP и repeated whitespace не могут создать ложный text.

Checks используют только confirmed exact mappings и optional template ordinal scope. Полный card render и template JavaScript не выполняются.

Отклонённые rule capabilities:

- arbitrary regex/substring languages;
- CSS selectors;
- Python, JavaScript, SQL или shell;
- imports/callbacks;
- filesystem/media existence;
- network rules;
- cross-note aggregates;
- review-history conditions.

## Evaluation и безопасное evidence

Failed checks создают typed internal results со следующими данными:

- profile/note-type/check identity;
- check kind;
- note scope;
- priority;
- roles;
- exact mapped field identities;
- profile revision;
- fingerprint;
- sibling count;
- template scope.

Evidence может включать expected condition, actual/expected text length или `markerPresent: false`.

Evidence никогда не содержит:

- raw note content;
- HTML;
- audio/image filename;
- local path;
- token;
- template source;
- exception text.

Preview принимает не более 20 explicit card IDs либо bounded sample точного note type и возвращает только safe failure evidence.

## Runtime API

Все endpoints:

- loopback-only;
- требуют текущий dashboard token;
- принимают `POST application/json`;
- передают IDs/documents в body;
- ограничивают body до 64 KiB;
- возвращают generic machine errors.

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

Операции:

- `query`: `schemaVersion`, `noteTypeIds` (`0..200`), `limit` (`1..500`); возвращает structures, effective states, stored profile, suggestions и store revision;
- `validate` v1: strict draft + `0..20` exact card IDs; не сохраняет изменения;
- `validate` v2: strict draft + `{mode: "sample", limit: 1..20}`; выбирает детерминированные минимальные card IDs только для `profile.noteTypeId`, читает не более `limit + 1`, сообщает truncation и ничего не сохраняет;
- `update/save`: `expectedRevision`, явный `targetState`, strict profile и current fingerprint/reference validation;
- `update/disable`: сохраняет configuration, но отключает authority;
- `update/delete`: удаляет только указанный profile.

Current model reads и preview card reads выполняются через serialized `QueryOp`.

Единственная write — profile-local JSON file. Она не является Anki `CollectionOp` и не изменяет collection state.

## Канонический Triage

Inspection Profiles добавляют в Triage:

- source status profile checks;
- aggregate `contentChecks`;
- stable `reasonId`;
- evidence типа `profile_check`.

Content codes:

```text
content.required_text_missing
content.audio_missing
content.image_missing
content.text_too_short
content.required_group_missing
```

Reason identity:

```text
profile:<profileId>:check:<checkId>
```

Поэтому два checks одного kind остаются различимыми. Content scope — `note`.

Одна failing note показывается один раз на детерминированной representative card; evidence сообщает только affected sibling count.

Automatic dataset выбирает минимальный candidate card ID. Search workset выбирает первый явно выбранный применимый sibling, сохраняет requested order и не создаёт unselected rows. Независимые card-level learning reasons siblings остаются отдельными.

Automatic evaluation использует один bounded shared candidate query для revlog/card/note с лимитом 100 + truncation sentinel, включая candidates без learning issue. Search workset загружает не более 200 exact IDs одним batch. Raw fields не покидают backend.

Legacy `attentionCards`, включая heuristic missing-field labels, не меняется; heuristics не становятся canonical content reasons.

Content status различает:

```text
available
no_confirmed_profiles
profiles_need_review
disabled
partial
unavailable
```

Отсутствующие profiles не считаются error. Недоступность store/model никогда не означает resolved.

## Примеры

Japanese Vocabulary может сопоставить:

```text
meaning → Meaning
audio → Audio
example → Example
```

и подтвердить checks `non_empty` / `contains_audio`. Missing audio marker создаёт `content.audio_missing` только после явного confirmation.

Programming может сопоставить:

```text
question → Question
answer → Answer
```

и подтвердить два checks `non_empty` без требования audio. Japanese rule не применяется к нему, потому что profiles привязаны к exact `noteTypeId` и fingerprint.

## Bounds, privacy и compatibility

| Resource | Bound |
| --- | ---: |
| document | 1 MiB |
| profiles | 500 |
| mappings/checks per profile | 32 / 32 |
| refs per mapping/check | 16 / 16 |
| fields/templates in structure | 64 / 32 |
| preview cards | 20 |
| automatic candidates | 100 |
| Search workset | 200 |

Profile contents, field mappings и checks никогда не отправляются через telemetry.

Logs содержат только operation/error codes и exception types, но не profile data, note values, paths или tokens.

Не меняются:

- Search;
- Safe Actions;
- Signals;
- Notifications;
- preview isolation;
- существующий CardsPage;
- legacy report payload.

C1.4 добавляет local Settings editor и strict client-side import/export одного profile, описанный в [`inspection-profiles-ui.md`](inspection-profiles-ui.md). Он не добавляет Cards queue/Inspector или collection mutation.

## Guided editor projection

UI C1.5R.6 не определяет вторую schema. Generated browser-only suggestion, Basic controls и Advanced controls редактируют один exact document v1.

Generated origin и user-dirty semantics являются UI state и никогда не сохраняются в profile. Validate schema v2 и update schema v1 остаются неизменными.