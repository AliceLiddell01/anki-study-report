# Локализация web dashboard

Web dashboard поддерживает две встроенные локали: `ru` и `en`. Русский язык —
детерминированный default и fallback. Browser language detector и сетевые
translation-сервисы не используются: оба словаря входят во frontend bundle и
работают офлайн внутри add-on.

## Runtime contract

- i18n-слой: `web-dashboard/src/i18n/index.ts` на `i18next` и
  `react-i18next`;
- допустимые значения: `ru | en`;
- storage key: `anki-study-report-language`;
- неизвестное или повреждённое значение нормализуется в `ru`;
- выбор меняется без reload через `changeAppLanguage()` и сохраняется в
  `localStorage`; ошибка storage не мешает сменить язык текущей сессии;
- при смене языка обновляются `html[lang]`, `html[dir="ltr"]` и
  `document.title`;
- theme storage и language storage независимы.

Глобальный selector живёт рядом с theme toggle в `GlobalUtilityDock`. Он
доступен с клавиатуры: Enter/Space открывают menu, стрелки и Home/End меняют
focus, Escape закрывает menu и возвращает focus на trigger.

## Resources и ключи

Ресурсы находятся в `web-dashboard/src/i18n/locales/ru.ts` и `en.ts` и имеют
одинаковую типизированную форму. Используются namespaces:

```text
common
navigation
pages
statistics
fsrs
```

Ключ описывает назначение, а не исходную фразу: например,
`navigation:primary.today` или `pages:cards.header.title`. Новый
пользовательский UI-текст добавляется сначала в обе locale resources, затем
используется через `t()`. Не следует собирать предложения из нескольких
переводимых фрагментов, если порядок слов зависит от языка.

Search v1 использует `pages.search.*`: query/filter/selection/inspector copy,
action labels, temporary bury explanation и mappings stable backend result
codes. Коды `cards.suspended`, `notes.tags_added` и другие не являются готовым
UI-текстом и всегда преобразуются в RU/EN key.

## UI-copy и данные

Переводятся product-owned headings, labels, buttons, hints, empty/error states,
accessibility names и frontend-generated recommendations. Не переводятся
пользовательские и технические значения из payload: имена профилей и колод,
содержимое карточек, search queries, IDs, deck/tag names, имена полей/шаблонов и backend error
details. Известный системный label локального профиля локализуется, но
произвольный пользовательский label сохраняется дословно.

Markdown/HTML report generation и Python payload contract в этот слой не
входят.

## Pluralization и форматирование

Plural forms задаются средствами i18next (`_one`, `_few`, `_many`, `_other`)
и всегда получают числовой `count`. Числа, проценты, даты и durations проходят
через общие helpers с locale `ru-RU` или `en-US`; компоненты не должны вручную
подставлять русские разделители или английские единицы измерения.

## Как добавить язык

1. Добавить код в `supportedLanguages` и mapping в `localeForLanguage()`.
2. Создать ресурс с точной структурой русского source-of-truth и подключить его
   в `i18n/index.ts`.
3. Добавить вариант в `GlobalUtilityDock` и человекочитаемые названия во все
   ресурсы.
4. Расширить parity, pluralization, formatting и representative render tests.
5. Расширить browser smoke: переключение, reload persistence, hash/theme
   independence, `html lang`, title и screenshots.

## Проверки

`resources.test.ts` рекурсивно проверяет совпадение ключей и непустые значения.
`language.test.ts`, `GlobalUtilityDock.test.tsx`, `TopNav.test.tsx`,
`LocalizationSmoke.test.tsx` и `formatters.localization.test.ts` покрывают
default/fallback, storage, переключение, shell/pages, plural forms и locale
formatting.

Targeted browser contract в `docker/anki-e2e/smoke-browser.mjs` проходит
RU/light → EN/light → EN/dark → RU/dark, проверяет сохранение hash, theme и
language после reload, снимает четыре localization screenshots и требует ноль
console/page errors. Финальный runtime proof выполняется exact-SHA cloud E2E.

Stage 7.7.1 закрыл остаточные frontend-owned подписи `Pass`/`Fail`/`Hard`/
`Easy`/`Again`, FSRS state labels и технические labels. Today больше не
показывает raw ISO date, а общие date/weekday/number/unit helpers всегда
выбирают `ru-RU` или `en-US` через активный язык. Значения payload, имена
пользовательских сущностей и backend narratives по-прежнему не переводятся.

## Ограничения первой версии

Telemetry state и ошибки не переводятся из произвольного backend text. UI
сопоставляет allowlisted codes (`not_attempted`, `waiting_retry`, `failed`,
`enrolled`, `network_error`, `service_disabled` и другие bounded codes) с
typed RU/EN resources; неизвестное значение получает безопасную общую строку.

Language menu не оставляет tooltip в DOM, пока открыт `role="menu"`; после
Escape, выбора или outside click tooltip возвращается, а Escape возвращает
фокус на trigger. Это исключает одновременно объявляемые tooltip и menu.

- только `ru` и `en`, оба LTR;
- язык выбирается явно, без browser/profile detection;
- preference browser-local и не синхронизируется через Python или Anki Sync;
- backend/user content не переводится;
- locale chunks не загружаются отдельно: оба словаря входят в bundle.

What’s New и consent используют namespace `pages.whatsNew`/`pages.privacy`.
Тексты changelog не дублируются в locale files: RU/EN пары генерируются из
`release/changelog.json`. Переключение языка обновляет открытый modal, не
сбрасывая раскрытые версии или выбранные purpose toggles.
