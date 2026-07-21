# Guided Inspection Profiles

Этот документ описывает актуальный продуктовый и interaction contract маршрута `#/settings/inspection-profiles` после C1.5R.6.

## Назначение продукта

Inspection Profiles отвечают на пять обычных пользовательских вопросов:

1. Какое содержимое должно присутствовать в карточках этого точного note type?
2. Какие точные Anki fields соответствуют этим назначениям?
3. Какие bounded declarative checks будут выполняться?
4. Можно ли безопасно включить предложенную configuration?
5. Почему ранее включённый profile перестал быть авторитетным?

Страница является локальной settings surface. Она никогда не редактирует collection и не выполняет arbitrary code, queries, regular expressions, JavaScript, Python или SQL.

## Generated draft

Выбор note type в состоянии `not_configured` немедленно преобразует детерминированную backend suggestion в browser-only strict profile draft v1.

```text
выбрать точный note type
→ появляется generated draft
→ save request не выполняется
→ confirmation не выполняется
→ authoritative inspection не включается
```

Отдельного normal-path шага `Use suggestion` нет.

Generated draft и пользовательская работа — разные состояния:

```text
origin: generated
userEdited: false
dirty: false
```

Clean generated draft можно отбросить при переключении note type или пересоздать после свежего catalog query.

Первое изменение profile через Basic или Advanced переводит draft в пользовательскую работу. Imported и start-empty drafts принадлежат пользователю сразу. Только настоящая пользовательская работа включает selection guard и защиту `beforeunload`.

Сохранённые profiles `suggested`, `confirmed`, `needs_review` и `disabled` загружаются как clean stored baselines. Ничего не сохраняется и не подтверждается автоматически.

## Нормальная information architecture

Selected workspace расположен в таком порядке:

```text
заголовок точного note type
lifecycle guidance
Suggested setup
Fields used
Requirements
Card scope
validation/sample result
state-aware primary actions
Advanced settings disclosure
Profile tools disclosure
```

Basic открыт по умолчанию. Advanced и Profile tools по умолчанию свёрнуты.

Существует один strict profile draft. Basic — понятная projection над ним, а не вторая persisted model.

## Понятные roles

Известные roles используют локализованные человеческие названия и короткие назначения, например:

```text
Word
Meaning
Example
Part of speech
Pitch accent
Audio
Image
Question
Answer
Code
Explanation
```

Exact field names берутся из выбранного note type. Ordinals и role slugs в Basic не показываются.

Field, уже занятый другим single-field role, disabled в соответствующем selector. Страница никогда молча не создаёт конфликтующее duplicate field claim.

Unknown roles используют безопасный humanized fallback custom role и сохраняют свой exact strict mapping.

## Понятные requirements

Basic проецирует каждый check kind Inspection Profile v1:

- `non_empty` → выбранный field обязателен;
- `contains_audio` → обязателен audio marker;
- `contains_image` → обязателен image marker;
- `min_text_length` → bounded minimum character count;
- `one_of_roles_non_empty` → заполнен хотя бы один selected role;
- `all_roles_non_empty` → заполнены все selected roles.

Пользователь может:

- изменить понятную priority;
- изменить selection roles;
- изменить minimum length;
- добавить поддерживаемый hard-coded requirement kind;
- удалить requirement.

Check IDs остаются стабильными внутренними identifiers и не пересоздаются при обычном редактировании.

## Ожидания для Japanese и Programming

Frontend использует `suggestion.detectedKind` и точную backend suggestion. Study kind не выводится из display name note type.

Japanese vocabulary suggestion с mapped role Audio явно содержит Audio requirement в Basic.

Programming suggestion явно содержит requirements Question и Answer и не выдумывает Audio requirement.

Safe selector добавления requirements всё ещё может предлагать поддерживаемый Audio check kind; это не означает, что Audio настроен по умолчанию.

## Card scope

Пустой `templateOrdinals` означает все card templates. Basic показывает template names и никогда не строит текст вокруг ordinal.

Для note type с одним template используется компактная read-only summary.

Отсутствующий selected template является blocking review error и никогда не сбрасывается молча.

## Lifecycle actions

| Effective state | Обычное primary behavior |
| --- | --- |
| `not_configured` | Confirm and enable; generated draft также можно сохранить как draft |
| `suggested` | Confirm and enable; dirty changes можно сохранить |
| `confirmed`, unchanged | показывается Enabled status; redundant confirmation отсутствует |
| `confirmed`, edited | Validate and confirm changes |
| `needs_review` | Review and confirm again |
| `disabled` | Review and enable |

Сохранение изменённого confirmed profile как `suggested` требует confirmation, потому что удаляет authority. Disable и delete остаются явными confirmed tools.

## Validation и sample

`Check setup` отправляет validate request schema v2 с bounded sample limit 10.

Confirmation сначала выполняет validation, а затем update schema v1. После invalid result mutation не отправляется.

Result группирует failures по понятному requirement, а не по check ID.

UI может показывать:

- counts;
- exact mapped field names;
- marker presence;
- bounded text length;
- sibling impact.

UI никогда не показывает:

- raw note values;
- card HTML;
- template source;
- media filenames;
- filesystem paths;
- tokens.

Structurally valid profile без доступных cards честно обозначается как валидная structure без content sample.

## Advanced и hidden errors

Advanced сохраняет:

- display name;
- exact template scope;
- role slugs;
- exact field references;
- check kinds;
- priorities;
- modes;
- minimum lengths;
- stable IDs.

Basic и Advanced редактируют один strict document.

Validation errors, относящиеся к collapsed Advanced controls, представлены:

- error count в summary disclosure;
- page error summary.

После явного failed Check/Confirm action focus переходит на summary. Активация соответствующей ссылки сначала открывает Advanced, затем переводит focus на точный control.

## Conflict и reload

Reads используют `AbortController` и latest-wins. Mutations сериализованы.

Revision conflict:

- сохраняет пользовательский draft;
- отдельно обновляет server catalog state;
- предлагает явный выбор review-server либо discard-and-reload.

Client никогда не повторяет conflicting mutation автоматически и не перезаписывает latest server revision молча.

## Accessibility

Страница содержит:

- один `h1`;
- native catalog buttons;
- видимые labels;
- groups `fieldset`/`legend`;
- native selects и checkboxes;
- keyboard-operable native disclosures;
- программно доступное open state;
- status/alert semantics;
- перемещение focus только после явного failed action или modal interaction.

State и priority выражаются текстом, а не только цветом. RU и EN используют одну strict data model.

## Безопасность и приватность

Frontend не имеет доступа к collection и использует только token-protected loopback API.

Basic компилируется исключительно в существующий hard-coded union v1.

Import остаётся strict data:

- maximum 1 MiB;
- bound к exact note type, fingerprint и references;
- dirty и non-authoritative до явного confirmation.

Export содержит только сохранённый локальный profile document.

## Граница этапа

C1.5R.6 проверил guided page на deterministic fixtures и в Chromium. Интегрированный package, Docker/real-Anki и owner product acceptance были завершены в C1.5R.7.

C1.6 остаётся отдельным этапом и не является частью Guided Inspection Profiles.