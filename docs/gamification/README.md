# Gamification Concept Documentation

Статус: **рабочий индекс концепта и исследовательской реализации**  
Дата: **2026-07-16**  
Область: **самостоятельное проектирование системы игрофикации до интеграции в Anki Study Report**

## Назначение папки

Эта папка изолирует продуктовую и исследовательскую документацию будущей системы игрофикации от основной документации уже реализованного Anki Study Report.

Документы описывают концепт, гипотезы, формулы, экспериментальные критерии и будущие правила. Наличие исследовательского симулятора не означает, что соответствующая функциональность реализована в production dashboard или что числовые параметры признаны production-ready.

## Текущие документы

### 1. [Progression Foundation](progression-foundation.md)

Общий фундамент системы: уровни и постоянный XP, стрик, `Momentum`, запланированный отдых, `Streak Guard`, пропуски, восстановление, anti-grind принципы и первая гипотеза кривой уровней.

Текущий статус: **DRAFT v0.2**.

### 2. [Anki XP Foundation](anki-xp-foundation.md)

Первый домен системы: `Review XP`, `Learn XP`, `Create XP`, `Immediate XP`, `Pending XP`, общие FSRS-сигналы и защита от повторяемых дешёвых действий.

Текущий статус: **DRAFT v0.2**.

### 3. [Anki Review Event Taxonomy](anki-review-event-taxonomy.md)

Определяет `Review Episode`, классы `core`, `support`, `supplemental`, `none`, `route_to_learn` и `deferred`, а также due, overdue, early, filtered, preview, forced-due, Undo, manual и provenance scenarios.

Текущий статус: **DRAFT v0.1**.

### 4. [Anki Review Reward Model](anki-review-reward-model.md)

Определяет `Review Unit`, `AttemptCredit`, `OutcomeCredit`, retrieval challenge, backlog protection, counterfactual `Good` memory gain, model confidence, neutral no-FSRS fallback, support cap и explainable breakdown.

Текущий статус: **DRAFT v0.1**.

### 5. [Anki Review XP Abuse Model](anki-review-abuse-model.md)

Разделяет deterministic и heuristic safeguards, `BaselineCredit` и `ContextBonus`, защищает reward floor честного core-review и задаёт idempotency, duplicate, Undo, relearning, preview, forced-due и manual-operation правила.

Ключевой инвариант:

> Anti-abuse не должен ослаблять нормальную механику получения XP. Неоднозначный контекст прежде всего ограничивает дополнительный бонус, а не базовую награду за реальную учебную работу.

Текущий статус: **DRAFT v0.1**.

### 6. [Anki Review Session and Day Aggregation](anki-review-session-and-day.md)

Определяет `Anki Day`, аналитические sessions, полное сохранение `CoreBaseline`, `QualifiedVolume`, `VolumeCredit`, support/supplemental caps, `Workload Snapshot`, completion statuses, contribution bands, reconciliation и derived transactions.

Ключевой инвариант:

> Каждое подтверждённое уникальное core-повторение сохраняет полную базовую награду. Diminishing returns и caps применяются только к дополнительным бонусам, support и supplemental channels.

Текущий статус: **DRAFT v0.1**.

### 7. [Anki Review Simulation Specification](anki-review-simulation-spec.md)

Этап 5A задаёт normalized inputs, deterministic examples, hard invariants, scenario matrix, parameter families, synthetic personas, exploit controls, fairness metrics, acceptance criteria, reproducibility manifest и границу research-пакета.

Ключевой инвариант:

> Вариант формулы не проходит дальше, если он лучше подавляет abuse ценой потери baseline честного review, нарушения session invariance или ухудшения fairness.

Текущий статус: **DRAFT v0.1**.

## Research Simulator

### Stage 5B.1 — Pure Deterministic Review Simulator Core

Исследовательский подэтап реализован в:

```text
research/gamification-sim/
```

Пакет содержит:

1. отдельный Python package с `src/` layout;
2. нормализованные immutable input/output models;
3. версионированный parameter set `review-v0.1`;
4. pure episode reward model;
5. deterministic safeguards;
6. Session and Day Aggregation;
7. полный explainable breakdown;
8. executable golden cases;
9. проверки hard invariants `H01–H18`;
10. локальный CLI для проверки fixtures.

Статус 5B.1 означает только соответствие кода текущей исследовательской спецификации. Формулы и числовые параметры остаются кандидатами для симуляции, а не утверждённой production-экономикой.

### Изоляция 5B.1

Simulator:

- не импортирует production-модули add-on;
- не читается production-кодом;
- не входит в dashboard payload или API;
- не входит в bundled Python runtime;
- не попадает в `.ankiaddon`;
- не меняет root dependency manifests или lockfiles;
- не входит в Fast CI, Full CI, release workflows или verification scripts;
- запускается локально и вручную из собственного environment.

### Следующий возможный этап

```text
Stage 5B.2 — deterministic scenario runner
```

Он может добавить structured multi-day scenarios и controls, но не должен начинаться автоматически в рамках 5B.1. Parameter sweep, Monte Carlo, synthetic populations, FSRS adapter и real-history replay остаются за пределами 5B.2 до отдельных решений.

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

Более новый детальный документ уточняет более общий. Исследовательский код должен следовать этой иерархии и не менять формулы молча.

### Уточнение Reward Model третьим этапом

```text
BaselineCredit = AttemptCredit + Pass × OutcomeCredit
ContextBonus   = Pass × ContextCredit
```

Эвристический сигнал не должен автоматически уменьшать baseline. Только детерминированно неучебное, отменённое или повторно обработанное событие может потерять базовую награду.

### Уточнение diminishing returns четвёртым этапом

```text
Review CoreBaseline
→ сохраняется полностью;

Volume, Completion, Support и Supplemental
→ имеют собственные ограниченные правила;

будущий combined-domain envelope
→ не должен повторно уменьшать подтверждённую базовую review-работу.
```

### Приоритет hard gates

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

## Правила развития

- Один крупный предмет проектирования — один отдельный документ или research-подэтап.
- Числовая гипотеза не становится финальным правилом до симуляции и документированного решения.
- Product concept, research implementation и production implementation не смешиваются.
- Anti-abuse не должен разрушать базовую награду честного пользователя.
- Одна слабая эвристика не может обнулить core reward.
- Несколько safeguards не должны повторно применять одну причину ограничения.
- Отсутствие FSRS использует нейтральный context и не лишает базовой награды.
- Длинная честная работа не получает diminishing returns по `CoreBaseline`.
- Сессия не сбрасывает дневные caps и не создаёт bonus.
- Completion не должен превращать микроколоды или искусственные scopes в выгодную стратегию.
- Simulation сравнивает abuse-сценарий с содержательным control.
- Hard invariants имеют приоритет над средними метриками.
- При сопоставимом качестве выбирается более простая и объяснимая модель.
- Реальные пользовательские histories не коммитятся и не читаются напрямую из рабочей collection.
- Research simulator не входит в production runtime, build, `.ankiaddon` или существующий CI.
