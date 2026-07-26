# Gamification track

**Track:** `G`
**Role:** parallel research/product direction
**Current status:** `G0 Complete`; `G1 Complete` with `DEFER_REVIEW_MODEL`; `G2 In Progress`; `G2.1 Complete`; `G2.2 Next / Not Started`; production integration not approved

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

**Status:** `NEXT / NOT STARTED`.

Entry contract requires G2.2 to:

```text
build a typed lifecycle
separate scheduler state from reward state
define pending/confirmed/expired/cancelled/invalidated transitions
formalize all identity candidates
create deterministic event traces
create fixtures for all six threat families
define observable and missing/ambiguous-data behavior
avoid XP amounts and screening
avoid production code changes
```

G2.2 requires a separate task. G2.1 did not start it.

### Later G2 stages

Prospective candidate design, bounded screening, confirmatory evidence and final G2 decision may be defined only after G2.2 establishes the lifecycle/threat model. No additional stage numbering is created by G2.1.

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

No production add-on, dashboard, payload, API, migration, scheduler, FSRS, package, release or telemetry integration is approved. G2.1 is a docs/contracts/schema-only research freeze. G2.2 is not started.
