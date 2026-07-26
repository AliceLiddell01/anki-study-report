# Learn XP — lifecycle и anti-farming model G2.2

**Model ID:** `learn-xp-lifecycle-model`  
**Version:** `1`  
**Status:** `FROZEN_PRE_CANDIDATE_DESIGN`  
**Stage:** `G2.2 — Learning lifecycle and anti-farming model`  
**Production integration:** `PROHIBITED`  
**G2.3:** `NEXT / NOT STARTED`

Нормативные machine-readable источники:

- [`learn-xp-lifecycle-model-v1.json`](../../research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json);
- [`learn-xp-lifecycle-model-v1.schema.json`](../../research/gamification-sim/schemas/learn-xp-lifecycle-model-v1.schema.json);
- [`learn-xp-lifecycle-fixture-v1.schema.json`](../../research/gamification-sim/schemas/learn-xp-lifecycle-fixture-v1.schema.json);
- [fixture manifest](../../research/gamification-sim/fixtures/learn-xp-lifecycle-v1/manifest.json).

Frozen source contract: [G2.1 Learn XP problem contract](learn-xp-problem-contract.md).

## 1. Назначение

G2.2 формализует lifecycle одного исследовательского Learn XP achievement, не выбирая числовую экономику и production architecture.

Модель отвечает на вопросы:

- какой объект владеет уникальностью achievement;
- какая bounded последовательность событий образует его lifecycle;
- какие состояния и transitions допустимы;
- какое evidence можно наблюдать или выводить;
- какие данные запрещено угадывать;
- как fail closed при missing/conflicting continuity;
- как нейтрализовать repetition, configuration, object, lifecycle, session/time и answer-behavior farming.

Модель не вычисляет XP и не утверждает mastery.

## 2. Source continuity

G2.2 сохраняет G2.1 contract v1 без semantic amendment:

```text
contract:
research/gamification-sim/contracts/learn-xp-problem-contract-v1.json

contract blob:
cef3a60bac31eab12faf40f1f2d27221dafc6cc4

schema:
research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json

schema blob:
cf342aa3c62747f45d526ac7953005d66266f404

source commit:
698fd6f7563b358bdd6c93a2ff1ab4a9d1ef1db9
```

Сохранены:

- три achievement-subject candidates: `CARD`, `NOTE`, `SIBLING_GROUP`;
- `LEARNING_EPISODE` как отдельный identity candidate из G2.1;
- шесть threat families;
- 19 protected invariants;
- отсутствие выбранных amount, ratio, delay, candidate family и production approval.

## 3. Official Anki boundary

Официальные Anki scheduler states:

```text
ANKI_STATE_NEW
ANKI_STATE_LEARNING
ANKI_STATE_REVIEW
ANKI_STATE_RELEARN
```

Learn XP lifecycle использует отдельный namespace:

```text
NOT_STARTED
IN_PROGRESS
PENDING
CONFIRMED
EXPIRED
CANCELLED
INVALIDATED
```

Следствия:

- Anki scheduler state не является Learn XP reward state;
- `New → Learning` не является доказательством learning;
- завершение learning steps не подтверждает Learn XP автоматически;
- `Review` не подтверждает achievement автоматически;
- `Relearn` не создаёт новый initial-learning achievement;
- G2.2 не меняет scheduler, FSRS, due dates или displayed intervals.

Официальные reference pages:

- <https://docs.ankiweb.net/getting-started.html#card-states>
- <https://docs.ankiweb.net/deck-options.html#learning-steps>
- <https://docs.ankiweb.net/deck-options.html#relearning-steps>
- <https://docs.ankiweb.net/studying.html#answer-buttons>
- <https://docs.ankiweb.net/filtered-decks.html>
- <https://docs.ankiweb.net/browsing.html>

## 4. Factorized identity architecture

G2.2 принимает factorized interpretation:

```text
LearningEpisode<AchievementSubject>
```

### Achievement subject candidates

```text
CARD
NOTE
SIBLING_GROUP
```

Achievement subject отвечает:

> Какой объект владеет уникальностью одного initial-learning achievement?

### Lifecycle container

```text
LEARNING_EPISODE
```

Learning episode отвечает:

> Какая bounded ordered sequence событий образует lifecycle этого achievement?

Примеры:

```text
LearningEpisode<CARD>
LearningEpisode<NOTE>
LearningEpisode<SIBLING_GROUP>
```

Это архитектурное разделение, а не выбор победителя.

```text
achievement-subject winner: NONE
```

Все три subject candidates передаются в G2.3.

## 5. Lifecycle states

### `NOT_STARTED`

- valid progress отсутствует;
- exposure, answer reveal или preview не продвигают state;
- reward не создаётся.

### `IN_PROGRESS`

- существует первый valid attempt или bounded progress;
- pending и confirmed ещё отсутствуют;
- дополнительные learning steps не создают новые achievements.

### `PENDING`

