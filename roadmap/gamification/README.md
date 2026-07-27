# Gamification track

**Track:** `G`
**Role:** parallel research/product direction
**Current status:** `G0 Complete`; `G1 Complete` with `DEFER_REVIEW_MODEL`; `G2 In Progress`; `G2.1–G2.4 Complete`; `G2.5 In Progress — Frozen Pre-Results`; final G2 decision stage not started; production integration not approved

Gamification does not block the Core path. Research code, fixtures, contracts and evidence do not enter the add-on package, Fast CI or release workflows without a later explicit decision.

## Branch and production policy

- `gamification` is the canonical independent branch.
- `gamification → master` is prohibited until a separate owner decision.
- `archive/gamification-concept-foundation-2026-07` is a historical read-only source and must not be merged/rebased wholesale.
- Any production integration requires a separate explicit decision.

## AI work mode for this track

Shared rules are defined in [ChatGPT and Codex work modes](../../docs/ai-work-modes.md), with separate [ChatGPT](../../docs/chatgpt-work-mode.md), [Codex](../../docs/codex-agent-rules.md) and [Codex local environment](../../docs/codex-local-environment.md) contracts.

For this track, target branch and PR base are `gamification`.

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

### Final state

```text
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended research candidate: NONE
P-STEP-ZERO: CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D: CONFIRMATORY_ELIGIBLE; not selected; not falsified
production integration: PROHIBITED
```

### Decomposition

- `G1.1 — Freeze problem and diagnostic contract`: Complete — [report](g1-problem-gate-freeze.md)
  - correction: Complete — [report](g1-contract-correction.md)
- `G1.2 — Root-cause attribution`: Complete — [report](g1-root-cause-attribution.md)
  - `G1.2a` correction: Complete — [report](g1-root-cause-attribution-correction.md)
- `G1.3 — Candidate protocol and hypothesis design`: Complete — [report](g1-candidate-protocol.md)
- `G1.4 — Bounded screening`: Complete — [report](g1-bounded-screening.md)
- `G1.5 — Confirmatory evidence`: Complete — [report](g1-confirmatory-evidence.md)
- `G1.6 — Candidate decision and closure`: Complete — [decision](g1-review-xp-decision.md)

G1.2a classified the root cause as `ROOT_CAUSE_PARTIALLY_LOCALIZED` / `MEDIUM`. G1.4 retained `P-STEP-ZERO` and `P-TAPER-ZERO-30D`; G1.5 marked both `CONFIRMATORY_ELIGIBLE`. G1.6 selected no winner because raw evidence continuity could not be freshly revalidated and accepted aggregates did not provide a non-arbitrary tie-breaker.

Review XP production integration remains prohibited.

## G2 — Learn XP specification and simulation

**Status:** In Progress.

G2 is independent from Review XP. It does not inherit Review formula, candidate families, matrices, thresholds or G1 outcome.

### G2.1 — Freeze Learn XP problem and contract

**Status:** Complete.

Artifacts:

- [human Learn XP problem contract](../../docs/gamification/learn-xp-problem-contract.md);
- [machine contract](../../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json);
- [strict schema](../../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json);
- [G2.1 closeout](g2-learn-xp-problem-contract.md).

Frozen status:

```text
contract_id: learn-xp-problem-contract
version: 1
status: FROZEN_PRE_LIFECYCLE_ANALYSIS
identity candidates: CARD; NOTE; SIBLING_GROUP; LEARNING_EPISODE
threat families: 6
protected invariants: 19
allowed final G2 outcomes: 3
identity winner: NONE
reward amount: NONE
pending ratio: NONE
confirmation delay: NONE
simulation executed: NO
production approved: NO
```

G2.1 freezes:

- problem statement and glossary;
- official Anki scheduler-state versus Learn XP research-state boundary;
- identity candidate set;
- pending/confirmed minimum requirements;
- rewardable/non-rewardable boundary;
- anti-farming threat taxonomy;
- button, step, configuration, session, reset and duplicate-object invariants;
- privacy/claims boundary;
- G2.2 entry contract;
- versioning and three-state final G2 outcome boundary.

Official Anki semantics and peer-reviewed spacing/retrieval research are methodological inputs only. They do not determine exact confirmation delay, amount, ratio, mastery, motivation or retention claims.

### G2.2 — Learning lifecycle and anti-farming model

**Status:** Complete.

Artifacts:

- [human lifecycle model](../../docs/gamification/learn-xp-lifecycle-model.md);
- [machine lifecycle model](../../research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json);
- [lifecycle model schema](../../research/gamification-sim/schemas/learn-xp-lifecycle-model-v1.schema.json);
- [fixture schema](../../research/gamification-sim/schemas/learn-xp-lifecycle-fixture-v1.schema.json);
- [fixture manifest](../../research/gamification-sim/fixtures/learn-xp-lifecycle-v1/manifest.json);
- [G2.2 closeout](g2-learn-xp-lifecycle.md).

Frozen status:

```text
model status: FROZEN_PRE_CANDIDATE_DESIGN
states: 7
events: 20
transitions: 12
identity architecture: FACTORIZED
generic form: LearningEpisode<AchievementSubject>
subject candidates: CARD; NOTE; SIBLING_GROUP
subject winner: NONE
fixtures: 23
threat families: 6
protected invariants: 19
manifest digest: 4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
XP amount / pending ratio / numeric delay: NONE
candidate family / screening matrix: NONE
production approved: NO
```

Focused validation and the full research suite passed. The evaluator remains research-only and does not import Anki or production code.

