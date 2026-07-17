# Gamification track

**Track:** `G`  
**Role:** parallel research/product direction  
**Current status:** `G0` is Next; production integration is not approved

Gamification does not block `C1` Cards v2 or `C2` Core 1.0. Research code, fixtures and generated evidence do not enter the add-on package, Fast CI or release workflows without an explicit later decision.

## Source audit

The source branch is `chatgpt/gamification-concept-foundation`. At the 2026-07-18 audit it diverged from current `master`: 48 commits ahead, 99 behind, merge base `4d197c1037fd66401735e654c6697791364518a4`.

The branch is a research source, not a merge-ready feature branch:

- concept documents describe `Level`, `Streak` and `Momentum` as separate axes;
- Progression and Anki XP foundations are `DRAFT v0.2`;
- Review taxonomy, reward, abuse and day aggregation are conceptually developed drafts;
- Stage 5A and several simulator sub-stages are documented as complete;
- Stage 5B.C and overall Review simulation remain `PARTIAL`;
- cross-horizon retention-cycling evidence is the open blocker;
- Learn XP and Create XP are not started;
- global XP conversion and production ledger/API/migrations/UI are not designed;
- the branch diff contains zero-length simulator modules and zero-length test files, so implementation claims must be reconciled against actual content before any import.

Do not merge or rebase the branch wholesale. A later research PR may selectively import current documents/code after auditing them against `master`.

## Evidence baseline

External research supports a cautious, theory-informed direction rather than a promise that points always improve learning:

- Self-Determination Theory interventions support autonomy and competence and can improve intrinsic motivation;
- gamification effects are design- and audience-dependent;
- personalized approaches can outperform one-size-fits-all designs;
- points, badges, competition and leaderboards can also produce motivational or performance harms;
- short interventions are overrepresented, while long-term effects require longitudinal and matched-control evidence.

Design consequences for this track:

- preserve autonomy, competence and relatedness;
- provide settings and opt-out before production activation;
- treat leaderboards/competition as conditional, never default requirements;
- separate engagement metrics from learning outcomes;
- measure novelty decay and long-horizon behavior;
- prefer explainable progress and constructive feedback over escalating extrinsic rewards.

Evidence references:

- https://doi.org/10.1016/j.lmot.2024.102015
- https://doi.org/10.1007/s11423-023-10337-7
- https://doi.org/10.1016/j.lindif.2024.102470
- https://doi.org/10.1111/jcal.13077
- https://doi.org/10.1016/j.infsof.2022.107142
- https://doi.org/10.3390/educsci11010032

## Sequence

```text
G0 Reconcile research branch with current master
→ G1 Close Review XP cycling evidence gap
→ G2 Learn XP specification and simulation
→ G3 Create XP specification and simulation
→ G4 Cross-domain economy calibration
→ G5 Production architecture foundation
→ G6 Gamification MVP
→ G7 Achievements foundation (conditional)
→ G8 Skills/quests/domain expansion (conditional)
```

## G0 — Research reconciliation

**Status:** Next

### Goal

Create a new branch from current `master`, selectively recover valid research assets and establish one truthful, executable research baseline.

### Dependencies

None on the core track. Requires read access to the old branch.

### Scope

- inventory branch documents, contracts, source, scenarios, schemas, tests and generated evidence;
- resolve zero-length or missing implementation/test files;
- distinguish current evidence from superseded reports;
- preserve research package isolation;
- decide which assets are imported, rewritten, archived or discarded;
- document reproducible commands and actual passing test/scenario counts.

### Out of scope

- production add-on integration;
- changing XP formulas merely to make tests pass;
- merging the historical branch wholesale;
- Fast CI or package inclusion.

### Activation criteria

Already met: the branch is materially diverged and internally inconsistent.

### Completion criteria

A master-based research branch/PR contains a self-consistent package and docs, actual checks are reproducible, superseded evidence is marked, and no production/runtime/workflow files change.

## G1 — Close Review XP cross-horizon cycling gap

**Status:** Blocked by G0

### Goal

Resolve the observed 90→365-day retention-cycling advantage without sacrificing honest baseline reward, session invariance or return-from-backlog behavior.

### Dependencies

- G0 executable baseline;
- persistent matched-card longitudinal simulator;
- versioned candidate/evidence contracts.