- provisional и non-spendable;
- создаётся не чаще одного раза для achievement;
- не размножается retries или `Again` loops;
- ожидает independent confirmation либо terminal outcome.

### `CONFIRMED`

- существует typed independent-success signal для того же subject;
- это не mastery;
- state terminal для одного achievement;
- retry, reset и reimport не создают повторную confirmation.

### `EXPIRED`

- pending завершён без confirmation;
- numeric expiry duration не выбрана;
- negative XP отсутствует;
- fresh eligibility автоматически не создаётся.

### `CANCELLED`

- active source event отменён через provenance-linked Undo;
- cancellation не используется как общий fallback для ambiguity;
- state terminal.

### `INVALIDATED`

- identity, ordering, provenance или continuity не позволяют безопасно продолжить;
- ambiguity не mint reward;
- state terminal и не создаёт automatic fresh eligibility.

## 6. Main transitions

```text
NOT_STARTED → IN_PROGRESS
IN_PROGRESS → IN_PROGRESS
IN_PROGRESS → PENDING
PENDING → CONFIRMED
PENDING → PENDING
PENDING → EXPIRED
IN_PROGRESS/PENDING → CANCELLED
IN_PROGRESS/PENDING → INVALIDATED
```

Обязательные semantics:

- exposure/show-answer/preview — no-op;
- repeated pending request — idempotent;
- same-chain success сохраняет `PENDING`;
- independent failure сохраняет `PENDING` без penalty;
- independent success может перевести `PENDING → CONFIRMED`;
- Undo переводит active lifecycle в `CANCELLED`;
- missing/conflicting continuity переводит active lifecycle в `INVALIDATED`;
- terminal states не открывают fresh eligibility.

Каждый transition записывает decomposable ledger:

```text
event_id
sequence_index
from_state
to_state
reason_code
subject_key
episode_id
```

## 7. Confirmation abstraction

Abstract predicate:

```text
is_independent_confirmation_signal(event, episode, subject)
```

Confirmation требует:

- тот же achievement subject;
- processed `source_event_id`;
- separation от same-chain repetition;
- typed `INDEPENDENT_SUCCESS`;
- valid provenance;
- stable или explicit continuity.

Недостаточно:

- `Good` или `Easy` сами по себе;
- scheduler state `Review`;
- configured step count;
- manual reschedule;
- filtered-deck repetition;
- answer reveal;
- response time.

Numeric confirmation delay остаётся решением G2.3.

## 8. Honest Again

`Again`:

- не создаёт negative XP;
- не отменяет achievement identity;
- не mint новый pending;
- не увеличивает reward;
- не подтверждает;
- не должен стимулировать `Hard` misreport.

Failed independent delayed retrieval:

```text
PENDING → PENDING
reason: DELAYED_FAILURE_NO_CONFIRMATION
penalty: NONE
```

`Hard` с тем же typed failure signal получает тот же lifecycle result, что честный `Again`.

## 9. Observable, derived и forbidden inputs

### Observable synthetic inputs

```text
synthetic_event_id
event_kind
sequence_index
synthetic_card_id
synthetic_note_id
synthetic_sibling_group_id
synthetic_episode_id
scheduler_state_before
scheduler_state_after
rating
answer_revealed
anki_day_index
monotonic_time_index
session_id
preset_id
learning_step_profile_id
source_event_id
provenance_status
signal_status
continuity_status
```

### Derived inputs

```text
same_chain_relation
independent_signal_relation
achievement_subject_key
episode_membership
continuity_status
duplicate_event_status
terminal_state_status
```

### Forbidden inferences

```text
actual correctness beyond typed synthetic signal
mastery
motivation
retention improvement
semantic equivalence from card text
concept identity
real-world cheating intent
```

## 10. Missing and ambiguous data

Typed actions:

```text
REJECT_EVENT
IGNORE_NON_REWARDABLE_EVENT
INVALIDATE_EPISODE
PRESERVE_CURRENT_STATE
```

Policy:

- missing subject identity → `INVALIDATE_EPISODE`;
- missing episode identity → `INVALIDATE_EPISODE`;
- out-of-order events → `REJECT_EVENT`;
- duplicate event ID → `REJECT_EVENT`;
- missing source linkage for independent retrieval → `REJECT_EVENT`;
- ambiguous confirmation relation → `PRESERVE_CURRENT_STATE`;
- unknown scheduler mapping alone → `PRESERVE_CURRENT_STATE`;
- non-rewardable ambiguity → `IGNORE_NON_REWARDABLE_EVENT`;
- forbidden/private input → `REJECT_EVENT`.

Silent defaults для identity, ordering, duplicate detection и confirmation relation запрещены.

## 11. Reset, Forget, delete и reimport

### Reset / Forget

- не создаёт новое achievement;
- не увеличивает reward;
- не переводит `CONFIRMED` в fresh eligible;
- active lifecycle с valid continuity сохраняет state;
- active lifecycle с lost/ambiguous continuity становится `INVALIDATED`.

