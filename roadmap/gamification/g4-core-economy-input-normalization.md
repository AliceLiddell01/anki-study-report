# G4.2 — Модель входов, normalization boundary и неопределённости

## Статус

```text
Mode: ChatGPT
G3: DEFERRED / POST-MVP / NOT STARTED
G4: IN PROGRESS
G4.1: COMPLETE
G4.2: COMPLETE
input/uncertainty model: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
G4.3: NEXT / NOT STARTED
Review winner: NONE
production approved: NO
production integration: PROHIBITED
```

## Repository / delivery

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
starting gamification HEAD: 80197fbd0425347cd9d8b59ff616ffe6000674f9
task branch: g4-2-input-normalization-model
PR: #165
PR base: gamification
validated pre-closeout HEAD: 8002cef1f11c8c9f52c7b8d3c889be4e3db69c8c
final merge SHA: RECORDED_IN_EXTERNAL_REPORT_AFTER_VERIFIED_MERGE
master changed: NO
AGENTS.md: NOT FOUND
```

G4.2 выполнен как один research-contract PR. Production runtime, dashboard, API, scheduler, FSRS, database, package, workflows, release и `master` не изменяются.

## G4.1 dependency

```text
contract:
core-economy-problem-contract v1

status:
FROZEN_PRE_NORMALIZATION_ANALYSIS

contract blob:
dda1336328df7e79bc5ba1978a102faf5ca40e14

schema blob:
d124ce0aafccd84c38c142c1fb8319ef91877f87
```

Canonical PR #164 chronology:

```text
defective intermediate schema commit reachable from merged history: YES
defective schema present in final tree: NO
defective schema used as validated result: NO
```

G4.1 contract/schema не изменялись.

## Frozen artifacts

```text
docs/gamification/core-economy-input-normalization-model.md
research/gamification-sim/contracts/core-economy-input-normalization-v1.json
research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json
roadmap/gamification/g4-core-economy-input-normalization.md
```

Machine identity:

```text
contract_id: core-economy-input-normalization
version: 1
stage: G4.2
status: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
schema draft: https://json-schema.org/draft/2020-12/schema

contract Git blob:
0cf1bbb6f3f088d48b4c78bcc37145dacc8cebc5

schema Git blob:
6a5c312ac873fdcb86c4ec820842f759061c5253

human doc Git blob:
72478cb841a93fe678e290c7e5ce54502b7420b2

contract SHA-256:
1834c2b4cdf3b3b92067db3d90dd7a5779ae43054e4accf582d8dbab3b08ac8d

schema SHA-256:
54f14a26a66816bfb7f8a410bafa7946c1857a01e0e9558b8cce86df805cce23

human doc SHA-256:
996bce4c2f3e9fadb1d8546f93ef533384769ce568749a9b7de022ca7dd447f9
```

## Contract inventory

```text
domain input types: 2
common interface record types: 4
axes: 3
dispositions: 7
fail-closed reasons: 18
personas: 9
fixture requirements: 15
threat families: 14
protected invariants: 28
validation rules: 24
G4.3 requirements: 14
```

## Typed records

```text
REVIEW_DOMAIN_INPUT
LEARN_DOMAIN_INPUT
NORMALIZATION_INPUT
DOMAIN_CONTRIBUTION_RECORD
DAILY_AGGREGATION_INPUT
DAILY_AGGREGATION_RESULT_PLACEHOLDER
```

All records preserve source identity, source status, source unit, limitations, axes, decomposition and provenance. No implicit coercion or production semantics are allowed.

## Review uncertainty ledger

```text
uncertainty axis:
REVIEW_MODEL_AXIS_V1

members:
P-STEP-ZERO
P-TAPER-ZERO-30D

candidate status:
CONFIRMATORY_ELIGIBLE

selection:
NONE

default:
NONE

aggregation:
PARALLEL_SEPARATE

averaging:
PROHIBITED

winner criterion:
NOT_DEFINED

