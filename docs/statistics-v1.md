# Statistics v1

Статус: implemented in Stage 6.

## Product role

Statistics — самостоятельный аналитический центр периодов. Он отвечает, как
меняются качество, нагрузка и прогресс, и чем отличаются непересекающиеся
группы колод. Он не заменяет Today, Activity, Decks, Cards, Profile или
нативное окно статистики Anki.

Primary navigation:

```text
Сегодня → Активность → Статистика → Колоды → Карточки
```

Canonical routes:

| Route | Раздел | Пользовательский вопрос |
| --- | --- | --- |
| `#/stats` | Обзор | Что изменилось за период? |
| `#/stats/quality` | Качество | Насколько стабильно проходят ответы? |
| `#/stats/load` | Нагрузка | Сколько работы было и ожидается? |
| `#/stats/progress` | Прогресс | Как растёт изучаемая коллекция? |
| `#/stats/decks` | Колоды | Чем колоды отличаются за период? |

Все routes используют одну layout/sidebar и общий session-only query state.
`GlobalUtilityDock` остаётся частью App Shell. Profile dropdown и Settings
hierarchy не меняются.

## Common controls

Один query содержит:

```json
{
  "scope": {"kind": "dashboard"},
  "period": "90d",
  "granularity": "auto",
  "comparison": true
}
```

Scope:

- `dashboard` — текущая область из Settings, не изменяя её;
- `all_collection` — все обычные колоды;
- `single_deck` — current deck ID и `subtree|direct`.

Backend заново разрешает deck ID по current catalog. Unknown/deleted и
filtered decks отклоняются typed validation error. Search string, SQL, code и
произвольные поля endpoint не принимает.

Periods: `7d`, `30d`, `90d`, `1y`, `all`. Finite periods сравниваются с
непосредственно предыдущим периодом той же календарной длины. Для `all`
comparison принудительно выключен. Недостаточное прошлое покрытие помечается
`partial`, а не дополняется нулями.

Granularity: `auto|day|week|month`. Auto использует day для 7/30d, week для
90d, month для 1y/all. Unsafe `1y+day` clamp-ится до week; all всегда month.
Series ограничены 400 buckets.

## Data architecture

```text
StatsCacheManager.report_snapshot()  current collection snapshot
               │                                │
               └──────── statistics_service.py ─┘
                                  │
StudyReport.statisticsHub.initialResult          POST /api/statistics/query
```

`statisticsHub` additive и содержит schema/generation/availability/coverage,
capabilities, metric definition version, default query, initial 90d dashboard
result и compact normal-deck options. Поэтому `#/stats` открывается без
дополнительного blank request.

`POST /api/statistics/query` использует тот же `StatisticsResult`. Endpoint:

- требует текущий dashboard token;
- имеет общий 8 KiB body limit;
- принимает только enum, positive deck ID и boolean;
- отклоняет unknown fields;
- memoize-ит identical normalized query для текущего cache SHA/date;
- строит запрос из одного cache snapshot и одного bounded current snapshot;
- не возвращает raw revlog, card/note text, IDs отдельных карточек, token или
  paths.

Frontend использует initial result, memory cache, AbortController и sequence
guard. Loading не стирает предыдущий result, ошибки retryable, stale response
не применяется. Analytics не сохраняется в localStorage.

## Five sections

### Overview

Шесть KPI: reviews, capped revlog study-time estimate, weighted success,
introduced cards, active days, weighted average answer time. Три bounded series
показывают workload, quality и introduced/review balance. До трёх factual
insights приходят semantic codes/params; causal text backend не формирует.

### Quality

Показывает weighted Pass/Fail success, ratings 1–4, average answer time и
отдельный True Retention. True Retention использует первый qualifying review
карточки за rollover-local day и split young/mature по previous interval 21
days. Single-day data не превращается в сильный вывод.

### Load

Разделяет past workload, current overdue backlog и future due 0..90 days.
Forecast разбит на learning/review/relearning и явно предполагает отсутствие
будущих новых карточек и ошибок. Daily load — `Σ 1/max(intervalDays,1)`, а не
число due сегодня.

