> **Recovery status:** `RECOVERED_UNVERIFIED`
> **Frozen source:** `48298d02c6871df0ffa112d862d9b2af629c523f:docs/gamification/anki-review-session-and-day.md`
> **Evidence status:** research candidate; numerical results were not reproduced in G0.4
> **Execution status:** G0.5–G0.7 pending
> **Production status:** integration not approved
> **Adaptation:** provenance/status header only; historical body and reward semantics unchanged

# Anki Review Session and Day Aggregation

Статус: **DRAFT v0.1**  
Дата: **2026-07-16**  
Область: **четвёртый этап проектирования Review XP; продуктовая модель агрегации без production-реализации**

## 1. Назначение документа

Этот документ определяет, как отдельные классифицированные и оценённые `Review Episode` объединяются в аналитические сессии и итог одного учебного дня Anki.

Документ продолжает:

- [Anki Review Event Taxonomy](anki-review-event-taxonomy.md) — определяет допустимость и класс события;
- [Anki Review Reward Model](anki-review-reward-model.md) — определяет относительную стоимость эпизода;
- [Anki Review XP Abuse Model](anki-review-abuse-model.md) — определяет допустимые ограничения и защиту честной базовой награды;
- [Anki XP Foundation](anki-xp-foundation.md) — задаёт общие инварианты домена Anki.

Главный вопрос этапа:

> Как сложить множество корректных Review Episodes в понятный и мотивирующий дневной результат, не обесценив длинную честную работу и не создав новые способы фарма через сессии, лимиты или completion-бонусы?

Документ не определяет:

- окончательную конвертацию `Review Units` в глобальный XP;
- общий дневной статус, объединяющий Review, Learn и Create;
- финальные правила стрика и `Momentum`;
- кривую уровней;
- квесты, достижения и косметические награды;
- production-схему хранения;
- интерфейс dashboard.

Все числовые значения являются кандидатами для будущей симуляции. Архитектурные инварианты считаются более устойчивыми, чем конкретные thresholds и caps.

## 2. Центральное решение: день важнее сессии

Экономической единицей агрегации является `Anki Day`.

```text
Review Episode
        ↓
Review Session — аналитическая группировка
        ↓
Anki Day — экономическая агрегация
```

### 2.1. Review Session

Сессия используется для:

- промежуточной обратной связи;
- анализа рабочего ритма;
- измерения активного и календарного времени;
- отображения результатов отдельного подхода;
- группировки событий для UX;
- диагностики аномальных паттернов.

Сессия не должна:

- сбрасывать дневные caps;
- давать отдельный множитель XP;
- выдавать собственный completion bonus;
- повторно запускать volume tiers;
- повышать награду за дробление работы;
- снижать награду за длинный непрерывный подход.

### 2.2. Anki Day

На уровне учебного дня рассчитываются:

- сумма базовой core-награды;
- сумма разрешённого контекстного бонуса;
- support reward;
- supplemental reward;
- `QualifiedVolume`;
- `VolumeCredit`;
- статус выполнения естественной нагрузки;
- `CompletionCredit`;
- итоговый дневной breakdown.

### 2.3. Граница дня

Граница берётся из текущего определения учебного дня Anki, а не из обязательной календарной полуночи операционной системы.

Следствия:

- работа с `23:30` до `01:30` может относиться к одному Anki-дню;
- одна аналитическая сессия может пересечь границу Anki-дня;
- в таком случае сессия остаётся одной для аналитики, но её reward events агрегируются в два разных дня;
- смена системной даты или часового пояса не должна создавать повторные дневные caps;
- clock anomalies обрабатываются Abuse Model, а не созданием отдельной экономики.

## 3. Определение Review Session

### 3.1. Кандидатная граница

```text
25 минут без Review Events
→ начинается новая аналитическая сессия
```

Порог выбран как нейтральный компромисс:

- короткий бытовой перерыв не дробит занятие;
- отдельные утренний и вечерний подходы разделяются;
- точное значение почти не влияет на XP, потому что экономика остаётся дневной.

### 3.2. Что считается активностью сессии

Сессию продолжают:

- `core` Review Episode;
- связанный `support` event;
- допустимый `supplemental` event;
- Undo или реклассификация недавнего review;
- короткие технические переходы между карточками.

Сессию не должны искусственно продолжать:

- открытое окно reviewer без событий;
- нахождение на экране ответа;
- административные операции без учебного review;
- фоновая работа add-on;
- простое нахождение Anki запущенным.

### 3.3. Поля аналитической сессии

```text
session_id
anki_day
started_at
ended_at
active_duration
wall_clock_duration

core_episode_count
failed_core_count
support_event_count
supplemental_event_count

unique_cards
unique_notes
decks_touched

core_baseline
core_context
support_units
supplemental_units
confirmed_units
provisional_units
```

### 3.4. Инвариант дробления

Для одинакового набора reward events:

```text
одна длинная сессия
=
несколько коротких сессий
```

с точки зрения итогового дневного Review XP.

## 4. Структура дневной награды