### Scope

- defensible candidate hypotheses;
- matched 90/365-day and sensitivity runs;
- hard gates before Pareto ranking;
- explicit rejection/defer decision when evidence remains insufficient.

### Out of scope

- declaring a production economy;
- Learn/Create XP;
- changing Anki scheduling.

### Activation criteria

G0 closes with trustworthy longitudinal tooling.

### Completion criteria

The cycling growth gate passes under documented tolerances or the Review model is explicitly rejected/deferred. A recommended research candidate is not called production-ready.

## G2 — Learn XP specification and simulation

**Status:** Planned after G1

### Goal

Define initial-learning units, pending/confirmed rewards and anti-farming behavior independently from Review XP.

### Dependencies

G1 complete; shared evidence methodology stable.

### Scope

Event taxonomy, state transitions, delayed confirmation, Undo/import/sync semantics, scenarios, simulation and fairness/abuse gates.

### Out of scope

Production ledger/UI and a universal Review/Learn formula.

### Activation criteria

Review evidence no longer blocks cross-domain calibration.

### Completion criteria

Versioned specification and reproducible simulator evidence exist; candidate values remain research-only.

## G3 — Create XP specification and simulation

**Status:** Planned after G2

### Goal

Reward useful material state transitions without incentivizing low-quality card spam or repeated edits.

### Dependencies

G2 methodology; clear Cards/Search/action provenance boundaries.

### Scope

Creation/readiness/fix events, delayed confirmation, lifetime reward state, quality and abuse controls, scenarios and simulation.

### Out of scope

Content scoring by remote AI, arbitrary surveillance or production integration.

### Activation criteria

A concrete and auditable notion of useful creation/fix work exists.

### Completion criteria

Versioned specification and evidence demonstrate bounded reward and resistance to duplicate/reset/import farming.

## G4 — Cross-domain economy calibration

**Status:** Planned after G1–G3

### Goal

Calibrate Review/Learn/Create conversion, level curve, productive-day scale, streak, Momentum, planned rest, Streak Guard and recovery behavior as one economy.

### Dependencies

Research candidates for all three Anki XP domains.

### Scope

Long-horizon synthetic populations, matched controls, sensitivity, individual-difference analysis, novelty-decay measurement plan and explicit opt-out requirements.

### Out of scope

Production storage/API/UI.

### Activation criteria

No domain is represented by placeholder values.

### Completion criteria

A versioned economy candidate passes fairness, abuse, workload and long-horizon gates; unresolved uncertainty remains visible.

## G5 — Production architecture foundation

**Status:** Conditional after G4

### Goal

Design a local-first, explainable and reconcilable production system before any gamification UI.

### Dependencies

G4 accepted research candidate; C2 core contracts sufficiently stable.

### Scope

Event capture, immutable/reconcilable reward ledger, per-profile persistence, migrations, Undo/sync/import/late-history reconciliation, privacy separation, versioning and explainability.

### Out of scope

Accounts by default, remote telemetry of learning history, competitive features and UI expansion.

### Activation criteria

The economy is stable enough that schema/versioning work will not immediately be invalidated.

### Completion criteria

Threat model, data model, migrations, reconciliation rules, API boundaries and verification plan are approved independently of UI.

## G6 — Gamification MVP

**Status:** Conditional after G5

### Goal

Deliver local level/XP, streak with planned rest, Momentum, explanations/history and settings/opt-out.

### Dependencies

G5 complete; required core contracts stable.

### Scope

Local-first MVP, accessible RU/EN UI, transparent reward breakdown and full disable/reset/export behavior.

### Out of scope

Leaderboards, social competition, marketplace, skills, quests and mandatory accounts.

### Activation criteria

Architecture and research gates are complete, and the owner explicitly approves product implementation.

### Completion criteria

MVP passes migrations/reconciliation, long-horizon economy, accessibility, privacy and real-Anki verification without sending study events to telemetry.

## G7 — Achievements foundation

**Status:** Conditional

Activation requires evidence that achievements add meaningful feedback without dominating intrinsic motivation. They are not required for G6 or core maturity.

## G8 — Skills, quests and domain expansion

**Status:** Deferred / conditional

Activation requires a validated non-Anki domain, a concrete user workflow and a new domain-specific evidence model. No generic life-tracking framework is prebuilt.
