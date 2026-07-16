# Anki Review Simulation Specification

Статус: **DRAFT v0.1**  
Дата: **2026-07-16**  
Область: **этап 5A проектирования Review XP; спецификация экспериментов без реализации симулятора и без интеграции в CI**

## 1. Назначение документа

Этот документ определяет, как проверить разработанную модель `Review XP` до появления production-реализации.

Он продолжает:

- [Anki Review Event Taxonomy](anki-review-event-taxonomy.md) — определяет, какие события являются `core`, `support`, `supplemental`, `none` или `deferred`;
- [Anki Review Reward Model](anki-review-reward-model.md) — определяет относительную стоимость одного допустимого `Review Episode`;
- [Anki Review XP Abuse Model](anki-review-abuse-model.md) — определяет допустимые safeguards и защищает базовую награду честного пользователя;
- [Anki Review Session and Day Aggregation](anki-review-session-and-day.md) — определяет сессии, дневную агрегацию, caps, volume и completion;
- [Anki XP Foundation](anki-xp-foundation.md) — задаёт общие инварианты домена Anki;
- [Progression Foundation](progression-foundation.md) — задаёт общий масштаб уровней и глобального XP.

Главный вопрос этапа 5A:

> Какие сценарии, данные, метрики и критерии должны использоваться, чтобы выбрать устойчивые параметры Review XP и одновременно доказать, что модель сохраняет награду честной работы, не создаёт выгодных exploit-стратегий и не ломается на обычных особенностях Anki?

Этап 5A является только спецификацией.

В рамках этого этапа:

- не создаётся `research/gamification-sim/`;
- не пишется код симулятора;
- не добавляются Python-зависимости;
- не добавляются workflow GitHub Actions;
- не изменяются fast CI и full CI;
- не добавляются команды в существующие verification scripts;
- не запускаются Monte Carlo или parameter sweep;
- не принимаются финальные числовые параметры экономики.

## 2. Разделение этапа 5

Работа разделяется на две самостоятельные части.

```text
Stage 5A — Simulation Specification

Документация:
- цели;
- модели входных данных;
- personas;
- сценарии;
- метрики;
- hard invariants;
- acceptance criteria;
- формат отчётов;
- границы будущего research-пакета.
```

```text
Stage 5B — Research Simulator

Будущая реализация:
- отдельный Python package;
- чистое вычислительное ядро;
- scenario runner;
- parameter sweep;
- property-based checks;
- synthetic populations;
- FSRS adapter;
- replay обезличенной истории;
- отчёты и графики.
```

Переход к 5B выполняется только после отдельного решения.

## 3. Центральный принцип симуляции

Симулятор должен оптимизировать не только сопротивляемость abuse.

Неправильная цель:

```text
минимизировать XP любого необычного поведения
```

Правильная цель:

```text
сохранить ценность подтверждённой учебной работы
+
ограничить дополнительную выгоду искусственных стратегий
+
сделать результат стабильным и объяснимым
```

Модель автоматически отклоняется, если она:

- лучше подавляет exploit, но уменьшает `CoreBaseline` честных reviews;
- делает нормальную длинную работу хуже короткой;
- зависит от количества искусственно созданных сессий;
- заметно наказывает отсутствие FSRS;
- делает backlog-return экономически бесполезным;
- стимулирует `Hard`, `Good` или `Easy` ради XP;
- создаёт резкие reward cliffs;
- повторно применяет один и тот же anti-grind фактор;
- получает хорошие средние значения только за счёт плохих результатов для отдельных групп пользователей.

## 4. Цели симуляции

Симуляция должна ответить на семь групп вопросов.

### 4.1. Корректность формул

- совпадает ли код будущего симулятора с примерами документации;
- соблюдаются ли caps и piecewise-функции;
- не возникают ли отрицательные или невозможные значения;
- сохраняется ли идемпотентность;
- одинаков ли результат при повторном расчёте;
- корректно ли пересчитываются derived transactions.

### 4.2. Поведение честного пользователя

- сохраняется ли базовая награда каждого core-review;
- насколько различаются обычные своевременные reviews;
- не доминируют ли context bonuses;
- не обесцениваются ли длинные дни;
- справедлива ли модель к маленьким коллекциям;
- справедлива ли модель к пользователям без надёжного FSRS;
- не наказывает ли модель нормальные filtered-deck workflows;
- не наказывает ли возвращение после перерыва.

### 4.3. Устойчивость к abuse

- выгодно ли намеренно копить backlog;
- выгодно ли менять desired retention;
- выгодно ли повторять future cards раньше срока;
- выгодно ли строить relearning loops;
- выгодно ли создавать много сессий;
- выгодно ли делать микроколоды ради completion;
- выдаётся ли повторный XP после import, sync или replay;
- можно ли получить награду административными операциями.

### 4.4. Дневная агрегация

- адекватен ли `VolumeCredit`;
- не слишком ли велик его вклад;
- достаточен ли cap `15 Review Units`;
- адекватны ли `DailySupportCap` и `DailySupplementalCap`;
- полезен ли `CompletionCredit`;
- корректно ли ведут себя маленькие и большие due queues;
- корректно ли учитываются review limits;
- одинаков ли результат при дроблении работы на сессии.

### 4.5. Fairness

- сопоставима ли награда одинаковой полезной работы при разных размерах коллекции;
- не получает ли чрезмерное преимущество пользователь с высокой desired retention;
- не получает ли чрезмерное преимущество пользователь с низкой desired retention;
- не обесценивается ли работа пользователя с низкой model confidence;
- не создают ли длинные аудиокарточки ложные validity penalties;
- не страдают ли пользователи с нерегулярным графиком.

### 4.6. Чувствительность параметров

- какие коэффициенты реально влияют на итог;
- какие параметры почти ничего не меняют;
- где существуют нестабильные пороги;
- какие комбинации создают нелинейный разгон;
- какие caps можно упростить без потери качества;
- насколько результаты зависят от версии FSRS.

### 4.7. Связь с общей прогрессией

На вторичном уровне симуляция должна оценить:

- распределение Review Units по дням;
- возможную конвертацию Review Units в глобальный XP;
- скорость уровней при разных режимах обучения;
- согласованность с ориентиром `200 Base XP` за продуктивный день;
- риск инфляции после добавления Learn и Create XP.

Эти результаты не должны преждевременно фиксировать глобальную экономику.

## 5. Non-goals этапа 5A

Этап 5A не должен:

- выбирать окончательный UI;
- проектировать dashboard;
- проектировать API;
- изменять payload Anki Study Report;
- подключаться к рабочей Anki collection;
- определять Learn XP;
- определять Create XP;
- окончательно определять стрик;
- окончательно определять `Momentum`;
- утверждать коэффициент конвертации в глобальный XP;
- публиковать competitive leaderboard;
- проектировать серверную верификацию;
- пытаться защититься от владельца полностью модифицированной локальной программы;
- включать исследовательские задачи в fast CI.

## 6. Модель под проверкой

### 6.1. Награда core Review Episode

Текущая логическая модель после уточнения Abuse Model:

```text
BaselineCredit =
    AttemptCredit
  + Pass × OutcomeCredit

ContextBonus =
    Pass × ContextCredit

CoreReviewUnits =
    CoreEligibility × BaselineCredit
  + BonusEligibility × ContextBonus
```

Кандидатные базовые значения:

```text
AttemptCredit        = 0.25
OutcomeCredit        = 0.65
NeutralContextCredit = 0.10
```

Следовательно:

```text
обычный успешный core-review ≈ 1.00 Review Unit
Again                         ≈ 0.25 Review Unit
```

### 6.2. Дневная модель

```text
ReviewDayUnits =
    CoreBaseline
  + CoreContext
  + CappedSupportUnits
  + CappedSupplementalUnits
  + VolumeCredit
  + CompletionCredit
```

### 6.3. Qualified Volume

```text
QualifiedVolume =
Σ BaselineCredit подтверждённых уникальных core-эпизодов
```

Context, support и supplemental не увеличивают `QualifiedVolume`.

### 6.4. Volume Credit

Текущая кандидатная модель:

```text
0–10 Q:      0%
10–25 Q:     5%
25–50 Q:     8%
50–100 Q:   10%
выше 100 Q: 12%

VolumeCredit cap = 15 Review Units
```

### 6.5. Support cap

```text
DailySupportCap =
min(
    3.00,
    max(0.50, 0.10 × CoreBaseline)
)
```

### 6.6. Supplemental cap

```text
DailySupplementalCap =
min(
    2.00,
    0.03 × CoreBaseline
)
```

При `CoreBaseline = 0` постоянный supplemental Review XP равен `0`.

### 6.7. Completion Credit

```text
BaseCompletionCredit =
min(3.00, 0.03 × QualifiedVolume)

CompletionCredit =
CompletionFactor × BaseCompletionCredit
```

Текущие коэффициенты:

| Completion status | Factor |
|---|---:|
| `collection_cleared` | `1.00` |
| `scope_cleared` | `0.80` |
| `configured_limit_reached` | `0.50` |
| `partial` | `0.00` |
| `zero_due` | `0.00` |
| `snapshot_uncertain` | `0.00` |

## 7. Уровни симуляции

Будущий simulator должен поддерживать несколько уровней проверки. Они не заменяют друг друга.

### 7.1. Deterministic example replay

Запускаются точные примеры из документации.

Цель:

- доказать соответствие формул спецификациям;
- обнаружить ошибку реализации;
- сохранить regression baseline;
- показать понятный reward breakdown.

### 7.2. Invariant checks

Проверяются свойства, которые должны выполняться для широких диапазонов входов.

Примеры:

- дробление дня на сессии не меняет итог;
- duplicate не увеличивает reward;
- Undo возвращает состояние;
- Hard, Good и Easy не меняют прямой reward при одинаковом pre-state;
- caps никогда не превышаются;
- `CoreBaseline` не уменьшается из-за дневного объёма.

### 7.3. Structured scenario matrix

Запускается заранее определённая матрица personas, параметров и учебных режимов.

Цель:

- сравнить конкретные осмысленные случаи;
- получить воспроизводимые таблицы;
- избежать зависимости только от случайной генерации.

### 7.4. Parameter sweep

Перебираются кандидатные варианты коэффициентов.

Цель:

- измерить чувствительность;
- найти доминирующие параметры;
- исключить нестабильные диапазоны;
- выбрать небольшой shortlist.

### 7.5. Monte Carlo population simulation

Генерируются виртуальные пользователи и многодневные истории.

Цель:

- увидеть распределения, а не только средние значения;
- обнаружить редкие хвостовые случаи;
- проверить многомесячный и многолетний эффект;
- сравнить скорость прогрессии.

### 7.6. Sanitized real-history replay

Позднее допускается replay обезличенной истории.

Цель:

- проверить модель на реальных распределениях;
- сравнить synthetic personas с настоящими паттернами;
- обнаружить сценарии, не представленные генератором.

Этот уровень не обязателен для первой версии 5B.

## 8. Каноническая модель входных данных

Симулятор не должен напрямую зависеть от `revlog`, collection API или конкретных Python-классов Anki.

Он должен принимать нормализованные модели.

### 8.1. ReviewEpisodeInput

```text
ReviewEpisodeInput

identity:
  episode_id
  source_event_key
  card_lineage_id
  note_lineage_id
  anki_day
  timestamp

classification:
  event_class
  episode_role
  due_relation
  source
  provenance

outcome:
  answer
  pass
  undone

memory_before:
  retrievability
  stability
  difficulty
  model_kind
  model_confidence
  desired_retention
  fsrs_parameter_version

scheduling:
  natural_due
  actual_due
  days_overdue
  schedule_origin
  forced_due
  rescheduling_enabled

response:
  response_time
  expected_response_time
  response_pattern_class

relationships:
  parent_episode_id
  same_card_attempt_index
  sibling_seen_today
  duplicate_group
```

### 8.2. RewardParameterSet

```text
RewardParameterSet

identity:
  parameter_set_id
  rule_version

baseline:
  attempt_credit
  outcome_credit
  neutral_context_credit

challenge:
  challenge_curve
  natural_due_reference_policy
  delay_credit_cap

memory_gain:
  enabled
  normalization_method
  credit_cap

confidence:
  high_weight
  medium_weight
  low_weight
  unavailable_weight

validity:
  bonus_eligibility_rules
  deterministic_core_exclusions

support:
  episode_support_cap
  daily_support_floor
  daily_support_rate
  daily_support_cap

supplemental:
  daily_supplemental_rate
  daily_supplemental_cap

volume:
  tiers
  cap

completion:
  base_rate
  cap
  status_factors
```

### 8.3. WorkloadSnapshotInput

```text
WorkloadSnapshotInput

anki_day
snapshot_time
scope_kind
scope_id
natural_due_at_start
overdue_at_start
due_visible_under_limits
due_hidden_by_limits
interday_learning
review_limit
snapshot_confidence
```

