# Stage 5B.C Review XP Calibration Correction

- Дата проверки: 2026-07-16
- Ветка: `chatgpt/gamification-concept-foundation`
- Статус: **PARTIAL**

Этот документ фиксирует исправленную методику и фактические результаты gates
C1–C6. Инфраструктура, assertion taxonomy, evidence statuses, persistent-card
симуляция, corrected sweep и обязательные longitudinal runs завершены. Closure
остаётся `PARTIAL`, потому что normalized retention-cycling advantage вырос от
90 к 365 дням во всех matched replicas для `R-CURRENT`.

## Reason for correction

Первый Stage 5 closure смешивал exact regression expectations текущей формулы с
parameter-independent gates и использовал placeholder значения для части
fairness/abuse metrics. Это делало выбор кандидатов круговым и не доказывало
longitudinal behavior. Исторический отчёт сохранён, но его shortlist и вывод
`COMPLETE` superseded этой проверкой.

## Original methodological defects

| Defect | Audit | Correction |
|---|---|---|
| Alternative rejected by current-only exact assertion | confirmed | assertions разделены на invariant/regression с explicit applicability |
| Missing metric represented by ideal `0`/`1` | confirmed | typed `MEASURED`/`DERIVED`/`UNSUPPORTED`/`DEFERRED` evidence |
| Volume/completion gates used configured caps instead of observations | confirmed | Q06/Q07 use measured maxima from scenario results |
| Independent days presented as longitudinal evidence | confirmed | report renamed to Independent-day workload stress simulation |
| Retention/backlog lacked persistent matched card histories | confirmed | separate 30/90/365-day persistent-card engine and matched policies |

Дополнительный результат аудита: отдельные 90- и 365-day endpoint gates могут
оставаться ниже 3%, но не выявляют систематический межгоризонтный рост. Поэтому
добавлена отдельная 90→365 comparison.

## Assertion taxonomy

- scenario contract: `review-scenario-v0.2`; `v0.1` сохранён как superseded history;
- migrated scenarios: 26/26;
- invariant assertions: 17;
- regression assertions: 36;
- каждый regression assertion имеет `applies_to_parameter_set_ids: ["R-CURRENT"]`;
- неприменимый regression получает `NOT_APPLICABLE` и не входит в failed count;
- current corpus result: 53/53 applicable assertions passed;
- scenario digest: `e0d228173839b22725b2f5b0d6547797f521cbef212acecef7a1a91c5f16e763`.

Applicability не выводится из имени файла, scenario category или rule-version
эвристики.

## Metric evidence statuses

| Metric | Old behavior | Corrected evidence | Sample/source | Gate use |
|---|---|---|---|---|
| collection-size parity | hardcoded zero | `DERIVED = 0` from absent metadata plus matched workload | 1 structural match | fairness |
| low-confidence parity | placeholder | `MEASURED = 0.04 RU` | 1 matched episode | fairness |
| no-FSRS parity | placeholder | `MEASURED = 0.053333 RU` | 1 matched episode | fairness |
| honest baseline suppression | ideal zero | `MEASURED = 0` | 325 eligible episode observations | hard gate |
| observed volume maximum | configured cap | `MEASURED = 6.75 RU` | 43 scenario-days | Q06 |
| observed completion maximum | configured cap | `MEASURED = 0.405 RU` | 43 scenario-days | Q07 |
| high/low retention parity | placeholder | `MEASURED = 0.089131` | 2 matched 90-day replicas | fairness |
| backlog-return viability | placeholder one | `MEASURED = 1.0` baseline preservation | 2 matched 90-day replicas | fairness |
| long-session baseline ratio | placeholder one | `MEASURED = 1.0` within float tolerance | 351 reviews in max-workload cell | baseline gate |
| intentional-backlog advantage | placeholder | `MEASURED = -0.000443` maximum | 2 matched 90-day replicas | Q16 |
| retention-cycling advantage | placeholder | `MEASURED = 0.010981` maximum | 4 matched 90-day replicas | Q15 |

Для candidate evaluation обязательных `UNSUPPORTED`/`DEFERRED` metrics нет.
Низкоуровневый `_metrics()` без longitudinal input по-прежнему честно возвращает
`UNSUPPORTED`/`DEFERRED` с `value: null` и причиной; такое evidence не может
попасть в final Pareto front.

## Longitudinal simulator contract

