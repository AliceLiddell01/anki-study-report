# G2.3 — Learn XP candidate protocol closeout

**Статус:** Complete  
**Режим:** ChatGPT  
**Repository:** `AliceLiddell01/anki-study-report`  
**Target branch:** `gamification`  
**Starting HEAD:** `cb2d174468c6475018fa3a9a620b517992c1afa8`  
**Fix commit:** `4d9b05f0347df85cb34ad85c1a935892ea7b4e4d`  
**Protocol publication SHA:** `41313c9369c76d331d489a9aa4b44da2497b3132`  
**Task branch:** `chatgpt/g2-3-learn-xp-candidate-protocol`

## 1. Итог

```text
G2: IN PROGRESS
G2.1: COMPLETE
G2.2: COMPLETE
G2.3: COMPLETE

protocol status:
FROZEN_PRE_SCREENING_IMPLEMENTATION

G2.4:
NEXT / NOT STARTED

screening executed:
NO

production approved:
NO

production integration:
PROHIBITED
```

G2.3 закрыл две bounded technical оговорки G2.2 и prospectively заморозил Learn XP candidate protocol до любого G2.4 screening.

## 2. G2.2 fixes

### Canonical digest

```text
shared helper:
canonical_json.canonical_digest

frozen lifecycle cases:
31

legacy/shared digest parity:
PASS

lifecycle result drift:
NONE

fixture manifest digest:
4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
```

Локальные `_canonical_payload()` и `canonical_digest()` удалены из `learn_lifecycle.py`. Frozen final states, transition ledgers, reason codes и canonical result digests сохранены.

### Exact direct-input typing

Direct lifecycle events теперь fail closed:

- exact non-empty strings;
- exact integer types без `bool` и float coercion;
- exact boolean;
- registered enum strings;
- registered scheduler-state strings;
- unknown properties rejected.

Negative coercion coverage включает string/bool/float integers, numeric booleans, numeric IDs, empty identity, unknown enum/state и unexpected property.

## 3. Frozen reward domain

```text
unit:
LRU — Learn Reward Unit

normalized total per confirmed achievement:
1.0 LRU

production XP:
NO

Review Unit:
NO

spendable:
NO
```

LRU — только comparative research accounting. Negative allocation и total выше `1.0` запрещены.

## 4. Candidate families

Ровно две families:

```text
F-CONFIRMATION-ONLY
pending: 0.0
confirmation settlement: 1.0

F-PENDING-CONFIRMED-SPLIT
pending: 0.25
confirmation settlement: 0.75
```

Parameterizations:

```text
P-CONFIRM-ONLY-D1
P-CONFIRM-ONLY-D2
P-SPLIT-D1
P-SPLIT-D2
```

Third family, adaptive variants и hidden parameters запрещены без versioned amendment.

## 5. Delay policies

```text
D1:
minimum elapsed = 1440 synthetic minutes
minimum Anki-day delta = 1
expiry = 10080 minutes / 7 Anki days

D2:
minimum elapsed = 4320 synthetic minutes
minimum Anki-day delta = 3
expiry = 20160 minutes / 14 Anki days
```

Обе policies:

- исключают same-chain repetition;
- требуют source-event linkage;
- не считают scheduler state `Review` достаточным;
- не используют displayed interval;
- устойчивы к session/time formatting boundary.

D1/D2 — prospective bounded contrasts, а не заявления об оптимальном human-learning schedule.

## 6. Subject strategies

```text
S-CARD
S-NOTE-SIBLING
```

`CARD` остаётся granular comparison strategy.

`NOTE` и `SIBLING_GROUP` классифицированы как:

```text
OPERATIONALLY_EQUIVALENT
```

В доступной synthetic/non-private identity boundary sibling group — cards, созданные из одной note; дополнительного безопасного distinction key нет.

## 7. Candidate registry и reference

```text
candidate count:
8

subject-aware reference variants:
2

reference:
L-NO-LEARN-XP
```

Reference:

- запускает тот же lifecycle evaluator;
- выделяет `0.0 LRU`;
- не candidate;
- не survivor.

Candidate IDs детерминированы сочетанием family, parameterization/delay и subject strategy.

## 8. Terminal disposition

```text
CONFIRMED:
pending settles into total 1.0 LRU

EXPIRED:
total 0.0; provisional VOID; no fresh eligibility

CANCELLED:
total 0.0; provisional VOID; no fresh eligibility

INVALIDATED:
total 0.0; provisional VOID; no fresh eligibility
```

Pending settlement не складывает `1.0` поверх provisional share. Negative reward отсутствует.

## 9. Hypotheses, gates и metrics

```text
hypotheses:
5

hard gates:
23

descriptive metrics:
14
```

Hard gates non-compensable. Weighted aggregate score запрещён. Missing evidence fails closed.

