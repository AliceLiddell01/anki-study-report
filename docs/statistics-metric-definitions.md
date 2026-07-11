# Statistics v1 — metric definitions

Версия definitions/calculation: `statistics-v1.0`.

Source of truth: `anki_study_report/statistics_service.py` и derived cache
schema v3 в `anki_study_report/stats_cache.py`.

## Common semantics

### Qualifying answer

Cache использует текущий `REVLOG_REVIEW_FILTER_SQL`:

```sql
r.ease between 1 and 4 and (r.type < 3 or r.factor != 0)
```

Manual/reschedule (`ease=0`, manual type/factor) исключены. Один card может
дать несколько ordinary reviews за день. Local day — готовый `YYYY-MM-DD` key,
полученный после вычитания Anki rollover и применения local time; frontend не
переводит key через UTC.

Scope применяется по current home deck: `odid` для карты во filtered deck,
иначе `did`. Исторические moves не реконструируются. Period bounds включают обе
границы. Суммируются numerators/denominators, а не дневные проценты.

## Metrics

| UI / ID | Definition | Numerator / denominator | Missing behavior | Comparison / limitations |
| --- | --- | --- | --- | --- |
| Повторения / `reviews` | Число qualifying answers; повторная встреча той же карты считается снова | `count(revlog)` | 0 при покрытом пустом периоде; unavailable без cache | sum; deleted-card deck history ограничена |
| Pass / `pass` | Hard/Good/Easy | `ease in (2,3,4)` | 0 при known empty | sum |
| Fail / `fail` | Again | `ease=1` | 0 при known empty | sum |
| Успешность / `success_rate` | Взвешенная доля ordinary Pass | `Σpass / (Σpass+Σfail)` | `null` при denominator 0 | difference in percentage points; не среднее процентов |
| Again/Hard/Good/Easy / `ratings` | Counts выбранных buttons 1..4 | count каждого ease / total для UI percentage | no data при total 0 | counts sum |
| Время учёбы / `study_time` | Сумма valid answer `time`, capped существующим `ANSWER_TIME_CAP_MS` | `Σmin(max(time,0),cap)` | `null`, если нет ни одного valid time; 0 возможно при valid zero | revlog estimate, не wall-clock session |
| Средний ответ / `average_answer_seconds` | Взвешенное среднее valid answer time | `ΣanswerSeconds / answer_time_count` | `null` при count 0 | не среднее дневных averages |
| Активные дни / `active_days` | Unique covered local days с reviews > 0 | count(date) | 0 при known empty | finite periods compare equal lengths |
| Новые карточки / `introduced_cards` | Card впервые встретилась в qualifying `type=0` event | distinct card with no earlier qualifying revlog | 0 при known empty | не created notes/cards; current deck attribution |
| True Retention / `true_retention` | Только первый qualifying review/relearn card за rollover-local day; learning/new и manual excluded | Pass = ease 2..4; Fail = ease 1 | `null` при denominator 0 | ordinary success не заменяет metric; single day noisy |
| Young retention | True Retention event с previous `lastIvl` 1..20 days | young pass / young total | `null` при 0 | `lastIvl` — interval before answer |
| Mature retention | True Retention event с previous `lastIvl >= 21` days | mature pass / mature total | `null` при 0 | threshold соответствует Anki |
| Current card states | Current grouped card snapshot | counts by state | 0 for absent state, unavailable if collection absent | не historical series |
| Cards / notes | Current cards и distinct note IDs | independent counts | 0 for empty collection | manual correction factor запрещён |
| Unseen | current `type=0`, кроме suspended/buried priority states | cards | 0 | snapshot |
| Learning | current `type in (1,3)` | cards | 0 | includes relearning state in current distribution |
| Young / mature | current `type=2`, split by `ivl <21 / >=21` | cards | 0 | current interval, not historical |
| Suspended / buried | current queues `-1` / `-2,-3` | cards | 0 | state priority over type |
| Overdue now | Current scheduled cards with due offset `<0` | cards | 0 | excluded from future due |
| Future due | Current scheduled cards due offsets `0..90` | cards by learning/review/relearning | empty series if none | assumes no future new cards/failures |
| Daily load | Anki-style long-run average review load | `Σ 1/max(ivlDays,1)` over current review cards | 0 for none | not cards due today |
| Deck metrics | Same period numerators within non-overlapping deck ID sets | weighted formulas above | row may be insufficient | top 12 root groups, no health verdict |

## Period and comparison rules

```text
7d   today-6 .. today
30d  today-29 .. today
90d  today-89 .. today
1y   calendar year subtraction + 1 day .. today
all  first available cache date .. today
```

Leap-day subtraction clamps to February 28. Previous finite period ends one
day before current start and has the same number of calendar days. If cache
starts inside the previous bounds, comparison is `partial`; missing days are
not zeros. All-time has no comparison.

## Confidence

`insufficient <30`, `preliminary 30..99`, `sufficient >=100` answered reviews.
Deck rows use `<10` insufficient. Factual qualitative insights require both
periods ≥30 reviews and at least 3 current active days. Это продуктовая
sample-confidence policy, не confidence interval.

## Coverage fields

Every result publishes `dataFrom`, `dataTo`, `requestedFrom`, `requestedTo`,
`full|partial|unavailable`, sample size, active days, study-time source,
limitations and calculation version. Missing data is never silently converted
to performance zero.

