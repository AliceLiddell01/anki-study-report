# Передача актуального контекста ИИ

**Снимок:** 2026-07-28

Этот файл — короткая точка входа. Он не заменяет production code, профильные contracts, roadmap или closeout reports.

## Порядок чтения

1. [`../README.md`](../README.md)
2. этот файл;
3. профильный roadmap;
4. профильный contract в `docs/`;
5. production/research code и tests нужного scope;
6. свежий closeout только когда он нужен задаче.

При противоречиях:

```text
production/research code и tests
→ docs/
→ roadmap/
→ reports/artifacts
→ старые планы и сообщения
→ предположения
```

## Проект и границы

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

- dashboard работает только через loopback и защищён access token;
- frontend получает bounded API projections и не читает collection напрямую;
- preview использует sanitizer и Shadow DOM без JavaScript execution surface;
- учебные и профильные данные остаются локальными;
- payload/public behavior меняются синхронно между слоями, tests и docs;
- Gamification research остаётся изолированным от add-on package, Fast CI и production runtime до отдельного решения.

Подробности: [architecture.md](architecture.md), [dashboard-api.md](dashboard-api.md), [security-and-safety.md](security-and-safety.md).

## Core

```text
C1 — завершён и принят
C2 implementation/integration — завершены и влиты в core
C2 owner acceptance — открыта bounded remediation
C3 → C4 → C5 → C6 — обязательный путь к Core 1.0
release — не начат
```

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

## Gamification

Canonical branch:

```text
gamification
```

Текущий repository state:

```text
G0 — Complete
G1 — Complete
G1 final outcome — DEFER_REVIEW_MODEL
recommended Review XP research candidate — NONE
P-STEP-ZERO — CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D — CONFIRMATORY_ELIGIBLE; not selected; not falsified

G2 — COMPLETE
G2.1 — COMPLETE
Learn XP contract — FROZEN_PRE_LIFECYCLE_ANALYSIS
G2.2 — COMPLETE
Learn XP lifecycle model — FROZEN_PRE_CANDIDATE_DESIGN
identity architecture — FACTORIZED; LearningEpisode<AchievementSubject>
lifecycle states / events / transitions — 7 / 20 / 12
fixtures / threat families / invariants — 23 / 6 / 19
fixture manifest digest — 4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
G2.3 — COMPLETE
Learn XP candidate protocol — FROZEN_PRE_SCREENING_IMPLEMENTATION
protocol publication SHA — 41313c9369c76d331d489a9aa4b44da2497b3132
families / candidates / reference variants — 2 / 8 / 2
subject strategies — S-CARD; S-NOTE-SIBLING
NOTE/SIBLING_GROUP relation — OPERATIONALLY_EQUIVALENT
delay policies — D1; D2
pending split — 0.25 provisional / 0.75 settlement
hypotheses / hard gates / metrics — 5 / 23 / 14
G2.4 matrix budget — 340 deterministic units
G2.4 — COMPLETE
screened implementation SHA — 548b27de6283b32fb27541db02ce6c8b65c29756
replacement matrix — 340 / 340 unique; 0 / 0 / 0 missing / extra / duplicates
manifest / evidence / bundle — fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a / 5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6 / a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78
F-CONFIRMATION-ONLY survivor — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
F-PENDING-CONFIRMED-SPLIT survivor — C-PENDING-SPLIT-D1-NOTE-SIBLING
G2.5 — COMPLETE — CONFIRMATORY INCONCLUSIVE
G2.5 variants / reference — 2 / 1
G2.5 conditions — 16 core / 12 identity / 8 explainability
G2.5 replay / expected units — FORWARD+REVERSE / 216
G2.5 identity evidence mode — SYNTHETIC_CONTRACT_ONLY
G2.5 results accessed — YES — AFTER PROTOCOL PUBLICATION
G2.6 — COMPLETE
G2 final outcome — RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended Learn XP research candidate — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
decision basis — MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE
selected candidate G2.5 status — CONFIRMATORY_INCONCLUSIVE
non-selected candidate — C-PENDING-SPLIT-D1-NOTE-SIBLING; not selected; not falsified
production integration — PROHIBITED

G3 — DEFERRED / POST-MVP / NOT STARTED
G3 critical path — NO
G3 blocks G4/G5/G6 — NO

G4 — IN PROGRESS
G4.1 — COMPLETE
core economy contract — FROZEN_PRE_NORMALIZATION_ANALYSIS
core economy domains — REVIEW_DOMAIN; LEARN_DOMAIN
Create XP — EXCLUDED / DEFERRED WITH G3
Review winner — NONE
G4.2 — COMPLETE
input/uncertainty model — FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
Review uncertainty axis — REVIEW_MODEL_AXIS_V1
Review default / averaging — NONE / PROHIBITED
axes — SESSION; ANKI_DAY; CALENDAR_DAY
G4.3 — NEXT / NOT STARTED
simulation — NOT STARTED
production integration — PROHIBITED
```

### G1 Review input