Максимум один survivor на family. Selection разрешён только после прохождения всех hard gates и по frozen lexicographic safety/accounting metrics. Exact tie даёт:

```text
FAMILY_INCONCLUSIVE
```

## 10. Exact G2.4 dry matrix

```text
candidate identities:
8

reference identities:
2

scenario registry:
30

scenario conditions per identity:
34

replicas:
[0]

seed axis:
ABSENT_DETERMINISTIC

expected units:
340

unique unit IDs:
340

adaptive units:
0
```

Unit ID:

```text
U-<canonical SHA-256 of typed unit identity>
```

Execution order и filesystem path не входят в identity.

G2.3 выполнил только dry generation и validation. Candidate reward execution и outcome analysis не выполнялись.

## 11. Protocol artifacts

```text
docs/gamification/learn-xp-candidate-protocol.md
research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json
research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json
research/gamification-sim/src/gamification_sim/learn_candidate_protocol.py
research/gamification-sim/tests/test_learn_candidate_protocol.py
```

Machine protocol содержит frozen families, parameterizations, subject/delay strategies, terminal disposition, reference, candidate registry, hypotheses, gates, metrics, survivor/tie policy, matrix axes, scenarios, unit identity, expected budget, amendments и G2.4 handoff.

## 12. Validation

### Fix-focused

```text
focused lifecycle tests:
32 PASS

frozen cases:
31

digest parity:
PASS

strict direct-input tests:
PASS

manifest digest:
UNCHANGED
```

### Protocol-focused

```text
Draft 2020-12 schema self-check:
PASS

protocol validation:
PASS

negative samples:
PASS

exact privacy-key scan:
PASS

dry matrix:
340 / 340 PASS
```

### Full research suite

После protocol publication выполнен один полный research suite:

```text
tests:
982

passed:
982

failures:
0

errors:
0

skipped:
0
```

Rust oracle environment:

```text
task-only Rust/Cargo
cargo fetch --locked
Cargo.lock unchanged
cargo build --locked --offline: PASS
```

Repository после conformance остался чистым и на exact protocol publication SHA.

## 13. Publication barrier

Protocol был опубликован до G2.4 results:

```text
protocol publication SHA:
41313c9369c76d331d489a9aa4b44da2497b3132

screening results before publication:
NONE

G2.4 started:
NO
```

Substantive amendment требует новой version, field-level diff, rationale, results-viewed disclosure, prior-run invalidation, required rerun и roadmap note.

## 14. Claims boundary

Допустимо утверждать только:

- прохождение frozen synthetic lifecycle/accounting gates;
- устойчивость к перечисленным synthetic farming traces;
- сохранение research-only technical boundaries.

Запрещено утверждать:

- mastery или факт обучения пользователя;
- реальное улучшение retention/motivation;
- предотвращение всего gaming;
- production readiness;
- объективную истинность rating.

## 15. Не запускалось

```text
G1 matrices
G2.4 implementation
G2.4 screening
candidate simulations/outcomes
Fast CI
Docker real-Anki E2E
frontend tests
.ankiaddon build
production package
release/deployment
```

Причина: diff research/docs-only и не меняет add-on package, dashboard, API, scheduler или FSRS production behavior.

## 16. G2.4 handoff

Следующий этап:

```text
G2.4 — Bounded Learn XP screening implementation
```

Frozen inputs:

- protocol version 1;
- 8 candidates и 2 reference variants;
- 30 scenarios;
- exact `340`-unit budget;
- 23 hard gates;
- 14 metrics;
- 5 hypotheses;
- D1/D2;
- `S-CARD` / `S-NOTE-SIBLING`;
- `0.0/1.0` и `0.25/0.75` allocation families;
- deterministic unit identity;
- amendment and claims boundaries.

```text
G2.4:
NEXT / NOT STARTED
```

## 17. External methodological basis

- Anki Manual — cards/notes/states: https://docs.ankiweb.net/getting-started.html
- Anki Manual — learning/relearning steps: https://docs.ankiweb.net/deck-options.html
- Anki Manual — answer buttons/siblings: https://docs.ankiweb.net/studying.html
- Anki Manual — templates: https://docs.ankiweb.net/templates/intro.html
- Anki Manual — filtered decks: https://docs.ankiweb.net/filtered-decks.html
- COS preregistration: https://www.cos.io/initiatives/prereg
- COS lifecycle open science: https://www.cos.io/lifecycle-open-science

Внешние sources определяют scheduler semantics и prospective research discipline, но не production reward amount, mastery или final model.

## 18. Финальный статус

```text
G2.3:
COMPLETE

protocol status:
FROZEN_PRE_SCREENING_IMPLEMENTATION

protocol publication SHA:
41313c9369c76d331d489a9aa4b44da2497b3132

full research suite:
982 PASS

G2.4:
NEXT / NOT STARTED

production approved:
NO

production integration:
PROHIBITED
```
