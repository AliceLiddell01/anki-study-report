# Gamification track

**Track:** `G`
**Role:** parallel research/product direction
**Current status:** `G0–G2 Complete`; G1 winner `P-TAPER-ZERO-30D`; G2 winner `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING`; `G3 Deferred / Post-MVP / Not Started`; `G4/G4.4 Complete` with `REJECT`; production integration not approved

Gamification does not block the Core path. Research code, fixtures, contracts, evidence and recommended research candidates do not enter the add-on package, Fast CI or release workflows without a later explicit decision.

## Branch and production policy

- `gamification` is the canonical independent branch.
- `gamification → master` is prohibited until a separate owner decision.
- `archive/gamification-concept-foundation-2026-07` is a historical read-only source and must not be merged/rebased wholesale.
- Any production integration requires a separate explicit decision.

## AI work mode for this track

Shared rules are defined in [ChatGPT and Codex work modes](../../docs/ai-work-modes.md), with separate [ChatGPT](../../docs/chatgpt-work-mode.md), [Codex](../../docs/codex-agent-rules.md) and [Codex local environment](../../docs/codex-local-environment.md) contracts.

For this track, target branch and PR base are `gamification`.

## Stage map

```text
G0  Research reconciliation                         COMPLETE
G1  Review XP cross-horizon cycling                 COMPLETE — P-TAPER-ZERO-30D
G2  Learn XP specification and simulation           COMPLETE — RECOMMEND_LEARN_XP_RESEARCH_MODEL
G3  Create XP specification and simulation          DEFERRED / POST-MVP / NOT STARTED
G4  Core gamification economy calibration           COMPLETE — REJECT
G4.1 Problem and contract freeze                    COMPLETE
G4.2 Input normalization and uncertainty model      COMPLETE
G4.3 Candidate protocol and hypothesis design       COMPLETE — v4 FROZEN_AND_EXECUTED
G4.4 Bounded screening                              COMPLETE — REJECT
G5  Production architecture foundation              CONDITIONAL
G6  Gamification MVP                                CONDITIONAL
G7  Achievements foundation                         CONDITIONAL
G8  Skills, quests and domain expansion             DEFERRED / CONDITIONAL
```

## G0 — Research reconciliation

**Status:** Complete.

- `G0.1` Canonical branch baseline — [report](g0-branch-baseline.md)
- `G0.2` Core compatibility — [report](g0-core-compatibility.md)
- `G0.3` Historical inventory — [report](g0-historical-asset-inventory.md), [manifest](g0-historical-asset-manifest.md)
- `G0.4` Selective recovery — [report](g0-selective-research-recovery.md), [ledger](g0-recovery-ledger.md)
- `G0.5` Reproducible environment — [report](g0-reproducible-environment.md)
- `G0.6` Functional baseline — [report](g0-functional-baseline.md), [correction](g0-installed-execution-boundary-correction.md)
- `G0.7` Evidence reproduction — [report](g0-evidence-reproduction.md), [closure](g0-reconciliation-closure.md)

G0 reproduced the current synthetic Review baseline without production integration.

## G1 — Close Review XP cross-horizon cycling gap

**Status:** Complete.

```text
G1 final outcome: RECOMMEND_RESEARCH_CANDIDATE
recommended research candidate: P-TAPER-ZERO-30D
P-STEP-ZERO: CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D: CONFIRMATORY_ELIGIBLE; selected research winner; not falsified
production integration: PROHIBITED
```

Decomposition:

- `G1.1` problem and diagnostic contract — [report](g1-problem-gate-freeze.md), [correction](g1-contract-correction.md)
- `G1.2` root-cause attribution — [report](g1-root-cause-attribution.md), [correction](g1-root-cause-attribution-correction.md)
- `G1.3` candidate protocol — [report](g1-candidate-protocol.md)
- `G1.4` bounded screening — [report](g1-bounded-screening.md)
- `G1.5` confirmatory evidence — [report](g1-confirmatory-evidence.md)
- `G1.6` candidate decision and closure — [decision](g1-review-xp-decision.md)

G1.6 originally selected no winner because accepted aggregates did not provide a pre-existing non-arbitrary tie-breaker. The owner-authorized G4 closure resolves that tie with `MINIMIZE_LEGITIMATE_CONTEXT_HARM`: `P-TAPER-ZERO-30D` is the research winner because it avoids immediate post-boundary zeroing. STEP remains eligible and non-falsified; Review averaging remains prohibited.

## G2 — Learn XP specification and simulation

**Status:** Complete.

