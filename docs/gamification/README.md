# Gamification Concept Documentation

Статус: **рабочий индекс концепта и исследовательской реализации**  
Дата: **2026-07-16**  
Область: **самостоятельное проектирование системы игрофикации до интеграции в Anki Study Report**

## Назначение папки

Эта папка изолирует продуктовую и исследовательскую документацию будущей системы игрофикации от основной документации уже реализованного Anki Study Report.

Документы здесь описывают концепт, гипотезы, формулы, экспериментальные критерии и будущие правила. Наличие исследовательского симулятора не означает, что соответствующая функциональность уже реализована или включена в production dashboard, а его числовые параметры не являются production-ready.

## Текущие документы

### 1. [Progression Foundation](progression-foundation.md)

Общий фундамент системы:

- уровни и постоянный XP;
- стрик;
- `Momentum`;
- запланированный отдых;
- `Streak Guard`;
- пропуски, санкции и восстановление;
- общие anti-grind принципы;
- первая гипотеза кривой уровней.

Текущий статус: **DRAFT v0.2**.

### 2. [Anki XP Foundation](anki-xp-foundation.md)

Первый домен системы — полезная работа в Anki:

- `Review XP`;
- `Learn XP`;
- `Create XP`;
- `Immediate XP` и `Pending XP`;
- общие FSRS-сигналы;
- защита от повторяемых дешёвых действий;
- целевая структура экономики Anki XP;
- ссылки на детальные Review-спецификации.

Текущий статус: **DRAFT v0.2**.

### 3. [Anki Review Event Taxonomy](anki-review-event-taxonomy.md)

Первый детальный этап Review XP:

- `Review Episode` как награждаемая единица;
- разделение `core`, `support`, `supplemental`, `none` и `route_to_learn`;
- due, overdue, early, filtered, preview и forced-due scenarios;
- связь первичного `Again` с relearning;
- ручные операции, Undo и FSRS-rescheduling;
- siblings;
- отсутствие надёжных FSRS-данных;
- старая и импортированная история;
- нормализованная модель эпизода;
- дедупликация и explainability.

Текущий статус: **DRAFT v0.1**.

### 4. [Anki Review Reward Model](anki-review-reward-model.md)

Второй детальный этап Review XP:

- `Review Unit` как промежуточная единица;
- ограниченная аддитивная формула вместо мультипликативной;
- `AttemptCredit` и `OutcomeCredit`;
- challenge curve по `Retrievability`;
- защита от backlog farming;
- counterfactual `Good` для memory gain;
- отказ от отдельного `DifficultyFactor`;
- время ответа как validity-сигнал;
- fallback без FSRS;
- support cap для relearning;
- explainability и версионирование;
- расчётные и классификационные примеры.

Текущий статус: **DRAFT v0.1**.

### 5. [Anki Review XP Abuse Model](anki-review-abuse-model.md)

Третий детальный этап Review XP:

- модель угроз для локальной системы;
- разделение deterministic и heuristic решений;
- `BaselineCredit` и `ContextBonus` как разные зоны воздействия;
- reward floor для честного core-review;
- идемпотентность и дедупликация;
- защита от relearning loop, early review и preview;
- forced due, reset и массовое FSRS-rescheduling;
- Reward Reference Policy для desired retention и presets;
- защита от backlog farming без наказания за возвращение;
- быстрые ответы, automation patterns и clock anomalies;
- duplicates, siblings, content drift и Custom Scheduling;
- Sync, imports, backups, Undo и lineage;
- принятый риск полного локального контроля;
- защита от накопления нескольких штрафов;
- пользовательские explainability-формулировки;
- acceptance criteria для сохранения честной экономики.

Ключевой инвариант этапа:

> Anti-abuse не должен ослаблять нормальную механику получения XP. Неоднозначный контекст прежде всего ограничивает дополнительный бонус, а не базовую награду за реальную учебную работу.

Текущий статус: **DRAFT v0.1**.