G1.6 закрыл Review XP outcome `DEFER_REVIEW_MODEL`; production approval отсутствует. `P-STEP-ZERO` и `P-TAPER-ZERO-30D` остаются `CONFIRMATORY_ELIGIBLE`, не выбраны и не фальсифицированы.

G4 сохраняет оба candidates как explicit `REVIEW_MODEL_AXIS_V1`:

```text
selection: NONE
default: NONE
aggregation: PARALLEL_SEPARATE
averaging: PROHIBITED
winner criterion: NOT_DEFINED
```

Raw G1 bundles не объявляются freshly revalidated.

### G2 Learn input

G2.1 заморозил отдельный Learn XP problem contract. Он отделяет официальные Anki states от Learn XP research lifecycle, фиксирует identity candidates, pending/confirmation requirements, шесть threat families, 19 invariants, privacy/claims и entry contract G2.2.

G2.2 определил семь states, 20 events и 12 transitions. Identity factorized как `LearningEpisode<AchievementSubject>`. G2.3 prospectively заморозил две families, две delay policies, две subject strategies, восемь candidates, две references и exact `340/340` G2.4 budget.

Первый G2.4 attempt на `ef7c638a…` изолирован как `INVALID`. Packaging-only correction опубликована как `548b27de…`; valid replacement run завершён `340/340` с detached validation и byte-identical reproduction.

G2.5 завершён на `216/216/216` units. Оба survivors получили `CONFIRMATORY_INCONCLUSIVE` из-за `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE`.

G2.6 рекомендует `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` под `MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE`. Recommendation не означает confirmatory eligibility, scientific superiority или production approval.

G4 использует этот candidate только как bounded input:

```text
status — CONFIRMATORY_INCONCLUSIVE
limitation — DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
achievement subject — NOTE_SIBLING
allocation — CONFIRMATION_ONLY_NO_PROVISIONAL_STATE
source unit — LRU
frozen source total — 1.0
common economy XP — false
```

### G3 owner decision

G3/Create XP отложен до периода после первого стабильного Gamification release, исключён из initial economy и не блокирует G4, G5 или G6.

Activation требует одновременно:

```text
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

G3.1, lifecycle, candidates, units, formulas и simulation не определены.

### G4.1 problem contract

Canonical artifacts:

- [human problem contract](gamification/core-economy-problem-contract.md)
- [machine contract](../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [strict schema](../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](../roadmap/gamification/g4-core-economy-problem-contract.md)

```text
contract_id — core-economy-problem-contract
version — 1
status — FROZEN_PRE_NORMALIZATION_ANALYSIS
terminology — 30
personas — 9
threats — 14
invariants — 28
G4.2 requirements — 14
```

Corrected schema chronology:

```text
defective intermediate commit reachable from merged PR history — YES
defective schema present in final tree — NO
defective schema used as validated result — NO
```

### G4.2 input normalization and uncertainty model

Canonical artifacts:

- [human model](gamification/core-economy-input-normalization-model.md)
- [machine contract](../research/gamification-sim/contracts/core-economy-input-normalization-v1.json)
- [strict schema](../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json)
- [G4.2 closeout](../roadmap/gamification/g4-core-economy-input-normalization.md)

```text
contract_id — core-economy-input-normalization
version — 1
status — FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
domain input types — 2
common interface records — 4
axes — 3
dispositions — 7
fail-closed reasons — 18
personas — 9
fixture requirements — 15
threats / invariants — 14 / 28
validation rules — 24
G4.3 requirements — 14
```

Typed records:

```text
REVIEW_DOMAIN_INPUT
LEARN_DOMAIN_INPUT
NORMALIZATION_INPUT
DOMAIN_CONTRIBUTION_RECORD
DAILY_AGGREGATION_INPUT
DAILY_AGGREGATION_RESULT_PLACEHOLDER
```

G4.2 определяет shapes, validation, provenance, decomposition, independent axes, fail-closed dispositions, persona descriptors и future fixture requirements.

G4.2 не выбирает:

```text
Review winner/default
candidate averaging
Review/Learn ratio
normalized unit/value
daily cap / soft cap
diminishing function
productive-day threshold
level curve/count
streak/rest/Momentum/recovery formulas
candidate families
exact traces
matrix
seed
simulation result
production storage/API/UI
```

G4.3 остаётся `NEXT / NOT STARTED`.

### Retained G2 technical chronology

G2.2 опубликовал research-only evaluator и 23 synthetic fixtures, покрывающие шесть threat families и все 19 invariants. Model status — `FROZEN_PRE_CANDIDATE_DESIGN`.

G2.3 устранил duplicate canonical digest helper, запретил direct-input coercion и доказал отсутствие drift на 31 frozen lifecycle case. Затем prospectively заморозил две Learn XP families, две delay policies, две operational subject strategies, восемь candidates, две reference variants и exact deterministic G2.4 budget `340/340`.

Protocol publication SHA — `41313c9369c76d331d489a9aa4b44da2497b3132`; G2.3 full research suite — `982 passed`. Первый canonical G2.4 attempt на `ef7c638a…` был изолирован как `INVALID` после failure byte-identical archive reproduction. Packaging-only `HARNESS` correction (`TarInfo.mode → 0644`) опубликована как `548b27de6283b32fb27541db02ce6c8b65c29756` без изменения screening design. Полный replacement run завершён `340/340`, detached validation и deterministic reproduction прошли. Внутри `F-CONFIRMATION-ONLY` выбран `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING`, внутри `F-PENDING-CONFIRMED-SPLIT` — `C-PENDING-SPLIT-D1-NOTE-SIBLING`. Cross-family ranking, final model selection и production approval в G2.4 не выполнялись.

G2.5 был активирован отдельно и завершён на prospectively frozen matrix из двух survivors, одной reference, 36 conditions и двух replay identities: `216/216/216`, `0/0/0`, detached validation и byte-identical reproduction прошли. Оба survivors получили `CONFIRMATORY_INCONCLUSIVE` из-за `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE`; reference осталась `REFERENCE_ONLY`. Ranking, winner, recommendation, final model selection и production approval в G2.5 не выполнялись.

G2.6 закрыл G2 outcome `RECOMMEND_LEARN_XP_RESEARCH_MODEL` и рекомендует `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` как bounded research model. Принцип `MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE` выбирает меньшую provisional/accounting/explanation surface при одинаковом frozen confirmed total и отсутствии подтверждённой human benefit дополнительного pending reward state. G2.5 outcome выбранного кандидата остаётся `CONFIRMATORY_INCONCLUSIVE`; non-selected pending-split candidate не фальсифицирован и не отклонён как invalid. Recommendation не означает confirmatory eligibility, scientific superiority или production approval.

Точные источники:

- [`../roadmap/gamification/README.md`](../roadmap/gamification/README.md)
- [Gamification docs index](gamification/README.md)
- [G1.6 decision](../roadmap/gamification/g1-review-xp-decision.md)
- [G2.6 decision](../roadmap/gamification/g2-learn-xp-decision.md)
- [G4.1 problem contract](gamification/core-economy-problem-contract.md)
- [G4.1 closeout](../roadmap/gamification/g4-core-economy-problem-contract.md)
- [G4.2 input normalization model](gamification/core-economy-input-normalization-model.md)
- [G4.2 machine contract](../research/gamification-sim/contracts/core-economy-input-normalization-v1.json)
- [G4.2 strict schema](../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json)
- [G4.2 closeout](../roadmap/gamification/g4-core-economy-input-normalization.md)

`gamification → master`, production integration, package inclusion и release запрещены без отдельного owner decision.

## Platform / CI

```text
real-deck E2E foundation — COMPLETE / merged
E2E-I1–E2E-I6 — COMPLETE / merged
E2E-I6 bounded corrective fix — COMPLETE / merged через PR #144
следующий Platform/CI stage — не активирован
```

Последний Core sync baseline:

```text
core HEAD: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
E2E-I6 corrective implementation: afe650adbf3ba55cb6b59068a1127022b651fbf3
PR #144 merge SHA: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
Fast CI: 30169763775 — PASS
standard/full: 30169890912 — PASS
```

E2E-I6 corrective fix не активирует CI 7–12. Любая оптимизация требует отдельного измеренного trigger и owner decision.

## Рабочие правила

- Сначала определить track, target branch и точный scope.
- Desktop/laptop — основной target; mobile не приоритет без отдельной задачи.
- Не добавлять placeholder routes, speculative APIs или future extension surfaces заранее.
- Не возвращать legacy aliases без доказанной compatibility необходимости.
- Не дробить roadmap stage на бесконечную лестницу.
- Successful unchanged exact-SHA gates не повторять.
- Harness failure не объявлять production failure без подтверждения.
- Docs/contracts/schema-only sync не требует Fast CI или Docker E2E.
- Для Gamification target и PR base — `gamification`.
- Не начинать G4.3 автоматически после G4.2.

## Режим работы

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [Codex agent rules](codex-agent-rules.md)
- [Codex local environment](codex-local-environment.md)

ChatGPT mode может использовать GitHub connector и консоль владельца WSL/PowerShell. Скачиваемые scripts выдаются отдельными файлами и предваряются `Unblock-File`.

Codex mode работает непосредственно в локальном task worktree.

Не начинать следующий roadmap stage автоматически только потому, что предыдущая техническая работа завершена.

### G2 final closeout

```text
G2.6: COMPLETE
G2: COMPLETE
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
selected candidate G2.5 status: CONFIRMATORY_INCONCLUSIVE
selected candidate reason: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
production approved: NO
production integration: PROHIBITED
```

### G4.2 closeout

```text
G4: IN PROGRESS
G4.1: COMPLETE
G4.2: COMPLETE
model: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
Review inputs: P-STEP-ZERO; P-TAPER-ZERO-30D
Review winner/default: NONE / NONE
Learn input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
axes: SESSION; ANKI_DAY; CALENDAR_DAY
numeric policy: NOT SELECTED
G4.3: NEXT / NOT STARTED
simulation: NOT STARTED
production approved: NO
production integration: PROHIBITED
```
