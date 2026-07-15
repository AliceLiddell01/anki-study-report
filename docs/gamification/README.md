# Gamification Concept Documentation

Статус: **рабочий индекс концепта**  
Дата: **2026-07-16**  
Область: **самостоятельное проектирование системы игрофикации до интеграции в Anki Study Report**

## Назначение папки

Эта папка изолирует продуктовую и исследовательскую документацию будущей системы игрофикации от основной документации уже реализованного Anki Study Report.

Документы здесь описывают концепт, гипотезы, формулы и будущие правила. Они не означают, что соответствующая функциональность уже реализована или включена в production dashboard.

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
- целевая структура экономики Anki XP.

Текущий статус: **DRAFT v0.1**.

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

## Принятый порядок проектирования

```text
Progression Foundation
        ↓
Anki XP Foundation
        ↓
Review Event Taxonomy                  ← текущий завершённый концептуальный этап
        ↓
Review Reward Model                    ← следующий этап
        ↓
Review Abuse Model
        ↓
Review Session and Day Aggregation
        ↓
Review Simulation Specification
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

## Следующий документ

Планируемый файл:

```text
anki-review-reward-model.md
```

Он должен определить относительную стоимость одного валидного `core` Review Episode и последовательно проработать:

1. `RetrievalChallengeFactor`;
2. `OutcomeFactor`;
3. `MemoryGainFactor`;
4. `DifficultyFactor`;
5. `ResponseValidityFactor`;
6. contextual modifiers;
7. caps и взаимодействие коэффициентов.

Первой подзадачей является функция:

```text
Retrievability before answer
→ Retrieval Challenge reward
```

## Правила развития документации

- Один крупный предмет проектирования — один отдельный документ.
- Общие решения не дублируются полностью в каждом файле; используются ссылки.
- Числовая гипотеза не становится правилом до симуляции.
- Сначала определяется валидное событие, затем его стоимость.
- Product concept не смешивается с production implementation.
- Новая механика не должна подталкивать к ухудшению реального обучения ради XP.
- Внешняя документация Anki и FSRS используется для проверки фактов, а не как готовый дизайн игровой экономики.
- При противоречии более детальный и новый документ уточняет общий foundation, но изменение должно быть явно отражено в индексах и версиях.