```text
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
decision basis: MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE
selected candidate evidence status: CONFIRMATORY_INCONCLUSIVE
production integration: PROHIBITED
```

Decomposition:

- `G2.1` problem contract — [closeout](g2-learn-xp-problem-contract.md)
- `G2.2` lifecycle and anti-farming model — [closeout](g2-learn-xp-lifecycle.md)
- `G2.3` candidate protocol — [closeout](g2-learn-xp-candidate-protocol.md)
- `G2.4` bounded screening — [closeout](g2-learn-xp-bounded-screening.md)
- `G2.5` confirmatory evidence — [closeout](g2-learn-xp-confirmatory-evidence.md)
- `G2.6` final decision — [decision](g2-learn-xp-decision.md)

The recommendation is a bounded research/product governance choice. It does not create confirmatory eligibility, prove human-learning or motivation benefit, or authorize production integration.

## G3 — Create XP specification and simulation

**Status:** Deferred / Post-MVP / Not Started.

```text
critical path for first Gamification MVP: NO
blocks G4: NO
blocks G5: NO
blocks G6: NO
production integration: PROHIBITED
```

G3/Create XP is excluded from the initial core economy. It may be activated only when all three conditions are met:

```text
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

G3.1, Create lifecycle, candidates, reward units, formulas and simulation are intentionally undefined.

## G4 — Core gamification economy calibration

**Status:** Complete — `REJECT`.

G4 prospectively defines and investigates a bounded, explainable and manipulation-resistant economy for:

```text
Review XP
+
Learn XP
```

Create XP is excluded and G3 is not a dependency.

Dependencies:

```text
G1: COMPLETE
G2: COMPLETE
G3: NOT REQUIRED / DEFERRED POST-MVP
```

### G4.1 — Freeze core gamification economy problem and contract

**Status:** Complete.

Artifacts:

- [human core economy contract](../../docs/gamification/core-economy-problem-contract.md)
- [machine contract](../../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](g4-core-economy-problem-contract.md)

```text
status: FROZEN_PRE_NORMALIZATION_ANALYSIS
initial domains: REVIEW_DOMAIN; LEARN_DOMAIN
Create XP: EXCLUDED
Review winner: NONE
Learn input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
production integration: PROHIBITED
```

G4.1 selects no conversion ratio, normalized XP, productive-day threshold, level curve, streak, Momentum or recovery formula.

### G4.2 — Input normalization and uncertainty model

**Status:** Complete.

Artifacts:

- [human input/uncertainty model](../../docs/gamification/core-economy-input-normalization-model.md)
- [machine contract](../../research/gamification-sim/contracts/core-economy-input-normalization-v1.json)
- [strict Draft 2020-12 schema](../../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json)
- [G4.2 closeout](g4-core-economy-input-normalization.md)

```text
status: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
Review axis: REVIEW_MODEL_AXIS_V1
Review members: P-STEP-ZERO; P-TAPER-ZERO-30D
Review winner/default: NONE / NONE
Review evaluation: PARALLEL_SEPARATE
Review averaging: PROHIBITED
Learn input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
axes: SESSION; ANKI_DAY; CALENDAR_DAY
numeric normalization: NOT SELECTED
simulation: NOT STARTED
production integration: PROHIBITED
```

G4.2 freezes typed source records, contribution/day placeholders, Review uncertainty, Learn limitation propagation, independent axes, fail-closed dispositions, persona descriptors, deterministic fixture requirements and provenance.

### G4.3 — Candidate economy protocol and hypothesis design (historical v1)

**Status:** Complete — historical publication superseded before execution.

Artifacts:

- [human candidate protocol](../../docs/gamification/core-economy-candidate-protocol.md)
- [machine candidate protocol](../../research/gamification-sim/contracts/core-economy-candidate-protocol-v1.json)
- [candidate protocol schema](../../research/gamification-sim/schemas/core-economy-candidate-protocol-v1.schema.json)
- [deterministic scenarios](../../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v1.json)
- [scenario schema](../../research/gamification-sim/schemas/core-economy-candidate-scenarios-v1.schema.json)
- [dry screening matrix](../../research/gamification-sim/matrices/core-economy-screening-matrix-v1.json)
- [matrix schema](../../research/gamification-sim/schemas/core-economy-screening-matrix-v1.schema.json)
- [G4.3 canonical closeout](g4-core-economy-candidate-protocol.md)
- [G4.3 post-merge report](../../reports/research/g4-3-candidate-economy-protocol-closeout-2026-07-28.md)

```text
owner principle: GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF
preferred research direction: TAPER / RECOVERY
abrupt uncertainty policy: RETAINED AS CONTROL
Review winner/default: NONE / NONE
Review averaging: PROHIBITED
Learn limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
primitive policies: 20
curated candidate bundles: 24
hypotheses: 24
non-compensable hard gates: 23
metrics: 19
deterministic scenarios: 40
matrix expected / unique: 762 / 762
matrix duplicates / missing / extra: 0 / 0 / 0
scenario digest: 9f53c8e6af181a0106a74f0bb52d1695a00e158a6ad15cb656c91bf6670881a3
matrix digest: 9f0ad95f8e99b3e25d19d859f88afa13a0b5b3b9efc99427facde336e146241c
results: NOT_AVAILABLE
screening executed: NO
simulation: NOT_STARTED
production integration: PROHIBITED
```

The protocol uses `CURATED_BOUNDED_FACTORIAL_DESIGN`; a full primitive Cartesian product is prohibited. Both Review members remain mandatory and separate. G4.3 selects no winner, production formula, default Review member or Review/Learn exchange rate.

PR #166 merged G4.3 into `gamification` at `0d42e7bbee80b99de7e3369071c9a2dcdc6ba6bb`.

### G4.4 — Bounded screening and G4 closure

**Status:** Complete — `REJECT`.

Artifacts:

- [technical screening evidence](../../docs/gamification/core-economy-bounded-screening.md)
- [canonical G4.4 closeout](g4-core-economy-bounded-screening.md)
- [research handoff](../../docs/gamification/core-economy-research-handoff.md)
- [accepted result manifest](../../research/gamification-sim/results/core-economy-screening-manifest-v4.json)
- [accepted row results](../../research/gamification-sim/results/core-economy-screening-results-v4.json)

```text
accepted protocol: v4
publication SHA: 78ce71d82d72577f8283707a85b8e6b226330c94
evaluator SHA: 6174c5deae40b339b7e738ae08c1060b3f0158fa
rows expected / actual / unique: 1275 / 1275 / 1275
missing / extra / duplicates: 0 / 0 / 0
gate results / metric results: 3952 / 3710
unexpected failures: 33
result artifact digest: ad000099135574d285561d8e9bcc624ff430d25c42dd5b2d89a35476f3fad5db
result-set digest: bbbacf3880378409a740c26d85dbc589178ec2480f471107639e4c7ed8198d90
final G4 outcome: REJECT
```

Все eligible integrated bundles провалили non-compensable gates: uncertainty policies — `HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED`, high daily policy — `HG-EXTREME-VOLUME-BOUNDED`. Isolated passing candidates не компенсируют эти failures и не образуют post-hoc bundle.

```text
Review winner: P-TAPER-ZERO-30D
Learn winner: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
Learn limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
recommended integrated bundle: NONE
production integration: PROHIBITED
```

Full dimension ledger and rejected/control candidates are recorded in the canonical closeout.

## G5 — Production architecture foundation

**Status:** Conditional after G4 and stable Core contracts.

Design local-first event capture, ledger, persistence, migrations, reconciliation, privacy, versioning and explainability before UI.

## G6 — Gamification MVP

**Status:** Conditional after G5 and explicit owner approval.

Local level/XP, streak with planned rest, Momentum, explanations/history and opt-out; no leaderboards, marketplace or mandatory accounts.

## G7 — Achievements foundation

**Status:** Conditional.

Add minimal explainable achievements only after MVP evidence identifies a concrete feedback gap.

## G8 — Skills, quests and domain expansion

**Status:** Deferred / conditional.

Add one named workflow/domain at a time; no generic life-tracking framework or speculative routes.

## Production boundary

No production add-on, dashboard, payload, API, migration, scheduler, FSRS, package, release or telemetry integration is approved. G3 is deferred and non-blocking. G4/G4.4 are complete with `REJECT`; G5/G6 remain conditional and not started.

## G4 publication chronology

```text
G4: COMPLETE
G4.3: COMPLETE
G4.3 v1: SUPERSEDED_PRE_EXECUTION
G4.3 v1 results: NOT_AVAILABLE
G4.3 v2: SUPERSEDED_PRE_EXECUTION
G4.3 v3: INVALIDATED_AFTER_SCREENING
G4.3 v4: FROZEN_AND_EXECUTED
G4.4: COMPLETE
final G4 outcome: REJECT
```

See [G4.3 v2 closeout](g4-core-economy-candidate-protocol-v2.md), [v3 invalidation](../../reports/research/g4-core-economy-v3-screening-invalidation.md) and [final G4.4 closeout](g4-core-economy-bounded-screening.md).