Кандидатная формула:

```text
ReviewDayUnits =
    CoreBaseline
  + CoreContext
  + CappedSupportUnits
  + CappedSupplementalUnits
  + VolumeCredit
  + CompletionCredit
```

### 4.1. CoreBaseline

```text
CoreBaseline =
Σ BaselineCredit подтверждённых уникальных core-эпизодов
```

В актуальной Reward/Abuse модели:

```text
BaselineCredit =
    AttemptCredit
  + Pass × OutcomeCredit
```

Кандидатные ориентиры:

```text
успешный core Review ≈ 0.90 Unit
Again                 ≈ 0.25 Unit
```

### 4.2. CoreContext

```text
CoreContext =
Σ BonusEligibility × ContextBonus
```

Сюда входят:

- retrieval challenge;
- нормализованный memory gain;
- нейтральный контекст при отсутствии надёжного FSRS;
- ограничения, принятые Abuse Model.

### 4.3. SupportUnits

Награда за связанные relearning events после первичного `Again`.

Она уже ограничена на уровне lapse episode и дополнительно получает дневной cap.

### 4.4. SupplementalUnits

Небольшая награда за допустимую дополнительную практику, не являющуюся полноценным естественным core-review.

Некоторые supplemental-события, включая preview без rescheduling, могут учитываться только как аналитическая практика и не конвертироваться в постоянный XP.

### 4.5. VolumeCredit

Небольшой аддитивный бонус за значительный объём уникальной основной работы.

### 4.6. CompletionCredit

Небольшой одноразовый бонус за выполнение заранее определённой естественной нагрузки.

## 5. Базовая работа не получает дневной diminishing returns

### 5.1. Принятое решение

```text
Каждый подтверждённый уникальный core Review Episode
сохраняет полный CoreBaseline независимо от объёма дня.
```

Система не применяет к `CoreBaseline` модель:

```text
первые N карточек: 100%
следующие: 60%
остальные: 25%
```

### 5.2. Причины

Если пользователь честно выполнил 300 естественных due-review, он совершил 300 реальных попыток извлечения знания.

Уменьшение базовой награды за поздние карточки:

- обесценило бы длинную честную работу;
- особенно наказывало бы пользователей с большими коллекциями;
- ухудшало бы восстановление backlog;
- делало бы завершение due queue экономически невыгодным;
- повторно накладывало бы anti-grind после event taxonomy и abuse safeguards;
- противоречило бы принципу одинаковой ценности одинакового полезного действия.

### 5.3. Где diminishing returns допустим

Уменьшающаяся отдача применяется только к дополнительным каналам:

- `VolumeCredit` растёт прогрессивно и имеет cap;
- `SupportUnits` имеют episode cap и day cap;
- `SupplementalUnits` имеют строгий day cap;
- `CompletionCredit` имеет небольшой предел;
- `ContextBonus` уже ограничивается Reward и Abuse Models.

### 5.4. Отношение к общему Progression Foundation

Ранняя гипотеза общего дневного diminishing returns не применяется к `Review CoreBaseline`.

До симуляции объединённой экономики допускается только следующий принцип:

```text
Review CoreBaseline
→ не уменьшается глобальным envelope;

дополнительные бонусные каналы
→ могут иметь собственные caps;

будущий combined-domain envelope
→ не должен повторно обесценивать уже подтверждённую базовую работу.
```

Этот детальный документ уточняет общий foundation в соответствии с принятой иерархией решений.

## 6. QualifiedVolume

### 6.1. Назначение

`QualifiedVolume` измеряет объём основной учебной работы без повторного учёта challenge, memory gain и bonus eligibility.

```text
QualifiedVolume =
Σ BaselineCredit уникальных подтверждённых core-эпизодов
```

### 6.2. Вклад событий

| Событие | Вклад в QualifiedVolume |
|---|---:|
| Успешный core Review | `≈0.90` |
| Первичный `Again` | `≈0.25` |
| Relearning support event | `0` |
| Early supplemental review | `0` |
| Preview без rescheduling | `0` |
| Manual/reset/reschedule | `0` |
| Duplicate source event | `0` |
| Undo | `0` |

### 6.3. Почему не используется число revlog

Количество строк истории может включать:

- learning;
- relearning;
- несколько показов одной карточки;
- early reviews;
- filtered preview;
- manual records;
- технические rescheduling records.

Поэтому оно не является числом независимых проверок долгосрочной памяти.

### 6.4. Почему не используются полные Review Units

Если включить `ContextBonus` в `QualifiedVolume`, трудная карточка получит дополнительную награду дважды:

1. за сложный конкретный эпизод;
2. за более быстрое достижение volume tiers.

Это нарушило бы принцип отсутствия двойного вознаграждения одного фактора.

## 7. VolumeCredit

### 7.1. Принятая кандидатная модель

```text
VolumeCredit =
    0.05 × clamp(Q − 10,  0, 15)
  + 0.08 × clamp(Q − 25,  0, 25)
  + 0.10 × clamp(Q − 50,  0, 50)
  + 0.12 × max(Q − 100, 0)

VolumeCredit = min(VolumeCredit, 15)
```

