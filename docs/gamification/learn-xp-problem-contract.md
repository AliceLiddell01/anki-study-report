# Learn XP — контракт проблемы и границ G2.1

**Contract ID:** `learn-xp-problem-contract`
**Version:** `1`
**Status:** `FROZEN_PRE_LIFECYCLE_ANALYSIS`
**Stage:** `G2.1 — Freeze Learn XP problem and contract`
**Production integration:** `PROHIBITED`
**G2.2:** `NEXT / NOT STARTED`

Нормативный machine-readable источник: [`learn-xp-problem-contract-v1.json`](../../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json). Его проверяет строгая Draft 2020-12 schema [`learn-xp-problem-contract-v1.schema.json`](../../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json).

## 1. Назначение

G2 — отдельный research/product domain. Он не наследует Review XP formula, candidate families, matrices или outcome G1.

Замороженный problem statement:

> Learn XP должна поощрять доказуемое продвижение нового материала от первого валидного учебного взаимодействия к более сильному, независимо подтверждённому learning signal, не вознаграждая количество кликов, learning steps, failures, reset cycles, duplicate objects или настройки scheduler.

Главный invariant:

> Пользователь не должен получать больше Learn XP за то, что сделал обучение менее эффективным, более дробным, более повторяемым или более манипулируемым.

G2.1 определяет problem, terminology, candidate identity set, минимальные pending/confirmation requirements, threat model, protected invariants и entry contract G2.2. Он не выбирает формулу, amount, ratio, delay, winner identity или simulation matrix.

## 2. Источники и граница выводов

### 2.1. Официальная семантика Anki

Официальная документация Anki определяет состояния `New`, `Learning`, `Review` и `Relearn`:

- [Card States](https://docs.ankiweb.net/getting-started.html#card-states);
- [Learning Steps](https://docs.ankiweb.net/deck-options.html#learning-steps);
- [Relearning Steps](https://docs.ankiweb.net/deck-options.html#relearning-steps);
- [Answer Buttons](https://docs.ankiweb.net/studying.html#answer-buttons).

Из этих источников используется только следующее:

- `New` — карточка, которая ещё не изучалась;
- `Learning` — карточка в первоначальных learning steps;
- `Review` — карточка, завершившая initial learning;
- `Relearn` — забытая review-карточка, проходящая восстановление;
- learning steps задают число повторений и интервалы;
- кнопки меняют scheduler path и отражают самооценку пользователя.

Не выводится:

- что `New → Learning` доказывает learning;
- что число steps измеряет learning quantity;
- что `Review` автоматически означает confirmed Learn XP;
- что rating является объективной истиной;
- что `Relearn` создаёт новое initial-learning achievement.

### 2.2. Методологические источники

Используются как ограниченная methodological evidence:

- Karpicke & Bauernschmidt, 2011 — [Spaced retrieval](https://pubmed.ncbi.nlm.nih.gov/21574747/);
- Kang et al., 2014 — [Expanding or equal-interval retrieval](https://pubmed.ncbi.nlm.nih.gov/24744260/);
- Cepeda et al., 2008 — [Spacing effects and retention interval](https://pubmed.ncbi.nlm.nih.gov/19076480/).

Поддерживаемый вывод:

- repeated retrieval может поддерживать long-term retention;
- spacing и независимость последующей проверки имеют значение;
- exact useful schedule зависит от task и retention interval;
- same-chain short-term success слабее независимого delayed signal.

Эти работы не определяют:

- точный confirmation delay;
- оптимальный learning-step preset;
- XP amount или pending ratio;
- mastery конкретного пользователя;
- улучшение motivation/retention из-за Learn XP.

### 2.3. Внутренние reference

Review XP документы используются только как reference исследовательской дисциплины:

- [Review event taxonomy](anki-review-event-taxonomy.md);
- [Review reward model](anki-review-reward-model.md);
- [Review abuse model](anki-review-abuse-model.md);
- [Review session/day model](anki-review-session-and-day.md);
- [Review simulation specification](anki-review-simulation-spec.md);
- [G1 process and final decision](../../roadmap/gamification/g1-review-xp-decision.md).

Переиспользуются: typed contracts, fail-closed validation, button neutrality, honest `Again`, session invariance, deterministic replay, privacy и research-only boundary.

Не переиспользуются: Review Units, AttemptCredit/OutcomeCredit, MemoryGain, Review candidates, matrices, thresholds или G1 outcome.

## 3. Terminology freeze

| Term | Значение G2 |
|---|---|
| `NEW` | Официальное состояние Anki до первого изучения. |
| `INITIAL_LEARNING` | Research-домен продвижения нового материала; не официальный Anki state. |
| `EXPOSURE` | Показ вопроса/ответа без достаточной самостоятельной попытки. |
| `ATTEMPT` | Наблюдаемое взаимодействие, которое ещё не признано валидным. |
| `VALID_ATTEMPT` | Attempt, прошедший prospectively defined integrity/eligibility requirements. |
| `SHORT_TERM_SUCCESS` | Успех внутри same-chain repetition; не независимое подтверждение. |
| `LEARNING_PROGRESS` | Bounded progress в research lifecycle, не mastery. |
| `PENDING_REWARD` | Временный research state, не confirmed learning и не spendable XP. |
| `CONFIRMATION_SIGNAL` | Independent delayed retrieval или prospectively defined equivalent. |
| `CONFIRMED_REWARD` | Research reward с более сильным signal; не mastery claim. |
| `EXPIRATION` | Завершение pending lifecycle без confirmation. |
| `CANCELLATION` | Отмена pending из-за Undo/отмены исходного event. |
| `INVALIDATION` | Fail-closed прекращение eligibility при запрещённых/повреждённых данных. |
| `RESET` | Administrative reset/Forget; не новый achievement. |
| `RELEARNING` | Восстановление ранее изученного Review material, не initial learning автоматически. |
| `IDENTITY_UNIT` | Объект уникальности одного Learn achievement. |
| `LEARNING_EPISODE` | Bounded grouping initial-learning events; не session-open и не step count. |
| `INDEPENDENT_DELAY` | Разделение signals от same-chain repetition; exact duration не выбрана. |
| `FARMING` | Synthetic strategy, увеличивающая reward без сопоставимого нового achievement. |

`Anki scheduler state` и `Learn XP research state` — разные namespaces.

## 4. Card-state boundary

Заморожены требования:

```text
scheduler state != reward state
New → Learning != proof of learning
learning step count != learning quantity
Review != automatic confirmed Learn XP
Relearn != new initial learning automatically
G2 does not modify scheduler semantics
```

`Again`, `Hard`, `Good`, `Easy` могут быть evidence inputs. Ни одна кнопка не получает самостоятельную положительную XP-цену. Модель обязана защищать честный `Again` и не стимулировать `Hard` при забывании.

## 5. Identity candidate set

G2.1 допускает ровно четыре research candidates и не выбирает winner.

| Candidate | Сильная сторона | Главный риск |
|---|---|---|
| `CARD` | отдельный prompt/retrieval task; высокая observability | reverse/cloze/template/duplicate proliferation |
| `NOTE` | сдерживает multiplication siblings | одна note может содержать несколько фактов и directions |
| `SIBLING_GROUP` | явно моделирует sibling hints/proliferation | group identity, burying и partial completion неоднозначны |
| `LEARNING_EPISODE` | естественно связывает retries и pending lifecycle | session/restart/reset/day-boundary episode farming |

`CONTENT_FINGERPRINT` и `CONCEPT` не входят в v1: current research/data boundary не даёт безопасной, стабильной и объяснимой identity без чтения content или создания production semantic layer.

Для всех candidates обязательны synthetic identifiers. Real card text, note fields и media не используются.

## 6. Pending boundary

`PENDING_REWARD`:

- не является confirmed learning;
- не создаётся за каждый learning step;
- не размножается в `Again` loop;
- не зависит от configured step count;
- не является production-spendable value;
- имеет bounded lifecycle;
- может стать `confirmed`, `cancelled`, `expired` или `invalidated`.

G2.1 не утверждает, что pending обязательно войдёт в final research model, и не выбирает amount или ratio.

## 7. Confirmation boundary

`CONFIRMED_REWARD`:

- требует signal сильнее same-chain repetition;
- требует independent delayed retrieval или prospectively defined equivalent;
- не выводится из количества learning steps;
- не создаётся повторно для того же achievement без explicit eligibility;
- не доказывает mastery.

Exact delay, lifecycle transition и equivalent signal определяются не раньше G2.2 и последующих prospective stages.

## 8. Rewardable и non-rewardable boundary

Potential future categories, без amount:

```text
FIRST_VALID_ENCOUNTER
VALID_INITIAL_ATTEMPT
BOUNDED_INITIAL_LEARNING_PROGRESS
INDEPENDENT_DELAYED_SUCCESSFUL_RETRIEVAL
```

Они являются только candidate categories.

Явно non-rewardable сами по себе:

```text
question exposure
Show Answer
preview/browser preview
card edit
deck/session open
time spent
response speed
configured step count
Again loop
manual reset/Forget
duplicate import/card/template
filtered-deck repetition
scheduler reschedule
relearning
button selection
```

## 9. Learning-step invariance

Final eligible Learn XP для одного achievement не растёт только из-за:

- большего количества learning steps;
- меньших intraday intervals;
- interday step;
- пустого списка steps;
- повторного прохождения step;
- изменения preset после начала episode.

G2.2 обязана формализовать equivalence classes и deterministic fixtures. G2.1 не выбирает implementation.

## 10. Threat taxonomy

| Threat | Required trace | Защищаемый принцип |
|---|---|---|
| `REPETITION_FARMING` | `Again → Good → Again → Good` | retries не размножают achievement |
| `CONFIGURATION_FARMING` | изменение learning/relearning steps и preset | configuration invariance |
| `OBJECT_FARMING` | duplicates, reverse, cloze, siblings | duplicate objects не умножают achievement |
| `LIFECYCLE_FARMING` | learn → reset/Forget/delete/reimport → learn | reset не mint новый achievement |
| `SESSION_TIME_FARMING` | session split/restart/day/clock change | session/time invariance |
| `ANSWER_BEHAVIOR_FARMING` | Hard вместо Again, Easy acceleration, fail/reveal | buttons are evidence, not prices |

Это synthetic threat model. Он не утверждает, что реальные пользователи применяют эти strategies.

## 11. Protected invariants

Machine contract содержит 19 non-negotiable invariants:

```text
INV-SCHEDULER-UNCHANGED
INV-FSRS-UNCHANGED
INV-DUE-DATES-UNCHANGED
INV-BUTTON-DIRECT-REWARD-NEUTRAL
INV-HONEST-AGAIN-NOT-PUNISHED
INV-NO-HARD-MISREPORT-INCENTIVE
INV-NO-STEP-COUNT-GAIN
INV-NO-RESPONSE-TIME-REWARD
INV-SESSION-INVARIANT
INV-CONFIGURATION-INVARIANT
INV-RESET-DOES-NOT-MINT-NEW-ACHIEVEMENT
INV-DUPLICATE-OBJECTS-DO-NOT-MULTIPLY-ACHIEVEMENT
INV-PENDING-BOUNDED
INV-CONFIRMATION-REQUIRES-INDEPENDENT-SIGNAL
INV-DETERMINISTIC-REPLAY
INV-DECOMPOSABLE-EVIDENCE
INV-RESEARCH-ONLY
INV-NO-REAL-USER-DATA
INV-NO-PRODUCTION-APPROVAL
```

Hard-gate failures нельзя компенсировать aggregate score или «least-bad» selection.

## 12. Privacy и security boundary

Разрешены:

```text
synthetic_card_id
synthetic_note_id
synthetic_sibling_group_id
synthetic_episode_id
synthetic_event_id
synthetic_fixture_id
```

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
```

Frontend не получает прямой collection access. Loopback, token, sanitizer, media validation и action allowlists не меняются.

## 13. Claims boundary

Допустимо утверждать только:

- модель записывает bounded initial-learning signal;
- модель invariant к перечисленным synthetic farming traces;
- protected technical surfaces сохранены;
- frozen fixtures детерминированы.

Запрещено утверждать:

- пользователь выучил или освоил concept;
- Learn XP улучшает motivation;
- Learn XP улучшает retention;
- rating объективно правдив;
- candidate production-ready;
- модель предотвращает весь gaming.

## 14. G2.2 entry contract

`G2.2 — Learning lifecycle and anti-farming model` обязана:

1. построить typed lifecycle;
2. отделить scheduler state от reward state;
3. определить transitions `pending/confirmed/expired/cancelled/invalidated`;
4. формализовать поведение всех identity candidates;
5. создать deterministic event traces;
6. создать fixtures для шести threat families;
7. определить observable inputs;
8. определить missing/ambiguous data behavior;
9. не выбирать XP amounts;
10. не запускать candidate screening;
11. не менять production code.

G2.2 не начата этим контрактом.

## 15. Allowed final G2 outcomes

Ровно:

```text
RECOMMEND_LEARN_XP_RESEARCH_MODEL
REJECT_LEARN_XP_MODEL
DEFER_LEARN_XP_MODEL
```

`RECOMMEND_LEARN_XP_RESEARCH_MODEL` означает только recommended research model. Production approval остаётся отдельным решением.

## 16. Versioning

После valid publication v1 имеет status `FROZEN_PRE_LIFECYCLE_ANALYSIS`.

Substantive amendment требует:

```text
new version
rationale
field-level diff
prior-evidence impact
results-viewed disclosure
required reruns
roadmap decision
```

Typo/link correction может сохранить version только при неизменной decision semantics.

## 17. Решения, намеренно не принятые

```text
identity winner: NONE
exact lifecycle: NOT SELECTED
reward amount: NOT SELECTED
pending ratio: NOT SELECTED
confirmation delay: NOT SELECTED
candidate family: NOT SELECTED
simulation matrix: NOT DEFINED
simulation executed: NO
production approved: NO
production integration: PROHIBITED
G2.2 started: NO
```
