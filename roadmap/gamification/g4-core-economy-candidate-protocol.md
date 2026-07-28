# G4.3 — Candidate economy protocol and hypothesis design

## Status

```text
Mode: ChatGPT
G4: IN PROGRESS
G4.1: COMPLETE
G4.2: COMPLETE
G4.3: COMPLETE
candidate protocol: FROZEN_PRE_SCREENING
stage outcome: PROTOCOL_FROZEN
G4.4: NEXT / NOT STARTED
Review winner: NONE
preferred research direction: GRACEFUL_DEGRADATION
results: NOT_AVAILABLE
simulation: NOT_STARTED
production approved: NO
production integration: PROHIBITED
```

## Repository / delivery

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
starting gamification HEAD: a46e920cea0bbe97f2d0c785965febf0a52ed9e7
task branch: g4-3-candidate-economy-protocol
PR: #166
PR base: gamification
protocol publication HEAD: 801a0112fa1af9334b0992725056da4292bc5d94
final PR head / merge SHA: RECORDED_IN_EXTERNAL_REPORT_AFTER_VERIFIED_MERGE
AGENTS.md: NOT FOUND
master changed: NO
local owner execution: OWNER_EXECUTED
```

## G4.2 artifact identity correction

The stale ledger entry described the pre-final human-document state. The current
document remains the exact final bytes merged by PR #165.

```text
old pre-final human blob:
b8fd53917eab9a1433d301383c76617de5ebb85f

old pre-final human SHA-256:
c851b14aaaab068d730ce7553d69593fb4d783e509830f4acb9badfa10de9c08

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

Only `roadmap/gamification/g4-core-economy-input-normalization.md` was corrected.

## Frozen protocol inventory

```text
owner principle:
GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF

Review source members:
P-STEP-ZERO
P-TAPER-ZERO-30D

Review winner:
NONE

Review evaluation:
PARALLEL_SEPARATE

Review averaging:
PROHIBITED

preferred research direction:
TAPER / RECOVERY

abrupt policy:
RETAINED AS CONTROL

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

The matrix uses `CURATED_BOUNDED_FACTORIAL_DESIGN`; a full Cartesian product is
prohibited. Hard failures under one Review member cannot be hidden by averaging.

## Canonical artifacts and identities at publication HEAD

- `roadmap/gamification/g4-core-economy-input-normalization.md` — blob `f608099bd0c607700511419ade9ea638b95aa60c`, SHA-256 `d4a8391142697edd68318f8baf521bad115888e5b4f29de703979bbaff545165`, `11211` bytes
- `docs/gamification/core-economy-candidate-protocol.md` — blob `398041e9b20e8bab3697d43131e4f429662b744a`, SHA-256 `0ebbb587f1e405923bc692bb54124bcdf1810b92a2f5626d2c303f2c35249fda`, `31802` bytes
- `research/gamification-sim/contracts/core-economy-candidate-protocol-v1.json` — blob `dcbae79f51f618524fd79ad87b5964e4664e4ba2`, SHA-256 `6b993ebd5f5587145e4e4c6d6d7e946d4b3da7e8633ddfd1334eab29dda93abf`, `75006` bytes
- `research/gamification-sim/schemas/core-economy-candidate-protocol-v1.schema.json` — blob `b0bbcd560879fd0065b744f43a6999183633e96f`, SHA-256 `fd9287da36657b6b4125d3240e8d05bc864cbbf024d41805ec24e270b91dc222`, `24385` bytes
- `research/gamification-sim/fixtures/core-economy-candidate-scenarios-v1.json` — blob `231bd5d85458fd40403fdbdfb7c7cad5d5e3eca6`, SHA-256 `3f9f320fa6131b4ecbfe3272d41631005e778425a8662203c37f3d6c534dd193`, `594047` bytes
- `research/gamification-sim/schemas/core-economy-candidate-scenarios-v1.schema.json` — blob `ce7f1ef48de8d5e672b90e6a3a89ee65f6f7ccc1`, SHA-256 `7de2c784d1b81755a2bdb7f25b514937baf4089ecc632090a5c1a4c8919a0a4e`, `13043` bytes
- `research/gamification-sim/matrices/core-economy-screening-matrix-v1.json` — blob `7fa618af1bb3513b4bd6a0f158acb7bc5d38e835`, SHA-256 `daba6406b60698dd0c2f4cd990f2923396bd23d0a4c0861891fe3632ccebaf13`, `306832` bytes
- `research/gamification-sim/schemas/core-economy-screening-matrix-v1.schema.json` — blob `bddb1ae14c886738735482c60e4781386650a272`, SHA-256 `917b86215e65d4ccc536b694dd49bac1c288ecccf212f1ed5743d35b74a610b3`, `7366` bytes

The G4.3 closeout identity is recorded after its commit in the external report.

## Validation

```text
strict duplicate-key-safe JSON parse: PASS
Draft 2020-12 schema self-check: PASS
artifact-schema validations: PASS
human/machine identity and status parity: PASS
G4.2 dependency identity parity: PASS
owner-principle parity: PASS
candidate registry uniqueness: PASS
hypothesis coverage: PASS
hard-gate coverage: PASS
metric coverage: PASS
scenario registry uniqueness: PASS
matrix exact cardinality: PASS
Review-member coverage: PASS
Learn limitation propagation: PASS
persona/threat/invariant coverage: PASS
results-not-run enforcement: PASS
G4.4-not-started enforcement: PASS
negative samples: 34 / 34 rejected
relative links and Markdown fences: PASS
git diff --check: PASS
changed-path allowlist: exact 9 paths
secret/private-path scan: PASS
production boundary: PASS
research execution boundary: PASS
```

## No-results proof

```text
protocol publication precedes execution: YES
results: NOT_AVAILABLE
all matrix rows: NOT_RUN
screening executed: NO
simulation: NOT_STARTED
G4.4: NEXT / NOT STARTED
production approved: NO
```

## Not run

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

## Changed paths

```text
roadmap/gamification/g4-core-economy-input-normalization.md
docs/gamification/core-economy-candidate-protocol.md
research/gamification-sim/contracts/core-economy-candidate-protocol-v1.json
research/gamification-sim/schemas/core-economy-candidate-protocol-v1.schema.json
research/gamification-sim/fixtures/core-economy-candidate-scenarios-v1.json
research/gamification-sim/schemas/core-economy-candidate-scenarios-v1.schema.json
research/gamification-sim/matrices/core-economy-screening-matrix-v1.json
research/gamification-sim/schemas/core-economy-screening-matrix-v1.schema.json
roadmap/gamification/g4-core-economy-candidate-protocol.md
```

## Boundaries and limitations

- No G4 result was available or viewed while candidates, gates, metrics, traces,
  and matrix were frozen.
- Review winner remains unresolved and both source members remain mandatory.
- Learn remains `CONFIRMATORY_INCONCLUSIVE`; its identity limitation propagates.
- External references are design patterns, not Anki economy evidence.
- No human motivation, retention, mastery, balance, optimality, or prevention of
  all farming is claimed.
- No production runtime, dashboard, API, storage, scheduler, FSRS, package,
  workflow, or release surface changed.

## G4.4 entry contract

`G4.4 — Bounded core-economy screening and simulation` remains inactive. Entry
requires exact publication SHA, candidate/scenario/matrix identities, valid
schemas, frozen gates and metrics, Review sensitivity, propagated Learn
limitation, detached validation, synthetic-only data, no production code, and a
separate owner decision.
