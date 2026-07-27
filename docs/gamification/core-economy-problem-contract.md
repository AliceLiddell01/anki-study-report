# Core Gamification Economy — контракт проблемы и границ G4.1

**Contract ID:** `core-economy-problem-contract`  
**Version:** `1`  
**Status:** `FROZEN_PRE_NORMALIZATION_ANALYSIS`  
**Stage:** `G4.1 — Freeze core gamification economy problem and contract`  
**Production integration:** `PROHIBITED`  
**G4.2:** `NEXT / NOT STARTED`

Нормативный machine-readable источник: [`core-economy-problem-contract-v1.json`](../../research/gamification-sim/contracts/core-economy-problem-contract-v1.json). Его проверяет строгая Draft 2020-12 schema [`core-economy-problem-contract-v1.schema.json`](../../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json).

## 1. Назначение

G4 определяет и исследует **core gamification economy** для двух доменов:

```text
Review XP
+
Learn XP
```

`Create XP` не входит в initial economy. G3 не отменён, но отложен до периода после первого стабильного Gamification release и не блокирует G4, G5 или G6.

Замороженный problem statement:

> Core Gamification economy должна преобразовывать bounded Review XP и Learn XP research signals в долгосрочную, объяснимую и устойчивую к манипуляциям progression, которая остаётся полезной для разных легитимных режимов обучения и не делает backlog, объём кликов, session splitting, календарные манипуляции, misreporting или экстремальный raw volume выгоднее качественной и регулярной учёбы.

Главный invariant:

> Пользователь не должен получать систематическое преимущество только потому, что его workflow генерирует больше технических событий, более крупный backlog, больше session boundaries или более удобную для farming конфигурацию при сопоставимом учебном результате.

XP, level, streak и Momentum не измеряют знания, mastery, intelligence, effort, качество, моральную ценность или дисциплину человека.

## 2. Статус G3 и новое определение G4

### 2.1. G3 / Create XP

```text
G3: DEFERRED / POST-MVP / NOT STARTED
critical path: NO
blocks G4/G5/G6: NO
production integration: PROHIBITED
initial core economy: EXCLUDED
```

Activation gate G3 требует одновременно:

```text
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

G4.1 не определяет G3.1, Create lifecycle, candidates, units, formulas или simulation.

### 2.2. G4

```text
G4 — Core gamification economy calibration
dependencies:
G1 COMPLETE
G2 COMPLETE
G3 NOT REQUIRED / DEFERRED POST-MVP
```

В scope:

- bounded Review XP research input;
- bounded Learn XP research input;
- cross-domain normalization problem;
- productive-day semantics;
- level progression;
- streak и planned rest;
- Momentum и recovery;
- fairness между legitimate study patterns;
- anti-gaming и explainability boundaries;
- research-only simulation в последующих G4 stages.

Вне scope:

- Create XP;
- production XP amounts, ledger, persistence и migrations;
- dashboard, API и UI;
- scheduler, FSRS и due-date mutation;
- remote AI scoring и real-user data;
- leaderboards, marketplace и mandatory accounts;
- G5/G6 implementation.

## 3. Input evidence ledger

### 3.1. Review XP uncertainty axis

```text
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review candidate: NONE

P-STEP-ZERO:
CONFIRMATORY_ELIGIBLE
selected: NO
falsified: NO

