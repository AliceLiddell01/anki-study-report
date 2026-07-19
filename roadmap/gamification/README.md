# Gamification track

**Track:** `G`
**Role:** parallel research/product direction
**Current status:** `G0` is Complete; `G1` is Next; production integration is not approved

Gamification does not block `C1` Cards v2 or `C2` Core 1.0. Research code, fixtures and generated evidence do not enter the add-on package, Fast CI or release workflows without an explicit later decision.

## Branch policy

- `gamification` is the canonical, independent, long-lived Gamification branch created from an explicitly recorded current `master` baseline.
- `master → gamification` is allowed for branch creation and later compatibility checkpoints. `gamification → master` is prohibited until a separate explicit decision by the project owner.
- `chatgpt/gamification-concept-foundation` is a read-only historical source. It must not be merged or rebased into the canonical branch.
- G0 does not create a Pull Request from `gamification` to `master`.
- G0.1 establishes only the branch and its baseline documentation: it imports no research assets, Core changes or production changes.
- Compatibility with later `master` and Core state is evaluated in subsequent G0 checkpoints, beginning with G0.2; it is not assumed by branch creation.
- Any production integration requires a separate explicit decision by the project owner.

## G0 checkpoints

- `G0.1 — Canonical branch baseline`: Complete — [`g0-branch-baseline.md`](g0-branch-baseline.md)
- `G0.2 — Core compatibility snapshot`: Complete — [`g0-core-compatibility.md`](g0-core-compatibility.md)
- `G0.3 — Historical asset inventory`: Complete — [`g0-historical-asset-inventory.md`](g0-historical-asset-inventory.md), [`g0-historical-asset-manifest.md`](g0-historical-asset-manifest.md)
- `G0.4 — Selective research recovery`: Complete — [`g0-selective-research-recovery.md`](g0-selective-research-recovery.md), [`g0-recovery-ledger.md`](g0-recovery-ledger.md)
- `G0.5 — Reproducible environment`: Complete — [`g0-reproducible-environment.md`](g0-reproducible-environment.md)
- `G0.6 — Functional baseline verification`: Complete — [`g0-functional-baseline.md`](g0-functional-baseline.md), corrective audit: [`g0-installed-execution-boundary-correction.md`](g0-installed-execution-boundary-correction.md)
- `G0.7 — Evidence reproduction`: Complete — [`g0-evidence-reproduction.md`](g0-evidence-reproduction.md), closure: [`g0-reconciliation-closure.md`](g0-reconciliation-closure.md)

G0.2 confirmed `core` as the active Core line on the same recorded `master`
baseline. It is six commits ahead with C1.0–C1.2 work, but has no same-path
conflict with the G0 documentation and creates no blocker for G0.3. No Core
import is required; stable Core changes should normally reach Gamification
through `master`, while C1/C2 contracts remain a watch item for later G3, G5
and G6 work.

G0.3 identified **128** tracked historical assets: 10 under
`docs/gamification/` and 118 under `research/gamification-sim/`. The exhaustive
manifest uses `IMPORT_AS_IS`, `IMPORT_WITH_ADAPTATION`, `REWRITE`,
`ARCHIVE_SUPERSEDED` and `DEFER`; no completeness issue remains and no asset was
imported. G0.4 must transfer only approved manifest rows in the recorded batch
order.

G0.4 recovered **127** historical-derived targets and deferred one global
progression foundation to G4. Exact imports retain frozen Git blob identity;
approved adaptations add provenance/status prefixes without changing historical
bodies or reward semantics. The package remains `RECOVERED_UNVERIFIED`: tests,
oracles, simulations and evidence were not executed, and production integration
remains prohibited.

G0.5 established one canonical Windows AMD64 / CPython 3.11.9
environment with an exact SHA-256 Python lock, clean offline wheelhouse replay,
regular local package installation, `pip check`, exact stable Rust 1.97.1
on `x86_64-pc-windows-msvc`, and locked online/offline Cargo metadata replay. Python and
Cargo declarations remained unchanged. Functional tests, simulations, oracle
execution and evidence reproduction remain pending; production integration is
still prohibited.

G0.6a corrected the regular installed-package execution boundary discovered by
the first G0.6 pytest collection. A central validated research workspace owns
schemas, fixtures, scenarios, personas, configs, contracts and the Rust oracle;
generated artifacts default outside the source tree; Cargo uses the tracked
exact MSVC toolchain with locked/offline execution.

G0.6 then reran the complete checkpoint sequence on the corrective commit. The
regular installed package and CLI, full recovered Python suite, deterministic
corpus, exact-toolchain Rust check/build/tests, every recovered parameter
candidate against the Rust oracle, and the FSRS reference contract passed.
Source, tests, fixtures, schemas, declarations and `Cargo.lock` remained
unchanged.

G0.7 reproduced the canonical corrected sweep, sensitivity, bounded population
and persistent-card 30/90/365-day evidence twice on Windows AMD64. The raw
artifact passed independent verification; historical and Linux supporting
claims were reconciled. The retention-cycling growth gap remains open for G1,
no candidate is recommended and production integration remains prohibited.

## Source audit

The source branch is `chatgpt/gamification-concept-foundation`. At the 2026-07-18 G0.1 check it diverged from current `master`: 48 commits ahead, 132 behind, merge base `4d197c1037fd66401735e654c6697791364518a4`.

The branch is a substantial research source, not a merge-ready production feature branch:

- Progression and Anki XP foundations are `DRAFT v0.2`;
- Review taxonomy, reward, abuse and day aggregation are developed drafts;
- Stage 5A and multiple simulator sub-stages are documented as complete;
- Stage 5B.C and overall Review simulation remain `PARTIAL`;
- cross-horizon retention-cycling evidence is the open blocker;
- Learn XP and Create XP are not started;
- global XP conversion and production ledger/API/migrations/UI are not designed.

Direct spot-checks confirmed that simulator implementation and tests are populated. For example, the scenario runner is implemented, and its tests assert 26 scenarios and 53 assertions. Those checks establish that the files exist; they do not substitute for executing the full branch test/simulation commands on a current master-based branch.

Do not merge or rebase the historical branch wholesale. Later G0 work on the canonical branch must selectively reconcile current assets with `master`, rerun the documented checks and separate reproducible current evidence from superseded reports.

## Evidence baseline

External research supports a cautious, theory-informed direction rather than a promise that points always improve learning:

- Self-Determination Theory interventions support autonomy and competence and can improve intrinsic motivation;
- gamification effects are design- and audience-dependent;
- personalized approaches can outperform one-size-fits-all designs;
- points, badges, competition and leaderboards can also produce motivational or performance harms;
- short interventions are overrepresented, while long-term effects require longitudinal and matched-control evidence.

Design consequences:

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

**Status:** Complete — G0.1–G0.7 Complete; G1 Next

### Goal

Use the canonical `gamification` branch created from a recorded current `master` baseline, selectively recover valid research assets and establish one truthful, reproducible research baseline without integrating Gamification into `master`.

### Dependencies

Read access to the historical branch. No dependency on the core track. Core compatibility is recorded separately beginning with G0.2.

### Scope

- establish and record the canonical branch baseline before importing research assets;
- inventory documents, contracts, source, scenarios, schemas, tests and evidence;
- resolve drift against current repository structure and policies;
- rerun and record actual test/scenario/oracle counts;
- distinguish current results from superseded reports;
- preserve research package isolation;
- decide which assets are imported, rewritten, archived or discarded;
- record later compatibility checkpoints against `master` and Core without merging Gamification into `master`.

### Out of scope

- production add-on integration;
- a Pull Request from `gamification` to `master`;
- importing research assets, Core changes or production changes during G0.1;
- changing XP formulas merely to make checks pass;
- merging or rebasing the historical branch wholesale;
- Fast CI or package inclusion.

### Activation criteria

Already met: the historical branch is materially diverged from `master` and must be reconciled before further authoritative research work.

### Completion criteria

The canonical master-based `gamification` branch contains a self-consistent research package and docs; actual checks are reproducible; superseded evidence is marked; no production/runtime/workflow files change; no Pull Request to `master` is created; production integration remains prohibited without a separate explicit owner decision.

## G1 — Close Review XP cross-horizon cycling gap
**Status:** Next

### Goal

Resolve the observed 90→365-day retention-cycling advantage without sacrificing honest baseline reward, session invariance or return-from-backlog behavior.

### Dependencies

G0 executable baseline; persistent matched-card longitudinal simulator; versioned candidate/evidence contracts.

### Scope

Defensible candidate hypotheses, matched 90/365-day and sensitivity runs, hard gates before Pareto ranking, and an explicit reject/defer decision when evidence remains insufficient.

### Out of scope

Production economy, Learn/Create XP and changes to Anki scheduling.

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

A versioned specification and reproducible simulator evidence exist; candidate values remain research-only.

## G3 — Create XP specification and simulation

**Status:** Planned after G2

### Goal

Reward useful material state transitions without incentivizing low-quality card spam or repeated edits.

### Dependencies

G2 methodology; clear Cards/Search/action provenance boundaries.

### Scope

Creation/readiness/fix events, delayed confirmation, lifetime reward state, quality and abuse controls, scenarios and simulation.

### Out of scope

Remote AI content scoring, arbitrary surveillance and production integration.

### Activation criteria

A concrete and auditable notion of useful creation/fix work exists.

### Completion criteria

A versioned specification and evidence demonstrate bounded reward and resistance to duplicate/reset/import farming.

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

Default accounts, remote telemetry of learning history, competitive features and UI expansion.

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

### Goal

Add durable milestones only when they improve feedback without dominating intrinsic motivation.

### Dependencies

G6 evidence and opt-out/settings contracts.

### Scope

A minimal achievement taxonomy, versioning, explainability and retroactive reconciliation.

### Out of scope

Competitive rankings, loot economies and mandatory engagement loops.

### Activation criteria

Measured MVP usage identifies a concrete feedback gap that achievements solve.

### Completion criteria

Achievement rules are bounded, explainable, optional and tested against retroactive/import/reset behavior.

## G8 — Skills, quests and domain expansion

**Status:** Deferred / conditional

### Goal

Extend progression only to a validated non-Anki domain or a specific quest/skill workflow.

### Dependencies

G6 stable; a domain-specific evidence model and product owner exist.

### Scope

One named domain/workflow at a time with its own event taxonomy, calibration and privacy model.

### Out of scope

A generic life-tracking framework, universal XP conversion and speculative routes/settings.

### Activation criteria

A concrete non-Anki workflow has evidence, maintenance ownership and a reason to share progression.

### Completion criteria

The new domain preserves local-first/privacy boundaries, has reproducible calibration and does not distort the Anki economy.
