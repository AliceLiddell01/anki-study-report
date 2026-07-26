# G2.1 — Freeze Learn XP problem and contract

## Статус

```text
Mode: ChatGPT
G2.1: COMPLETE
G2: IN PROGRESS
G2.2: NEXT / NOT STARTED
production approved: NO
production integration: PROHIBITED
```

## Repository / delivery

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
starting origin/gamification HEAD: 1168f42eaecc28fc59d12a6612f22f73ded5b391
task branch: chatgpt/g2-1-learn-xp-problem-contract
PR: recorded after publication
```

Starting `gamification` был exact identity с `1168f42eaecc28fc59d12a6612f22f73ded5b391`. Основной WSL checkout владельца не переключался и не очищался. Mutation выполнялась только в отдельной GitHub task branch без force push и без изменения `master`.

Локальный WSL checkout, stash и worktree list владельца не были доступны исполняемой среде ChatGPT и не объявляются проверенными. Contract/schema validation выполнялась в изолированной ChatGPT sandbox: Python `3.13.5`, `jsonschema 4.26.0`.

## Цель

G2.1 заморозил problem и research contract Learn XP независимо от Review XP:

```text
initial-learning problem statement
terminology
Anki scheduler-state / reward-state boundary
identity candidate set
pending / confirmation minimum requirements
rewardable / non-rewardable boundary
anti-farming threats
protected invariants
privacy / claims boundary
G2.2 entry contract
allowed final G2 outcomes
versioning
```

G2.1 не выбрал lifecycle, amount, ratio, delay, identity winner, candidate family или simulation matrix.

## Источники

### Internal

- `README.md`;
- `docs/README.md`;
- `docs/ai-handoff.md`;
- `roadmap/README.md`;
- `roadmap/gamification/README.md`;
- `research/gamification-sim/README.md`;
- work-mode contracts;
- Review XP event/reward/abuse/session/simulation references;
- G1 problem/protocol/decision process;
- current strict JSON, canonical JSON and workspace conventions.

### External

Official Anki:

- card states;
- learning steps;
- relearning steps;
- answer-button semantics.

Peer-reviewed methodology:

- Karpicke & Bauernschmidt (2011);
- Kang et al. (2014);
- Cepeda et al. (2008).

External methodology использовалась только для общего вывода о различии same-chain repetition и более независимого delayed retrieval. Она не использовалась для выбора exact delay, amount, ratio, motivation claim или mastery claim.

## Published artifacts

```text
docs/gamification/learn-xp-problem-contract.md
research/gamification-sim/contracts/learn-xp-problem-contract-v1.json
research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json
```

Status machine contract:

```text
contract_id: learn-xp-problem-contract
version: 1
contract_status: FROZEN_PRE_LIFECYCLE_ANALYSIS
```

## Frozen problem

> Learn XP должна поощрять доказуемое продвижение нового материала от первого валидного учебного взаимодействия к более сильному, независимо подтверждённому learning signal, не вознаграждая количество кликов, learning steps, failures, reset cycles, duplicate objects или настройки scheduler.

Главный invariant:

> Пользователь не должен получать больше Learn XP за то, что сделал обучение менее эффективным, более дробным, более повторяемым или более манипулируемым.

## Scheduler / reward boundary

Заморожено:

```text
New / Learning / Review / Relearn:
official Anki scheduler states

INITIAL_LEARNING / PENDING_REWARD / CONFIRMED_REWARD:
Learn XP research states
```

Следствия:

- `New → Learning` не доказывает learning;
- step count не является learning quantity;
- `Review` не автоматически confirmed;
- `Relearn` не создаёт new initial learning;
- scheduler/FSRS/due dates не меняются.

## Identity candidates

Ровно:

```text
CARD
NOTE
SIBLING_GROUP
LEARNING_EPISODE
```

Winner не выбран.

`CONTENT_FINGERPRINT` и `CONCEPT` исключены из v1: current boundary не даёт безопасную и стабильную identity без content processing или production semantic layer.

## Pending / confirmed boundary

`PENDING_REWARD`:

- provisional;
- no per-step/Again multiplication;
- step-config invariant;
- bounded;
- not production-spendable;
- terminal paths: confirmed/cancelled/expired/invalidated.

`CONFIRMED_REWARD`:

- stronger than same-chain repetition;
- independent delayed retrieval or prospectively defined equivalent;
- no step-count derivation;
- no duplicate confirmation without explicit eligibility;
- no mastery claim.

Exact delay и amount не выбраны.

## Threat coverage

Ровно шесть families:

```text
REPETITION_FARMING
CONFIGURATION_FARMING
OBJECT_FARMING
LIFECYCLE_FARMING
SESSION_TIME_FARMING
ANSWER_BEHAVIOR_FARMING
```

Каждая содержит typed precondition, attack trace, undesired effect, protected principle, required G2.2 fixture, severity, observability и open questions.

## Protected invariants

Machine contract содержит 19 required invariants, включая:

- scheduler/FSRS/due unchanged;
- button neutrality и honest Again;
- no Hard misreport incentive;
- step/config/session/time invariance;
- reset и duplicate-object protection;
- bounded pending;
- independent confirmation;
- deterministic replay;
- decomposable evidence;
- research-only/privacy/production boundaries.

## Allowed final G2 outcomes

Ровно:

```text
RECOMMEND_LEARN_XP_RESEARCH_MODEL
REJECT_LEARN_XP_MODEL
DEFER_LEARN_XP_MODEL
```

Recommendation означает research model, не production readiness.

## Machine flags

```text
candidate_selected: false
reward_amount_selected: false
identity_model_selected: false
confirmation_delay_selected: false
simulation_executed: false
production_approved: false
production_integration: false
g2_2_started: false
```

## Validation

Выполнено до publication:

```text
strict duplicate-key-safe JSON parse: PASS
Draft 2020-12 schema self-check: PASS
contract-schema validation: PASS
unique ID/reference validation: PASS
required terminology coverage: PASS
required identity candidates: PASS
required threat coverage: PASS
required invariant coverage: PASS
exact three final outcomes: PASS
all selection/execution/production flags false: PASS
deterministic canonical serialization: PASS
non-finite numeric rejection boundary: PASS
forbidden/private-data field scan: PASS
Markdown code-fence balance: PASS
relative-link target audit: PASS
changed-path allowlist: PASS
whitespace check: PASS
```

Negative samples rejected:

```text
duplicate JSON key
duplicate semantic ID
unknown identity candidate
missing threat family
missing invariant
fourth final outcome
true production flag
selected reward amount
selected confirmation delay
real profile path
raw card content field
unexpected property
non-finite number
```

No generic validator framework or executable research code was added.

## Changed paths

```text
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
docs/gamification/learn-xp-problem-contract.md
research/gamification-sim/README.md
research/gamification-sim/contracts/learn-xp-problem-contract-v1.json
research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g2-learn-xp-problem-contract.md
```

## Не запускалось

```text
G1 matrices
G2 simulation
full research pytest
Fast CI
Docker real-Anki E2E
frontend tests
.ankiaddon / package build
production package
```

Причина: G2.1 — docs/contracts/schema-only freeze. Production и executable research code не изменялись.

## Cleanup

После verified merge удаляются только task branch и task-specific temporary validation files. G1 evidence, shared environments и unrelated worktrees/backups не затрагиваются.

## Final

```text
G2.1: COMPLETE
G2: IN PROGRESS
G2.2: NEXT / NOT STARTED
identity winner: NONE
reward amount: NONE
pending ratio: NONE
confirmation delay: NONE
simulation executed: NO
production approved: NO
production integration: PROHIBITED
```
