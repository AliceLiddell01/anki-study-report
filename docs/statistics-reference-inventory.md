# Statistics reference inventory

Stage 7 implements aggregate D/S/R state, estimated remembered, calibration,
Steps scenarios and native read-only simulation. Forgetting curves and time
machine remain future FSRS Advanced/Analytics Pack.

Дата аудита: 2026-07-12. Inventory описывает идеи, а не code reuse.

References:

- [Anki Manual — Statistics](https://docs.ankiweb.net/stats.html)
- [Search Stats Extended](https://github.com/Luc-Mcgrady/Anki-Search-Stats-Extended), GPL-3.0-only
- [More Overview Stats 2.1](https://github.com/patrick-mahnkopf/Anki_More_Overview_Stats), GPL-3.0

Код, locale, CSS и runtime modules референсных add-ons не копировались и не
vendored. Они не являются dependencies. Реализация Core основана на официальной
семантике Anki и самостоятельно написанных стандартных aggregates.

## Classification fields

`source` — revlog aggregate, current card/schedule snapshot, FSRS memory state
или snapshot/provider. `scope` — поддерживаемая область. Cost:
`cheap|moderate|expensive|snapshot-required|provider-only`.

## Search Stats Extended inventory

| Feature | User question / precise meaning | Source | Limits / reconstruction | Cost | Scope | Destination / status | License reuse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Future Due Types | Какие типы карточек ожидаются? current due split | schedule snapshot | прогноз условный, overdue отдельно | moderate | all/deck | Stage 6 Core / implemented | idea only |
| Future Due Retention | Как future due связано с retention? | schedule+history | causal ambiguity | expensive | all/deck | Advanced / future | no code |
| Intra Day Due | Какая внутридневная очередь? | scheduler | volatile | moderate | all/deck | Diagnostics / future | no code |
| Today's Retention | Каков retention сегодня? | first daily review | noisy one-day sample | moderate | all/deck | Stage 6 Core / value available, no verdict | official semantics |
| Custom Pie | Пользовательский slice | arbitrary query | conflicts with bounded API | provider-only | custom | Reject | no code |
| Custom Bar | Пользовательский slice | arbitrary query | conflicts with bounded API | provider-only | custom | Reject | no code |
| Review Speed Trend | Меняется ли время ответа? weighted answer time | revlog aggregate | missing/capped time | cheap | all/deck | Stage 6 Core / implemented | independent |
| SxR Heatmap | Stability × retrievability | FSRS memory state | Stage 7+ complexity | expensive | all/deck | Stage 7 FSRS | no code |
| Interval Distribution | Как распределены intervals сейчас? | current cards | snapshot only | moderate | all/deck | Advanced | no code |
| Interval Load | Где interval создаёт нагрузку? | cards+schedule | interpretation required | moderate | all/deck | Advanced | no code |
| Lapse Load | Нагрузка из lapses | revlog aggregate | attribution/history | moderate | all/deck | Advanced | no code |
| Lapse Distribution | Распределение lapses | revlog/cards | current vs historical | moderate | all/deck | Advanced | no code |
| Lapse Total | Сколько lapses? | revlog aggregate | definition/version | cheap | all/deck | Advanced | no code |
| Repetition Load | Reviews per learned card | aggregate | denominator cohort | moderate | all/deck | Advanced | no code |
| Repetition Distribution | Distribution reviews/card | card identity aggregate | larger derived cache | expensive | all/deck | Advanced | no code |
| Repetition Total | Total answers | daily aggregate | repeated card counts intentionally | cheap | all/deck | Stage 6 Core / implemented | independent |
| Time Distribution | Distribution answer time | revlog | raw histogram/cache needed | moderate | all/deck | Advanced | no code |
| Time Totals | Study-time totals | capped time aggregate | estimate, missing data | cheap | all/deck | Stage 6 Core / implemented | independent |
| Introduced | First studied cards | first qualifying event | current deck attribution | moderate | all/deck | Stage 6 Core / implemented | independent |
| Forgotten | Previously known then failed | revlog sequence | definition ambiguity | expensive | all/deck | Needs research | no code |
| Introductory Rating | First rating per card | first event aggregate | cache extension | moderate | all/deck | Advanced | no code |
| Ratings | Again/Hard/Good/Easy | daily counts | denominator zero | cheap | all/deck | Stage 6 Core / implemented | official semantics |
| Interval Ratings | Rating by prior interval | revlog histogram | bounded bins needed | moderate | all/deck | Advanced | no code |
| Time Ratings | Rating by answer time | revlog histogram | bounded bins needed | moderate | all/deck | Advanced | no code |
| Load Trend | Historical workload | daily reviews/time | no causal verdict | cheap | all/deck | Stage 6 Core / implemented | independent |
| Learn Reviews per Card | Learning repetitions per card | card identity/revlog | derived distribution | expensive | all/deck | Advanced | no code |
| Memorised | Inferred memorized events | custom definition | not official, risk of overclaim | expensive | all/deck | Needs research | no code |
| FSRS Calibration | Predicted vs observed recall | FSRS states/revlog | careful cohorts | expensive | all/deck | Stage 7 FSRS | no code |
| Stability Time Machine | Historical stability state | snapshots/reconstruction | manual changes break reconstruction | snapshot-required | all/deck | Analytics Pack | no code |
| Difficulty Time Machine | Historical difficulty state | snapshots/reconstruction | same | snapshot-required | all/deck | Analytics Pack | no code |
| Stability Over Time | Stability trend | FSRS snapshots | current-only is insufficient | snapshot-required | all/deck | Stage 7 research / Analytics Pack | no code |
| Card Count Time Machine | Historical card states | snapshots | cannot derive current state backward honestly | snapshot-required | all/deck | Analytics Pack | no code |
| Review Interval Time Machine | Historical interval states | snapshots/revlog | reschedules/manual changes | snapshot-required | all/deck | Analytics Pack | no code |
| Daily Hourly Breakdown | Time-of-day success/count | revlog hour aggregate | rollover/timezone | moderate | all/deck | Advanced | no code |
| Short-term forgetting curves | Recall vs short elapsed time | detailed FSRS/revlog cohorts | fitting/sample bias | expensive | all/deck | Stage 7 FSRS | no code |
| Long-term forgetting curves | Recall decay | long cohorts | fitting/selection bias | expensive | all/deck | Analytics Pack | no code |
| Real decay curves | Empirical decay fitting | raw cohorts/provider | heavy compute/model choice | provider-only | configurable | Analytics Pack | no code |
| Load by introduction day | Future work by cohort | introduced cohort+schedule | expensive join | expensive | all/deck | Analytics Pack | no code |
| Sum retrievability / load by day | Expected knowledge/load | FSRS states+forecast | simulator assumptions | expensive | all/deck | Stage 7/Analytics Pack | no code |

## Search Stats Extended technical patterns

| Pattern | Meaning / limitation | Cost | Destination |
| --- | --- | --- | --- |
| `autoRevlogStats` | Expensive revlog graphs can be lazy | expensive | Future lazy architecture; Stage 6 does not expose provider system |
| `autoMemorisedStats` | Separate expensive inferred metrics | expensive | Needs research |
| lazy loading | Avoid blocking initial stats | expensive | Required for future Advanced/Pack |
| cutoff warnings | Expose incomplete history | cheap | Stage 6 coverage/limitations implemented |
| trend toggles | User controls derived trend lines | moderate | Advanced, not needed for bounded Core |
| category order/removal | Customize many graphs | moderate | Reject for v1; five fixed sections |
| graph resolution | Bound point count | cheap | Stage 6 auto granularity/max 400 implemented |
| empty revlog handling | No data ≠ zero quality | cheap | Stage 6 implemented |
| revlog performance work | Avoid repeated full fetch | moderate | Schema v3 aggregates + memoization implemented |
| manual changes/reconstruction | Reschedules/moves break historical state | snapshot-required | Explicit limitation; Time Machine deferred |

## More Overview Stats inventory

| Feature | Question / meaning | Source | Limitation | Cost | Scope | Destination / status | Reuse |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mature | Current cards with interval ≥21d | cards snapshot | not historical | cheap | all/deck | Stage 6 Core / implemented | official concept |
| young | Current review cards interval <21d | cards snapshot | not historical | cheap | all/deck | Stage 6 Core / implemented | official concept |
| unseen | Current new cards | cards snapshot | reset semantics | cheap | all/deck | Stage 6 Core / implemented | independent |
| buried | Current buried queue | cards snapshot | temporary state | cheap | all/deck | Stage 6 Core / implemented | independent |
| suspended | Current suspended queue | cards snapshot | current only | cheap | all/deck | Stage 6 Core / implemented | independent |
| learned | Broad learned total | cards snapshot | ambiguous overlap | cheap | all/deck | Reject as separate KPI; explicit states used | no code |
| unlearned | New/learning grouping | cards snapshot | ambiguous | cheap | all/deck | Reject as separate KPI | no code |
| new | Current new state | cards snapshot | differs from introduced events | cheap | all/deck | Stage 6 Core as unseen + introduced distinction | independent |
| learning | Current learning/relearning | cards snapshot | current only | cheap | all/deck | Stage 6 Core / implemented | independent |
| review | Current review state | cards snapshot | young/mature split preferred | cheap | all/deck | Stage 6 Core / implemented via split | independent |
| due | Current due count | schedule | overdue/future distinction needed | moderate | all/deck | Stage 6 Core / separated | official semantics |
| total | Total cards | cards snapshot | cards not notes | cheap | all/deck | Stage 6 Core / implemented | independent |
| percentages | State share | counts | denominator zero | cheap | all/deck | Stage 6 Core UI distribution | independent |
| percentages excluding suspended | Alternate denominator | counts | can confuse totals | cheap | all/deck | Advanced | no code |
| approximate finish date | unseen / new-per-day | config+cards | future errors, pauses and limits make date unreliable | moderate | deck | Reject for Stage 6; future simulator research | no code |
| note correction factors | Approximate notes from cards | manual factor | wrong for multi-template note types | cheap | deck | Reject; exact distinct notes used | no code |
| current-deck overview placement | Put stats on native Overview | UI hook | duplicates native/product IA | cheap | selected deck | Reject; Statistics is separate route | no code |

## Roadmap summary

- Stage 6 Core: overview, quality, load, progress, deck comparison; bounded
  cache/query/current snapshot.
- Stage 7 FSRS: stability, difficulty, retrievability, estimated knowledge,
  calibration and basic forgetting curves.
- Statistics Advanced v1.1: intervals, lapses, repetitions, time/rating
  distributions, hourly and deeper load/introduced analysis.
- Analytics Pack: snapshots, Time Machine, heavy curve fitting, custom
  analytics and experimental providers.
- Reject/research: arbitrary query UI, naive finish date, correction factors,
  inferred memorised/forgotten metrics without a precise contract.

