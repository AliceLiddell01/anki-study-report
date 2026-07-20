# Gamification track

**Track:** `G`
**Role:** parallel research/product direction
**Current status:** `G0 Complete`; `G1 In Progress`; `G1.3 Complete`; G1.4 protocol `Ready`; G1.4 execution `Blocked on implementation`; production integration not approved

Gamification does not block `C1` Cards v2 or `C2` Core 1.0. Research code, fixtures and evidence do not enter the add-on package, Fast CI or release workflows without a later explicit decision.

## Branch and production policy

- `gamification` is the canonical independent branch.
- `gamification → master` is prohibited until a separate owner decision.
- `chatgpt/gamification-concept-foundation` is historical read-only source and must not be merged/rebased wholesale.
- Any production integration requires a separate explicit decision.

## G0 — Research reconciliation

**Status:** Complete.

- `G0.1` Canonical branch baseline — [report](g0-branch-baseline.md)
- `G0.2` Core compatibility — [report](g0-core-compatibility.md)
- `G0.3` Historical inventory — [report](g0-historical-asset-inventory.md), [manifest](g0-historical-asset-manifest.md)
- `G0.4` Selective recovery — [report](g0-selective-research-recovery.md), [ledger](g0-recovery-ledger.md)
- `G0.5` Reproducible environment — [report](g0-reproducible-environment.md)
- `G0.6` Functional baseline — [report](g0-functional-baseline.md), [correction](g0-installed-execution-boundary-correction.md)
- `G0.7` Evidence reproduction — [report](g0-evidence-reproduction.md), [closure](g0-reconciliation-closure.md)

G0 reproduced the current synthetic baseline without production integration. The cross-horizon cycling gap passed to G1.

## G1 — Close Review XP cross-horizon cycling gap

**Status:** In Progress.

### Current decomposition

- `G1.1 — Freeze problem and diagnostic contract`: Complete — [report](g1-problem-gate-freeze.md)
  - corrective checkpoint: Complete — [report](g1-contract-correction.md)
- `G1.2 — Root-cause attribution`: Complete — [report](g1-root-cause-attribution.md)
  - `G1.2a — Attribution contract and evidence correction`: nested corrective checkpoint, Complete — [report](g1-root-cause-attribution-correction.md)
- `G1.3 — Candidate protocol and hypothesis design`: Complete — [report](g1-candidate-protocol.md)
- `G1.4 — Bounded screening`: Next; protocol readiness `READY`; execution readiness `BLOCKED_ON_IMPLEMENTATION`
- `G1.5 — Confirmatory 90/365, robustness and safety evidence`: Planned after G1.4
- `G1.6 — Candidate decision and G1 closure`: Planned after G1.5

The duplicated top-level G1.2a row is removed: G1.2a is a correction nested under G1.2.

### G1.2a scientific state

```text
classification: ROOT_CAUSE_PARTIALLY_LOCALIZED
confidence: MEDIUM
memory_main share: 0.4552230855238075
post_transition share: 0.8565121323195105
Challenge direction-consistent: false
candidate selected: false
reward formula changed: false
scheduler semantics changed: false
production approved: false
```

Review-count delta is removed by baseline subtraction. The attribution is synthetic and post-hoc; it does not prove one unique corrective formula.

### G1.3 frozen protocol

- [Human protocol](../../docs/gamification/review-xp-candidate-protocol.md)
- [Machine protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json)
- [Strict schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json)

G1.3 freezes two post-transition MemoryGain families, four predefined parameterizations, four explicit policy pairs, horizons 90/365, two replicas, primary/secondary seeds and a 160-unit budget. Hard gates are non-compensable. No screening was run and no candidate was selected.

The protocol is ready. Execution is blocked because the current simulator has no window-conditioned reward hook or registered candidate parameterizations. G1.4 must first implement the frozen mechanism without changing protocol semantics.

### G1 goal and closure boundary

Resolve the cycling growth gate under frozen tolerances or explicitly reject/defer the Review model. A recommended research candidate is never called production-ready. Allowed final outcomes are exactly:

```text
RECOMMEND_RESEARCH_CANDIDATE
REJECT_REVIEW_MODEL
DEFER_REVIEW_MODEL
```

## Later stages

### G2 — Learn XP specification and simulation

**Status:** Planned after G1. Define initial-learning units, pending/confirmed rewards and anti-farming behavior independently from Review XP. Production ledger/UI remain out of scope.

### G3 — Create XP specification and simulation

**Status:** Planned after G2. Reward useful material state transitions without incentivizing low-quality card spam or repeated edits. Remote AI scoring and production integration remain out of scope.

### G4 — Cross-domain economy calibration

**Status:** Planned after G1–G3. Calibrate Review/Learn/Create conversion, level curve, productive-day scale, streak, Momentum, planned rest and recovery as one bounded research economy.

### G5 — Production architecture foundation

**Status:** Conditional after G4 and stable Core contracts. Design local-first event capture, ledger, persistence, migrations, reconciliation, privacy, versioning and explainability before UI.

### G6 — Gamification MVP

**Status:** Conditional after G5 and explicit owner approval. Local level/XP, streak with planned rest, Momentum, explanations/history and opt-out; no leaderboards, marketplace or mandatory accounts.

### G7 — Achievements foundation

**Status:** Conditional. Add minimal explainable achievements only after MVP evidence identifies a concrete feedback gap.

### G8 — Skills, quests and domain expansion

**Status:** Deferred / conditional. Add one named workflow/domain at a time; no generic life-tracking framework or speculative routes.

## Production boundary

No production add-on, dashboard, payload, API, migration, package, release or telemetry integration is approved. `G1.4` is the only next Gamification stage, and it has not started in G1.3.
