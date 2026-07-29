# G4.4 — bounded screening core economy

**Статус:** `COMPLETE`

**Final G4 outcome:** `REJECT`

**Production integration:** `PROHIBITED`

G4.4 выполнил deterministic synthetic screening двухдоменной экономики Review/Learn. Это research-only evidence: реальные данные Anki, production runtime, scheduler, FSRS, database, dashboard, API, package и release не использовались и не менялись.

## Исполненная версия

После просмотра первых результатов v3 выявились substantive defects в row-local gate coverage, expected-control predicates и marginal probes. Результаты v3 признаны недействительными и не используются в решении. Исправления были опубликованы до replacement run как новая immutable version v4.

```text
v4 publication SHA: 78ce71d82d72577f8283707a85b8e6b226330c94
v4 evaluator SHA: 6174c5deae40b339b7e738ae08c1060b3f0158fa
protocol digest: a6f8faf819e7d4a7c3d5ffd73ad82775642020faa019584b823e20ad3f2b18cd
pipeline digest: f49169b3e91e04e781819bea33b5c86778b981e17a27c954b0ed7295b387af62
scenario digest: fabd2cb9934953987cf6b64a6e34d070c3c1d26ef2d4f21641cfe5649cf6443d
matrix digest: 6c640a17643ac83c09fe56276072930152baa07f46147ab76c36b7f2b8160f67
```

Исполненные артефакты:

- [run manifest](../../research/gamification-sim/results/core-economy-screening-manifest-v4.json);
- [full row results](../../research/gamification-sim/results/core-economy-screening-results-v4.json);
- [machine protocol](../../research/gamification-sim/contracts/core-economy-candidate-protocol-v4.json);
- [evaluation pipeline](../../research/gamification-sim/contracts/core-economy-evaluation-pipeline-v4.json);
- [scenario registry](../../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v4.json);
- [screening matrix](../../research/gamification-sim/matrices/core-economy-screening-matrix-v4.json).

## Run accounting

```text
expected / actual / unique rows: 1275 / 1275 / 1275
missing / extra / duplicate rows: 0 / 0 / 0
gate results: 3952
metric results: 3710
control expected failures: 186
unexpected control passes: 50
unexpected failures: 33
result manifest digest: 585fe8ffd480db71feecd1d188eb3eb4ee4efe464ec2329bf26df56e96656dcf
result artifact digest: ad000099135574d285561d8e9bcc624ff430d25c42dd5b2d89a35476f3fad5db
result-set digest: bbbacf3880378409a740c26d85dbc589178ec2480f471107639e4c7ed8198d90
detached validation: PASS
byte-identical reproduction: PASS
```

Все 33 unexpected failures относятся к двум non-compensable gates:

- 21 × `HG-EXTREME-VOLUME-BOUNDED` у `D-PER-DOMAIN-SQRT-HIGH`;
- 12 × `HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED` у двух recommendation-eligible uncertainty policies.

Ни один recommendation-eligible integrated bundle не прошёл все hard gates:

| Bundle | Unexpected failures | Outcome |
| --- | ---: | --- |
| `B-INTEGRATED-GRACEFUL-MEDIUM` | 4 | `REJECTED_HARD_GATE` |
| `B-INTEGRATED-STEPPED` | 4 | `REJECTED_HARD_GATE` |
| `B-INTEGRATED-GRACEFUL-HIGH` | 11 | `REJECTED_HARD_GATE` |
| `B-INTEGRATED-ABRUPT-CONTROL` | 0 unexpected; 62 expected failures | `CONTROL_ONLY` |

Hard-gate compensation и weighted overall score запрещены. Поэтому passing isolated candidates не образуют рекомендованный integrated bundle.

## Dimension outcomes

