# G2.2 — Learn XP lifecycle and anti-farming model closeout

**Статус:** Complete  
**Режим:** ChatGPT  
**Repository:** `AliceLiddell01/anki-study-report`  
**Target branch:** `gamification`  
**Starting HEAD:** `698fd6f7563b358bdd6c93a2ff1ab4a9d1ef1db9`  
**Pre-conformance model SHA:** `63741bcc4d757cd131ab94d9e262042679460d6f`  
**Task branch:** `chatgpt/g2-2-learn-xp-lifecycle`

## 1. Итог

```text
G2: IN PROGRESS
G2.1: COMPLETE
G2.2: COMPLETE
Learn XP lifecycle model: FROZEN_PRE_CANDIDATE_DESIGN
G2.3: NEXT / NOT STARTED

production approved: NO
production integration: PROHIBITED
```

G2.2 определил research-only typed lifecycle Learn XP, отделил achievement subject от lifecycle container, формализовал observable/derived/forbidden inputs, fail-closed missing-data behavior, deterministic transitions и bounded anti-farming fixtures.

Этап не выбирает XP amount, pending ratio, numeric confirmation delay, achievement-subject winner, candidate family или screening matrix. G2.3 не запускался.

## 2. Непрерывность G2.1

Frozen G2.1 contract и schema были проверены до mutation:

```text
source commit:
698fd6f7563b358bdd6c93a2ff1ab4a9d1ef1db9

problem contract blob:
cef3a60bac31eab12faf40f1f2d27221dafc6cc4

problem schema blob:
cf342aa3c62747f45d526ac7953005d66266f404

G2_1_CONTINUITY:
PASS
```

G2.1 status сохранился как:

```text
FROZEN_PRE_LIFECYCLE_ANALYSIS
```

Ни один selection, simulation или production flag G2.1 не был изменён.

## 3. Опубликованные артефакты

```text
docs/gamification/learn-xp-lifecycle-model.md
research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json
research/gamification-sim/schemas/learn-xp-lifecycle-model-v1.schema.json
research/gamification-sim/schemas/learn-xp-lifecycle-fixture-v1.schema.json
research/gamification-sim/src/gamification_sim/learn_lifecycle.py
research/gamification-sim/tests/test_learn_lifecycle.py
research/gamification-sim/fixtures/learn-xp-lifecycle-v1/
```

Closeout и status indexes:

```text
roadmap/gamification/g2-learn-xp-lifecycle.md
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
research/gamification-sim/README.md
roadmap/README.md
roadmap/gamification/README.md
```

## 4. Lifecycle model

Заморожено семь состояний:

```text
NOT_STARTED
IN_PROGRESS
PENDING
CONFIRMED
EXPIRED
CANCELLED
INVALIDATED
```

Модель содержит:

```text
states: 7
events: 20
transitions: 12
```

`CONFIRMED` означает только один bounded achievement, подкреплённый более сильным independent signal. Это не означает mastery.

`PENDING` остаётся provisional и non-spendable. Он имеет bounded terminal paths:

```text
CONFIRMED
EXPIRED
CANCELLED
INVALIDATED
```

## 5. Factorized identity architecture

Принята архитектура:

```text
LearningEpisode<AchievementSubject>
```

Результат G2.2:

- `LEARNING_EPISODE` — lifecycle container;
- `CARD`, `NOTE`, `SIBLING_GROUP` — achievement-subject candidates;
- subject winner не выбран;
- architecture status — `FACTORIZED`;
- candidate comparison передан в G2.3.

Это устраняет ложную развилку между subject identity и episode grouping: они являются ортогональными слоями.

## 6. Scheduler/reward boundary

Официальные Anki scheduler states и Learn XP lifecycle states остаются раздельными.

```text
Anki scheduler state != Learn XP lifecycle state
```

Learning steps, ratings, filtered-deck route, session boundaries, clock/day boundaries и scheduler rescheduling не создают reward сами по себе.

Официальные methodological references:

- [Anki Manual — Card States](https://docs.ankiweb.net/getting-started.html#card-states)
- [Anki Manual — Learning Steps](https://docs.ankiweb.net/deck-options.html#learning-steps)
- [Anki Manual — Filtered Deck Steps and Returning](https://docs.ankiweb.net/filtered-decks.html#steps--returning)
- [Anki Manual — Studying and Answer Buttons](https://docs.ankiweb.net/studying.html)

Внешняя документация определяет scheduler semantics, но не выбирает Learn XP amount, ratio, delay или achievement subject.

## 7. Honest Again и confirmation

Зафиксировано:

- honest `Again` не отменяет identity и не создаёт отрицательную награду;
- `Again` не mint-ит pending и не подтверждает achievement;
- `Hard` не может давать преимущество перед честным `Again`;
- same-chain success не является independent confirmation;
- failed delayed retrieval сохраняет pending без наказания;
- exact confirmation delay не выбран;
- rating alone недостаточен.

Confirmation predicate остаётся абстрактным:

```text
is_independent_confirmation_signal(event, episode, subject)
```

## 8. Reset, reimport и missing data

Зафиксировано:

```text
reset/Forget:
preserve state with valid continuity; never mint

confirmed reset/reimport:
preserve confirmed; no fresh eligibility

pending with lost continuity:
invalidate

missing or conflicting subject:
invalidate episode

ambiguous confirmation relation:
preserve current state

duplicate event:
reject or ignore through typed duplicate handling
```

Private content fingerprint запрещён. Реальные card text, note fields, media, profile paths, tokens и raw revlog не используются.

## 9. Fixture manifest

```text
fixture count: 23
fixture IDs: 23
threat fixtures: 6
threat families: 6
protected invariants: 19

manifest digest:
4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
```

Digest проверяется как detached canonical SHA-256: поле `manifest_digest` временно обнуляется перед canonical serialization.

Категории:

```text
identity: 3
invariance: 2
missing-data: 2
ordinary: 6
terminal: 4
threats: 6
```

## 10. Threat coverage

Все шесть G2.1 threat families имеют обязательные fixtures:

```text
REPETITION_FARMING
CONFIGURATION_FARMING
OBJECT_FARMING
LIFECYCLE_FARMING
SESSION_TIME_FARMING
ANSWER_BEHAVIOR_FARMING
```

Fixture registry:

```text
FIX-REPETITION-AGAIN-GOOD-LOOP
FIX-CONFIG-STEPS-EQUIVALENCE
FIX-OBJECT-DUPLICATE-REVERSE-CLOZE
FIX-LIFECYCLE-RESET-REIMPORT
FIX-SESSION-DAY-CLOCK-INVARIANCE
FIX-ANSWER-RATING-REVEAL-NEUTRALITY
```

## 11. Protected invariants

Все 19 G2.1 invariants mapped:

- executable lifecycle invariants — `PROVEN_BY_FIXTURE`;
- production/scheduler/privacy boundaries — `REPOSITORY_BOUNDARY`.

Hard failures не компенсируются score.

## 12. Research-only evaluator

`learn_lifecycle.py`:

- не импортирует Anki, `aqt` или production package;
- не читает collection;
- не использует filesystem side effects в core evaluator;
- не читает wall-clock;
- не использует random;
- выдаёт typed deterministic transition ledger;
- обрабатывает duplicate replay idempotently;
- fail closed при missing/conflicting identity и continuity;
- не вычисляет XP amount.

## 13. Focused validation

Focused gate:

```text
focused tests: PASS
G2.1 continuity: PASS
model/schema validation: PASS
fixture schema validation: PASS
fixture inventory: PASS
threat fixture coverage: PASS
19-invariant coverage: PASS
deterministic replay/digest: PASS
forbidden/private-data scan: PASS
no numeric amount/ratio/delay: PASS
no production imports: PASS
git diff --check: PASS
```

Focused run содержал 14 tests.

## 14. Pre-conformance publication

До full suite модель была опубликована двумя логическими commits:

```text
e451f94 — Define the Learn XP lifecycle and identity model
63741bc — Add deterministic Learn XP anti-farming fixtures
```

Local и remote pre-conformance SHA совпали:

```text
63741bcc4d757cd131ab94d9e262042679460d6f
```

Changed-path boundary:

```text
30 research/docs files
ahead of base: 2 commits
behind base: 0
```

## 15. Full research suite

Full suite был запущен после freeze pre-conformance SHA.

Первый запуск обнаружил environment blocker:

```text
cargo unavailable
```

После task-only установки Rust/Cargo suite был запущен, но два Rust oracle tests не смогли разрешить crate `fsrs` из-за обязательного repository режима:

```text
cargo run --locked --offline
```

Root cause:

```text
new task-only CARGO_HOME had no locked crates cache
```

Выполнено bounded environment repair:

```text
cargo fetch --locked
Cargo.lock unchanged
cargo build --locked --offline: PASS
```

После конкретного cache repair выполнен один bounded full-suite retry:

```text
full research pytest: PASS
```

Pass count не фиксируется, поскольку `pytest -q` не напечатал итоговое число. G2.2 tests и существующие Review/Rust/FSRS tests завершились без failures.

После suite два вспомогательных summary scripts завершались `KeyError` из-за неверных отчётных путей (`fixtures`, затем `contract_status`). Эти ошибки произошли после зелёного `pytest`, не меняли repository/model и не требовали повторного full suite. Финальный read-only summary исправил пути и прошёл.

## 16. Post-conformance summary

```text
remote identity: PASS
manifest detached digest: PASS
fixture inventory: PASS
model status: FROZEN_PRE_CANDIDATE_DESIGN
identity architecture: FACTORIZED
selection/screening/production flags: PASS
repository integrity: PASS
```

После просмотра результатов lifecycle semantics не менялась. Closeout изменяет только human-readable status/docs.

## 17. Решения, намеренно не принятые

```text
achievement-subject winner: NONE
XP amount: NONE
pending ratio: NONE
numeric confirmation delay: NONE
candidate family: NONE
screening matrix: NONE
screening executed: NO
production approved: NO
production integration: NO
```

## 18. Не запускалось

```text
G1 matrices
G2 candidate screening
Fast CI
Docker real-Anki E2E
frontend tests
.ankiaddon build
production package
release
deployment
```

Причина: G2.2 — изолированная research lifecycle model; production runtime, dashboard, API, scheduler, FSRS integration и package contents не менялись.

## 19. G2.3 handoff

Следующий этап:

```text
G2.3 — Candidate protocol and hypothesis design
```

Frozen inputs:

- state/event/transition model;
- factorized identity architecture;
- unresolved subject candidates;
- abstract confirmation predicate;
- fixture manifest и digest;
- six-threat coverage;
- 19-invariant mapping;
- prohibited assumptions и mutation boundaries.

G2.3 может определить candidate families, comparison protocol, numeric confirmation delays, pending ratios, amounts и screening matrix только после отдельной активации.

```text
G2.3: NEXT / NOT STARTED
```

## 20. Финальный статус этапа

```text
G2.2: COMPLETE
model status: FROZEN_PRE_CANDIDATE_DESIGN
G2.3: NEXT / NOT STARTED

production approved: NO
production integration: PROHIBITED
```
