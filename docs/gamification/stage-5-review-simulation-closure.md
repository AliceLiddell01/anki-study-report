# Stage 5 Review Simulation Closure

Дата закрытия: 2026-07-16

Ветка: `chatgpt/gamification-concept-foundation`

## Status

**PARTIAL — calibration methodology correction in progress**

The initial closure result was superseded by Stage 5B.C because the first sweep
mixed current-model regression assertions with candidate-independent gates and
used placeholder metrics. Исторические результаты ниже сохранены как evidence
первого прогона, но shortlist и вывод `COMPLETE` не являются актуальной
калибровкой до прохождения gates C1–C6.

Все обязательные research gates `H`, `P`, `G`, `M`, `R` и `F` выполнены.
Статус не означает production readiness, утверждение финальной экономики или
интеграцию в Anki Study Report.

## Implemented stages

| Stage | Result |
|---|---|
| 5A — Simulation Specification | COMPLETE |
| 5B.1 — Deterministic Core | COMPLETE |
| 5B.1 hardening | COMPLETE |
| 5B.2 — Scenario Runner | COMPLETE |
| 5B.2H — Contract Hardening | COMPLETE |
| 5B.3 — Initial Parameter Sweep | SUPERSEDED |
| 5B.4 — Initial Property-based Verification | SUPERSEDED |
| 5B.5 — Independent-day Workload Stress | COMPLETE (not longitudinal evidence) |
| 5B.C — Calibration Correction | IN PROGRESS |
| 5B.6 — Rust Oracle | COMPLETE |
| 5B.7 — FSRS Reference | COMPLETE |

## Baseline contract

`review-v0.1` сохранён без изменения числовых значений. `R-CURRENT` проходит
`H01–H18`, 31 golden case, 26 scenario definitions, deterministic digest,
property-based verification и Python/Rust differential verification.

Hard gates выполняются до Pareto ranking. Ни один средний показатель или
composite score не может компенсировать потерю baseline, нарушение session
invariance, duplicate/replay reward, preview reward, cap или breakdown identity.

## Candidate outcomes

Первый sequential sweep выполнил 17 evaluations при budget 48. Fairness в
таблице показывает `session delta / honest baseline ratio`; abuse — duplicate
increment / intentional-backlog advantage. Bonus — ordinary p95 Additional /
Support share. Complexity — прозрачный rule-based count.

