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
- 22 расчётных и классификационных примера.

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
Review Session and Day Aggregation     ← следующий этап
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
anki-review-session-and-day.md
```

Он должен определить:

1. границы `Review Session`;
2. агрегацию нескольких сессий в один Anki-день;
3. сумму `core`, `support` и `supplemental` units;
4. количество уникальных карточек и уникальных эпизодов;
5. нужен ли volume bonus;
6. нужен ли бонус за закрытие due queue;
7. как избежать второго слоя anti-grind поверх episode-level safeguards;
8. минимальный, частичный и полноценный Review-день;
9. поведение при backlog;
10. поведение при нулевой due queue;
11. взаимодействие с будущим стриком;
12. дневные caps и diminishing returns;
13. защиту длинной честной сессии от чрезмерного обесценивания;
14. explainability итоговой награды за день.

Главное ограничение следующего этапа:

> Дневная агрегация не должна повторно штрафовать работу, которая уже прошла event taxonomy, reward model и abuse safeguards.

## Иерархия решений

При пересечении документов действует правило:

```text
более новый детальный документ
→ уточняет профильный foundation
→ профильный foundation
→ общий Progression Foundation
```

В частности:

- `anki-review-event-taxonomy.md` определяет право события участвовать в Review XP;
- `anki-review-reward-model.md` определяет относительную стоимость допустимого эпизода;
- `anki-review-abuse-model.md` определяет допустимые ограничения и уточняет применение validity-сигналов;
- ранние формулы из `anki-xp-foundation.md` не применяются, если детальная спецификация уже приняла другое решение.

### Уточнение Reward Model третьим этапом

Abuse Model разделяет:

```text
BaselineCredit
и
ContextBonus
```

Эвристический сигнал не должен автоматически умножать вниз всю награду.

Только детерминированно неучебное, отменённое или повторно обработанное событие может потерять baseline. Неоднозначное событие сохраняет базовую учебную награду и при необходимости теряет только контекстный бонус.

## Правила развития документации

- Один крупный предмет проектирования — один отдельный документ.
- Общие решения не дублируются полностью в каждом файле; используются ссылки.
- Числовая гипотеза не становится правилом до симуляции.
- Сначала определяется валидное событие, затем его стоимость.
- Product concept не смешивается с production implementation.
- Новая механика не должна подталкивать к ухудшению реального обучения ради XP.
- Anti-abuse не должен разрушать базовую награду честного пользователя.
- Одна слабая эвристика не может обнулить core reward.
- Несколько safeguards не должны повторно штрафовать одно событие за одну причину.
- Неопределённость должна ограничивать bonus раньше, чем baseline.
- Внешняя документация Anki и FSRS используется для проверки фактов, а не как готовый дизайн игровой экономики.
- При противоречии более детальный и новый документ уточняет общий foundation, но изменение должно быть явно отражено в индексах и версиях.
- Примеры внутри спецификаций являются обязательной частью проверки понятности модели.
- Формула должна быть не только вычислимой, но и объяснимой пользователю через reward breakdown.
- Каждая контрмера обязана проходить симуляцию честных edge cases вместе с exploit-сценариями.