Где:

```text
Q = QualifiedVolume
```

### 7.2. Смысл диапазонов

```text
0–10 Q:
  обычная работа, отдельный volume bonus не нужен;

10–25 Q:
  небольшой бонус 5%;

25–50 Q:
  дополнительный диапазон 8%;

50–100 Q:
  дополнительный диапазон 10%;

выше 100 Q:
  дополнительный диапазон 12%;

общий cap:
  15 Review Units.
```

### 7.3. Примеры

| QualifiedVolume | VolumeCredit | Доля от Q |
|---:|---:|---:|
| `5` | `0.00` | `0%` |
| `10` | `0.00` | `0%` |
| `18` | `0.40` | `2.2%` |
| `25` | `0.75` | `3.0%` |
| `45` | `2.35` | `5.2%` |
| `50` | `2.75` | `5.5%` |
| `90` | `6.75` | `7.5%` |
| `100` | `7.75` | `7.8%` |
| `135` | `11.95` | `8.9%` |
| `180` | `15.00` | `8.3%` |
| `300` | `15.00` | `5.0%` |

### 7.4. Почему используется аддитивный bonus

Не используется модель:

```text
Q достиг порога
→ весь дневной reward умножается на 1.10
```

Аддитивная модель:

- не создаёт обрыв на границе tiers;
- не повышает ретроспективно стоимость всех предыдущих карточек;
- не делает одну последнюю карточку непропорционально ценной;
- сохраняет ограниченный максимальный вклад;
- не превращает марафон в обязательную стратегию эффективной прокачки.

### 7.5. Статус параметров

Форма модели считается принятой кандидатной архитектурой.

Точные значения:

- `10`, `25`, `50`, `100`;
- `5%`, `8%`, `10%`, `12%`;
- cap `15`;

должны быть проверены симуляцией.

## 8. Daily Support Cap

### 8.1. Episode cap

Reward Model уже ограничивает один lapse episode:

```text
SupportUnits одного lapse episode ≤ 0.12
```

### 8.2. Дневной cap

Принятая кандидатная формула:

```text
DailySupportCap =
min(
    3.00,
    max(0.50, 0.10 × CoreBaseline)
)
```

```text
CappedSupportUnits =
min(RawSupportUnits, DailySupportCap)
```

### 8.3. Почему существует minimum allowance

В новый Anki-день могут перейти interday relearning steps, связанные с ошибкой предыдущего дня.

Даже при небольшом новом `CoreBaseline` такая работа не должна полностью исчезнуть.

Поэтому допускается до:

```text
0.50 Support Unit
```

даже при нулевом или очень маленьком CoreBaseline.

### 8.4. Почему cap зависит от CoreBaseline

Нормальный объём relearning обычно связан с основной review-нагрузкой.

Пропорциональный cap:

- замечает реальную дополнительную работу;
- не позволяет построить весь день на циклах `Again → relearning`;
- не считает каждый шаг новым полноценным извлечением долгосрочной памяти;
- не уменьшает сам CoreBaseline.

### 8.5. Примеры

| CoreBaseline | DailySupportCap |
|---:|---:|
| `0` | `0.50` |
| `3` | `0.50` |
| `10` | `1.00` |
| `20` | `2.00` |
| `30` | `3.00` |
| `100` | `3.00` |

## 9. Daily Supplemental Cap

### 9.1. Принятая политика

Supplemental practice не должна становиться самостоятельным основным источником постоянного Review XP.

```text
DailySupplementalCap =
min(
    2.00,
    0.03 × CoreBaseline
)
```

```text
CappedSupplementalUnits =
min(RawSupplementalUnits, DailySupplementalCap)
```

### 9.2. День без core-work

Если:

```text
CoreBaseline = 0
```

то:

```text
постоянный Supplemental Review XP = 0
```

Дополнительная практика всё равно может отображаться как отдельная аналитическая метрика:

```text
Practice activity
```

Она может использоваться в будущем для:

- отчёта;
- личной статистики;
- целей практики;
- exam-preparation mode;
- достижений без постоянного XP.

### 9.3. Почему не создаётся отдельный Practice Credit сейчас

Отдельная числовая валюта усложнила бы экономику до появления доказанной продуктовой необходимости.

На текущем этапе принято:

- сохранять количество и длительность supplemental-практики;
- не конвертировать её в отдельную валюту;
- вернуться к вопросу при проектировании goals, quests или exam mode.

### 9.4. Примеры

| CoreBaseline | DailySupplementalCap |
|---:|---:|
| `0` | `0.00` |
| `10` | `0.30` |
| `30` | `0.90` |
| `50` | `1.50` |
| `100` | `2.00` |
| `300` | `2.00` |

## 10. Workload Snapshot

### 10.1. Зачем нужен snapshot

Completion нельзя определять только по текущему значению:

```text
remaining due = 0
```

Причины:

- Anki может скрывать карточки дневным review limit;
- scope может измениться во время дня;
- карточки могут синхронизироваться с другого устройства;
- пользователь может вручную изменить due dates;
- FSRS-rescheduling может создать новую нагрузку;
- filtered deck может временно переместить карточки;
- natural due и forced due имеют разный смысл.

### 10.2. Момент создания

Snapshot создаётся перед первым подтверждённым `core` Review Episode текущего Anki-дня.

Если пользователь явно выбирает дневной review-scope, он должен сделать это до первого core-эпизода.

### 10.3. Поля snapshot

```text
snapshot_id
anki_day
created_at
scope_type
scope_id
scope_hash

natural_due_at_start
overdue_at_start
due_visible_under_limits
due_hidden_by_limits
interday_learning_at_start

review_limit_at_start
scheduler_kind
scheduler_version
desired_retention
fsrs_parameter_hash

collection_lineage_id
snapshot_confidence
```

### 10.4. Natural workload

В completion workload входят:

- naturally due review cards;
- overdue review cards;
- due review cards внутри допустимого locked scope.

Не входят:

- early reviews;
- preview cards;
- cards made due вручную после snapshot;
- administrative rescheduling records;
- new cards;
- initial learning;
- supplemental practice.

Interday learning учитывается отдельно и не смешивается с Review completion до Learn XP Specification.

## 11. Completion scope

### 11.1. Допустимые scope

На текущем этапе разрешены:

```text
collection
locked_deck_subtree
```

`locked_deck_subtree` включает выбранную колоду и её дочерние колоды.

### 11.2. Фиксация scope

Scope:

- выбирается до первого core Review Episode дня;
- фиксируется на весь Anki-день;
- не может быть уменьшен задним числом;
- не меняется из-за перехода между колодами;
- не позволяет получить несколько completion bonuses за разные колоды.

### 11.3. Completion выдаётся один раз в день

```text
не более одного CompletionCredit
на один Anki Day
```

Это правило устраняет фарм через множество микроколод.

### 11.4. Минимальный meaningful scope

Отдельный жёсткий минимум количества карточек не вводится.

Причины:

- у пользователя может законно быть одна due-карточка;
- completion bonus пропорционален QualifiedVolume;
- одно событие даёт только очень маленький bonus;
- bonus выдаётся один раз на весь день;
- микроколода не позволяет повторно сбросить scope.

Пример:

```text
Q = 0.90
BaseCompletionCredit = 0.027
```

После округления такая награда может быть практически незаметной, поэтому отдельная сложная anti-micro-deck эвристика не требуется.

### 11.5. Scope, созданный после начала дня

Новая колода или изменённая структура не изменяет уже сохранённый snapshot.

Новые naturally due cards после существенного sync могут быть добавлены через reconciliation, но scope остаётся прежним.

## 12. Completion statuses

Приняты следующие статусы:

### 12.1. `collection_cleared`

Все naturally due review cards исходного collection snapshot завершены.

```text
CompletionFactor = 1.00
```

### 12.2. `scope_cleared`

Все naturally due review cards locked deck subtree завершены.

```text
CompletionFactor = 0.80
```

Меньший коэффициент отражает ограниченный scope, но сохраняет мотивацию пользователя, который осознанно работает только над выбранной областью.

### 12.3. `configured_limit_reached`

Пользователь завершил все review cards, доступные под лимитом, который существовал в snapshot, но natural due workload за лимитом остался.

```text
CompletionFactor = 0.50
```

Это не считается провалом.

### 12.4. `partial`

Часть natural workload осталась доступной и дневной лимит не был достигнут.

```text
CompletionFactor = 0
```

### 12.5. `zero_due`

В snapshot отсутствовали naturally due review cards.

```text
CompletionFactor = 0
```

Отсутствие due-нагрузки не считается ошибкой и не требует создавать фиктивную активность.

### 12.6. `snapshot_uncertain`

Система не может надёжно восстановить исходную natural workload.

```text
CompletionFactor = 0
```

Базовая награда за review сохраняется. Неопределённость убирает только completion bonus.

### 12.7. Planned target

`planned_target_reached` не даёт Review CompletionCredit в версии `v0.1`.

Причины:

- произвольную цель легко занизить;
- goal system ещё не спроектирована;
- planned target может иметь значение для будущего стрика;
- смешивание цели пользователя с natural queue требует отдельной спецификации.

Статус можно сохранять аналитически, но не использовать для постоянного Review XP до проектирования goal contracts.

## 13. CompletionCredit

### 13.1. Базовая формула

```text
BaseCompletionCredit =
min(3.00, 0.03 × QualifiedVolume)
```

```text
CompletionCredit =
CompletionFactor × BaseCompletionCredit
```

### 13.2. Примеры полного collection completion

| QualifiedVolume | CompletionCredit |
|---:|---:|
| `0.90` | `0.027` |
| `10` | `0.30` |
| `25` | `0.75` |
| `50` | `1.50` |
| `100` | `3.00` |
| `200` | `3.00` |