### G2.3 — Candidate protocol and hypothesis design

**Status:** Complete.

Artifacts:

- [human candidate protocol](../../docs/gamification/learn-xp-candidate-protocol.md);
- [machine candidate protocol](../../research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json);
- [strict schema](../../research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json);
- [dry matrix generator](../../research/gamification-sim/src/gamification_sim/learn_candidate_protocol.py);
- [G2.3 closeout](g2-learn-xp-candidate-protocol.md).

Frozen status:

```text
protocol status: FROZEN_PRE_SCREENING_IMPLEMENTATION
protocol publication SHA: 41313c9369c76d331d489a9aa4b44da2497b3132
families / parameterizations: 2 / 4
subject strategies / delay policies: 2 / 2
candidates / reference variants: 8 / 2
hypotheses / hard gates / metrics: 5 / 23 / 14
expected units / unique IDs: 340 / 340
seed axis: ABSENT_DETERMINISTIC
full research suite: 982 passed
screening executed: NO
production approved: NO
```

G2.3 fixed lifecycle canonical serialization and direct-input typing without drift, then prospectively froze the candidate registry, allocation, delay, subject, gate, metric, survivor/tie, matrix and amendment boundaries.

### G2.4 — Bounded Learn XP screening

**Status:** Complete.

Artifacts: [technical reference](../../docs/gamification/learn-xp-bounded-screening.md), [closeout](g2-learn-xp-bounded-screening.md), [evidence schema](../../research/gamification-sim/schemas/learn-xp-bounded-screening-evidence-v1.schema.json).

The screened implementation is `548b27de6283b32fb27541db02ce6c8b65c29756`. The replacement run completed `340/340` unique units with `0/0/0` missing/extra/duplicates, 23 hard gates and 14 metrics per candidate, detached validation, deterministic replay and byte-identical external bundle reproduction. `F-CONFIRMATION-ONLY` retained `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING`; `F-PENDING-CONFIRMED-SPLIT` retained `C-PENDING-SPLIT-D1-NOTE-SIBLING`. The earlier attempt remains quarantined as `INVALID`; its disclosed packaging correction changed no screening-design field. No cross-family ranking, final Learn XP model, production approval or integration was performed.

### G2.5 — Confirmatory evidence

**Status:** In Progress — Frozen Pre-Results.

Artifacts:

- [human confirmatory protocol](../../docs/gamification/learn-xp-confirmatory-protocol.md);
- [machine confirmatory protocol](../../research/gamification-sim/contracts/learn-xp-confirmatory-protocol-v1.json);
- [protocol schema](../../research/gamification-sim/schemas/learn-xp-confirmatory-protocol-v1.schema.json);
- [evidence schema](../../research/gamification-sim/schemas/learn-xp-confirmatory-evidence-v1.schema.json);
- [confirmatory harness](../../research/gamification-sim/src/gamification_sim/learn_confirmatory.py);
- [focused tests](../../research/gamification-sim/tests/test_learn_confirmatory.py);
- [pre-results stage record](g2-learn-xp-confirmatory-evidence.md).

Frozen pre-results state:

```text
survivors / reference: 2 / 1
condition groups: 16 core / 12 identity / 8 explainability
replay identities: FORWARD / REVERSE
expected / unique units: 216 / 216
adaptive units: 0
identity evidence mode: SYNTHETIC_CONTRACT_ONLY
results accessed: NO
cross-family ranking: NO
final G2 decision stage: NOT STARTED
production integration: PROHIBITED
```

G2.5 checks each survivor separately. It does not rerun G2.4, add D2 or `S-CARD`, choose a family winner, select a final Learn XP model or approve production integration.

### Later G2 stages

Confirmatory evidence and final G2 decision may be defined only after G2.4 completes bounded screening under the published protocol. No additional stage numbering is created by G2.3.

Allowed final G2 outcomes are frozen as:

```text
RECOMMEND_LEARN_XP_RESEARCH_MODEL
REJECT_LEARN_XP_MODEL
DEFER_LEARN_XP_MODEL
```

Recommendation means research model, not production readiness.

## G3 — Create XP specification and simulation

**Status:** Planned after G2. Reward useful material state transitions without incentivizing low-quality card spam or repeated edits. Remote AI scoring and production integration remain out of scope.

## G4 — Cross-domain economy calibration

**Status:** Planned after G1–G3. Calibrate Review/Learn/Create conversion, level curve, productive-day scale, streak, Momentum, planned rest and recovery as one bounded research economy.

## G5 — Production architecture foundation

**Status:** Conditional after G4 and stable Core contracts. Design local-first event capture, ledger, persistence, migrations, reconciliation, privacy, versioning and explainability before UI.

## G6 — Gamification MVP

**Status:** Conditional after G5 and explicit owner approval. Local level/XP, streak with planned rest, Momentum, explanations/history and opt-out; no leaderboards, marketplace or mandatory accounts.

## G7 — Achievements foundation

**Status:** Conditional. Add minimal explainable achievements only after MVP evidence identifies a concrete feedback gap.

## G8 — Skills, quests and domain expansion

**Status:** Deferred / conditional. Add one named workflow/domain at a time; no generic life-tracking framework or speculative routes.

## Production boundary

No production add-on, dashboard, payload, API, migration, scheduler, FSRS, package, release or telemetry integration is approved. G2.1–G2.4 are complete research stages. G2.5 is active only as frozen pre-results confirmatory research; production integration and the final G2 decision stage have not started.
