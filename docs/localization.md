# Локализация web dashboard

Web dashboard поддерживает две встроенные локали:

```text
ru
en
```

Русский — детерминированный default и fallback.

Browser language detector и network translation services не используются. Оба словаря входят во frontend bundle и работают offline внутри add-on.

## Namespace Notifications

Namespace `notifications` имеет полную RU/EN parity для:

- bell и panel;
- Notification Center;
- tabs;
- categories;
- signal evidence;
- context actions;
- settings;
- live regions;
- summary toast.

Evidence форматируется только из bounded numeric/status fields. Card/note text не попадает в notification payload.

Real-browser evidence включает RU light и EN dark surfaces.

## Runtime contract

- i18n layer: `web-dashboard/src/i18n/index.ts` на `i18next` и `react-i18next`;
- допустимые values: `ru | en`;
- storage key: `anki-study-report-language`;
- неизвестное или damaged value нормализуется в `ru`;
- язык меняется без reload через `changeAppLanguage()` и сохраняется в `localStorage`;
- ошибка storage не мешает сменить язык текущей session;
- при смене языка обновляются `html[lang]`, `html[dir="ltr"]` и `document.title`;
- theme storage и language storage независимы.

Global selector находится рядом с theme toggle в `GlobalUtilityDock`.

Keyboard behavior:

- `Enter`/`Space` открывают menu;
- arrows и `Home`/`End` перемещают focus;
- `Escape` закрывает menu и возвращает focus на trigger.

## Resources и keys

Inspection Profiles UI хранит весь workflow copy в симметричном `pages.inspectionProfiles`:

- route title/description;
- lifecycle states;
- filters;
- roles;
- allowlisted check kinds;
- modes/priorities;
- validation/preview;
- save/confirm/disable/delete;
- import/export;
- conflicts;
- unsaved changes.

Settings label находится в `navigation.settings.inspectionProfiles`:

```text
Проверка карточек / Card checks
```

Unknown runtime/suggestion codes получают локализованный safe fallback и не становятся основным machine label.

Resources:

```text
web-dashboard/src/i18n/locales/ru.ts
web-dashboard/src/i18n/locales/en.ts
```

Они имеют одну typed shape.

Namespaces:

```text
common
navigation
pages
statistics
fsrs
notifications
```

Key описывает назначение, а не исходную фразу, например:

```text
navigation:primary.today
pages:cards.header.title
```

Новый пользовательский UI text сначала добавляется в обе locale resources, затем используется через `t()`.

Не следует собирать предложения из нескольких translated fragments, если word order зависит от языка.

Search использует `pages.search.*` для:

- query/filter/selection/Inspector copy;
- action labels;
- explanation temporary bury;
- mappings stable backend result codes.

Codes вроде `cards.suspended` или `notes.tags_added` не являются готовым UI text и всегда преобразуются в RU/EN key.

Canonical Cards workspace использует `pages.cards.workspace.*`:

- summary;
- filters;
- queue;
- Inspector;
- preview;
- reason/evidence mappings;
- action и recheck status.

Названия decks, note types, templates, card content и IDs являются user data и не переводятся.

## UI copy и данные

Переводятся product-owned:

- headings;
- labels;
- buttons;
- hints;
- empty/error states;
- accessibility names;
- frontend-generated recommendations.

Не переводятся пользовательские и технические values из payload:

- profile и deck names;
- card content;
- Search queries;
- IDs;
- deck/tag names;
- field/template names;
- backend error details.

Известный system label локального profile локализуется. Произвольный пользовательский label сохраняется дословно.

Markdown/HTML report generation и Python payload contract не входят в этот layer.

## Pluralization и formatting

Plural forms задаются i18next:

```text
_one
_few
_many
_other
```

Они всегда получают numeric `count`.

Numbers, percentages, dates и durations проходят через shared helpers с locale:

```text
ru-RU
en-US
```

Components не должны вручную подставлять русские separators или английские units.

## Как добавить язык

1. Добавить code в `supportedLanguages` и mapping в `localeForLanguage()`.
2. Создать resource с точной structure русского source of truth и подключить его в `i18n/index.ts`.
3. Добавить variant в `GlobalUtilityDock` и human-readable names во все resources.
4. Расширить parity, pluralization, formatting и representative render tests.
5. Расширить browser smoke: switching, reload persistence, independence hash/theme, `html lang`, title и screenshots.

## Проверки

`resources.test.ts` рекурсивно проверяет совпадение keys и non-empty values.

Тесты:

```text
language.test.ts
GlobalUtilityDock.test.tsx
TopNav.test.tsx
LocalizationSmoke.test.tsx
formatters.localization.test.ts
```

Они покрывают:

- default/fallback;
- storage;
- switching;
- shell/pages;
- plural forms;
- locale formatting.

Targeted browser contract в `docker/anki-e2e/smoke-browser.mjs` проходит последовательность:

```text
RU/light
→ EN/light
→ EN/dark
→ RU/dark
```

Он проверяет сохранение hash, theme и language после reload, снимает четыре localization screenshots и требует ноль console/page errors.

Финальный runtime proof выполняется exact-SHA cloud E2E.

Stage 7.7.1 закрыл остаточные frontend-owned labels:

```text
Pass
Fail
Hard
Easy
Again
FSRS states
technical labels
```

Today больше не показывает raw ISO date. Shared helpers date/weekday/number/unit всегда выбирают `ru-RU` или `en-US` по active language.

Payload values, user entity names и backend narratives не переводятся.

## Ограничения первой версии

Telemetry state и errors не переводятся из arbitrary backend text.

UI сопоставляет allowlisted codes с typed RU/EN resources, например:

```text
not_attempted
waiting_retry
failed
enrolled
network_error
service_disabled
```

Unknown value получает safe generic string.

Language menu не оставляет tooltip в DOM, пока открыт `role="menu"`. После `Escape`, selection или outside click tooltip возвращается. `Escape` возвращает focus на trigger.

Это исключает одновременно объявляемые tooltip и menu.

Ограничения:

- только `ru` и `en`, обе LTR;
- язык выбирается явно, без browser/profile detection;
- preference browser-local и не синхронизируется через Python или Anki Sync;
- backend/user content не переводится;
- locale chunks не загружаются отдельно: оба dictionaries входят в bundle.

What’s New и consent используют namespaces:

```text
pages.whatsNew
pages.privacy
```

Changelog text не дублируется в locale files. RU/EN pairs генерируются из `release/changelog.json`.

Переключение языка обновляет открытый modal и не сбрасывает expanded versions или selected purpose toggles.

## Preview semantics C1.5R.3

См. [`card-preview-semantics.md`](card-preview-semantics.md). Full preview использует reviewer/native front и answer: Inspector показывает front, expanded dialog — answer, compact identity остаётся неизменной.

## Терминология Guided Inspection Profiles

Полную RU/EN parity имеют:

- friendly detected kinds;
- role purposes;
- requirement titles;
- priorities;
- lifecycle guidance;
- validation/no-card/conflict states;
- Advanced;
- Profile tools.

Unknown backend kind/role/warning values используют safe localized fallbacks и не показывают machine identifiers как обычный UI copy.