| Candidate | Hard gate | Fairness | Abuse | Bonus p95 | Complexity | Decision |
|---|---|---|---|---|---:|---|
| `R-CURRENT` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 17 | retained; recommended |
| `R-CURRENT+V-CURRENT` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 17 | equivalent overlay; retained |
| `R-CURRENT+V-CURRENT+C-CURRENT` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 17 | equivalent overlay; retained |
| `R-CURRENT+V-CURRENT+C-CURRENT+S-CURRENT` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 17 | equivalent overlay; retained |
| `R-CURRENT+V-CURRENT+C-CURRENT+S-CURRENT+P-CURRENT` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 17 | equivalent overlay; retained |
| `R-CURRENT+V-CURRENT+C-CURRENT+S-CURRENT+P-LOW` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 19 | hard-gate survivor; Pareto dominated |
| `R-CURRENT+V-CURRENT+C-CURRENT+S-CURRENT+P-METRIC-ONLY` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 18 | hard-gate survivor; Pareto dominated |
| `R-CURRENT+V-CURRENT+C-CURRENT+S-EPISODE-ONLY` | REJECT | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.070%` | 20 | scenario assertion failure |
| `R-CURRENT+V-CURRENT+C-CURRENT+S-LOW` | REJECT | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 20 | scenario assertion failure |
| `R-CURRENT+V-CURRENT+C-LOW` | REJECT | `0 / 1.00` | `0 / 2.50%` | `1.996% / 0.137%` | 19 | scenario assertion failure |
| `R-CURRENT+V-CURRENT+C-SYMBOLIC` | REJECT | `0 / 1.00` | `0 / 2.50%` | `0.316% / 0.137%` | 18 | scenario assertion failure |
| `R-CURRENT+V-LOW-CAP` | PASS | `0 / 1.00` | `0 / 2.50%` | `2.814% / 0.137%` | 18 | hard-gate survivor; Pareto dominated |
| `R-CURRENT+V-NONE` | REJECT | `0 / 1.00` | `0 / 2.50%` | `2.629% / 0.137%` | 18 | scenario assertion failure |
| `R-CURRENT+V-SOFT` | REJECT | `0 / 1.00` | `0 / 2.50%` | `2.713% / 0.137%` | 18 | scenario assertion failure |
| `R-LOW-CHALLENGE` | REJECT | `0 / 1.00` | `0 / 1.695%` | `2.814% / 0.137%` | 19 | scenario assertion failure |
| `R-NEUTRAL-CONTEXT` | REJECT | `0 / 1.00` | `0 / 0%` | `2.814% / 0.137%` | 18 | scenario assertion failure |
| `R-NO-GAIN` | REJECT | `0 / 1.00` | `0 / 2.632%` | `2.814% / 0.137%` | 17 | scenario assertion failure |

Sweep digest: `ea880d062a92b9f9b40a5255a93601ccceae19b0600f25c46c37ea73dc15edd2`.

## Pareto shortlist

Недоминируемый output содержит baseline и его пустые current-family overlays.
После удаления семантически эквивалентных overlays research shortlist:

1. `R-CURRENT`.

Выбор сделан hard gates + Pareto dominance, без aggregate score.

## Recommended candidate

`R-CURRENT` — **recommended research candidate for later cross-domain
calibration**.

Он не является final production economy. Параметры должны пройти общую
калибровку с будущими Learn/Create domains до продуктового решения.

## Population results

- personas: 16 synthetic classes;
- development: 480 persona-days;
- standard: 584,000 persona-days, 100 child seeds на persona, master seed `20260716`;
- standard digest: `a7823e39eb85c5b39f37266ad4b7057d12febe54d4c7478e06d9c911425703c4`;
- long mode: около 1.098 млн persona-days, explicit opt-in;
- long smoke: 112 persona-days, digest `9673b69b231cf12a7583f9598cef850650e787105fef6374daafadc745efcbbb`.

Все honest personas сохранили baseline ratio `1.00`; gate failures отсутствуют.
Mean/p95 RU диапазон standard run — от `0.021/0` для zero-due до
`44.61/61.18` для high-volume. Наиболее широкие tails ожидаемо наблюдаются у
backlog-return (`p95 39.10`), filtered exam prep (`35.02`) и irregular schedule
(`22.87`). Это synthetic workload effects, а не вывод о реальных пользователях.

Fairness matrix отдельно показывает baseline ratios и не скрывает suppression
средним reward. Abuse matrix использует matched controls для expressible
contracts; lifetime/FSRS-dependent exploits помечены `deferred`, без placeholder
numbers.

## Differential verification

- Rust: `rustc 1.97.1`;
- deterministic dependencies: `serde 1.0.228`, `serde_json 1.0.150`, `thiserror 2.0.18`;
- cases: 126;
- exact: 125;
- within `1e-9`: 1;
- semantic mismatch: 0;
- unsupported: 0;
- invalid parity cases: 2, rejected with non-zero Rust exit.

Corpus includes 31 golden cases, 43 scenario-days from all 26 scenario files,
42 threshold cases, 5 survivor overlays, 3 fixed property edges and 2 invalids.

## FSRS reference

- `py-fsrs 6.3.1`;
- official `fsrs-rs 6.6.1` crate;
- 10 versioned synthetic UTC trajectories;
- state/retrievability/counterfactual tolerance: `1e-4`;
- state mismatches: 0;
- trajectory digest: `2c184f547e1b79480bef66aaf6e81158c0540c563f91c8e5b1343fac8d14bf0f`.

Known difference: py-fsrs applies configured learning/relearning steps, whereas
`fsrs-rs::next_states` reports a model interval. The 28 interval differences are
reported as scheduler-layer differences. Serialized Card/ReviewLog objects are
implementation-specific; normalized trajectory signature and state fields are
compared. FSRS high/low/no-context and backlog natural-due inputs all preserve
the same `0.9` CoreBaseline.

## Residual risks

- synthetic personas approximate workload classes, not human motivation or real histories;
- sanitized real-history replay: **DEFERRED — optional, requires separate privacy and data-contract task**;
- no Learn XP or Create XP specification/implementation;
- no global XP conversion or cross-domain economy calibration;
- no production reward ledger, persistence, migration or reconciliation;
- local-owner tampering remains an accepted risk;
- no production integration and no `.ankiaddon` inclusion;
- no CI integration; all research checks are manual/local;
- no real collection, revlog, card content or personal data was accessed.

## Next product-design stage

**Learn XP Specification**

Этот этап не начат автоматически.