### 6. [Anki Review Session and Day Aggregation](anki-review-session-and-day.md)

Четвёртый детальный этап Review XP:

- `Anki Day` как экономическая единица;
- `Review Session` как аналитическая группировка;
- отсутствие session multipliers и reset-эксплойтов;
- полное сохранение `CoreBaseline` независимо от дневного объёма;
- `QualifiedVolume` без повторного учёта context bonus;
- аддитивный прогрессивный `VolumeCredit` с cap;
- дневные caps для support и supplemental work;
- `Workload Snapshot`;
- locked completion scope;
- `collection_cleared`, `scope_cleared`, `configured_limit_reached`, `partial` и `zero_due`;
- небольшой пропорциональный `CompletionCredit`;
- нейтральный zero-due day;
- review contribution bands;
- late sync reconciliation;
- derived transactions;
- подробные сценарии и acceptance criteria.

Ключевой инвариант этапа:

> Каждое подтверждённое уникальное core-повторение сохраняет полную базовую награду. Diminishing returns и caps применяются только к дополнительным бонусам, support и supplemental channels.

Текущий статус: **DRAFT v0.1**.

### 7. [Anki Review Simulation Specification](anki-review-simulation-spec.md)

Этап 5A — спецификация проверки Review XP до реализации:

- разделение `5A Specification` и `5B Research Simulator`;
- нормализованные inputs, независимые от Anki runtime;
- deterministic examples и hard invariants;
- structured scenario matrix;
- parameter sweep и sensitivity analysis;
- seeded Monte Carlo personas;
- optional sanitized real-history replay;
- ordinary, edge-case и abuse scenarios;
- обязательные exploit controls;
- correctness, reward, fairness и abuse-resistance metrics;
- quantitative acceptance criteria;
- reward-cliff analysis;
- reproducibility manifest;
- формат simulation report;
- Pareto shortlist вместо одного общего score;
- privacy requirements для реальных данных;
- граница пакета `research/gamification-sim/`;
- явный запрет неявной интеграции research-задач в Fast CI и существующие workflows.

Ключевой инвариант этапа:

> Вариант формулы не проходит дальше, если он лучше подавляет abuse ценой потери baseline честного review, нарушения session invariance или ухудшения fairness.

Текущий статус: **DRAFT v0.1**.

## Принятый порядок проектирования

```text
Progression Foundation
        ↓
Anki XP Foundation
        ↓
Review Event Taxonomy                  ← завершённый концептуальный этап
        ↓
Review Reward Model                    ← завершённый концептуальный этап
        ↓
Review Abuse Model                     ← завершённый концептуальный этап
        ↓
Review Session and Day Aggregation     ← завершённый концептуальный этап
        ↓
Stage 5A: Simulation Specification     ← завершённый концептуальный этап
        ↓
Stage 5B.1: Deterministic Core         ← реализованный research-подэтап
        ↓
Stage 5B.2: Scenario Runner            ← реализованный research-подэтап
        ↓
Stage 5B.3: Parameter Sweep Design     ← следующий возможный research-подэтап
        ↓
Learn XP Specification
        ↓
Create XP Specification
        ↓
Anki Day and Streak Specification
        ↓
Full Economy Calibration
        ↓
Skills, achievements, quests, rewards and UI
```

## Research Simulator

### Stage 5B.1 — Pure Deterministic Review Simulator Core

Подэтап реализован в отдельном пакете:

```text
research/gamification-sim/
```

Реализованы:

1. отдельный Python package с `src/` layout и собственным `pyproject.toml`;
2. нормализованные immutable input/output models;
3. версионированный кандидатный parameter set `review-v0.1`;
4. pure episode reward model;
5. deterministic Abuse safeguards;
6. Session and Day Aggregation;
7. explainable episode/day breakdown;
8. executable golden cases;
9. автоматические проверки hard invariants `H01–H18`;
10. локальный CLI для проверки fixtures;
11. strict non-coercing integer validation;
12. единый versioned источник support reward по `SupportKind`.