### 13.3. Пример scope completion

```text
Q = 50
BaseCompletionCredit = 1.50
CompletionFactor = 0.80
CompletionCredit = 1.20
```

### 13.4. Пример configured limit

```text
Q = 90
BaseCompletionCredit = 2.70
CompletionFactor = 0.50
CompletionCredit = 1.35
```

### 13.5. Почему completion остаётся небольшим

Completion должен:

- поддерживать чувство завершённости;
- не делать очередь обязательной любой ценой;
- не штрафовать пользователя за незавершение;
- не доминировать над карточками;
- не подталкивать к снижению качества ответа в конце сессии;
- не превращать лимиты Anki в средство фарма.

## 14. Изменение дневного лимита

### 14.1. Лимит из snapshot

Для `configured_limit_reached` используется лимит, сохранённый до первого core-review.

### 14.2. Снижение лимита в течение дня

Если пользователь уменьшает лимит после начала работы:

- scheduler Anki следует новой настройке;
- completion evaluation продолжает использовать исходный snapshot limit;
- уменьшение лимита не создаёт более лёгкую completion-цель текущего дня;
- новая настройка применяется к следующему Anki-дню.

### 14.3. Увеличение лимита

Если лимит увеличен:

- дополнительные выполненные карточки получают полный CoreBaseline;
- QualifiedVolume растёт;
- collection/scope completion может быть достигнут;
- `configured_limit_reached` не ухудшает уже заработанный baseline;
- snapshot сохраняет происхождение изменения.

## 15. Backlog

### 15.1. Базовая политика

```text
Backlog review
→ полный CoreBaseline
→ обычный вклад в QualifiedVolume
→ обычный VolumeCredit
```

### 15.2. Что уже ограничено предыдущими этапами

Reward и Abuse Models уже ограничивают:

- дополнительный challenge из-за просрочки;
- artificial due changes;
- schedule cycling;
- massive rescheduling artifacts.

### 15.3. Отдельный catch-up multiplier не вводится

Отдельный multiplier за сокращение backlog не нужен, потому что пользователь уже получает:

- базовую награду за каждую карточку;
- допустимый context bonus;
- volume credit;
- completion credit при соответствующем статусе.

Дополнительный multiplier повторно вознаградил бы один и тот же объём.

### 15.4. Нематериальное признание

Позже сокращение backlog может использоваться для:

- achievement;
- recovery quest;
- milestone;
- визуального индикатора;
- отдельного отчёта.

## 16. Zero-due day

Если `natural_due_at_start = 0`:

- пользователь не обязан создавать фиктивные reviews;
- CompletionCredit не начисляется;
- отсутствие Review XP не считается нарушением;
- early practice может быть показана аналитически;
- Review-компонент дня остаётся нейтральным;
- финальное решение о стрике принимается будущей объединённой Anki Day Specification.

Zero-due day особенно важен для небольших коллекций и новых пользователей. Система не должна заставлять их менять scheduling только ради игровой активности.

## 17. Review contribution bands

Эти статусы описывают только вклад Review в день. Они не являются окончательным общим статусом Anki-дня и не управляют стриком самостоятельно.

### 17.1. `review_none`

```text
QualifiedVolume = 0
```

Нет подтверждённой core-review работы.

### 17.2. `review_light`

```text
0 < QualifiedVolume < 10
```

Полезная работа была, но объём небольшой.

### 17.3. `review_substantive`

```text
10 ≤ QualifiedVolume < 25
```

Содержательный review-вклад, который может существенно участвовать в будущем общем дневном статусе.

### 17.4. `review_full`

```text
QualifiedVolume ≥ 25
```

или:

```text
QualifiedVolume ≥ 5
и
CompletionStatus ∈ {
  collection_cleared,
  scope_cleared,
  configured_limit_reached
}
```

Вторая ветка нужна для пользователя с небольшой естественной due-нагрузкой: выполнение всей доступной работы не должно выглядеть неполноценным только из-за маленькой коллекции.

### 17.5. Ограничение статусов

- `review_full` не означает автоматический глобальный `complete`;
- Learn и Create позже могут дополнять или самостоятельно формировать общий день;
- thresholds должны пройти симуляцию;
- изменение thresholds не меняет уже заработанные Review Units.

## 18. Late sync and reconciliation

### 18.1. Состояния дневного итога

```text
open
soft_final
reconciled
```

### 18.2. `open`

Текущий Anki-день продолжается.

- episode rewards отображаются;
- VolumeCredit показывается как estimated;
- CompletionCredit остаётся pending;
- Undo и новые события пересчитывают totals.

### 18.3. `soft_final`

Наступает после границы Anki-дня.

- известные эпизоды подтверждены;
- volume и completion рассчитаны по доступным данным;
- breakdown сохранён;
- итог может быть дополнен поздним sync.

### 18.4. Reconciliation window

Кандидатное окно:

```text
48 часов после границы Anki-дня
```

В течение окна:

- поздние native events добавляются к исходному дню;
- volume credit пересчитывается;
- completion status может уточняться;
- provisional duplicates и Undo корректируются;
- пользователь видит статус `sync pending` при известной несинхронизированной коллекции.

### 18.5. `reconciled`

После успешного sync либо завершения 48-часового окна день получает статус `reconciled`.

### 18.6. События после reconciliation

Позднее обнаруженные валидные events:

- получают BaselineCredit и ContextBonus по исходному Anki-дню;
- могут увеличить QualifiedVolume;
- создают положительную adjustment transaction;
- не отнимают ранее подтверждённый completion bonus только потому, что поздний sync обнаружил дополнительную natural workload;
- могут удалить reward только при детерминированном duplicate, Undo или corrupted source event согласно Abuse Model.

### 18.7. Почему completion не отзывается из-за поздней нагрузки

Пользователь не должен терять подтверждённую награду из-за того, что другое устройство поздно сообщило дополнительные due cards.

Поэтому после reconciliation completion может:

- сохраниться;
- повыситься при доказанном completion;
- получить диагностическую отметку неполного snapshot;

но не снижается только на основании поздно появившейся workload.

## 19. Derived transactions

`VolumeCredit` и `CompletionCredit` являются derived reward transactions.

Они не должны храниться только как необратимое изменение одного счётчика.

Минимальная логическая модель:

```text
source reward ledger
        ↓
day aggregation calculation
        ↓
derived volume transaction
        ↓
derived completion transaction
```

Преимущества:

- повторный расчёт после Undo;
- reconciliation после sync;
- воспроизводимость версии правил;
- объяснимый breakdown;
- отсутствие двойного начисления;
- безопасная миграция параметров.

Каждая derived transaction хранит:

```text
anki_day
rule_version
input_digest
calculated_at
amount
status
reason_code
```

## 20. Дневной pipeline

```text
1. Получить reward events исходного Anki-дня
2. Проверить source-event idempotency
3. Собрать Review Episodes
4. Применить Event Taxonomy
5. Применить Reward Model
6. Применить Abuse Model
7. Суммировать CoreBaseline
8. Суммировать разрешённый CoreContext
9. Рассчитать RawSupportUnits
10. Применить DailySupportCap
11. Рассчитать RawSupplementalUnits
12. Применить DailySupplementalCap
13. Рассчитать QualifiedVolume
14. Рассчитать VolumeCredit
15. Проверить Workload Snapshot
16. Определить CompletionStatus
17. Рассчитать CompletionCredit
18. Определить ReviewContributionBand
19. Сформировать reward breakdown
20. Сохранить derived transactions и rule version
```

После этого, но не внутри этапа 4:

```text
ReviewDayUnits
→ объединение с Learn и Create
→ конвертация в глобальный XP
→ Momentum
→ общий статус дня
→ стрик
→ уровень
```

## 21. Explainability contract

Пользователь должен видеть не только итоговую цифру.

Кандидатный breakdown:

```text
Review day

Core work:             82.40
Memory context:         8.10
Relearning support:     2.30 / cap 3.00
Supplemental practice:  0.90 / cap 2.00
Volume bonus:           6.10
Completion bonus:       2.40

Total:                102.20 Review Units
```

Дополнительные reason codes:

```text
volume_tier_1
volume_tier_2
volume_tier_3
volume_tier_4
volume_cap_reached
support_cap_applied
supplemental_cap_applied
collection_cleared
scope_cleared
configured_limit_reached
zero_due
snapshot_uncertain
sync_pending
late_positive_adjustment
```

Explainability не должна использовать обвинительные формулировки.

## 22. Подробные сценарии

### Сценарий 1. Короткий обычный день

```text
Успешных core: 10
Again:           2
Support:       0.08
```

```text
CoreBaseline =
10 × 0.90 + 2 × 0.25
= 9.50

QualifiedVolume = 9.50
VolumeCredit = 0
```

Результат:

- базовая работа полностью вознаграждена;
- маленький день не получает штраф;
- volume bonus ещё не начинается;
- contribution band: `review_light`.

### Сценарий 2. Содержательный обычный день

```text
Успешных core: 30
Again:           4
```

```text
CoreBaseline =
30 × 0.90 + 4 × 0.25
= 28.00

QualifiedVolume = 28.00
VolumeCredit =
0.75 + 0.08 × 3
= 0.99
```

Contribution band: `review_full`.

### Сценарий 3. 100 успешных core reviews

```text
CoreBaseline =
100 × 0.90
= 90.00

QualifiedVolume = 90.00
VolumeCredit = 6.75
```

Если collection workload очищена:

```text
CompletionCredit =
0.03 × 90
= 2.70
```

Базовая награда не уменьшается.

### Сценарий 4. Те же reviews в трёх сессиях

```text
Утро:   40 reviews
День:   30 reviews
Вечер:  30 reviews
```

Итог полностью совпадает со сценарием 3.

Сессии не создают отдельные tiers или caps.

### Сценарий 5. Длинная честная сессия

```text
Успешных core: 300
```