P-TAPER-ZERO-30D:
CONFIRMATORY_ELIGIBLE
selected: NO
falsified: NO
```

Оба кандидата являются обязательной `REVIEW_UNCERTAINTY_AXIS` для будущего G4 analysis.

G4.1:

- не выбирает Review winner;
- не использует один candidate как скрытый default;
- требует prospectively defined cross-domain criterion до любого выбора;
- допускает получение новой cross-domain evidence в G4 без переписывания G1;
- не превращает старые aggregate summaries в новую eligibility.

### 3.2. Learn XP input

```text
candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
G2.5 status: CONFIRMATORY_INCONCLUSIVE
reason: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
confirmatory eligible: NO
production ready: NO
production approved: NO
```

G4 может использовать candidate только как bounded research input. Его identity limitation сохраняется во всех позднейших claims. Frozen `1.0 LRU` остаётся comparative Learn accounting и не становится автоматически common economy XP.

## 4. Terminology freeze

| Term | Определение |
|---|---|
| `CORE_ECONOMY` | G4 research economy, объединяющая bounded Review и Learn contributions; не production economy. |
| `REVIEW_DOMAIN` | Review XP research input с unresolved two-candidate uncertainty axis. |
| `LEARN_DOMAIN` | Recommended Learn XP research input с сохранённым confirmatory limitation. |
| `DOMAIN_SIGNAL` | Typed research evidence одного домена; не production event или price. |
| `DOMAIN_CONTRIBUTION` | Bounded и explainable contribution после будущей normalization policy. |
| `REVIEW_UNCERTAINTY_AXIS` | Обязательная параллельная обработка `P-STEP-ZERO` и `P-TAPER-ZERO-30D` без winner. |
| `NORMALIZATION` | Будущее typed преобразование heterogeneous domain signals в common comparative interface. |
| `CONVERSION_POLICY` | Будущее versioned отношение Review/Learn contributions; ratio в G4.1 не выбран. |
| `PRODUCTIVE_DAY` | Research classification из bounded eligible signals; не обязанность учиться каждый calendar day. |
| `DAILY_PRODUCTIVE_SIGNAL` | Decomposable day-level evidence после eligibility и aggregation. |
| `RAW_VOLUME` | Unbounded technical event/object count, недостаточный сам по себе для productivity. |
| `BOUNDED_CONTRIBUTION` | Contribution, защищённая от event multiplication, backlog, configuration и calendar manipulation. |
| `DIMINISHING_RETURNS` | Возможная будущая compression excess contribution; function/parameters не выбраны. |
| `LEVEL` | Presentation cumulative bounded progression; не mastery, certification, intelligence или human worth. |
| `LEVEL_CURVE` | Будущее versioned mapping cumulative progression в presentation levels. |
| `STREAK` | Presentation productive-day continuity; не XP и не moral evaluation. |
| `STREAK_GROWTH` | Увеличение streak после будущего qualifying productive day. |
| `STREAK_PRESERVATION` | Сохранение streak без growth, включая planned-rest boundary. |
| `PLANNED_REST` | Neutral rest: no XP, no growth, no break, no debt. |
| `UNPLANNED_ABSENCE` | Non-productive interval без negative XP debt; streak semantics отложены. |
| `MOMENTUM` | Bounded, explainable, non-spendable rhythm indicator; не XP multiplier. |
| `RECOVERY` | Return-to-rhythm behavior без backlog multiplier, debt или return bonus loop. |
| `BACKLOG` | Accumulated due work; размер сам по себе не reward source. |
| `SESSION_SPLITTING` | Деление одинаковой работы на большее число sessions; contribution не растёт. |
| `CALENDAR_BOUNDARY` | Civil date/time boundary, отдельная от Anki day и session. |
| `ANKI_DAY` | Typed Anki scheduler-day aggregation axis; не автоматически calendar day. |
| `PERSONA` | Synthetic workload class; не real user profile. |
| `FAIRNESS` | Отсутствие systematic exploit/devaluation legitimate workflow, а не equal XP за разную работу. |
| `FARMING` | Synthetic strategy, увеличивающая progression без comparable bounded productive signal. |
| `EXPLAINABILITY` | Возможность разложить progression на typed domain/day contributions, reasons и limitations. |

Ключевые продуктовые границы:

- `PRODUCTIVE_DAY` не означает обязанность учиться ежедневно;
- `LEVEL` не является mastery rank или certification;
- `STREAK` не оценивает моральную ценность или дисциплину;
- `MOMENTUM` является bounded non-spendable indicator и не умножает XP;
- `FAIRNESS` не означает одинаковые XP при разном объёме полезной работы.

## 5. Candidate source и non-rewardable boundary

Potential G4 inputs:

```text
BOUNDED_REVIEW_RESEARCH_SIGNAL
CONFIRMED_LEARN_RESEARCH_SIGNAL
```

Это research categories, а не production events или prices.

Сами по себе не rewardable:

```text
BUTTON_SELECTION
SHOW_ANSWER
QUESTION_EXPOSURE
TIME_SPENT
RESPONSE_SPEED
SESSION_OPEN
SESSION_SPLIT
DECK_OPEN
DASHBOARD_OPEN
CONFIGURED_REVIEW_LIMITS
CONFIGURED_NEW_CARD_LIMITS
BACKLOG_SIZE
CARD_COUNT
NOTE_COUNT
SCHEDULER_PRESET_CHOICE
TIMEZONE_CHANGE
CLOCK_CHANGE
PLANNED_REST
STREAK_VALUE
MOMENTUM_VALUE
LEVEL_VALUE
IMPORT_VOLUME
MANUAL_RESET
RAW_EVENT_COUNT
CALENDAR_DAY_BOUNDARY
ANKI_APPLICATION_IDLE_TIME
```

`CARD_COUNT`, `NOTE_COUNT`, `CONFIGURED_NEW_CARD_LIMITS` и `IMPORT_VOLUME` не могут использоваться для обходного восстановления Create XP.

## 6. Productive-day boundary

Заморожено:

- productive day строится из bounded eligible domain signals;
- raw event count и time spent не равны productivity;
- маленький legitimate day не считается автоматически неудачным;
- intensive legitimate day не должен быть полностью обнулён;
- extreme volume не должен линейно ломать progression;
- Anki day, calendar day и session являются разными axes;
- session splitting не должно повышать contribution;
- exact cap, compression, threshold и mathematical function не выбраны.

## 7. Level boundary

```text
level = presentation of cumulative bounded progression
level != mastery
level != certification
level does not modify scheduler/FSRS
```

Accumulated research progression не становится отрицательной. Level progression monotonic внутри одной versioned economy. Migration/versioning относится к G5. Exact level curve и thresholds не выбраны.

## 8. Streak и planned rest

```text
streak growth
!= streak preservation
!= XP
!= Momentum
```

Заморожено:

- planned rest не ломает streak;
- planned rest не увеличивает streak;
- planned rest не даёт XP;
- planned rest не создаёт progression debt;
- tiny token action не обязана считаться productive day;
- streak не требует учёбы каждый calendar day;
- streak не является direct XP multiplier;
- absence не создаёт negative XP debt.

Не выбраны threshold, grace, reset, rest quota, advance planning, weekly schedule, timezone policy и UI. Planned rest не является premium resource, consumable freeze или reward.

## 9. Momentum и recovery

`Momentum`:

- bounded indicator текущего учебного ритма;
- non-spendable;
- не создаёт recursive positive feedback;
- не умножает XP напрямую;
- explainable и decomposable;
- не считает planned rest автоматически negative activity;
- не имеет выбранных window, range, decay или formula.

`Recovery`:

- не отнимает accumulated level;
- не создаёт цикл `уйти → вернуться → получить больше`;
- не использует backlog как reward multiplier;
- не требует погашения XP debt;
- не имеет выбранной bonus/shape policy;
- не поддерживает claims о motivation или retention.

## 10. Personas

G4.1 фиксирует только synthetic persona classes. Exact traces создаются не раньше G4.2.

| Persona | Назначение | Fairness risk | Почему raw volume недостаточен |
|---|---|---|---|
| `BEGINNER_HEAVY` | Early study с высокой Learn share и малой Review base. | Learn-heavy normalization может доминировать или обесцениваться. | New-material count не доказывает confirmed learning. |
| `MATURE_DECK` | Mature collection с преимущественно Review work. | Review-heavy workflow может быть наказан Learn-centric economy. | Due volume может быть legitimate maintenance или backlog. |
| `BALANCED` | Mixed Review и Learn activity. | Conversion может double-count или привилегировать домен. | Similar raw totals скрывают разные bounded contributions. |
| `BACKLOG_RETURNER` | Legitimate return к accumulated due work. | Backlog может стать multiplier или penalty. | Volume не отличает farming от обычного return. |
| `LOW_VOLUME_CONSISTENT` | Малый, но регулярный legitimate study. | Threshold может стереть meaningful low-volume work. | Низкий volume может содержать valid signals. |
| `INTENSIVE_LEARNER` | Legitimate high-intensity Learn day. | Cap может стереть работу, flooding — раздуть её. | New-card count не отличает confirmation от exposure. |
| `ALTERNATING_INTENSIVE_LIGHT` | Чередование heavy/light legitimate days. | Streak/Momentum могут наказывать natural variance. | Average/raw total скрывают day-shape fairness. |
| `PLANNED_REST_SCHEDULE` | Schedule с intentional rest days. | Daily pressure может наказывать planned rest. | Zero activity в rest day не является failure. |
| `IRREGULAR_LEGITIMATE` | Non-uniform legitimate study. | Calendar/recovery могут создать permanent disadvantage. | Irregular volume не доказывает manipulation. |

## 11. Threat taxonomy

Это synthetic threat model; он не утверждает, что реальные пользователи применяют перечисленные strategies. G4.2 должна определить deterministic traces. Hard-gate failure нельзя компенсировать aggregate score.

| Threat | Protected principle | Required G4.2 trace |
|---|---|---|
| `DOMAIN_IMBALANCE` | Normalize domains без hidden Review winner. | `TRACE-DOMAIN-IMBALANCE` |
| `RAW_VOLUME_FARMING` | Bounded eligible signals вместо raw count. | `TRACE-RAW-VOLUME-FARMING` |
| `BACKLOG_FARMING` | Backlog size не multiplier. | `TRACE-BACKLOG-FARMING` |
| `NEW_MATERIAL_FLOODING` | Только confirmed bounded Learn signal. | `TRACE-NEW-MATERIAL-FLOODING` |
| `SESSION_SPLIT_FARMING` | Session grouping contribution-neutral. | `TRACE-SESSION-SPLIT-FARMING` |
| `CALENDAR_BOUNDARY_FARMING` | Anki day, calendar day и session разделены. | `TRACE-CALENDAR-BOUNDARY-FARMING` |
| `CONFIGURATION_FARMING` | Settings — context, не price. | `TRACE-CONFIGURATION-FARMING` |
| `ANSWER_BEHAVIOR_FARMING` | Buttons — evidence, не direct prices; honest Again protected. | `TRACE-ANSWER-BEHAVIOR-FARMING` |
| `STREAK_PRESSURE` | Growth, preservation, XP и Momentum разделены. | `TRACE-STREAK-PRESSURE` |
| `PLANNED_REST_EXPLOIT` | Rest neutral, не reward. | `TRACE-PLANNED-REST-EXPLOIT` |
| `RECOVERY_BONUS_LOOP` | Return не создаёт bonus/debt cycle. | `TRACE-RECOVERY-BONUS-LOOP` |
| `MOMENTUM_SNOWBALL` | Momentum bounded и не recursive multiplier. | `TRACE-MOMENTUM-SNOWBALL` |
| `UNCERTAINTY_COLLAPSE` | Оба Review candidates сохраняются. | `TRACE-UNCERTAINTY-COLLAPSE` |
| `EXPLANATION_OPACITY` | Domain/day contribution decomposable. | `TRACE-EXPLANATION-OPACITY` |

`UNCERTAINTY_COLLAPSE` означает скрытое использование одного Review candidate как истины. `EXPLANATION_OPACITY` означает невозможность разложить progression на понятные contributions.

## 12. Protected invariants

Machine contract замораживает 28 non-negotiable invariants:

```text
INV-G3-CREATE-XP-EXCLUDED
INV-REVIEW-UNCERTAINTY-PRESERVED
INV-LEARN-LIMITATION-PRESERVED
INV-SCHEDULER-UNCHANGED
INV-FSRS-UNCHANGED
INV-DUE-DATES-UNCHANGED
INV-NO-DIRECT-BUTTON-PRICING
INV-HONEST-AGAIN-NOT-PUNISHED
INV-NO-RESPONSE-TIME-REWARD
INV-NO-TIME-SPENT-REWARD
INV-NO-SESSION-SPLIT-GAIN
INV-NO-BACKLOG-SIZE-GAIN
INV-NO-NEW-MATERIAL-FLOOD-GAIN
INV-NO-CONFIGURATION-GAIN
INV-XP-NONNEGATIVE
INV-LEVEL-MONOTONIC
INV-PLANNED-REST-NEUTRAL
INV-NO-ABSENCE-XP-DEBT
INV-RECOVERY-NO-BONUS-LOOP
INV-STREAK-NO-XP-MULTIPLIER
INV-MOMENTUM-BOUNDED-NONSPENDABLE
INV-MOMENTUM-NO-RECURSIVE-MULTIPLIER
INV-DETERMINISTIC-REPLAY
INV-DECOMPOSABLE-EVIDENCE
INV-EXPLAINABLE-CONTRIBUTIONS
INV-RESEARCH-ONLY
INV-NO-REAL-USER-DATA
INV-NO-PRODUCTION-APPROVAL
```

Каждый invariant имеет threat/persona/G4.2 coverage. Invariants не выбирают numeric policy и не создают production implementation.

## 13. Fairness boundary

Future candidate economy проверяется минимум на:

```text
BEGINNER_VS_MATURE_DECK
REVIEW_HEAVY_VS_LEARN_HEAVY
LOW_VOLUME_CONSISTENCY
LEGITIMATE_INTENSIVE_STUDY
ALTERNATING_INTENSIVE_LIGHT
PLANNED_REST_SCHEDULE
BACKLOG_RETURN
IRREGULAR_LEGITIMATE_SCHEDULE
BOTH_REVIEW_CANDIDATES_SENSITIVITY
```

Fairness означает отсутствие systematic exploit или devaluation legitimate workflow. Equal XP между personas не требуется. Hard fairness failure не компенсируется средним aggregate score.

## 14. Privacy и security

Разрешены только synthetic identifiers, personas и traces.

Запрещены:

```text
real card text
note fields
media
profile paths
usernames
tokens
raw revlog
private absolute paths
identifiable learning history
real user personas
remote AI scoring
cloud upload of study data
```

Не меняются loopback boundary, token validation, sanitizer, media validation, action allowlists и frontend collection access boundary.

G4 research остаётся вне add-on runtime, dashboard, Fast CI package, `.ankiaddon`, release и telemetry.

## 15. Claims boundary

Разрешено утверждать только:

- G4.1 prospectively определил problem и boundaries;
- G3/Create XP исключён из initial economy;
- Review uncertainty и Learn limitation сохранены;
- personas, threats и invariants перечислены;
- contract/schema прошли validation;
- production surfaces не изменены.

Запрещено утверждать:

```text
economy balanced
economy optimal
users will be more motivated
retention will improve
streak improves discipline
Momentum improves consistency
one Review candidate is superior
exact ratio is correct
level measures knowledge
candidate production-ready
all gaming prevented
```

## 16. Unresolved selections

G4.1 намеренно не выбирает:

```text
Review winner: NONE
Review/Learn conversion ratio: NONE
normalized XP amount: NONE
daily cap / soft cap: NONE
diminishing-return function: NONE
productive-day threshold: NONE
level curve / level count: NONE
streak threshold / grace: NONE
planned-rest quota: NONE
Momentum formula / range / decay: NONE
recovery bonus or shape: NONE
persona traces: NOT_DEFINED
candidate families: NOT_DEFINED
screening matrix: NOT_DEFINED
simulation seed: NONE
production storage/API/UI: NOT_DESIGNED
```

## 17. Allowed final G4 outcomes

G4.1 замораживает ровно три outcomes и не выбирает ни один:

| Outcome | Semantics |
|---|---|
| `RECOMMEND_CORE_ECONOMY_RESEARCH_MODEL` | Разрешает bounded research recommendation; не означает production readiness/approval. |
| `DEFER_CORE_ECONOMY_MODEL` | Viable inputs/models остаются, но evidence недостаточно для non-arbitrary recommendation. |
| `REJECT_CORE_ECONOMY_MODEL` | Только evidence-supported fundamental invalidity, а не просто missing data. |

## 18. G4.2 entry contract

```text
G4.2 — Input normalization and uncertainty model
NEXT / NOT STARTED
```

G4.2 обязана:

1. сохранить `P-STEP-ZERO` и `P-TAPER-ZERO-30D` как explicit uncertainty axis;
2. не выбирать Review winner без prospective cross-domain criterion;
3. сохранить Learn candidate и `CONFIRMATORY_INCONCLUSIVE` limitation;
4. определить typed domain input и contribution records;
5. определить common normalization interface без production amount или ratio;
6. формализовать daily aggregation boundary;
7. разделить Anki day, calendar day и session;
8. определить fail-closed missing/ambiguous/conflicting behavior;
9. определить synthetic persona descriptors без exact traces;
10. определить deterministic fixture requirements;
11. определить, как G4.3 сможет ввести candidate families;
12. не выбирать ratio, productive-day threshold, level/streak/Momentum/recovery formulas;
13. не запускать simulation и не создавать screening matrix;
14. не менять production surfaces.

Entry blockers:

```text
invalid G4.1 contract or schema
missing required registry
Review uncertainty collapsed
Learn limitation removed
Create XP included
numeric economy policy preselected
real user data or production integration required
```

G4.2 не начат этим этапом.

## 19. Production boundary

```text
production approved: NO
production integration: PROHIBITED
review winner selected: NO
conversion ratio selected: NO
numeric economy model selected: NO
candidate registry created: NO
screening matrix created: NO
simulation executed: NO
G4.2 started: NO
```

G4.1 не меняет production runtime, dashboard, API, scheduler, FSRS, database, package, workflows или release.