| Dimension | Selected research candidate | Не выбранные / control | Decisive evidence | Confidence |
| --- | --- | --- | --- | --- |
| `CROSS_DOMAIN_CONVERSION` | `X-EQUALIZED-1_0-1_0` | `X-LEARN-LEANING-0_8-1_2` — bounded alternative; `X-REVIEW-LEANING-1_2-0_8-CONTROL` — control | cross-domain decomposition, marginal-contribution и crowdout gates не дали unexpected failures; equalized не вводит неподтверждённую премию одной области | bounded synthetic |
| `UNCERTAINTY_RESPONSE` | `NONE` | `U-CONFIDENCE-TAPER-RECOVERY` и `U-FIXED-STEPPED-TAPER` rejected; abrupt cutoff — control | обе eligible policies получили по 4 unexpected failures `HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED` на repeated conflict | decisive rejection |
| `DAILY_BOUNDING` | `D-PER-DOMAIN-BOUNDED-MEDIUM` | sqrt-high rejected; combined hard cap — control | medium не провалил daily gates; sqrt-high получил 7 unexpected failures `HG-EXTREME-VOLUME-BOUNDED` | bounded synthetic |
| `PRODUCTIVE_DAY` | `P-DAY-DOMAIN-EVIDENCE` | `P-DAY-BOUNDED-075` — bounded alternative | обе policies сохранили classification-only и planned-rest boundary; domain evidence меньше теряет легитимный single-domain day | governance tie-break |
| `LEVEL_CURVE` | `L-NPU-POWER-1_6` | `L-NPU-PIECEWISE` — bounded alternative | `HG-NO-LEVEL-LOSS` и `M-LEVEL-SCALE-SENSITIVITY` без unexpected failure; одна monotonic formula имеет меньшую policy surface | governance tie-break |
| `STREAK_PLANNED_REST` | `S-ONE-GRACE-14D` | `S-STRICT-PLANNED-REST` — bounded alternative | no-XP-multiplier и planned-rest gates сохранены; one-grace уменьшает вред единичного легитимного пропуска | governance tie-break |
| `MOMENTUM` | `M-ROLLING-7-NONREST` | `M-EMA-025` — bounded alternative | обе bounded/non-spendable и не создают snowball; rolling window проще объяснить и проверить | governance tie-break |
| `RECOVERY` | `R-STEPWISE-2-NORMAL-DAYS` | `R-LINEAR-3-NORMAL-DAYS` — bounded alternative | обе state-only, без return bonus и recovery loop; stepwise быстрее снимает ограничение и имеет меньшую state surface | governance tie-break |

Эти dimension selections — research defaults для объяснения результата, а не production approval. Из-за `UNCERTAINTY_RESPONSE = NONE` они не складываются в допустимый core-economy recommendation.

## Review axis

```text
winner: P-TAPER-ZERO-30D
default for future bounded research: P-TAPER-ZERO-30D
non-selected member: P-STEP-ZERO
both members falsified: NO
averaging: PROHIBITED
```

Оба members получили одинаковые агрегаты G4.4: `606` rows, `12` unexpected failures и `17` unexpected control passes. Неарбитрарный tie-breaker задан governance-приоритетом: сначала минимизировать вред легитимному контексту, затем policy complexity. TAPER сохраняет постепенный переход на днях 60–90 и не обнуляет допустимый контекст мгновенно; поэтому он выбран вместо STEP. Это не доказывает human-learning superiority. Усреднение остаётся запрещённым, потому что оно скрывает member-specific failures и меняет frozen source semantics.

## Learn input

```text
winner / bounded input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
evidence status: CONFIRMATORY_INCONCLUSIVE
limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
confirmed source total: 1.0 LRU
production ready: NO
```

Confirmation-only выбран вместо pending-split по принципу `MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE`: одинаковый confirmed total без provisional exposure, settlement и дополнительной explanation surface. Missing disposable identity probe не закрыт и снижает confidence всего Learn-зависимого G4 evidence.

## Final decision

```text
G4: COMPLETE
G4.4: COMPLETE
screening: COMPLETE
results: AVAILABLE
final G4 outcome: REJECT
recommended integrated bundle: NONE
production integration: PROHIBITED
G5: CONDITIONAL / NOT STARTED
G6: CONDITIONAL / NOT STARTED
```

`REJECT` относится к опубликованному v4 candidate set: все recommendation-eligible integrated bundles провалили хотя бы один non-compensable hard gate. Решение не доказывает невозможность любой будущей экономики и не разрешает post-hoc tuning v4.
