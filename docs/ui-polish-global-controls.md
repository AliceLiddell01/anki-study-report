# UI Polish & Global Controls

Статус: implemented in Stage 5.5.

## Scope

Этап возвращает постоянное управление темой в App Shell и уплотняет
presentation слои Activity и Decks перед Statistics v1. Routes, backend,
`StudyReport`, `activityHub`, `deckHub`, метрики и security boundaries не
изменяются.

## Global Utility Dock

`GlobalUtilityDock` монтируется один раз в `AppLayout`, вне route content. Это
компактный fixed stack справа снизу с App Shell safe inset. Dock находится ниже
modal/popover/toast слоёв, не входит в primary navigation, avatar menu или
Settings sidebar и остаётся на месте при hash navigation.

Сейчас stack содержит только theme toggle. Будущий language selector сможет
стать вторым utility item без переработки shell, но Stage 5.5 не показывает
language button/placeholder, не добавляет locale files и не внедряет i18n.

## Theme storage и initialization

Сохранён прежний browser contract:

```text
key: anki-study-report-theme
values: light | dark | system
```

Inline bootstrap в `web-dashboard/index.html` применяет resolved theme до
React render. Значение `system` остаётся совместимым и следует
`prefers-color-scheme`; нажатие toggle фиксирует явное `light` или `dark`.
Backend request, dashboard token и query string не меняются.

Иконка показывает доступное действие: луна включает тёмную тему, солнце —
светлую. Dynamic `aria-label` совпадает с tooltip. Tooltip появляется по hover
и keyboard focus, но accessible name не зависит от него.

## Activity presentation

- ordinary `daily_summary` больше не повторяет visible badge;
- milestones сохраняют labels `серия`, `рекорд`, `возвращение`;
- видимая история группируется frontend-side по локальному месяцу;
- weekly summaries остаются в общей newest-first chronology;
- load-more сохраняет 14 + 14 и объединяет записи с существующим month group;
- календарная клетка показывает дату как primary line и metric как secondary;
- selected-day decks используют две строки: имя и `reviews · success`.

`activityHub`, deterministic IDs, feed derivation, period/date/scope semantics,
keyboard navigation и sorting не менялись.

## Decks presentation

- filtered exclusion стал compact info-line и отсутствует при zero;
- `Развернуть группы` раскрывает только root groups;
- при manual expansion control становится `Свернуть все`;
- во время search/filter control disabled и объясняет auto-expansion, не стирая
  manual state;
- disclosure остаётся отдельным native button с target 32×32;
- detail разделён на identity, reasons, metrics, direct/subtree, issues,
  recommendations и actions;
- master grid использует natural content height.

Hierarchy, health/confidence, selection fallback, sorting, Browser actions и
query validation не менялись.

## Accessibility и consistency

- theme control и deck disclosure являются native buttons;
- focus state отличается от selected state;
- tooltip доступен mouse и keyboard;
- essential values остаются visible text;
- motion учитывает существующий `prefers-reduced-motion` contract;
- shared theme variables и focus colors переиспользованы;
- Cards renderer, Shadow DOM и sanitizer не затрагивались.

## Visual и zoom verification

Docker smoke проверяет toggle на product/settings routes, persistence после
reload, navigation stability, отсутствие duplicate dock и overlap с profile
menu. Activity и Decks получают light/dark и дополнительные state screenshots.

125% proof использует изолированный Playwright browser context: CSS viewport
`1152×800`, `deviceScaleFactor=1.25`, physical target `1440×1000`. Это
page/device scale emulation, а не browser UI shortcut.
Activity, Decks и Settings проверяются на horizontal overflow и пересечение
dock с actionable content; manifest индексирует proof как `kind: zoom`.

## Explicit non-goals

Statistics/FSRS, новые routes, i18n/language UI, новый payload/backend API,
Activity derivation, Decks scoring, Profile/Cards redesign, mobile-first layout,
theme sync и release/CD automation не входят в этап.

## Проверки

```text
web-dashboard/src/layout/AppLayout.test.tsx
web-dashboard/src/pages/ActivityPage.test.tsx
web-dashboard/src/pages/DecksPage.test.tsx
tests/test_docker_smoke_helpers.py
docker/anki-e2e/smoke-browser.mjs
```

Финальное доказательство — exact-SHA Fast CI и manual cloud
`Full Docker / Anki E2E` в режиме `standard`; одинаковые локальные full gates
после успешных cloud runs не дублируются.