Статус 5B.1 подтверждает соответствие реализации текущей исследовательской спецификации. Он не объявляет формулы или числовые параметры утверждённой production-экономикой.

### Stage 5B.2 — Deterministic Scenario Runner

Подэтап реализован поверх чистого ядра 5B.1 без копирования reward-формул.

Реализованы:

1. локальная JSON Schema Draft 2020-12 `review-scenario-v0.1`;
2. strict UTF-8 JSON loader с запретом BOM, duplicate keys, `NaN` и infinities;
3. schema validation через `Draft202012Validator.check_schema()` и `iter_errors()`;
4. отдельная domain validation для версий, порядка дней, уникальности и controls;
5. immutable typed models для scenarios, days, sessions, assertions, comparisons и manifests;
6. последовательности нескольких Anki-дней;
7. аналитические sessions, сворачиваемые в единый `ReviewDayInput` без session multipliers;
8. выполнение каждого дня через существующий `aggregate_day()`;
9. allowlisted assertions без `eval`, `exec`, arbitrary JSONPath и пользовательского кода;
10. matched control comparisons с component deltas, ratios и compatibility warnings;
11. canonical JSON и SHA-256 digests;
12. deterministic JSON и Markdown reports;
13. script-friendly CLI с фиксированными exit codes;
14. committed corpus из 26 deterministic scenarios;
15. автоматические tests strict loader, schema, domain rules, assertions, controls, reports, digests, CLI и всего corpus.

Corpus включает:

```text
ordinary:   6
edge:       7
control:    6
abuse:      6
regression: 1
```

Каждый committed abuse scenario имеет содержательный control.

Stage 5B.2 доказывает воспроизводимое выполнение заявленного deterministic corpus и проверку текущих contracts. Он не завершает population calibration и не делает simulator или `review-v0.1` production-ready.

### Stage 5B.3 — Parameter Sweep and Sensitivity Engine

Подэтап реализован как ограниченный последовательный поиск, а не полный
Cartesian product. `review-v0.1` сохранён без числовых изменений.

Реализованы:

1. typed catalog из 17 versioned candidates с полным parameter snapshot и digest;
2. явная передача `RewardParameterSet` в scenario runner;
3. strict Draft 2020-12 contract `review-sweep-v0.1`;
4. последовательность Reward → Volume → Completion → Support → Supplemental;
5. верхний budget на число evaluated candidates;
6. H01–H18, deterministic digest и component/cap gates до ranking;
7. reason codes для каждого rejected candidate;
8. correctness, reward, bonus, fairness, abuse и complexity metrics;
9. quantitative gates из simulation specification без изменения порогов;
10. nondominated Pareto front без единого aggregate score;
11. deterministic one-at-a-time sensitivity по 13 explicit grids;
12. автоматические `threshold ± epsilon` reward-cliff probes;
13. gitignored report set для локального анализа.

Первый sweep является исследовательским сравнением committed corpus. Он не
утверждает production-экономику и не заменяет property-based, population,
cross-language или FSRS-reference gates следующих подэтапов.

### Stage 5B.4 — Property-based invariants and cliffs

Hypothesis добавлен только в research test extra. Reproducible profile отключает
persistent example database и использует derandomized generation без machine
time, external state или global random. Properties покрывают H01–H18 для
`review-v0.1` и финального shortlist overlay, а также invalid `NaN`/infinity,
negative и bool-as-int values, duplicate JSON keys, unknown enums, unsorted days,
non-monotonic anchors и negative caps.

`RewardParameterSet` теперь проверяет ranges, enum maps, monotonic anchors и
volume tiers при создании. Некорректные candidates отклоняются, а не
исправляются автоматически.

### Stage 5B.5 — Seeded synthetic personas and population

