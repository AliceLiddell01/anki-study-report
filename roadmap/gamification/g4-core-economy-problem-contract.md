# G4.1 — Контракт проблемы core-экономики Gamification

## Статус

```text
Mode: ChatGPT
G3: DEFERRED / POST-MVP / NOT STARTED
G3 critical path: NO
G3 blocks G4/G5/G6: NO
G4: IN PROGRESS
G4.1: COMPLETE
contract status: FROZEN_PRE_NORMALIZATION_ANALYSIS
G4.2: NEXT / NOT STARTED
production approved: NO
production integration: PROHIBITED
```

## Repository / delivery

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
starting gamification HEAD: abb1d26e416d29f64d505546cca74de0f7379eab
task branch: g4-1-core-economy-problem-contract
PR: #163
PR base: gamification
validated pre-closeout HEAD: f0f76ce3f694e64555743ec9f3d6e891cf0c0305
final merge SHA: RECORDED_IN_EXTERNAL_REPORT_AFTER_VERIFIED_MERGE
master changed: NO
AGENTS.md: NOT FOUND
```

G4.1 выполнен как один research-contract PR с base `gamification`. Production runtime, dashboard, API, scheduler, FSRS, package, workflows и `master` не изменяются.

## Owner decision

Зафиксировано:

```text
G3/Create XP:
DEFERRED / POST-MVP / NOT STARTED

first Gamification MVP critical path:
NO

blocks G4/G5/G6:
NO

activation:
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

G4 переопределён как:

```text
G4 — Core gamification economy calibration

initial domains:
Review XP
Learn XP

Create XP:
EXCLUDED / DEFERRED WITH G3
```

## Frozen artifacts

```text
docs/gamification/core-economy-problem-contract.md
research/gamification-sim/contracts/core-economy-problem-contract-v1.json
research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json
roadmap/gamification/g4-core-economy-problem-contract.md
```

Machine identity:

```text
contract_id: core-economy-problem-contract
version: 1
status: FROZEN_PRE_NORMALIZATION_ANALYSIS
schema draft: https://json-schema.org/draft/2020-12/schema
contract Git blob: dda1336328df7e79bc5ba1978a102faf5ca40e14
schema Git blob: d124ce0aafccd84c38c142c1fb8319ef91877f87
contract SHA-256: acfefc0754dbd05bacf729d7a19ed1ea0c2ded51cfb9cef98b78bdeb6906be6f
schema SHA-256: bb83a51ad25fc774c45e54d2c11e412e1ffcc7a5e436d043302690313cb334c7
```

## Input evidence ledger

### Review XP

```text
G1 final outcome: DEFER_REVIEW_MODEL
recommended candidate: NONE
P-STEP-ZERO: CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D: CONFIRMATORY_ELIGIBLE; not selected; not falsified
Review winner: NONE
```

Оба Review candidates переданы в G4.2 как explicit uncertainty axis. G4.1 не выбирает default и не переписывает G1.

### Learn XP

```text
candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
G2.5 status: CONFIRMATORY_INCONCLUSIVE
reason: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
confirmatory eligible: NO
production ready: NO
production approved: NO
```

Candidate разрешён только как bounded research input. `1.0 LRU` не становится автоматически common economy XP.

## Contract inventory

```text
terminology: 30
terminology definitions: 30
personas: 9
persona definitions: 9
threat families: 14
threat definitions: 14
protected invariants: 28
per-invariant coverage records: 28
candidate source categories: 2
non-rewardable surfaces: 26
allowed final outcomes: 3
G4.2 requirements: 14
```

## Unresolved numeric and policy selections

```text
Review winner: NONE
Review/Learn conversion ratio: NONE
normalized XP amount: NONE
daily cap / soft cap: NONE
diminishing-return function: NONE
productive-day threshold: NONE
level curve / level count: NONE
streak threshold / grace: NONE
planned-rest quota: NONE
Momentum formula / range / decay: NONE
recovery bonus or shape: NONE
persona traces: NOT_DEFINED
candidate families: NOT_DEFINED
screening matrix: NOT_DEFINED
simulation seed: NONE
production storage/API/UI: NOT_DESIGNED
```

## Validation

Focused validation выполнен на exact serialized bytes, опубликованных в Git:

```text
strict duplicate-key-safe JSON parse: PASS
Draft 2020-12 schema self-check: PASS
contract-schema validation: PASS
contract local/Git blob equality: PASS
schema local/Git blob equality: PASS
human/machine identity parity: PASS
status parity: PASS
Review input parity: PASS
Learn input parity: PASS
G3 deferral parity: PASS
domain scope parity: PASS
terminology registry/definition parity: 30 / 30 PASS
persona registry/definition parity: 9 / 9 PASS
threat registry/definition parity: 14 / 14 PASS
invariant registry/definition parity: 28 / 28 PASS
invariant threat/persona/G4.2 references: PASS
final outcome coverage: 3 / 3 PASS
G4.2 entry coverage: 14 / 14 PASS
Markdown code-fence balance: PASS
relative-link target review: PASS
private-path scan: PASS
secret/token scan: PASS
changed-path allowlist: exact 10 paths
production paths changed: NO
research execution code/tests changed: NO
```

Negative samples rejected:

```text
unknown top-level property
missing required field
invalid contract status
Create XP inside initial domain list
selected Review winner
Learn candidate marked CONFIRMATORY_ELIGIBLE
production approval true
missing required invariant
unknown final outcome
G4.2 marked started
numeric conversion ratio
numeric level curve
real-data category in allowed data
missing terminology definition
invalid invariant threat reference
duplicate JSON key
```

```text
negative validation: 16 / 16 PASS
```

### Disclosed pre-merge schema correction

Semantic PR review обнаружил, что в одном промежуточном schema commit definition maps были ошибочно вложены в `production_flags`. Этот intermediate state не был смёржен и не объявляется validated result.

Исправление:

```text
classification: SCHEMA_STRUCTURE
results accessed: NO — G4.1 has no simulation/results
contract semantics changed: NO
registries changed: NO
numeric policy introduced: NO
required rerun: focused contract/schema validation
focused rerun: PASS
final schema blob: d124ce0aafccd84c38c142c1fb8319ef91877f87
```

Validation environment available to ChatGPT:

```text
Python: 3.13.5
jsonschema: 4.26.0
```

Project-local Python 3.11 WSL execution не была независимо доступна в connector sandbox. Contract/schema являются data-only Draft 2020-12 artifacts; production/runtime Python code не менялся.

## Exact changed paths

```text
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
docs/gamification/core-economy-problem-contract.md
research/gamification-sim/README.md
research/gamification-sim/contracts/core-economy-problem-contract-v1.json
research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g4-core-economy-problem-contract.md
```

Top-level `README.md` не требуется: его entrypoint и high-level track statement остаются корректными.

## Pull request pre-merge state

```text
PR: #163
base: gamification
head: g4-1-core-economy-problem-contract
base SHA: abb1d26e416d29f64d505546cca74de0f7379eab
validated contract/schema head: f0f76ce3f694e64555743ec9f3d6e891cf0c0305
branch ahead / behind before final closeout commit: 16 / 0
changed files: 10
mergeable: YES
combined status checks: 0
workflow runs: 0
```

Ноль workflow runs фиксируется как факт. Это не `CI PASS`; для docs/contracts/schema-only contour current policy допускает focused local validation без Fast CI и Docker E2E.

## Not run

```text
G1 matrices
G2 matrices
G4.2 normalization design
G4 candidate registry
economy simulation
full research pytest
Fast CI
frontend tests/build
Docker real-Anki E2E
package / .ankiaddon validation
production implementation
```

Причина: diff ограничен docs/contracts/schema; production и research execution code не меняются. Current test matrix и verification policy не требуют Fast CI или Docker для такого contour.

## Limitations

- Review winner остаётся unresolved;
- Learn input сохраняет `CONFIRMATORY_INCONCLUSIVE`;
- raw G1/G2 evidence bundles не перепроверяются в G4.1;
- G4.1 не доказывает balanced/optimal economy или human benefit;
- exact normalization, formulas, thresholds и traces не определены;
- WSL owner checkout/worktree/tool state не проверялся локальной командой в этой connector-сессии.

Эти ограничения являются входами G4.2, а не blocker G4.1.

## Proof that G3 does not block G4/G5/G6

Machine и human contracts синхронно фиксируют:

```text
G3 critical path: false
G3 blocks G4: false
G3 blocks G5: false
G3 blocks G6: false
G3 initial economy included: false
```

Activation требует release + owner decision + evidence-backed trigger. Ни G3.1, ни Create XP model не определялись.

## Next stage boundary

```text
G4.2 — Input normalization and uncertainty model
NEXT / NOT STARTED
```

G4.2 не начат. G4.1 не создаёт candidate registry, matrix или simulation и не начинает G5/G6.