### 8.4. DayScenarioInput

```text
DayScenarioInput

scenario_id
persona_id
seed
anki_day
sessions
review_episodes
workload_snapshot
settings_changes
sync_events
expected_properties
```

### 8.5. SimulationManifest

Каждый запуск должен иметь manifest:

```text
SimulationManifest

simulation_version
code_commit
parameter_set_ids
scenario_set_version
random_seed
fsrs_adapter_version
started_at
completed_at
input_digest
output_digest
```

## 9. Правило чистого ядра

Будущая реализация должна использовать чистые функции.

Концептуальный контракт:

```text
ReviewEpisodeInput
+
RewardParameterSet
→
ReviewRewardBreakdown
```

```text
list[ReviewRewardBreakdown]
+
WorkloadSnapshotInput
+
DayAggregationParameters
→
ReviewDayBreakdown
```

Ядро не должно:

- открывать Anki collection;
- обращаться к сети;
- читать системные настройки напрямую;
- зависеть от dashboard;
- изменять входные события;
- хранить глобальное mutable state;
- выбирать параметры неявно.

Это необходимо для воспроизводимости и будущего переноса стабилизированных формул в production.

## 10. Candidate parameter families

Симуляция не должна сразу перебирать полный декартов продукт всех параметров. Сначала сравниваются ограниченные семейства.

### 10.1. Reward family

#### `R-CURRENT`

Текущая модель:

- Attempt `0.25`;
- Outcome `0.65`;
- Neutral context `0.10`;
- challenge enabled;
- memory gain enabled;
- reward cap около `1.32`.

#### `R-NO-GAIN`

- текущий baseline;
- challenge enabled;
- memory gain disabled.

Цель: проверить, создаёт ли memory gain полезное различие или только усложняет модель.

#### `R-LOW-CHALLENGE`

- challenge cap уменьшен;
- memory gain сохранён.

Цель: проверить чувствительность к backlog и низкой retrievability.

#### `R-NEUTRAL-CONTEXT`

- `ContextCredit = 0.10` для всех обычных успешных core-review;
- challenge и memory gain отключены.

Это контрольный benchmark, а не предполагаемый финальный вариант.

### 10.2. Volume family

#### `V-CURRENT`

Текущие tiers и cap `15`.

#### `V-LOW-CAP`

Те же tiers, cap `10`.

#### `V-SOFT`

Пониженные проценты tiers.

#### `V-NONE`

Volume Credit отсутствует.

Цель: определить, создаёт ли volume bonus реальную мотивационную ценность без инфляции.

### 10.3. Completion family

#### `C-CURRENT`

Rate `3%`, cap `3`, текущие status factors.

#### `C-LOW`

Rate `2%`, cap `2`.

#### `C-SYMBOLIC`

Completion status сохраняется, числовой reward отсутствует.

Цель: проверить, нужен ли completion именно как XP-механика.

### 10.4. Support family

#### `S-CURRENT`

Floor `0.50`, rate `10%`, cap `3`.

#### `S-LOW`

Floor `0.25`, rate `7.5%`, cap `2`.

#### `S-EPISODE-ONLY`

Сохраняется episode cap, дневной дополнительный reward минимален.

### 10.5. Supplemental family

#### `P-CURRENT`

Rate `3%`, cap `2`, no-core reward `0`.

#### `P-LOW`

Rate `1.5%`, cap `1`.

#### `P-METRIC-ONLY`

Supplemental activity отображается, но не даёт постоянный Review XP.

## 11. Стратегия перебора параметров

Полный cartesian sweep не используется на первом проходе.

Порядок:

```text
1. Проверить hard invariants текущей модели
2. Сравнить Reward family при фиксированной day aggregation
3. Выбрать 1–2 reward candidates
4. Сравнить Volume family
5. Сравнить Completion family
6. Сравнить Support и Supplemental families
7. Запустить sensitivity analysis вокруг shortlist
8. Запустить population simulation
9. Проверить exploit matrix
10. Сформировать Pareto shortlist
```

Это предотвращает ситуацию, когда тысячи комбинаций дают много чисел, но мало понимания причин.

## 12. Synthetic personas

Каждая persona описывает не конкретного человека, а устойчивый класс учебного поведения.

### `P01_NEW_SMALL`

- новая коллекция;
- мало history;
- низкая FSRS confidence;
- `5–20` due reviews в день;
- заметная доля learning, но Review simulator анализирует только review-часть.

### `P02_BEGINNER_REGULAR`

- `20–50` reviews в день;
- стабильный график;
- умеренная доля Again;
- небольшая mature history.

### `P03_MATURE_CONSISTENT`

- большая зрелая коллекция;
- высокая model confidence;
- `50–120` reviews в день;
- большинство reviews близко к natural due.

### `P04_HIGH_VOLUME`

- `150–400` reviews в день;
- честная длинная работа;
- несколько сессий или одна длинная сессия;
- используется для защиты CoreBaseline от diminishing returns.

### `P05_SMALL_MATURE_COLLECTION`

- естественная due queue `1–12` карточек;
- высокая completion frequency;
- проверяет отсутствие дискриминации маленьких коллекций.

### `P06_BACKLOG_RETURN`

- перерыв `7–60` дней;
- большая overdue queue;
- честное возвращение;
- повышенная доля Again;
- восстановление в течение нескольких недель.

### `P07_IRREGULAR_SHIFT_WORKER`

- нерегулярное время занятий;
- разные размеры сессий;
- часть работы близко к границе Anki-дня;
- пропуски без exploit-намерения.

### `P08_NO_FSRS`

- FSRS context unavailable;
- используется neutral context;
- проверяет сохранение обычной базовой награды.

### `P09_LOW_CONFIDENCE_FSRS`

- FSRS включён;
- мало history;
- model confidence `low` или `medium`;
- проверяет плавный fallback.

### `P10_HIGH_RETENTION`

- desired retention выше обычной;
- больше reviews;
- многие карточки относительно лёгкие;
- проверяет отсутствие volume-driven преимущества.

### `P11_LOW_RETENTION`

- desired retention ниже обычной;
- меньше reviews;
- lower retrievability at due;
- проверяет отсутствие challenge-driven преимущества.

### `P12_MULTI_DEVICE`

- sessions на двух устройствах;
- late sync;
- overlapping history;
- duplicate replay;
- позднее изменение Workload Snapshot.

### `P13_HEAVY_LAPSE`

- высокая доля Again;
- много relearning;
- проверяет episode и day support caps.

