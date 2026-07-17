# FSRS Helper reference inventory

Дата аудита: 2026-07-13. Reference: tag `26.06.12`, commit
`29208f220f21ff994c199712a6aaac47636773bf`, MIT License. Исходники изучались
во временном checkout вне project tree; runtime dependency и vendored code нет.

Проверены `README.md`, `License`, `manifest.json`, `config.json`, `config.md`,
`configuration.py`, `stats.py`, `steps.py`, `dsr_state.py`, `utils.py`,
`sync_hook.py`, `browser/custom_columns.py`, все файлы `schedule/` и wiki
`Home`, `Reschedule`, `Advance & Postpone`, `Load Balance & Easy Days`,
`Disperse Siblings`, `Flatten`. Wiki snapshot:
`8c65fe6d3f342a5c4a93e810b00ed7ec8e164114`.

## Решение

Helper — product/edge-case reference. Stage 7 использует Anki 26.05 collection
и backend как source of truth. Никакие private modules/menu/actions Helper не
вызываются. Его locale/UI не копируются. Mutating scheduling tools относятся к
future Scheduling Pack / DLC или остаются в native Anki и не входят в core
read-only dashboard.

| Feature | User question | Mode / source | Native overlap / preset semantics | Minimum / cost / effects | Destination | Reuse and decision |
| --- | --- | --- | --- | --- | --- | --- |
| FSRS Stats | Сколько материала вероятно помню? | read-only; cards memory state + time | Native Stats retrievability and knowledge; scoped deck/preset | valid states; moderate; none | Stage 7 Core | idea only; native/project aggregates |
| Average predicted retention | Какова средняя вероятность? | read-only; memory state | Native retrievability; own target per deck | ≥1 state; moderate | Stage 7 Core | independently aggregated |
| Average stability | Насколько устойчива память? | read-only; cards state | Native Stability; compatible scope | ≥1 state; moderate | Stage 7 Core | median preferred to Helper mean |
| Daily Load | Какова ожидаемая нагрузка? | read-only; schedule/state | Native future due/simulator | ≥1 reviewed card; moderate | Stage 7 simulator | native simulator, not Helper formula |
| Estimated knowledge | Сколько вероятно вспомню? | read-only; sum R | Native Stats `sum_by_card` semantics | ≥1 state; moderate | Stage 7 Core | independently aggregated |
| Steps Stats | Подходят ли короткие шаги? | read-only; revlog scenarios | No equivalent public graph; same-preset scope | per scenario 30/100; expensive; none | Stage 7 Core | scenarios/reference only; project aggregation |
| Learning recommendation | Какой диапазон наблюдается? | read-only; scenario delays | Native settings remain authoritative | key scenarios ≥100; expensive | Stage 7 Core | observed range, no copied optimizer |
| Relearning recommendation | Подходит ли переучивание? | read-only; review→Again sequence | Same preset | own sample; expensive | Stage 7 Core | observed range only |
| True Retention integration | Совпадают ли ответы и прогноз? | read-only; first/qualifying reviews | Native Stats True Retention | 100 preliminary, 400 sufficient | Stage 7 calibration | existing/native semantics |
| D/S/R display | Что означают состояния? | read-only; card memory state | Native Card/Stats API | valid state; moderate | Stage 7 aggregate; Cards v2 later | no per-card list |
| Target R Browser column | Какая цель конкретной карты? | read-only; deck override | Native desired retention | per-card; moderate | Future Browse/Search | rejected from Stage 7 |
| Reschedule | Пересчитать due? | mutating; card/revlog writes | Native reschedule-on-change overlaps | collection-wide; expensive; due/history effects | Future Scheduling Pack / native | no reuse, rejected |
| Advance | Повторить раньше? | mutating; due/interval | partial native custom study | selected cards; expensive | Future Scheduling Pack | rejected |
| Postpone | Отложить due? | mutating; due/interval | no safe analytics overlap | selected cards; expensive | Future Scheduling Pack | rejected |
| Schedule a Break | Перераспределить отпуск? | mutating; due/card custom data/log | no read-only overlap | window cards; expensive | Future Scheduling Pack | rejected |
| Load Balance | Выровнять очередь? | mutating; fuzz/due | native load balancer overlap | group-wide; expensive | Native / future pack | rejected |
| Easy Days | Снизить отдельные дни? | mutating when applied | native easy-day config overlaps | preset; moderate | Native / future pack | rejected |
| Disperse Siblings | Разнести siblings? | mutating; due/card updates | native sibling scheduling differs | note families; expensive | Future Scheduling Pack | rejected |
| Flatten | Ограничить дни? | mutating; due redistribution | no analytics overlap | due queue; expensive | Future Scheduling Pack | rejected |
| Remedy Hard Misuse | Переписать Hard? | mutating; review history | native FSRS treats Hard as recall | one-way/history risk | Diagnostics/Maintenance | rejected; neutral help only |
| Reset custom records | Удалить Helper metadata? | mutating; card JSON | Helper-specific | cards; moderate | Diagnostics/Maintenance | rejected |
| Reset manual/reschedule logs | Удалить revlog? | mutating; `DELETE revlog` | no safe overlap | destructive/one-way sync | Reject | rejected |
| Post-sync auto-reschedule | Исправить remote reviews? | mutating sync hook | native FSRS now available cross-device | remote changes; expensive | Native / future pack | rejected |

## License / implementation notes

`steps.py` contains a ternary-search curve fit and SQL scenario extraction.
Stage 7 does not copy it. It implements its own bounded ordered-event
aggregation and reports an observed successful-delay range rather than claiming
an optimal minute. `stats.py` and `dsr_state.py` confirmed semantics and edge
cases only. No copyright-bearing Helper source is present in this repository.