Добавлен strict `review-persona-v0.1` catalog из 16 synthetic classes. Profiles
содержат только model inputs и не включают тексты карточек, deck names,
collection content, personal identifiers или реальные histories.

Generator создаёт нормализованные `ReviewDayInput`/`ReviewEpisodeInput`, после
чего вызывает единственный reward core 5B.1. Child seeds выводятся SHA-256 из
master seed, persona ID и replica; каждая траектория использует собственный
`random.Random`, без global random state.

Режимы:

- development — 480 persona-days;
- standard — 584 000 persona-days;
- long — примерно 1,098 млн persona-days, только по explicit request;
- long `--smoke` — 112 persona-days для проверки пути без полного stress run.

Отчёт сохраняет distributions, tails, bonus shares, baseline preservation,
fairness matrix и matched abuse/control comparisons. Unsupported lifetime/FSRS
trajectory concepts отмечаются `deferred` без вымышленных placeholder metrics.

### Stage 5B.6 — Rust deterministic verification oracle

В `research/gamification-sim/rust-oracle/` добавлена независимая реализация
deterministic episode/day subset. Process boundary — только UTF-8 JSONL;
отсутствуют PyO3, FFI, shared libraries, production imports и build/CI wiring.

Differential runner сравнивает every component и ordered reason codes с
tolerance `1e-9`, классифицируя exact, within-tolerance, semantic mismatch и
unsupported cases. Corpus охватывает 31 golden cases, все 26 scenario files,
threshold triplets, Stage 5B.3 survivors, фиксированные property edges и
invalid-input rejection parity.

### Stage 5B.7 — FSRS reference comparison

Optional research extras фиксируют официальный `py-fsrs 6.3.1` и официальный
crate `open-spaced-repetition/fsrs-rs 6.6.1`. Они не входят в deterministic core,
production runtime или add-on package.

Versioned UTC corpus содержит 10 synthetic trajectories. Сравниваются
retrievability, stability, difficulty, scheduled interval, counterfactual Good
state и normalized serialized trajectory. `f64`/`f32` state tolerance задан как
`1e-4`; различие learning/relearning step scheduler в py-fsrs и model interval
из `fsrs-rs::next_states` документируется отдельно и не объявляется defect.

Reward integration отдельно подтверждает одинаковый `CoreBaseline` для
high-confidence, low-confidence, no-FSRS fallback и backlog natural-due context.

### Изоляция и CI

```text
Stage 5B.1 + Stage 5B.2 + Stage 5B.3 + Stage 5B.4 + Stage 5B.5 + Stage 5B.6 + Stage 5B.7
→ local/manual execution
→ отдельное environment
→ не импортируют production-модули
→ не входят в add-on build или .ankiaddon
→ не входят в production verification chain
→ не меняют Fast CI, Full CI или release workflows
→ generated outputs остаются gitignored
```

Подключение отдельной research-проверки возможно только после отдельного решения. Fast CI не должен автоматически получать simulator job.

### Следующий возможный этап

```text
Stage 5B.3 — parameter sweep and sensitivity design
```

Он может определить ограниченные parameter families, sweep contract, sensitivity metrics и gates. Monte Carlo, synthetic populations, FSRS adapter и real-history replay требуют последующих отдельных решений и не начинаются автоматически.

## Иерархия решений

При пересечении документов действует правило:

```text
актуальный simulator code и tests
→ anki-review-simulation-spec.md
→ anki-review-session-and-day.md
→ anki-review-abuse-model.md
→ anki-review-reward-model.md
→ anki-review-event-taxonomy.md
→ anki-xp-foundation.md
→ progression-foundation.md
```

Более новый детальный документ уточняет более общий.

В частности:

- актуальный simulator code и tests задают фактически реализованный research-contract;
- `anki-review-event-taxonomy.md` определяет право события участвовать в Review XP;
- `anki-review-reward-model.md` определяет относительную стоимость допустимого эпизода;
- `anki-review-abuse-model.md` определяет допустимые ограничения и уточняет применение validity-сигналов;
- `anki-review-session-and-day.md` определяет дневную агрегацию, caps и дополнительные бонусы;
- `anki-review-simulation-spec.md` определяет, как проверяются предыдущие решения и по каким gates выбирается модель;
- ранние формулы из `anki-xp-foundation.md` и `progression-foundation.md` не применяются, если детальная спецификация уже приняла другое решение.

### Уточнение Reward Model третьим этапом

Abuse Model разделяет:

```text
BaselineCredit
и
ContextBonus
```

Эвристический сигнал не должен автоматически умножать вниз всю награду.

Только детерминированно неучебное, отменённое или повторно обработанное событие может потерять baseline. Неоднозначное событие сохраняет базовую учебную награду и при необходимости теряет только контекстный бонус.

### Уточнение общего diminishing returns четвёртым этапом

Ранняя гипотеза глобального дневного envelope не применяется к `Review CoreBaseline`.

```text
Review CoreBaseline
→ сохраняется полностью;

Volume, Completion, Support и Supplemental
→ имеют собственные ограниченные правила;

будущий combined-domain envelope
→ не должен повторно уменьшать подтверждённую базовую review-работу.
```

Окончательная междоменная политика будет выбрана после Review simulation и проектирования Learn/Create XP.

### Приоритет hard gates этапов 5A–5B

Средний результат симуляции не может оправдать нарушение инварианта.

```text
hard invariant violation
→ parameter set отклоняется;

baseline loss у честного core-review
→ parameter set отклоняется;

session split изменяет XP
→ parameter set отклоняется;

duplicate или replay создаёт дополнительный XP
→ parameter set отклоняется.
```

Только после hard gates сравниваются fairness, bonus shares, sensitivity и exploit ratios.

## Правила развития документации

- Один крупный предмет проектирования — один отдельный документ.
- Общие решения не дублируются полностью в каждом файле; используются ссылки.
- Числовая гипотеза не становится финальным правилом до симуляции и калибровки.
- Сначала определяется валидное событие, затем его стоимость, дневная агрегация и только потом экспериментальная проверка.
- Product concept, research implementation и production implementation не смешиваются.
- Новая механика не должна подталкивать к ухудшению реального обучения ради XP.
- Anti-abuse не должен разрушать базовую награду честного пользователя.
- Одна слабая эвристика не может обнулить core reward.
- Несколько safeguards не должны повторно штрафовать одно событие за одну причину.
- Неопределённость должна ограничивать bonus раньше, чем baseline.
- Длинная честная работа не получает diminishing returns по базовому reward.
- Сессия не является способом сбросить дневные caps или повторно получить bonus.
- Completion не должен превращать микроколоды или искусственные scopes в выгодную стратегию.
- Simulation всегда сравнивает abuse-сценарий с содержательным control.
- Hard invariants имеют приоритет над средними метриками.
- Один общий optimization score не используется для выбора экономики.
- При сопоставимом качестве выбирается более простая и объяснимая модель.
- No-FSRS, low-confidence, small-collection и backlog-return входят в обязательную fairness matrix.
- Реальные пользовательские histories не коммитятся и не читаются напрямую из рабочей collection.
- Research simulator не входит в production runtime и `.ankiaddon`.
- Stage 5B.1 и Stage 5B.2 не меняют Fast CI, Full CI, workflows или production verification scripts.
- Generated scenario reports и local outputs не коммитятся.
- Внешняя документация Anki, Python, JSON Schema и FSRS используется для проверки фактов, а не как готовый дизайн игровой экономики.
- При противоречии более детальный и новый документ уточняет общий foundation, но изменение должно быть явно отражено в индексах и версиях.
- Примеры внутри спецификаций являются обязательной частью проверки понятности модели.
- Формула должна быть не только вычислимой, но и объяснимой пользователю через reward breakdown.
- Каждая контрмера обязана проходить симуляцию честных edge cases вместе с exploit-сценариями.