### `P14_AUDIO_AND_LONG_PROMPTS`

- длинные audio cards;
- response time выше медианы обычных карточек;
- проверяет отсутствие ложных validity penalties.

### `P15_FILTERED_EXAM_PREP`

- due cards в filtered deck;
- часть early practice;
- часть preview без rescheduling;
- проверяет корректное разделение core и supplemental.

### `P16_ZERO_DUE`

- периодические дни без due reviews;
- пользователь не запускает Review Ahead;
- проверяет нейтральность zero-due day.

## 13. Обычные сценарии

Минимальный набор ordinary scenarios:

1. Один своевременный успешный `Good`.
2. Аналогичный `Hard`.
3. Аналогичный `Easy`.
4. Один честный `Again`.
5. `Again` с нормальным relearning.
6. `10` successful core reviews.
7. `30` successful core reviews.
8. `100` successful core reviews.
9. `300` successful core reviews.
10. Одинаковый день в одной сессии.
11. Одинаковый день в трёх сессиях.
12. Маленькая коллекция с одной due-карточкой.
13. Маленькая коллекция с шестью due-карточками.
14. Полностью очищенная collection workload.
15. Полностью очищенный locked deck subtree.
16. Достигнут configured review limit.
17. Несколько decks в одном дне.
18. Interday relearning без нового core-review.
19. День без FSRS.
20. День с low model confidence.
21. Длинные аудиокарточки.
22. Due reviews внутри filtered deck с rescheduling.
23. Нормальный backlog-return.
24. Работа через календарную полночь до границы Anki-дня.
25. Одна сессия, пересекающая границу Anki-дня.

## 14. Edge-case scenarios

Минимальный набор edge cases:

1. `QualifiedVolume = 9.99`, `10.00`, `10.01`.
2. Переход через каждый volume tier.
3. Точное достижение volume cap.
4. Значение существенно выше volume cap.
5. `CoreBaseline = 0` при наличии support.
6. `CoreBaseline = 0` при наличии supplemental.
7. Support ровно на floor.
8. Support ровно на cap.
9. Supplemental ровно на cap.
10. Completion при `Q < 1`.
11. Completion ровно на cap.
12. Zero-due snapshot.
13. Snapshot unavailable.
14. Snapshot uncertain.
15. Review limit изменён после начала дня.
16. Scope изменён после начала дня.
17. Late sync увеличивает `QualifiedVolume`.
18. Late sync добавляет due workload.
19. Undo удаляет последний core-event.
20. Undo переводит день через volume tier вниз.
21. Undo снимает completion status.
22. Duplicate event приходит после reconciliation.
23. Event приходит с неизвестной FSRS version.
24. `Retrievability` отсутствует.
25. `Stability` отсутствует.
26. Response time отсутствует.
27. Clock moves backward.
28. Timezone changes during the day.
29. Card deleted after confirmed review.
30. Card content edited after review.
31. Sibling shown earlier in the same day.
32. Custom scheduler marks event origin as uncertain.
33. Extremely large collection and workload.
34. Empty event list.
35. Repeated calculation with identical input digest.

## 15. Abuse scenarios

Каждый abuse scenario сравнивается с честным control scenario.

### `A01_DUPLICATE_REPLAY`

Один source event обрабатывается многократно.

Ожидание:

```text
incremental reward after first application = 0
```

### `A02_MULTI_SESSION_RESET`

Одинаковая работа дробится на множество сессий.

Ожидание:

```text
total day reward delta = 0
```

### `A03_RELEARNING_LOOP`

Создаются дополнительные relearning cycles.

Ожидание:

- episode support cap соблюдается;
- day support cap соблюдается;
- `CoreBaseline` не увеличивается.

### `A04_EARLY_REVIEW_FARM`

Большое количество future cards повторяется раньше срока.

Ожидание:

- отсутствует core reward;
- отсутствует challenge bonus;
- supplemental ограничен;
- без core work постоянный reward равен `0`.

### `A05_PREVIEW_FARM`

Preview без rescheduling повторяется многократно.

Ожидание:

```text
permanent Review XP = 0
```

### `A06_FORCED_DUE`

Future cards массово переводятся в due.

Ожидание:

- manual records дают `0`;
- review до natural due не становится обычным core;
- completion не создаётся искусственно.

### `A07_RESET_RELEARN`

Карточки сбрасываются и повторно проходят цикл.

Ожидание:

- lifetime state не очищается;
- review reward не дублируется;
- событие корректно маршрутизируется между Learn и Review.

### `A08_RETENTION_HIGH_CYCLE`

Desired retention временно повышается для создания большого объёма лёгких reviews.

Ожидание:

- базовая работа признаётся;
- отсутствует повышенный context bonus;
- volume bonus не делает стратегию выгоднее стабильной политики на сопоставимом горизонте.

### `A09_RETENTION_LOW_CYCLE`

Desired retention временно понижается для получения более сложных reviews.

Ожидание:

- Reward Reference Policy ограничивает дополнительный challenge;
- накопленная награда на горизонте не превышает честный control значимо.

### `A10_INTENTIONAL_BACKLOG`

Reviews намеренно откладываются.

Ожидание:

- baseline сохраняется;
- delay-created bonus ограничивается;
- cumulative strategy не становится выгоднее своевременной работы.

### `A11_BUTTON_GAMING`

Одинаковые pre-state и outcome моделируются с `Hard`, `Good` и `Easy`.

Ожидание:

```text
direct reward delta = 0
```

### `A12_FAST_MACRO_BURST`

Создаётся серия практически невозможных времён ответа.

Ожидание:

- baseline не удаляется одной эвристикой автоматически;
- context bonus ограничивается;
- deterministic automation evidence может переводить reward в provisional state;
- нет положительной выгоды от скорости.

### `A13_WAIT_FARM`

Карточка удерживается открытой.

Ожидание:

```text
longer time does not increase reward
```

### `A14_MICRO_SCOPE_COMPLETION`

Пользователь выбирает scope с одной карточкой.

Ожидание:

- completion остаётся пропорциональным `Q`;
- reward крайне мал;
- повторная смена scope не создаёт новые bonuses.

### `A15_REVIEW_LIMIT_MANIPULATION`

Review limit снижается после начала дня.

Ожидание:

- Workload Snapshot сохраняет исходный limit;
- completion не создаётся из-за снижения;
- выполненный baseline сохраняется.

### `A16_SYNC_REPLAY`

Одинаковая история приходит с нескольких устройств.

Ожидание:

- source-event idempotency;
- отсутствует двойной reward;
- late unique events учитываются один раз.

### `A17_IMPORT_REPLAY`

Одна история импортируется повторно.

Ожидание:

- duplicate lineage не создаёт новый live reward;
- ambiguous history получает historical policy, а не полный bonus.

### `A18_CLOCK_ROLLBACK`

Системное время переводится назад для создания дополнительных дней.

Ожидание:

- day caps не сбрасываются без нового достоверного Anki-day identity;
- bonus eligibility ограничивается;
- уже выполненная честная работа не конфискуется.

### `A19_EXACT_DUPLICATE_CARDS`

Создаются точные дубликаты одной карточки.

Ожидание:

- exact duplicate group ограничивает повторный reward;
- probable duplicates не вызывают жёсткого baseline removal без надёжного основания.

### `A20_CUSTOM_SCHEDULER_MANIPULATION`

Custom Scheduling искусственно создаёт выгодные states.

Ожидание:

- baseline реального review сохраняется;
- uncertain schedule origin ограничивает context bonus;
- scheduler-generated state не считается абсолютным доказательством natural difficulty.

## 16. Control scenarios

Abuse strategy нельзя оценивать без control.

Для каждого exploit определяются один или несколько controls.

Примеры:

| Abuse | Control |
|---|---|
| Intentional backlog | те же карточки, повторённые около natural due |
| Early review farm | те же карточки в их natural due dates |
| Retention cycling | стабильная retention policy на том же горизонте |
| Relearning loop | один нормальный lapse и стандартное relearning |
| Multi-session reset | тот же набор events в одной session |
| Micro-scope completion | тот же `QualifiedVolume` без искусственной смены scope |
| Fast macro | правдоподобные ответы на тот же набор карточек |
| Duplicate replay | однократная обработка исходных events |

Сравнение выполняется минимум по трём основаниям:

```text
reward per unique core episode
reward per simulated day
cumulative reward over matched horizon
```

Время не используется как единственная мера effort, поскольку его легко искажать и оно зависит от типа карточек.

## 17. Метрики корректности

### 17.1. Example conformance

```text
example_conformance_rate =
passed_documented_examples / all_documented_examples
```

Требование:

```text
100%
```

### 17.2. Invariant violation count

```text
hard_invariant_violations
```

Требование:

```text
0
```

### 17.3. Recalculation determinism

Одинаковые inputs, parameter set и seed должны давать идентичный output digest.

Требование:

```text
100% deterministic for deterministic modes
```

## 18. Метрики награды

### 18.1. Baseline preservation rate

```text
BaselinePreservation =
awarded_core_baseline / eligible_core_baseline
```

Для честных подтверждённых событий:

```text
BaselinePreservation = 1.00
```

### 18.2. Mean units per successful core review

Отдельно измеряется для:

- on-time;
- overdue;
- no-FSRS;
- low-confidence;
- high-confidence;
- small collection;
- high-volume day.

### 18.3. Context share

```text
ContextShare =
CoreContext / ReviewDayUnits
```

Цель: context должен быть заметен, но не доминировать.

### 18.4. Additional bonus share

```text
AdditionalBonusShare =
(VolumeCredit + CompletionCredit) / ReviewDayUnits
```

### 18.5. Support share

```text
SupportShare =
CappedSupportUnits / ReviewDayUnits
```

### 18.6. Supplemental share

```text
SupplementalShare =
CappedSupplementalUnits / ReviewDayUnits
```

### 18.7. Reward distribution

Для каждой persona выводятся:

- mean;
- median;
- standard deviation;
- p05;
- p25;
- p75;
- p95;
- p99;
- maximum;
- доля zero-reward days;
- доля days по contribution bands.

## 19. Fairness metrics

### 19.1. Collection-size parity

Сравнивается reward per eligible core episode для маленьких и больших коллекций.

Базовая часть должна быть одинаковой.

### 19.2. FSRS availability parity

Сравнивается обычное успешное on-time review:

```text
FSRS unavailable
vs
FSRS high confidence
```

No-FSRS пользователь должен сохранять нейтральную награду около `1.00 Review Unit`.

### 19.3. Session-pattern parity

```text
SessionPatternDelta =
abs(reward_one_session - reward_split_sessions)
```

Требование:

```text
0
```

### 19.4. Schedule-policy parity

Сравниваются стабильные high-retention и low-retention policies на долгом горизонте.

Цель: ни одна настройка не должна давать очевидный XP multiplier без сопоставимого увеличения реальной работы.

### 19.5. Backlog-return viability

Возвращение после перерыва должно сохранять:

- полный baseline;
- положительную дневную награду;
- возможность normal progression.

### 19.6. Long-session preservation

```text
LongSessionBaselineRatio =
awarded_baseline / eligible_baseline
```

Требование:

```text
1.00
```

## 20. Abuse-resistance metrics

### 20.1. Incremental exploit reward

```text
IncrementalExploitReward =
reward_exploit - reward_control
```

### 20.2. Exploit gain ratio

```text
ExploitGainRatio =
reward_exploit / reward_control
```

Метрика используется только при содержательно сопоставимом control.

### 20.3. Duplicate amplification

```text
DuplicateAmplification =
reward_after_replay / reward_single_application
```

Требование:

```text
1.00
```

Дополнительная обработка не должна увеличивать итог.

### 20.4. Relearning amplification

Измеряется reward при росте количества искусственных steps после достижения episode cap.

Ожидание:

```text
marginal reward after cap = 0
```

### 20.5. Retention-cycling advantage

Сравнивается cumulative reward cycling policy и stable control за `30`, `90` и `365` дней.

### 20.6. Backlog-delay advantage

Сравнивается cumulative reward intentional-delay strategy и timely control на одинаковом горизонте.

### 20.7. Completion farming efficiency

Измеряется дополнительный CompletionCredit при микроскопическом scope.

Ожидание:

- не более `3%` соответствующего `QualifiedVolume` до factor;
- не более одного completion bonus в Anki-день.

## 21. Hard invariants

Вариант модели немедленно отклоняется при нарушении хотя бы одного hard invariant.

### H01. Core baseline preservation

Честный подтверждённый core-event не теряет baseline из-за дневного объёма или слабой эвристики.

### H02. Source-event idempotency

Повторная обработка одного source event не создаёт новую reward transaction.

### H03. Card/day core uniqueness

Одна card lineage не получает более одного core Review Episode за Anki-день.

### H04. Undo reversibility

После Undo итог соответствует состоянию, как будто отменённого review не существовало.