```text
CoreBaseline = 270
VolumeCredit = 15 cap
```

Система не уменьшает последние 200 карточек.

### Сценарий 6. Большое количество relearning

```text
CoreBaseline:   24
RawSupport:      5.60
DailySupportCap: 2.40
```

```text
CappedSupportUnits = 2.40
```

Ограничивается только support channel. CoreBaseline остаётся `24`.

### Сценарий 7. Interday relearning без нового core

```text
CoreBaseline: 0
RawSupport:   0.36
```

```text
DailySupportCap = 0.50
CappedSupport = 0.36
```

Реальная восстановительная работа замечена, но не создаёт полноценный core-day.

### Сценарий 8. Попытка фарма relearning

```text
CoreBaseline: 2
RawSupport:   8
```

```text
DailySupportCap = 0.50
CappedSupport = 0.50
```

Дополнительные циклы не увеличивают cap.

### Сценарий 9. Supplemental practice после core work

```text
CoreBaseline:     50
RawSupplemental:   4
```

```text
DailySupplementalCap = 1.50
CappedSupplemental = 1.50
```

### Сценарий 10. Только preview

```text
CoreBaseline: 0
Preview cards: 200
```

Результат:

```text
Permanent Review XP: 0
Practice activity: 200 cards
VolumeCredit: 0
CompletionCredit: 0
```

### Сценарий 11. Маленькая коллекция полностью завершена

```text
Naturally due: 6
Все 6 успешно повторены
CoreBaseline: 5.40
```

```text
CompletionStatus = collection_cleared
CompletionCredit = 0.162
ContributionBand = review_full
```

Пользователь получает признание полного естественного объёма без большого числового бонуса.

### Сценарий 12. Одна due-карточка

```text
Naturally due: 1
CoreBaseline: 0.90
```

```text
CompletionCredit = 0.027
```

Completion не создаёт значимого способа фарма.

### Сценарий 13. Locked deck subtree

```text
Collection due: 150
Locked scope due: 40
Scope полностью очищен
Q = 36
```

```text
BaseCompletion = 1.08
Factor = 0.80
CompletionCredit = 0.864
```

### Сценарий 14. Достигнут configured review limit

```text
Natural due: 180
Snapshot limit: 100
Выполнено доступных: 100
Осталось скрыто: 80
Q = 90
```

```text
CompletionStatus = configured_limit_reached
BaseCompletion = 2.70
Factor = 0.50
CompletionCredit = 1.35
```

Никакого штрафа за оставшиеся за лимитом карточки нет.

### Сценарий 15. Лимит уменьшен после начала дня

```text
Snapshot limit: 100
После 20 reviews лимит изменён на 20
```

Результат:

- current scheduler может остановить выдачу;
- completion evaluation остаётся привязана к snapshot limit `100`;
- уменьшение не создаёт completion bonus;
- baseline за 20 reviews сохраняется.

### Сценарий 16. Возвращение к backlog

```text
Уникальных core: 150
Многие карточки overdue
```

Результат:

- полный CoreBaseline;
- обычный QualifiedVolume;
- VolumeCredit по той же формуле;
- ContextBonus уже ограничен Reward/Abuse Models;
- отдельного catch-up multiplier нет.

### Сценарий 17. Zero-due day

```text
Natural due: 0
```

Результат:

- completion status `zero_due`;
- CompletionCredit `0`;
- Review-компонент дня нейтрален;
- пользователь не обязан запускать Review Ahead.

### Сценарий 18. Работа через календарную полночь

```text
Session: 23:30–01:00
Anki day boundary: 04:00
```

Вся работа относится к одному Anki-дню.

### Сценарий 19. Сессия пересекает Anki day boundary

```text
Session: 03:30–04:30
Anki day boundary: 04:00
```

Аналитически это одна session.

Экономически:

- events до 04:00 относятся к предыдущему дню;
- events после 04:00 относятся к новому дню;
- caps и volume tiers не переносятся между днями.

### Сценарий 20. Late sync добавляет reviews

```text
Soft-final Q: 30
Late native events: +20 Q
```

После reconciliation:

```text
Q = 50
VolumeCredit пересчитан вверх
```

Создаётся положительная adjustment transaction.

### Сценарий 21. Late sync обнаруживает дополнительную due workload

Пользователь уже получил небольшой collection completion по известному snapshot.

Поздний sync показывает, что на другом устройстве существовали дополнительные due cards.

Результат:

- ранее подтверждённый completion не отнимается;
- snapshot получает uncertainty marker;
- будущие дни используют полную синхронизированную коллекцию;
- deterministic duplicate или Undo по-прежнему могут корректировать конкретные rewards.

### Сценарий 22. Undo после показа дневного bonus

Undo удаляет исходный core event.

Результат:

- CoreBaseline пересчитывается;
- QualifiedVolume пересчитывается;
- VolumeCredit derived transaction заменяется;
- completion status может измениться;
- до reconciliation bonus остаётся provisional;
- это не считается конфискацией постоянного XP, потому что исходное действие отменено.