- card lineage и scheduler state сохраняются между днями;
- py-fsrs scheduler использует `fsrs 6.3.1`; no-FSRS mode явно называется
  `neutral-synthetic-v0.1` и не заявляет Anki scheduler parity;
- режимы: 30 days / 12 cards / 1 replica, 90 days / 24 cards / 2 replicas,
  365 days / 20 cards / 2 replicas;
- due cards выбираются из state-derived due dates; пропущенные cards становятся
  overdue, остаются теми же lineages и обрабатываются после delay window;
- policy review limit ограничивает workload, а не создаёт независимые reviews;
- `Again` — failed recall; `Hard`, `Good`, `Easy` — successful outcomes;
- matched policies получают одинаковые initial cohort и latent draws, ключованные
  master seed, replica, lineage, review ordinal и channel;
- `CoreBaseline` не зависит от FSRS confidence/availability и сохраняется во всех
  honest histories.

Scheduler assumptions сверены с [официальным Anki FSRS manual](https://docs.ankiweb.net/deck-options.html#fsrs),
адаптер — с [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs),
reference oracle — с [fsrs-rs](https://github.com/open-spaced-repetition/fsrs-rs).

## Matched fairness matrix

Каждая pair меняет ровно один declared factor; initial cohort digest и latent
stream совпадают внутри replica.

| Comparison | Horizon | Reviews left/right (replicas 0;1) | Baseline delta | Context delta | Total delta | Status |
|---|---:|---|---|---|---|---|
| stable high vs low retention | 90 | `158/76; 162/56` | `77.7; 92.8` | `-0.919; 2.138` | `78.852; 98.064` | MEASURED |
| honest backlog return vs timely | 90 | `103/114; 76/77` | `-8.6; -0.9` | `-0.530; -0.009` | `-9.488; -0.936` | PASS |
| stable high vs low retention | 365 | `208/89; 282/84` | `110.35; 175.6` | `-2.438; 0.479` | `110.972; 181.554` | MEASURED |
| honest backlog return vs timely | 365 | `150/151; 116/135` | `-0.9; -13.85` | `0.112; -1.449` | `-0.815; -15.965` | PASS |

Разный total при разных retention targets не называется exploit автоматически:
отчёт отдельно показывает review-count и legitimate baseline delta.

## Matched abuse matrix

`Unexplained advantage = (total delta - legitimate additional baseline) /
control total`.

| Comparison | Horizon | Advantage replica 0 | Advantage replica 1 | Endpoint gate | Horizon-growth gate |
|---|---:|---:|---:|---|---|
| high-retention cycle vs stable high | 90 | `-0.377%` | `-1.004%` | PASS | — |
| high-retention cycle vs stable high | 365 | `1.740%` | `0.154%` | PASS | **FAIL** |
| low-retention cycle vs stable low | 90 | `1.098%` | `0.402%` | PASS | — |
| low-retention cycle vs stable low | 365 | `1.162%` | `1.360%` | PASS | **FAIL** |
| intentional backlog vs timely | 90 | `-0.788%` | `-0.044%` | PASS | — |
| intentional backlog vs timely | 365 | `0.056%` | `-1.567%` | PASS | PASS |

365-day endpoint values ниже 3%, но обе retention-cycle groups увеличились в
каждой matched replica. Это и есть открытый evidence gap. Однодневные matched
controls для duplicate replay, relearning, preview, forced due, session split и
micro-scope completion проходят.

## Corrected sweep

- evaluated candidate IDs: 30 при budget 48;
- statuses: 30 `PASS`, 0 `REJECT`, 0 `INCOMPLETE_EVIDENCE`;
- all 17 requested catalog candidates evaluated;
- current-only regressions для alternatives: `NOT_APPLICABLE`;
- only `PASS` candidates ranked;
- Pareto objectives use measured comparable metrics;
- semantic duplicates removed by normalized parameter digest;
- output digest: `16ce6388691f4645fd77ead50f548c3f0985224fa0813f2f1fd6ebee99eeeeb1`;
- repeated fixed-config/seed digest: identical.

Corrected Pareto front contains 14 normalized states:

`R-CURRENT`, `R-CURRENT+V-CURRENT+C-CURRENT+S-EPISODE-ONLY`,
`R-CURRENT+V-CURRENT+C-LOW`,
`R-CURRENT+V-CURRENT+C-LOW+S-EPISODE-ONLY`,
`R-CURRENT+V-CURRENT+C-SYMBOLIC`, `R-CURRENT+V-NONE`,
`R-CURRENT+V-NONE+C-LOW`, `R-CURRENT+V-NONE+C-SYMBOLIC`,
`R-CURRENT+V-SOFT`, `R-LOW-CHALLENGE`,
`R-LOW-CHALLENGE+V-NONE`, `R-LOW-CHALLENGE+V-SOFT`,
`R-NEUTRAL-CONTEXT`, `R-NO-GAIN`.

## Property verification

- 43 distinct normalized parameter states;
- includes catalog candidates, all corrected Pareto states, every sensitivity
  endpoint and a valid expected-rejection boundary;
- Hypothesis: `max_examples=40`, `database=None`, `derandomize=True`,
  `deadline=None`;
- properties: H01–H18, baseline monotonicity, session invariance, source
  idempotency, Undo reversibility, button neutrality, no response-time reward,
  manual/preview zero, caps, non-negative/explainable result, determinism,
  serialization and canonical digest stability;
- selected attempt-credit boundary is valid by parameter contract, passes
  H01–H18 and is rejected only by measured `Q01_ORDINARY_MEDIAN`.
- standalone Rust differential oracle covers 135 cases across all 14 corrected
  Pareto states: 134 exact, 1 within tolerance, 0 semantic mismatch and
  0 unsupported; output digest
  `425351ebce1d2b1408f6c2e0c04d43541bd0e2b8c1657f3e16a5009ffe64e5e1`.

## Sensitivity

- 13 explicit one-at-a-time grids, 63 points;
- 63/63 complete evidence, 63/63 invariant PASS;
- 53 quantitative PASS, 10 expected gate crossings;
- crossings: attempt credit 0.15/0.20/0.35, outcome credit 0.55/0.60/0.75,
  neutral context 0.05/0.075, support episode cap 0.15/0.18;
- every point includes longitudinal metric deltas and cliff status;
- digest: `2ebc1c182fb6075f441a473e842ad198d80977e6128c82ce9427d0a72c4dd682`;
- repeated fixed-config/seed digest: identical.

## Corrected population results

Independent-day workload stress simulation remains historical stress evidence:
584,000 independent persona-days with digest
`a7823e39eb85c5b39f37266ad4b7057d12febe54d4c7478e06d9c911425703c4`.
It is not longitudinal evidence.

| Run | Candidates | Policies | Results | Reviews | Trajectory digest | Final cohort digest | Report digest |
|---|---:|---:|---:|---:|---|---|---|
| development 30-day | 4 | 9 | 36 | 1,484 | `26896e7a…56da` | `2a6d13d6…8419` | `0f80052a…2341` |
| calibration 90-day | 14 | 9 | 252 | 31,892 | `82fe245b…d0b0` | `f6273abe…31bf` | `ffdeb479…1790` |
| calibration 365-day | 1 | 7 | 14 | 2,189 | `d531ea73…425c` | `4e4de0fd…6a99` | `91e438c5…06fa` |

Для 90/365 runs повторяются trajectory, final-cohort и report digests. Другой
seed создаёт другую trajectory при том же versioned contract. Baseline ratio во
всех policy-results равен `1.0` в пределах floating tolerance. Каждый generated
run содержит `manifest.json`, `policy-metrics.csv`, `fairness.json`, `abuse.json`,
`cohort-state-summary.json`, `summary.md`; все paths находятся под gitignored
`outputs/longitudinal/`.

## Candidate decisions

Все 30 corrected-sweep evaluations имеют полное 90-day evidence и статус
`PASS`. Однако `R-CURRENT` не проходит отдельный cross-horizon cycling gate, а
остальные Pareto candidates не имеют полного обязательного 365-day решения.
Поэтому этот этап не объявляет recommended Review XP research candidate и не
утверждает коэффициенты. `R-CURRENT` остаётся regression reference, не final
production economy.

## Residual limitations

- retention cycling требует отдельной parameter/policy investigation и нового
  matched 90/365 rerun;
- 365-day calibration охватывает `R-CURRENT`, 20 cards и 2 replicas;
- synthetic recall не доказывает human motivation или real-world economy;
- sanitized real-history replay остаётся optional and deferred;
- Rust parity доказывает implementation consistency, не economic correctness;
- simulator не читает Anki collection/revlog и не интегрирован в production;
- add-on build, Fast CI, Full CI и Docker E2E не являются проверками этой задачи;
- Learn XP и Create XP не начаты.

Следующий шаг: **resolve listed Stage 5 evidence gaps**. Learn XP Specification
может начаться только после повторного closure со статусом `COMPLETE`.