### Delete / reimport

- explicit continuity сохраняет state;
- stable identity сохраняет state;
- missing/ambiguous continuity active lifecycle → `INVALIDATED`;
- confirmed history сохраняет `CONFIRMED`, но не открывает fresh eligibility;
- duplicate import не умножает achievement;
- private content fingerprint запрещён.

## 12. Configuration invariance

Эквивалентными для lifecycle eligibility считаются:

```text
one intraday step
multiple intraday steps
interday step
empty steps / FSRS short-term scheduling
preset change during episode
relearning steps
filtered-deck route
```

Количество steps, preset и displayed interval не являются reward quantity.

## 13. Session and time invariance

Lifecycle зависит от:

- validated event order;
- subject continuity;
- episode continuity;
- abstract signal relation.

Lifecycle не зависит от:

- process lifetime;
- количества session IDs;
- session splitting;
- restart;
- timezone string;
- wall-clock `now`;
- response duration.

`monotonic_time_index` используется только для deterministic ordering, а не для reward.

## 14. Button and reveal semantics

Fixtures разделяют:

```text
question shown
answer shown
rating recorded
typed retrieval signal
```

Правила:

- `Show Answer` alone — non-rewardable;
- preview — non-rewardable;
- rating alone — no-op для reward state;
- `Hard`, `Good`, `Easy` не имеют direct reward price;
- `Easy` не обходит independent confirmation;
- response speed не создаёт reward path.

## 15. Deterministic fixture package

Fixture root:

```text
research/gamification-sim/fixtures/learn-xp-lifecycle-v1/
```

Frozen categories:

```text
ordinary/
terminal/
identity/
missing-data/
threats/
invariance/
```

Exact fixture count:

```text
23
```

Manifest digest:

```text
4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
```

Required threat fixtures:

```text
FIX-REPETITION-AGAIN-GOOD-LOOP
FIX-CONFIG-STEPS-EQUIVALENCE
FIX-OBJECT-DUPLICATE-REVERSE-CLOZE
FIX-LIFECYCLE-RESET-REIMPORT
FIX-SESSION-DAY-CLOCK-INVARIANCE
FIX-ANSWER-RATING-REVEAL-NEUTRALITY
```

Fixtures are a bounded conformance corpus, not a screening matrix.

## 16. Protected invariants

Все 19 G2.1 invariants mapped.

Repository-boundary verification:

```text
INV-SCHEDULER-UNCHANGED
INV-FSRS-UNCHANGED
INV-DUE-DATES-UNCHANGED
INV-RESEARCH-ONLY
INV-NO-REAL-USER-DATA
INV-NO-PRODUCTION-APPROVAL
```

Executable model/fixture verification:

```text
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
```

Hard invariant failure cannot be compensated by another score.

## 17. Research-only evaluator

Implementation:

```text
research/gamification-sim/src/gamification_sim/learn_lifecycle.py
```

Properties:

- pure deterministic evaluation;
- immutable typed events and results;
- no Anki imports;
- no production imports;
- no filesystem writes in evaluator;
- no wall-clock reads;
- no random;
- no environment-dependent ordering;
- typed transition ledger;
- duplicate replay idempotency;
- strict event-order validation;
- canonical SHA-256 result digest;
- no numeric XP.

Public conceptual entrypoint:

```text
evaluate_lifecycle(events) -> LifecycleResult
```

CLI не добавлен: G2.2 does not require a new command surface.

## 18. Methodological boundary

Peer-reviewed spacing/retrieval literature используется только для двух ограниченных решений:

- same-chain repetition не считается эквивалентом более независимого retrieval;
- exact useful spacing зависит от task и retention horizon.

References:

- Karpicke & Bauernschmidt (2011), PMID 21574747;
- Kang et al. (2014), PMID 24744260;
- Cepeda et al. (2008), PMID 19076480.

Из этих работ не выводятся numeric confirmation delay, reward amount, mastery или motivation/retention claims для продукта.

## 19. G2.3 handoff

Следующий этап:

```text
G2.3 — Candidate protocol and hypothesis design
```

Передаются:

- frozen states/events/transitions;
- factorized identity architecture;
- unresolved subject candidates;
- abstract confirmation predicate;
- fixture manifest и digest;
- six-threat coverage;
- 19-invariant mapping;
- prohibited assumptions.

G2.3 может позже определить candidate families, subject models для сравнения, exact confirmation delays, pending ratios/amounts и screening matrix.

G2.2 этого не делает.

## 20. Decision flags

```text
lifecycle_defined: true
factorized_identity_evaluated: true
fixture_manifest_frozen: true

achievement_subject_selected: false
reward_amount_selected: false
pending_ratio_selected: false
confirmation_delay_selected: false
candidate_family_selected: false
screening_executed: false
production_approved: false
production_integration: false
g2_3_started: false
```