## 23. Принятые решения этапа 4

Предварительно приняты:

1. `Anki Day` является экономической единицей, а `Review Session` — аналитической.
2. Кандидатная граница сессии составляет 25 минут без review events.
3. Разделение или объединение сессий не меняет XP.
4. `CoreBaseline` не получает дневной diminishing returns.
5. Объём измеряется через `QualifiedVolume`, а не количество строк `revlog`.
6. `ContextBonus` не участвует в QualifiedVolume.
7. `VolumeCredit` является аддитивным, прогрессивным и имеет cap `15`.
8. `SupportUnits` имеют episode cap и day cap.
9. `SupplementalUnits` зависят от CoreBaseline и не создают постоянный Review XP без core-work.
10. Отдельный `Practice Credit` пока не вводится.
11. Completion scope фиксируется до первого core Review Episode.
12. Допускаются collection scope и один locked deck subtree.
13. CompletionCredit выдаётся не более одного раза в Anki-день.
14. Жёсткий минимум размера scope не нужен из-за пропорционального малого bonus.
15. `collection_cleared` имеет factor `1.00`.
16. `scope_cleared` имеет factor `0.80`.
17. `configured_limit_reached` имеет factor `0.50`.
18. Planned target не даёт Review CompletionCredit в v0.1.
19. CompletionCredit равен `factor × min(3, 0.03 × Q)`.
20. Backlog сохраняет полный CoreBaseline и не получает отдельный catch-up multiplier.
21. Zero-due day является нейтральным, а не провальным.
22. Review contribution bands не управляют глобальным стриком самостоятельно.
23. Дневной итог проходит `open → soft_final → reconciled`.
24. Кандидатное reconciliation window составляет 48 часов.
25. Late sync может добавить положительную adjustment transaction.
26. Поздно найденная workload сама по себе не отнимает подтверждённый completion bonus.
27. Volume и completion являются derived transactions.
28. Дневная агрегация не повторяет ограничения, уже применённые к отдельному эпизоду.
29. Подробный breakdown является обязательным.
30. Все числовые параметры должны пройти симуляцию.

## 24. Параметры для симуляции

Следующие параметры считаются выбранными кандидатами, но не финальными значениями:

- session gap `25 минут`;
- volume thresholds `10 / 25 / 50 / 100`;
- volume rates `5% / 8% / 10% / 12%`;
- volume cap `15`;
- support formula `min(3, max(0.5, 0.10 × CoreBaseline))`;
- supplemental formula `min(2, 0.03 × CoreBaseline)`;
- completion base `min(3, 0.03 × Q)`;
- completion factors `1.00 / 0.80 / 0.50`;
- contribution thresholds `10 / 25` и completion shortcut при `Q ≥ 5`;
- reconciliation window `48 часов`.

Симулятор должен сравнить минимум:

- текущую кандидатную модель;
- модель без VolumeCredit;
- модель с меньшим volume cap;
- модель без CompletionCredit;
- более строгий support cap;
- supplemental cap `0`;
- contribution thresholds `15 / 30`;
- reconciliation windows `24 / 48 / 72 часа`.

## 25. Acceptance criteria

До признания модели готовой симуляция должна показать:

1. Дробление одной работы на сессии меняет итог не более чем на погрешность округления.
2. Длинная честная сессия сохраняет 100% CoreBaseline.
3. VolumeCredit не превышает установленный cap.
4. VolumeCredit не становится главным источником дневного reward.
5. CompletionCredit не делает микроколоды выгодной стратегией.
6. Снижение review limit после snapshot не создаёт completion exploit.
7. Support и supplemental не могут доминировать над core-work.
8. Zero-due user не вынужден делать early reviews ради дневного статуса.
9. Backlog recovery остаётся хорошо вознаграждённым без отдельного multiplier.
10. Late sync не создаёт двойное начисление.
11. Поздняя workload не вызывает необъяснимую потерю уже подтверждённого XP.
12. Undo корректно пересчитывает derived transactions.
13. Review contribution bands разумно работают для маленьких и больших коллекций.
14. Обычный день остаётся понятным без изучения формул.
15. Итоговый breakdown полностью воспроизводим по source ledger и rule version.

## 26. Следующий этап

Следующий документ:

```text
anki-review-simulation-spec.md
```

Он должен определить:

- формат synthetic personas;
- импорт и анонимизацию реальных review histories;
- набор честных и exploit-сценариев;
- сравниваемые варианты параметров;
- метрики справедливости;
- метрики устойчивости к abuse;
- распределение Review Units по пользователям и дням;
- влияние параметров на длинные сессии, backlog и маленькие коллекции;
- критерии выбора окончательной модели;
- формат отчёта симуляции.

## Stage 5B.C matched-history clarification

Backlog evidence requires a full pre-delay, delay, catch-up, and post-catch-up
stabilization horizon on the same card lineages. Analytical session partition
remains reward-neutral: the same Anki-day events in one or several sessions
must produce zero delta. Longitudinal policy names and iteration order do not
participate in child-seed derivation.