### H05. Session invariance

Дробление одинакового набора events на сессии не меняет дневной итог.

### H06. Button neutrality

При одинаковом pre-state успешные `Hard`, `Good` и `Easy` не имеют прямого различия игровой награды.

### H07. No time bonus

Увеличение response time само по себе не увеличивает reward.

### H08. Manual operations yield zero

Administrative records не дают Review XP.

### H09. Preview permanent reward is zero

Preview без rescheduling не создаёт постоянный Review XP.

### H10. Core baseline has no daily diminishing returns

Каждый eligible baseline складывается полностью.

### H11. Support caps

Episode и daily support caps никогда не превышаются.

### H12. Supplemental caps

Daily supplemental cap никогда не превышается.

### H13. Volume cap

```text
VolumeCredit ≤ 15
```

для текущего parameter set.

### H14. Completion cap

```text
CompletionCredit ≤ 3
```

для текущего parameter set.

### H15. Zero-due neutrality

Zero-due day не создаёт CompletionCredit и не требует early review.

### H16. Non-negative reward

```text
ReviewDayUnits ≥ 0
```

### H17. Explainable breakdown

Итоговая сумма равна сумме компонентов breakdown с допустимой точностью округления.

### H18. Determinism

Повтор deterministic simulation с теми же inputs даёт тот же результат.

## 22. Quantitative acceptance criteria

Числа ниже являются кандидатными gates для выбора parameter shortlist. Они могут быть уточнены после первого прогона, но изменение должно быть задокументировано.

### 22.1. Ordinary successful review

Для обычного on-time успешного core-review:

```text
median total reward: 0.98–1.08 Review Unit
```

### 22.2. Core episode cap

Для текущего Reward Model:

```text
maximum core Review Episode ≤ 1.32 Review Unit
```

### 22.3. Honest baseline preservation

```text
100% eligible honest core baseline preserved
```

Ни одна эвристика не может сама создать baseline loss.

### 22.4. Typical additional day bonus

Для ordinary personas `P02` и `P03`:

```text
median AdditionalBonusShare ≤ 12%
p95 AdditionalBonusShare ≤ 18%
```

Volume и completion должны мотивировать, но не доминировать.

### 22.5. High-volume day bonus

Для `P04_HIGH_VOLUME`:

```text
CoreBaseline preservation = 100%
VolumeCredit ≤ 15
CompletionCredit ≤ 3
```

### 22.6. Support share

Для обычных дней с core work:

```text
median SupportShare ≤ 10%
p95 SupportShare ≤ 15%
```

Дни, состоящие только из interday relearning, анализируются отдельно.

### 22.7. Supplemental share

Для дней с core work:

```text
SupplementalShare ≤ 3% CoreBaseline
и
CappedSupplementalUnits ≤ 2
```

### 22.8. No-FSRS parity

Обычный успешный no-FSRS core-review:

```text
≈ 1.00 Review Unit
```

Разница с нейтральным high-confidence on-time review не должна превышать обычный контекстный диапазон.

### 22.9. Session parity

```text
absolute day reward delta = 0
```

для любых перестановок session boundaries при одинаковом event set.

### 22.10. Duplicate and replay

```text
incremental reward = 0
```

### 22.11. Preview-only day

```text
permanent Review XP = 0
```

### 22.12. Relearning farm

После достижения episode или day cap:

```text
marginal reward = 0
```

### 22.13. Retention cycling

На горизонте `90` дней:

```text
cumulative cycling advantage ≤ 3%
```

относительно содержательно сопоставимого stable control.

На горизонте `365` дней преимущество не должно систематически расти.

### 22.14. Intentional backlog

На полном горизонте от своевременного review до завершения catch-up:

```text
intentional-delay cumulative reward
≤
timely-control cumulative reward + 3%
```

При этом честный backlog-return сохраняет baseline полностью.

### 22.15. Honest edge-case false suppression

Для честных edge scenarios:

```text
baseline suppression events = 0
```

Context suppression допускается только с объяснимой причиной и оценивается отдельно.

## 23. Reward cliffs

Симулятор должен отдельно искать резкие скачки около thresholds.

Для каждой piecewise-функции проверяются значения:

```text
threshold - ε
threshold
threshold + ε
```

Где `ε` выбирается достаточно малым для используемой точности.

Проверяются:

- challenge curve points;
- volume tiers;
- volume cap;
- support floor;
- support cap;
- supplemental cap;
- completion cap;
- contribution-band thresholds.

Критерий:

> Малое изменение полезной работы не должно создавать непропорциональный скачок итоговой награды, кроме явно дискретного изменения статуса без крупного числового бонуса.

## 24. Sensitivity analysis

Для каждого shortlist candidate изменяются по одному параметры вокруг базового значения.

Минимальные диапазоны:

| Parameter | Candidate range |
|---|---:|
| `AttemptCredit` | `0.15–0.35` |
| `OutcomeCredit` | `0.55–0.75` |
| `NeutralContextCredit` | `0.05–0.15` |
| Challenge cap | `0.20–0.40` |
| Memory gain cap | `0.00–0.15` |
| Episode support cap | `0.06–0.18` |
| Daily support rate | `0.05–0.15` |
| Daily support cap | `1–4` |
| Supplemental rate | `0–0.05` |
| Supplemental cap | `0–3` |
| Volume cap | `5–25` |
| Completion rate | `0–0.05` |
| Completion cap | `0–5` |

Выходы:

- изменение median reward;
- изменение p95;
- изменение bonus shares;
- изменение exploit ratios;
- изменение fairness metrics;
- изменение прогнозируемой скорости уровней.

Параметр считается нестабильным, если небольшое изменение вызывает непропорциональное изменение нескольких ключевых метрик.

## 25. Simulation budgets

Значения определяют будущие режимы запуска, а не CI.

### 25.1. Deterministic suite

- все документированные examples;
- все hard invariants;
- все threshold boundary cases;
- фиксированные seeds;
- должен выполняться локально быстро.

### 25.2. Development sample

```text
16 personas
× 30 days
× 10 seeds
≈ 4 800 persona-days
```

Используется для быстрой локальной итерации в 5B.

### 25.3. Standard research run

```text
16 personas
× 365 days
× 100 seeds
≈ 584 000 persona-days
```

### 25.4. Long-horizon stress run

Для выбранных personas:

```text
6 personas
× 3 650 days
× 50 seeds
≈ 1 095 000 persona-days
```

### 25.5. Abuse matrix

Каждый abuse scenario выполняется:

- для каждого shortlist parameter set;
- с соответствующим control;
- минимум на `30`, `90` и `365` дней, где применимо;
- с несколькими уровнями интенсивности exploit.

## 26. Randomness and reproducibility

Monte Carlo не должен означать невоспроизводимый результат.

Правила:

- каждый run имеет explicit seed;
- набор seeds сохраняется в manifest;
- generator version фиксируется;
- parameter set version фиксируется;
- FSRS adapter version фиксируется;
- outputs имеют digest;
- случайные параметры persona записываются;
- report содержит точную команду будущего запуска;
- regression scenarios используют фиксированные seeds.

При сравнении parameter sets используется один и тот же набор seeds, чтобы различия отражали формулы, а не разную случайную выборку.

## 27. Генерация учебных событий

Synthetic generator должен различать:

- истинное состояние памяти;
- прогноз scheduler;
- выбранную кнопку;
- реальное событие;
- игровую классификацию.

Нельзя генерировать reward напрямую.

Правильная цепочка:

```text
persona state
→ memory outcome
→ scheduler event
→ normalized ReviewEpisodeInput
→ reward pipeline
→ day aggregation
```

Это позволяет моделировать:

- честные ошибки;
- неверное использование кнопок;
- model uncertainty;
- drift между истинной памятью и scheduler prediction;
- backlog;
- настройку retention;
- delayed sync.

## 28. FSRS adapter

В будущем 5B может использовать отдельный FSRS adapter.

Требования:

- adapter не должен быть частью pure reward core;
- версия реализации фиксируется;
- входные и выходные значения нормализуются;
- критические сценарии позднее сверяются с поддерживаемой версией Anki;
- различия между Python и official implementation документируются;
- отсутствие adapter не блокирует deterministic formula tests.

Первая версия simulator может начать с заранее заданных memory states без полной генерации scheduler history.

## 29. Sanitized real-history replay

### 29.1. Принцип

Simulator не получает прямой доступ к рабочей Anki collection.

Предпочтительный pipeline:

```text
локальный export adapter
→ normalized export
→ sanitization
→ simulator input
```

### 29.2. Необходимые данные

Для Review XP могут потребоваться:

- анонимный card lineage ID;
- анонимный note lineage ID;
- timestamp;
- Anki day;
- event type;
- rating;
- old/new interval;
- response time;
- natural/actual due context, если доступен;
- FSRS states;
- model confidence;
- scheduler configuration hash;
- source provenance;
- manual/undo/reschedule markers.

### 29.3. Не требуются

Для первой Review simulation не нужны:

- текст вопроса;
- текст ответа;
- media files;
- deck names;
- note field contents;
- profile name;
- collection path;
- dashboard token;
- полный URL локального сервера.

### 29.4. Privacy

- реальные exports не коммитятся;
- raw exports остаются локальными;
- результаты по возможности агрегируются;
- IDs псевдонимизируются;
- timestamps могут быть сдвинуты при сохранении интервалов;
- report не должен раскрывать содержание коллекции.

## 30. Формат результатов

Будущий simulation run должен создавать структурированный набор outputs.

### 30.1. Manifest

```text
manifest.json
```

Содержит версии, seeds, parameter sets и digests.

### 30.2. Summary data

```text
summary.csv
persona_summary.csv
scenario_summary.csv
abuse_comparison.csv
sensitivity.csv
```

### 30.3. Human-readable report

```text
report.md
```

Минимальная структура:

1. цель запуска;
2. tested parameter sets;
3. dataset and seeds;
4. hard invariant results;
5. honest-user metrics;
6. fairness metrics;
7. abuse metrics;
8. threshold analysis;
9. sensitivity analysis;
10. rejected variants;
11. Pareto shortlist;
12. limitations;
13. recommendation.

### 30.4. Charts

Будущие графики:

- reward distribution by persona;
- Review Units against core count;
- bonus share against `QualifiedVolume`;
- challenge reward against retrievability;
- cumulative reward over time;
- exploit vs control;
- parameter sensitivity;
- predicted level progression.

Большие generated outputs не должны коммититься в основной репозиторий.

## 31. Выбор модели

Один общий score не используется.

Причина: модель может получить высокий средний score, скрыв серьёзное нарушение baseline или fairness.

Порядок выбора:

```text
1. Отбросить варианты с hard invariant violations
2. Отбросить варианты, нарушающие baseline preservation
3. Отбросить варианты с exploit advantage выше gates
4. Отбросить варианты с неприемлемыми fairness gaps
5. Сравнить оставшиеся по bonus shares и sensitivity
6. Построить Pareto shortlist
7. Выбрать более простую модель при сопоставимом качестве
8. Провести human review breakdown и UX-смысла
```

Принцип простоты:

> Если сложный компонент не даёт устойчивого улучшения fairness, motivation или abuse resistance, он удаляется.

Особенно это относится к `MemoryGainCredit`.

## 32. Pareto dimensions

Shortlist сравнивается минимум по измерениям:

- baseline preservation;
- honest reward stability;
- exploit resistance;
- fairness;
- parameter sensitivity;
- explainability;
- implementation complexity;
- dependence on FSRS-specific details;
- long-horizon inflation;
- compatibility with future Learn/Create XP.

Ни одно измерение не должно полностью поглощаться одной средней метрикой.

## 33. Решения после simulation report

Итоговый отчёт должен классифицировать каждый parameter set:

```text
accept
accept with adjustment
repeat simulation
reject
```

Для принятой модели фиксируются:

- точные параметры;
- rule version;
- причины выбора;
- rejected alternatives;
- known limitations;
- required production safeguards;
- required regression scenarios.

Изменение параметров после этого требует новой версии и повторного regression run.

## 34. Граница будущего research-пакета

При переходе к 5B рекомендуется создать:

```text
research/gamification-sim/
```

Пакет должен быть отделён от production runtime.

Он не должен:

- импортироваться add-on;
- попадать в `.ankiaddon`;
- добавлять зависимости в bundled runtime;
- менять dashboard assets;
- читать collection напрямую;
- запускаться из dashboard;
- входить в production API.

Будущий пакет может содержать:

```text
pyproject.toml
README.md
src/gamification_sim/
tests/
configs/
scenarios/
fixtures/
```

## 35. План будущего этапа 5B

### 5B.1. Pure deterministic core

- нормализованные dataclasses;
- Reward Model;
- Abuse safeguards;
- Day Aggregation;
- breakdown;
- exact examples.

### 5B.2. Scenario runner