cross-domain criterion:
NOT_DEFINED
```

Matched synthetic evidence may produce one record per distinct member. Repetition within the same member is duplicate. Missing member or collapsed partition fails closed.

## Learn limitation ledger

```text
source model:
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

status:
CONFIRMATORY_INCONCLUSIVE

limitation:
DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE

achievement subject:
NOTE_SIBLING

allocation:
CONFIRMATION_ONLY_NO_PROVISIONAL_STATE

source unit:
LRU

frozen source total:
1.0

common economy XP:
false

confirmatory eligible:
false

production ready:
false

production approved:
false
```

The limitation propagates through domain input, contribution placeholder, daily aggregation, future explanation, candidate evaluation and final G4 claims.

## Axis model

```text
SESSION:
GROUPING_AND_OBSERVABILITY_ONLY

ANKI_DAY:
TYPED_SCHEDULER_DAY_AGGREGATION_AXIS

CALENDAR_DAY:
CIVIL_REPORTING_AXIS
```

```text
session multiplier: PROHIBITED
Anki day == calendar day by default: NO
missing Anki day → calendar fallback: PROHIBITED
missing calendar day → Anki fallback: PROHIBITED
host timezone fallback: PROHIBITED
timezone policy: NOT_SELECTED
streak reset time: NOT_SELECTED
```

## Fail-closed model

Registered reasons:

```text
MISSING_REQUIRED_FIELD
UNKNOWN_DOMAIN
UNKNOWN_SOURCE_MODEL
SOURCE_STATUS_MISMATCH
REVIEW_CANDIDATE_MISSING
REVIEW_UNCERTAINTY_COLLAPSED
LEARN_LIMITATION_MISSING
LEARN_IDENTITY_AMBIGUOUS
DAY_AXIS_MISSING
DAY_AXIS_CONFLICT
DUPLICATE_RECORD_ID
DUPLICATE_SOURCE_EVENT
UNIT_MISMATCH
PROVENANCE_MISSING
REAL_DATA_FIELD_PRESENT
CREATE_DOMAIN_PRESENT
NUMERIC_POLICY_PRESELECTED
SOURCE_IDENTITY_CONFLICT
```

Each reason has a detection point, record disposition, whole-batch behavior, explanation code and retry policy. Silent defaults are prohibited.

## Persona and fixture boundary

Nine G4.1 personas are preserved as descriptor metadata. Exact event sequences, counts, durations, expected XP and seeds are `NOT_DEFINED`.

Fifteen fixture requirements are frozen. Every requirement identifies threats, invariants, personas, input categories, expected disposition and deterministic replay requirement.

```text
exact traces:
NOT_DEFINED

exact numeric outputs:
NOT_DEFINED

matrix:
NOT_DEFINED

