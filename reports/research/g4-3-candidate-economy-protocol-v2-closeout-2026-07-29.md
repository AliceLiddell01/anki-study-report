# G4.3 v2 corrective candidate economy protocol — post-merge closeout

**Дата:** 2026-07-29  
**Track:** Gamification `G`  
**Stage:** `G4.3 — Candidate economy protocol and hypothesis design`  
**Target branch:** `gamification`  
**Scope:** corrective republication, independent audit, merge verification and post-merge documentation sync

## Итог

```text
G4.3: COMPLETE
G4.3 v1: SUPERSEDED_PRE_EXECUTION
G4.3 v1 results: NOT_AVAILABLE
G4.3 v2: FROZEN_PRE_SCREENING
stage outcome: CORRECTIVE_PROTOCOL_FROZEN
G4.4: NEXT / NOT STARTED
results: NOT_AVAILABLE
screening: NOT_STARTED
simulation: NOT_STARTED
Review winner: NONE
production approved: NO
production integration: PROHIBITED
```

Актуальный contract находится в [G4.3 v2 human protocol](../../docs/gamification/core-economy-candidate-protocol-v2.md). Канонический stage closeout находится в [roadmap](../../roadmap/gamification/g4-core-economy-candidate-protocol-v2.md).

## Проверенные Git identities

```text
starting gamification HEAD / exact PR base:
002c5d683040494a9e66cc999d5f627379986767

corrective PR head:
976ccfd0d998644e2b157b2735f690fbe17bbf29

PR:
#168

PR state:
MERGED

merge method:
MERGE COMMIT

merge SHA:
9a13cc40a2bae9ece4377a3781452beab46116f2

remote corrective task branch:
PRESERVED

owner execution checkout:
C:\Users\KykLa\Documents\anki-study-report

worktree created:
NO
```

The exact comparison was four commits ahead and zero commits behind the frozen base. The merged changed-path set contained 20 G4.3 v2 research and documentation paths. No v1 contract, v1 scenario, v1 matrix or production-runtime path was changed.

## Owner checkpoint result

The owner-executed PowerShell checkpoint used PowerShell 7.6.3 in the primary repository checkout and did not create a Git worktree.

The final runner completed the substantive checkpoint and pushed commit `976ccfd0d998644e2b157b2735f690fbe17bbf29`:

```text
validator: PASS
byte-identical regeneration: PASS
negative corpus: 40 / 40 PASS
focused pytest: 15 passed
repository guards: PASS
staged paths: 19
commit: PASS
push: PASS
```

The runner then exited with code `1` only after the successful push because its post-push PowerShell result handling attempted to read `.Count` from a scalar object. This failure did not affect repository content, validation, commit identity or push completion. PR metadata, independent audit and merge were completed separately through GitHub with the exact expected PR head.

## Frozen protocol inventory

```text
primitive candidates: 19
candidate bundles: 21
hypotheses: 20
hard gates: 29
metrics: 22
typed pipeline steps: 17
scenarios: 41
matrix expected / unique / missing / extra: 864 / 864 / 0 / 0
negative samples: 40
personas / threats / invariants: 9 / 14 / 28
```

Review remains an unresolved parallel axis:

```text
P-STEP-ZERO
P-TAPER-ZERO-30D
selection: NONE
default: NONE
winner: NONE
averaging: PROHIBITED
evaluation: PARALLEL_SEPARATE
```

Learn remains bounded by the frozen G2 limitation:

```text
candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
status: CONFIRMATORY_INCONCLUSIVE
limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
frozen source total: 1.0 LRU
```

Create remains excluded from the initial core economy.

## Frozen digests

```text
protocol:
f13f85e627297d328bcd30481924ff139f43c78d84b72f57a2ce6543cdcddd8b

pipeline:
6fe8d3f1b8b830dc258b7ca096428bc2ef53f5354ad2aa4aed2d35a76f04f6d2

scenarios:
83c89cd3667fe866a423f8a2cf9d58ce344030c4e2f65316559d8391de21edb7

matrix:
27a511b0601b259de6a75d62b6900193ead6fe38deea04e9d20230980af9ff0f

validator:
core-economy-protocol-v2-validator-3

generator:
core-economy-protocol-v2-generator-2
```

## Corrective validation coverage

The merged validator and focused tests verify:

- exact G4.1/G4.2 persona, threat and invariant identities;
- exact Review pair preservation without default, averaging or winner selection;
- Learn status and unresolved identity limitation preservation;
- positive Review and Learn marginal contributions below boundaries;
- explicit combined-cap control crowdout differentiation;
- candidate-specific expected outcomes only through matrix gate profiles;
- typed 17-step evaluation order and nonlinear-order distinction;
- deterministic row identities and exact matrix completeness;
- protocol, pipeline, scenario, matrix and row digest continuity;
- targeted negative-sample rejection using declared error codes;
- dependent digest and derived row-ID refresh for semantic mutations;
- intentional corruption preservation only for dedicated digest/row-ID samples;
- research-only, synthetic-only and no-production boundaries;
- no negative XP, XP debt, level loss, screening result or G4.4 activation.

Nine explicit source-boundary scenarios replace identifier-only coverage injection. They cover Review uncertainty, the Learn limitation, backlog/time neutrality, Create/new-material exclusion, configuration/calendar/scheduler/FSRS/due-date neutrality, honest Again/direct-price neutrality, planned rest/no debt, Momentum/recovery state-only behavior, and research/explanation/production boundaries.

## CI and workflow status

```text
GitHub Actions workflow runs for corrective PR head: 0
combined commit statuses: 0
CI PASS claim: NO
```

No GitHub Actions workflow was configured for this research-only commit. The bounded local semantic/schema validator and focused pytest checkpoint were the merge gate. Zero workflow runs are not represented as a CI pass.

## Documentation synchronization

The corrective PR synchronized current-state references in:

```text
README.md
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
research/gamification-sim/README.md
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g4-core-economy-candidate-protocol-v2.md
```

The synchronized state is:

```text
G4.3 COMPLETE
G4.3 v1 SUPERSEDED_PRE_EXECUTION
G4.3 v2 FROZEN_PRE_SCREENING
G4.4 NEXT / NOT STARTED
RESULTS NOT_AVAILABLE
SCREENING NOT_STARTED
SIMULATION NOT_STARTED
PRODUCTION PROHIBITED
```

## Не запускалось

```text
G1 matrices
G2 matrices
G4.4 screening
economy simulation
full research pytest
Fast CI
frontend tests/build
Docker real-Anki E2E
package / .ankiaddon validation
production implementation
```

These checks were outside the corrective protocol-publication risk surface. No dashboard payload, add-on runtime, scheduler, FSRS, collection access, package or release behavior changed.

## Ограничения

- No G4.4 screening result existed or was read during corrective protocol work.
- Both Review members remain unresolved and must be evaluated separately.
- The Learn identity limitation remains active.
- The protocol makes no human motivation, retention, mastery, balance or optimality claim.
- Candidate values and caps are research hypotheses, not production prices.
- Merge does not authorize production integration or start G4.4 automatically.

## Финальный вердикт

```text
G4_3_VERDICT=COMPLETE
G4_3_V1=SUPERSEDED_PRE_EXECUTION
G4_3_V2=FROZEN_PRE_SCREENING
PR_NUMBER=168
PR_HEAD=976ccfd0d998644e2b157b2735f690fbe17bbf29
MERGE_SHA=9a13cc40a2bae9ece4377a3781452beab46116f2
RESULTS=NOT_AVAILABLE
G4_4=NOT_STARTED
SIMULATION=NOT_STARTED
PRODUCTION=PROHIBITED
```