### Progress

Показывает current snapshot unseen/learning/young/mature/suspended/buried,
отдельные card/note counts и introduced trend. Historical young/mature series
не строится: без snapshots это было бы недостоверной реконструкцией.

### Deck comparison

Default rows — непересекающиеся normal root groups, top 12 по reviews. Metrics:
reviews, success, answer time, study time, introduced cards, equal-period delta
и sample confidence. Search и focus selection происходят в bounded rows.
Health badges/verdicts отсутствуют. Single-deck common scope поддерживает
direct/subtree; parent subtree и descendant subtree не публикуются как две
независимые серии.

## Confidence and missing data

Product sample-confidence policy:

```text
insufficient  < 30 answered reviews
preliminary  30..99
sufficient   >= 100
deck row preliminary starts at 10
```

Qualitative comparison insight скрывается, если любой период имеет менее 30
answers; trend требует минимум 3 active days. `0`, `null`, `partial` и
`insufficient` различаются. Missing answer time остаётся `null`/«Нет данных».

## Accessibility and visual contract

- route sidebar uses `aria-current` and native links;
- every control has an associated label;
- charts have heading, summary, text legend and expandable data table;
- essential values do not depend on hover or color;
- native buttons/selects/checkboxes remain keyboard-usable;
- light/dark share existing theme tokens;
- at 125% sidebar may move above content; horizontal overflow and dock overlap
  are E2E failures.

## Performance bounds

- initial `statisticsHub` ≤ 200 KiB compact JSON;
- query result ≤ 300 KiB;
- full deterministic `/api/report` target ≤ 500 KiB;
- maximum 400 buckets, 12 default deck rows, 90 due days;
- one cache snapshot and bounded grouped collection calls per build;
- no N+1 per deck/day and no revlog scan on route navigation;
- cache schema v3 stores derived retention and answer-time availability counts.

Machine timings are recorded for diagnostics and are not the sole gate.

Local deterministic 500-day structural measurement (2026-07-12):

```text
base compact report fixture       9,606 bytes
statisticsHub                    14,561 bytes
report + statisticsHub           24,184 bytes
all-time query response          16,336 bytes
initial/all-time points          13 / 18
deck rows                         1
hub/query build                   4.195 / 7.713 ms (diagnostic only)
frontend JS before/after        803,424 / 824,880 bytes
frontend CSS before/after        58,595 / 68,463 bytes
```

Real Anki Docker artifact remains authoritative for the E2E fixture numbers;
local values above prove shape/bounds and are not machine performance gates.

## Native Anki Statistics

Secondary action `POST /api/actions/open-native-stats` accepts an empty object
only and calls supported Anki 26.05 `mw.onStats()` on the main thread. It does
not promise to synchronize dashboard scope with the native window.

## Known limitations

- historical deck moves/renames and deleted-card deck attribution are not
  reconstructed;
- deck association is current home deck (`odid` when filtered);
- current states/due are live snapshots, not period history;
- revlog time is capped estimate and can be unavailable;
- future due excludes overdue and assumes no future new cards/failures;
- cache is disposable; v2 requires controlled rebuild to schema v3.

## Docker proof

Synthetic collection contains >1 year of sparse history, current/previous
periods, gaps, repeat reviews per card/day, ratings 1–4, young/mature retention,
manual entry, introduced events, multiple roots, filtered exclusion, current
states and due categories. Browser smoke checks five routes, 90d default,
period/all-time/deck/direct controls, typed query, native callback, light/dark
screenshots and 125% overview/decks proof. Canonical report must have zero
console errors, actionable request failures and token exposure.

## Explicit non-goals

FSRS/stability/difficulty/retrievability, calibration, forgetting curves,
Time Machine, historical card-state reconstruction, arbitrary search/query
builder, provider system, third-party add-on integration/detection, finish-date
prediction, health scoring, problem cards, Cards v2, Notifications, i18n and
mobile-first redesign remain outside Statistics v1.
