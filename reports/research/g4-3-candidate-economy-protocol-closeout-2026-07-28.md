# G4.3 candidate economy protocol — post-merge closeout

**Дата:** 2026-07-28  
**Track:** Gamification `G`  
**Stage:** `G4.3 — Candidate economy protocol and hypothesis design`  
**Target branch:** `gamification`  
**Scope:** post-merge verification and documentation synchronization

## Итог

```text
G4.3: COMPLETE
candidate protocol: FROZEN_PRE_SCREENING
stage outcome: PROTOCOL_FROZEN
G4.4: NEXT / NOT STARTED
results: NOT_AVAILABLE
screening: NOT_STARTED
simulation: NOT_STARTED
production approved: NO
production integration: PROHIBITED
```

Актуальный contract находится в [G4.3 human protocol](../../docs/gamification/core-economy-candidate-protocol.md). Канонический stage closeout находится в [roadmap](../../roadmap/gamification/g4-core-economy-candidate-protocol.md).

## Проверенные Git identities

```text
starting gamification HEAD:
a46e920cea0bbe97f2d0c785965febf0a52ed9e7

protocol publication HEAD:
801a0112fa1af9334b0992725056da4292bc5d94

final PR head:
8b22851abbd71f661957fefcbde84548fdcd38f4

PR:
#166

PR state:
MERGED

merge SHA:
0d42e7bbee80b99de7e3369071c9a2dcdc6ba6bb

remote task branch:
DELETED

owner local task worktree:
REMOVED

owner local task branch:
DELETED
```

GitHub verification confirmed that PR #166 was merged into `gamification` and that its changed-path set contained exactly the nine expected G4.3 publication paths.

## G4.2 provenance correction

G4.3 corrected only a stale identity ledger in the G4.2 closeout.

```text
stale pre-final human blob:
b8fd53917eab9a1433d301383c76617de5ebb85f

current final merged human blob:
72478cb841a93fe678e290c7e5ce54502b7420b2

current final merged human SHA-256:
996bce4c2f3e9fadb1d8546f93ef533384769ce568749a9b7de022ca7dd447f9

G4.2 human document changed:
NO

G4.2 semantics changed:
NO

G4.2 contract/schema changed:
NO
```

## Frozen protocol inventory

```text
owner principle:
GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF

preferred research direction:
TAPER / RECOVERY

abrupt uncertainty policy:
RETAINED AS CONTROL

Review members:
P-STEP-ZERO
P-TAPER-ZERO-30D

Review winner/default:
NONE / NONE

Review averaging:
PROHIBITED

Learn input:
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

Learn status:
CONFIRMATORY_INCONCLUSIVE

Learn limitation:
DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE

primitive policies:
20

curated candidate bundles:
24

hypotheses:
24

non-compensable hard gates:
23

metrics:
19

deterministic scenarios:
40

matrix expected / unique:
762 / 762

matrix duplicates / missing / extra:
0 / 0 / 0

scenario digest:
9f53c8e6af181a0106a74f0bb52d1695a00e158a6ad15cb656c91bf6670881a3

matrix digest:
9f0ad95f8e99b3e25d19d859f88afa13a0b5b3b9efc99427facde336e146241c
```

The protocol uses `CURATED_BOUNDED_FACTORIAL_DESIGN`; the full primitive Cartesian product is prohibited. Graceful degradation is a preferred research direction, not a selected winner.

## Focused validation recorded by the owner runner

```text
strict duplicate-key-safe JSON parse: PASS
Draft 2020-12 schema self-check: PASS
artifact-schema validation: PASS
semantic reference integrity: PASS
G4.2 exact dependency identity: PASS
candidate/scenario/matrix uniqueness: PASS
Review-axis coverage: PASS
Learn limitation propagation: PASS
results-not-run enforcement: PASS
negative samples: 34 / 34 rejected
scenario count: 40
matrix rows: 762
changed-path allowlist: exact 9 paths
workflow checks: 0
```

`workflow checks: 0` is intentionally not reported as `CI PASS`.

## Owner runner cleanup result

The bounded runner completed validation, commits, push, PR creation, merge and remote branch deletion. Its original `EXIT_CODE=1` occurred only during local safe deletion:

```text
git branch -d g4-3-candidate-economy-protocol
```

The current owner checkout was on an unrelated branch, so `git branch -d` compared merge status against that checkout rather than `origin/gamification`. The owner subsequently removed the already-merged local task branch with no repository-content change.

This cleanup failure was not a publication, validation, merge or G4.3 failure.

## Documentation synchronization

After the owner cleanup, the following current-state entrypoints were synchronized:

```text
README.md
docs/project-overview.md
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g4-core-economy-candidate-protocol.md
reports/README.md
```

The sync replaces stale statements such as `G4.3 NEXT / NOT STARTED` with the verified state:

```text
G4.3 COMPLETE
FROZEN_PRE_SCREENING
G4.4 NEXT / NOT STARTED
RESULTS NOT_AVAILABLE
SIMULATION NOT_STARTED
PRODUCTION PROHIBITED
```

It does not change the frozen candidate protocol, machine contracts, schemas, scenarios, dry matrix or any production surface.

## Не запускалось

```text
G1 matrices
G2 matrices
G4 screening
economy simulation
full research pytest
Fast CI
frontend tests/build
Docker real-Anki E2E
package / .ankiaddon validation
production implementation
```

These checks were outside the docs-only post-merge synchronization risk surface. The G4.3 publication itself had already completed its focused contract/schema/semantic validation before merge.

## Ограничения

- No G4 screening result existed or was read during protocol design.
- Both Review members remain unresolved and must be evaluated separately.
- The Learn identity limitation remains active.
- No human motivation, retention, mastery, balance or optimality claim is made.
- No runtime, dashboard, API, storage, scheduler, FSRS, package, workflow or release behavior changed.
- G4.4 is not activated by this report or by the documentation sync.

## Финальный вердикт

```text
G4_3_VERDICT=COMPLETE
PROTOCOL_STATUS=FROZEN_PRE_SCREENING
PR_NUMBER=166
MERGE_SHA=0d42e7bbee80b99de7e3369071c9a2dcdc6ba6bb
RESULTS=NOT_AVAILABLE
G4_4=NOT_STARTED
SIMULATION=NOT_STARTED
PRODUCTION=PROHIBITED
```