execution:
NOT_STARTED
```

## Coverage

```text
threat registry/reference coverage: 14 / 14
invariant registry/reference coverage: 28 / 28
persona registry/reference coverage: 9 / 9
fixture registry/reference coverage: 15 / 15
validation-rule coverage: 24 / 24
G4.3 entry coverage: 14 / 14
hard-gate failures compensable: NO
weighted score: ABSENT
```

## Unresolved selections

```text
Review winner: NONE
Review candidate default: NONE
Review candidate averaging: PROHIBITED
Review/Learn ratio: NONE
normalized unit: NONE
normalized XP amount: NONE
daily cap: NONE
soft cap: NONE
diminishing function: NONE
productive-day threshold: NONE
level curve / count: NONE
streak formula: NONE
rest quota: NONE
Momentum formula: NONE
recovery formula: NONE
candidate families: NOT_DEFINED
exact fixture traces: NOT_DEFINED
screening matrix: NOT_DEFINED
simulation seed: NONE
simulation results: NOT_AVAILABLE
production storage/API/UI: NOT_DESIGNED
```

## Validation

Focused validation completed on exact serialized bytes published in Git:

```text
strict duplicate-key-safe JSON parse: PASS
Draft 2020-12 schema self-check: PASS
contract-schema validation: PASS
contract local/Git blob equality: PASS
schema local/Git blob equality: PASS
human/machine identity parity: PASS
stage/status parity: PASS
Review uncertainty parity: PASS
Learn limitation parity: PASS
domain input type coverage: PASS
axis coverage: 3 / 3 PASS
fail-closed disposition coverage: 18 / 18 PASS
persona descriptor coverage: 9 / 9 PASS
fixture requirement coverage: 15 / 15 PASS
threat reference coverage: 14 / 14 PASS
invariant reference coverage: 28 / 28 PASS
G4.3 entry coverage: 14 / 14 PASS
unresolved selection coverage: PASS
semantic unique-ID/reference checks: PASS
negative samples: 45 / 45 PASS
```

Negative cases include all mandatory categories: unknown/missing fields, forbidden domain/model, Review candidate omission/default/collapse/mismatch, Learn status/limitation/eligibility/identity drift, common-unit or numeric-policy selection, axis substitution, duplicate IDs/events, missing provenance, real data, G4.3/simulation activation and unknown fixture/invariant/threat/persona references.

Validation environment:

```text
Python: 3.13.5
jsonschema: 4.26.0
```

Project-local WSL Python 3.11 and owner worktree state were not independently available in this connector session.

## Exact expected changed paths

```text
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
docs/gamification/core-economy-input-normalization-model.md
research/gamification-sim/README.md
research/gamification-sim/contracts/core-economy-input-normalization-v1.json
research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g4-core-economy-input-normalization.md
```

Top-level `README.md`, G4.1 artifacts, G1/G2 contracts/schemas, research execution code/tests and production paths remain unchanged.

## Pull request pre-merge state

```text
PR: #165
base: gamification
head: g4-2-input-normalization-model
base SHA: 80197fbd0425347cd9d8b59ff616ffe6000674f9
validated pre-closeout HEAD: 8002cef1f11c8c9f52c7b8d3c889be4e3db69c8c
branch ahead / behind before final closeout commit: 14 / 0
changed files: 10
mergeable: YES
combined status checks: 0
workflow runs: 0
```

Zero workflow runs is recorded as a fact, not as `CI PASS`.

## Not run

```text
G1 matrices
G2 matrices
economy simulation
full research pytest
Fast CI
frontend tests/build
Docker real-Anki E2E
package / .ankiaddon validation
production implementation
```

Reason: docs/contracts/schema-only contour; no executable research or production code changes.

## Limitations

- Review winner remains unresolved.
- Learn input remains `CONFIRMATORY_INCONCLUSIVE`.
- Raw G1/G2 bundles were not freshly revalidated.
- Disposable Anki identity probe was not executed.
- G4.2 defines an interface, not a balanced or optimal economy.
- Exact candidate policies, traces, matrix, formulas and results do not exist.
- Owner WSL checkout/worktree/tool state was not independently verified.
- No local task worktree was created in the connector environment.

## G4.3 boundary

```text
G4.3 — Candidate economy protocol and hypothesis design
NEXT / NOT STARTED
```

G4.3 may only use frozen G4.2 records and must publish candidate families, gates, metrics, exact synthetic traces and matrix prospectively before screening.

```text
candidate families created: NO
exact traces created: NO
screening matrix created: NO
simulation executed: NO
results accessed: NO
G4.3 started: NO
```

## Production boundary

```text
production approved: NO
production integration: PROHIBITED
runtime/dashboard/API changed: NO
scheduler/FSRS/due dates changed: NO
database/ledger changed: NO
package/workflows/release changed: NO
master changed: NO
```

## G4.3 bounded provenance correction

The G4.2 closeout previously recorded the pre-final human-document identity.
The human document itself remains unchanged at the exact bytes merged by PR #165.

```text
old identity:
pre-final human-document state

old pre-final human blob:
b8fd53917eab9a1433d301383c76617de5ebb85f

old pre-final human SHA-256:
c851b14aaaab068d730ce7553d69593fb4d783e509830f4acb9badfa10de9c08

current identity:
final merged human-document bytes

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
