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
- граница будущего пакета `research/gamification-sim/`;
- явный запрет интеграции этапа 5A в fast CI и существующие workflows.

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
Stage 5B.2: Scenario Runner            ← следующий возможный research-подэтап
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
10. локальный CLI для проверки fixtures.

Статус 5B.1 подтверждает соответствие реализации текущей исследовательской спецификации. Он не объявляет формулы или числовые параметры утверждённой production-экономикой.

### Изоляция и CI

```text
Stage 5B.1
→ local/manual execution
→ отдельное environment
→ не импортирует production-модули
→ не входит в add-on build или .ankiaddon
→ не входит в production verification chain
→ не меняет Fast CI, Full CI или release workflows
```

Возможное подключение отдельной research-проверки рассматривается только позднее, после измерения времени выполнения и отдельного одобрения. Fast CI не должен автоматически получать simulator job.

### Следующий возможный этап

```text
Stage 5B.2 — deterministic scenario runner
```

Он может добавить structured multi-day scenarios и controls. Parameter sweep, Monte Carlo, synthetic populations, FSRS adapter и real-history replay требуют последующих отдельных решений.

## Иерархия решений

При пересечении документов действует правило:

```text
anki-review-simulation-spec.md
→ anki-review-session-and-day.md
→ anki-review-abuse-model.md
→ anki-review-reward-model.md
→ anki-review-event-taxonomy.md
→ anki-xp-foundation.md
→ progression-foundation.md
```

Более новый детальный документ уточняет более общий.

В частности:

- `anki-review-event-taxonomy.md` определяет право события участвовать в Review XP;
- `anki-review-reward-model.md` определяет относительную стоимость допустимого эпизода;
- `anki-review-abuse-model.md` определяет допустимые ограничения и уточняет применение validity-сигналов;
- `anki-review-session-and-day.md` определяет дневную агрегацию, caps и дополнительные бонусы;
- `anki-review-simulation-spec.md` определяет, как проверяются все предыдущие решения и по каким gates выбирается модель;
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

### Приоритет hard gates этапа 5A

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
- Числовая гипотеза не становится финальным правилом до симуляции.
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
- Stage 5B.1 не меняет fast CI, full CI, workflows или verification scripts.
- Внешняя документация Anki и FSRS используется для проверки фактов, а не как готовый дизайн игровой экономики.
- При противоречии более детальный и новый документ уточняет общий foundation, но изменение должно быть явно отражено в индексах и версиях.
- Примеры внутри спецификаций являются обязательной частью проверки понятности модели.
- Формула должна быть не только вычислимой, но и объяснимой пользователю через reward breakdown.
- Каждая контрмера обязана проходить симуляцию честных edge cases вместе с exploit-сценариями.