- YAML/JSON scenarios;
- deterministic replay;
- manifest;
- Markdown summary.

### 5B.3. Invariant and property checks

- generated inputs;
- boundary cases;
- session invariance;
- idempotency;
- caps;
- non-negative totals.

### 5B.4. Parameter sweep

- candidate families;
- comparison tables;
- sensitivity analysis;
- Pareto shortlist.

### 5B.5. Synthetic population generator

- personas;
- multi-day histories;
- seeded Monte Carlo;
- long-horizon progression.

### 5B.6. FSRS adapter

- memory-state generation;
- scheduler scenarios;
- version comparison.

### 5B.7. Sanitized real-history replay

- optional local export adapter;
- privacy-preserving normalization;
- local-only raw data.

Каждый подпункт может быть отдельным небольшим research-этапом.

## 36. Политика CI

### 36.1. Этап 5A

Этап 5A является documentation-only.

В рамках этого этапа запрещено:

- добавлять simulator job в fast CI;
- добавлять simulator job в full CI;
- изменять существующие GitHub Actions workflows;
- изменять `run_fast_check` или аналогичные scripts;
- добавлять research dependencies в основной lockfile;
- запускать Docker E2E;
- создавать отдельный scheduled workflow.

### 36.2. Начало этапа 5B

По текущему решению даже начало 5B выполняется локально и вручную.

Необходимо:

- отдельное virtual environment;
- отдельный package manifest;
- локальные команды запуска;
- отсутствие связи с production verification chain.

### 36.3. Возможное будущее подключение CI

CI рассматривается только после того, как:

- pure core стабилен;
- deterministic suite мала и быстра;
- package boundaries подтверждены;
- пользователь отдельно одобрил интеграцию;
- измерено реальное время выполнения;
- доказано, что fast CI не замедляется.

Предпочтительная будущая политика, если она вообще понадобится:

```text
fast CI
→ не содержит gamification simulator

optional research checks
→ отдельный manual workflow или отдельная команда
```

Это не является решением текущего этапа.

## 37. Verification этапа 5A

Поскольку этап документационный, достаточно:

- проверить внутренние ссылки;
- проверить согласованность названий параметров;
- проверить отсутствие противоречий с этапами 1–4;
- проверить, что CI и production files не изменялись;
- проверить branch diff.

Запуск fast CI, full CI или Docker E2E не требуется.

## 38. Формат первого отчёта 5B

Первый полезный report не обязан содержать Monte Carlo.

Минимальный первый report:

```text
Review Simulation Report v0.1

- exact examples: PASS/FAIL
- hard invariants: PASS/FAIL
- current parameter set breakdown
- R-CURRENT vs R-NO-GAIN
- V-CURRENT vs V-NONE
- C-CURRENT vs C-SYMBOLIC
- ordinary scenarios
- edge scenarios
- abuse controls
- rejected assumptions
- next experiment
```

Это позволит принимать решения постепенно, не строя сразу чрезмерно сложную систему.

## 39. Completion criteria этапа 5A

Этап 5A считается завершённым, когда:

1. определены уровни симуляции;
2. определена нормализованная модель inputs;
3. зафиксированы current parameter sets;
4. определены candidate families;
5. определены synthetic personas;
6. определены ordinary scenarios;
7. определены edge-case scenarios;
8. определены abuse scenarios и controls;
9. определены metrics;
10. определены hard invariants;
11. определены quantitative acceptance criteria;
12. определён sensitivity analysis;
13. определены simulation budgets;
14. определены reproducibility requirements;
15. определён формат report;
16. определена privacy policy для real-history replay;
17. определена граница будущего research-пакета;
18. явно исключена интеграция с fast CI;
19. дальнейшая реализация вынесена в отдельный этап 5B.

## 40. Принятые решения этапа 5A

Предварительно приняты:

1. Этап 5 разделяется на specification `5A` и implementation `5B`.
2. Этап 5A не содержит кода.
3. Будущий simulator располагается отдельно от production runtime.
4. Формулы проверяются чистыми нормализованными inputs.
5. Deterministic examples и hard invariants имеют приоритет над средними метриками.
6. Вариант с baseline loss отклоняется независимо от качества abuse suppression.
7. Abuse scenarios всегда сравниваются с содержательным control.
8. Один общий optimization score не используется.
9. Выбор выполняется через hard gates и Pareto shortlist.
10. При сопоставимом качестве выбирается более простая модель.
11. `MemoryGainCredit` должен доказать полезность отдельно от challenge.
12. Маленькие и большие коллекции проверяются раздельно.
13. No-FSRS и low-confidence users входят в обязательную fairness matrix.
14. Backlog-return и intentional backlog проверяются как разные сценарии.
15. Session splitting должен давать нулевой reward delta.
16. Volume и completion проверяются как дополнительные, а не основные источники reward.
17. Real-history replay является optional later layer.
18. Raw collection data и тексты карточек не коммитятся.
19. Этап 5A не меняет fast CI, full CI, workflow или verification scripts.
20. Начало 5B также планируется local/manual до отдельного решения.

## 41. Следующий шаг

После утверждения этой спецификации возможны два пути:

```text
A. Перейти к этапу 5B.1
   и создать минимальное pure deterministic core.

B. До реализации уточнить один из спорных параметров
   или добавить дополнительные personas/scenarios.
```

По умолчанию рекомендуемый следующий шаг:

```text
Stage 5B.1 — Pure Deterministic Review Simulator Core
```

Он должен реализовать только формулы, breakdown и exact scenarios без Monte Carlo, FSRS adapter и CI-интеграции.

## Stage 5B.C correction: longitudinal evidence boundary

The original seeded persona generator is retained as an **independent-day
workload stress simulation**. It remains valid for distribution and cap stress,
but it is not evidence that card memory, due state, backlog, or desired
retention evolved across days.

Longitudinal calibration uses the separate strict
`review-longitudinal-v0.1` contract. A persistent `card_lineage_id` carries
memory state, last review, natural next due, interval, lapse/review counts,
policy/preset identity, and active state across the horizon. FSRS-enabled
histories call official py-fsrs transitions; no-FSRS histories use the declared
neutral synthetic scheduler. A missed due card remains the same overdue lineage
until catch-up. Common random numbers derive from seed, replica, lineage, review
ordinal, and channel—not iteration order or policy ID.

Learning/relearning transitions exist only for schedule continuity. They do not
define or award Learn XP. Review events continue through the existing reward
core, and scheduling-adapter uncertainty cannot suppress eligible CoreBaseline.
