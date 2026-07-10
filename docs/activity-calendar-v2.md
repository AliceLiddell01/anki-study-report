# Activity / Calendar v2

Статус: implemented in Stage 4.

## Product role and route

Пользовательское название раздела — `Активность`, canonical route остаётся
`#/calendar`. Route `#/activity` не существует.

Activity отвечает на вопрос: когда и как пользователь занимался, как менялся
ритм и что произошло в выбранный день. Здесь нет risk/health рекомендаций,
FSRS analytics, Notifications или исторических card-state transitions.

Границы:

- Today — текущий день;
- Activity — scoped calendar, day details и derived history;
- Profile — all-collection identity/lifetime view;
- Decks — текущее состояние колод;
- Cards — текущие карточки внимания.

## Scope and canonical source

`StudyReport.activityHub` строится backend-side из одного
`StatsCacheManager.report_snapshot()`:

```text
daily aggregates + deck-day aggregates
              │
              └─ build_activity_hub_payload(..., dashboard display scope)
```

Activity сохраняет historical dashboard scope: selected deck IDs уже учитывают
`includeChildDecks` в orchestration layer. Для selected scope daily totals
агрегируются из filtered deck-day rows. Profile продолжает читать исходный
all-collection snapshot; Today и старый top-level historical report не меняются.

Frontend не читает collection/cache/raw revlog и не выполняет N+1 requests.
Дополнительный endpoint не добавлен.

## Public bound and date semantics

Public payload ограничен последним календарным годом включительно. Backend
публикует точные bounds для четырёх периодов:

| Key | UI | Начало |
| --- | --- | --- |
| `30d` | Последние 30 дней | today minus 29 fixed calendar days |
| `90d` | Последние 90 дней | today minus 89 fixed calendar days |
| `6m` | Последние 6 месяцев | calendar-month subtraction plus one day |
| `1y` | Последний год | calendar-year subtraction plus one day |

Все даты — local date keys `YYYY-MM-DD`, уже рассчитанные cache с Anki rollover
semantics. Frontend сравнивает date keys без UTC conversion, поэтому DST не
сдвигает календарный день. Month-end clamp и leap day покрыты tests.

Feed milestones и records вычисляются из полной доступной scoped history до
обрезания public year. Это сохраняет pre-window context без публикации старых
дневных rows.

## Availability

Каждый опубликованный день имеет одно состояние:

- `active`: есть реальные reviews;
- `inactive`: дата покрыта all-time cache, но в текущем scope занятий нет;
- `unavailable`: дата раньше первой достоверной cache date.

Unavailable визуально штрихуется и имеет отдельный accessible text; это не
«пропуск». Default selected date — сегодня, даже если она inactive.

## Calendar metrics

Поддерживаются только реальные modes:

- `reviews` — filtered real review events;
- `study_time` — nullable capped revlog estimate с явным source caption;
- `new_cards` — cache new-card semantics;
- `success_rate` — `pass / (pass + fail)`, denominator zero → `null`.

Forecast mode удалён. Heat intensity использует deterministic 90th-percentile
cap, поэтому единичный outlier не обнуляет остальные active cells. Legend
различает unavailable, inactive и active; selected/focus имеют отдельные ring.

## Page structure

1. Heading и четыре neutral overview cards.
2. До трёх factual observations, только если facts существуют.
3. Metric controls и period selector (default `90d`).
4. Month-aligned mini calendars.
5. Detail panel выбранного дня.
6. Derived History feed с explicit load-more.

Month blocks не растягивают одну клетку на ширину страницы и остаются compact
для всех четырёх периодов.

## Day detail and deck semantics

Active day показывает date, reviews, new cards, Pass, Fail, weighted success,
nullable study time и active decks. Deck rows используют canonical current-deck
association cache; descendants не агрегируются frontend-side. Sort:

```text
reviews descending → casefolded name → deck id
```

Первые пять rows видимы сразу; остальные раскрываются `Показать ещё N` и
`Свернуть`, с `aria-expanded`. Backend ограничивает pathological day максимум
100 canonical deck rows.

Inactive day сообщает `Занятий не было`; unavailable day — `Статистика для
этой даты недоступна`.

## Derived feed

Feed не хранится на диске. Каждый active day получает deterministic
`YYYY-MM-DD:daily-summary` и zero or more highlights:

- `return_after_break` — после минимум двух известных inactive days;
- `streak_milestone` — только 3/7/14/30/60/100/180/365;
- `new_activity_record` — strict greater-than against all prior scoped history;
  first active day и ties не создают event.

Unavailable days не считаются break. Feed newest first, показывает 14 active
days и добавляет ещё 14 по явной кнопке. Persistent event DB, read/unread,
retention и notification state отсутствуют.

## Weekly summaries

Неделя: Monday–Sunday. Публикуются только завершённые недели с полной known
coverage. Summary содержит active days, reviews, nullable study time и weighted
Pass/Fail success.

Comparison с предыдущей completed week появляется только когда обе недели
имеют минимум 2 active days и 20 reviews. Деление на zero невозможно. Текст
нейтрален: `больше/меньше повторений`, без `лучше/хуже/эффективнее`.

ID: `YYYY-Www:weekly-summary`.

## Keyboard and accessibility

Calendar использует обычные buttons без ложного `role=grid`:

- один roving `tabIndex=0`;
- Left/Right — соседняя дата;
- Up/Down — минус/плюс 7 дней;
- Home/End — начало/конец недели в доступном range;
- Enter/Space — selection;
- focus сохраняется после выбора;
- `aria-pressed` сообщает selected date;
- accessible label содержит full date, availability и текущую metric value;
- essential values есть в detail panel, не только tooltip/color.

## Contract shape

```text
activityHub
├─ schemaVersion
├─ today / scope / bounds / periods
├─ metrics.studyTimeSource
├─ overview.currentStreak / bestStreak
├─ days[]
│  └─ date, availability, metrics, decks[]
└─ feed
   ├─ days[] + highlights[]
   └─ weeks[] + comparison
```

Payload JSON-safe и не содержит token, paths, card/note content или raw revlog.
На минимальном cache fixture additive slice занимает около 20 KB compact JSON;
абсолютный test ceiling — 100 KB даже при полном 365-day availability range.

## Empty states and non-goals

No history получает полный empty explanation; no active days сохраняет
calendar и честно пустой feed; one active day не создаёт fake weekly trend;
missing time/success отображаются как `Нет данных`.

Statistics v1, FSRS page, persistent Activity Feed, Notifications, `#/activity`,
Calendar tabs, Activity inside Profile, Decks/Cards redesign и historical card
transitions не входят в Stage 4.

## Verification

Основные contracts:

```text
tests/test_activity_feed.py
web-dashboard/src/lib/activityHub.ts
web-dashboard/src/pages/ActivityPage.test.tsx
docker/anki-e2e/smoke-browser.mjs
```

Docker fixture содержит multiple active days, known gap/return, streak,
completed comparable weeks и больше пяти active decks. Browser smoke проверяет
metric/day interaction, deck expand, 14+ load-more, derived events, light/dark
screenshots и отсутствие console/actionable request errors.
