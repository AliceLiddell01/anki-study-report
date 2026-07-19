# G1.2 — Root-cause attribution

## Status

`G1.2 — Complete`

`classification — ROOT_CAUSE_PARTIALLY_LOCALIZED`

`confidence — MEDIUM`

`G1.3 — Next / Ready`

`production integration — PROHIBITED`

G1.2 implements deterministic synthetic tracing and localizes the current
Review XP cycling mechanism class. It does not alter reward or scheduler
semantics, select a coefficient or candidate, or approve production use.

## Canonical and temporary refs

- canonical input: `f8374c58578d3a492dffa3e5b758e78b4049cdbf`;
- final canonical commit: this commit;
- development ref: `temp/g1-2-root-cause-attribution` (deleted after publication);
- execution ref: `temp/g1-2-root-cause-attribution-execution` (deleted after publication);
- `master` and `core`: outside write scope.

## Frozen blobs

- `research/gamification-sim/contracts/review-cycling-diagnostic-v1.json`: `8f5c3526cd1c98440ad513d9773f145c1971f995`;
- `research/gamification-sim/schemas/review-cycling-diagnostic-v1.schema.json`: `d64070f68e9b96f54dba4941b85fa7a770c8e8cf`;
- `research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json`: `6d08e6d701d6b57b5e24992223185764bc29e66e`;
- `research/gamification-sim/configs/review-longitudinal-v0.1.json`: `e8b30247b83f8d466cacaec93e9842f9ff23e257`;

All four frozen blobs were checked before and after execution and remain unchanged.

## Sources read

- `README.md`
- `docs/ai-handoff.md`
- `roadmap/README.md`
- `roadmap/gamification/README.md`
- `docs/test-matrix.md`
- `docs/verification-run-policy.md`
- `roadmap/gamification/g1-problem-gate-freeze.md`
- `roadmap/gamification/g1-contract-correction.md`
- `roadmap/gamification/g0-evidence-reproduction.md`
- `roadmap/gamification/g0-reconciliation-closure.md`
- `docs/gamification/review-xp-cycling-problem.md`
- `docs/gamification/README.md`
- `research/gamification-sim/README.md`
- `research/gamification-sim/evidence/README.md`
- `research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json`
- `research/gamification-sim/contracts/review-cycling-diagnostic-v1.json`
- `research/gamification-sim/schemas/review-cycling-diagnostic-v1.schema.json`
- `research/gamification-sim/src/gamification_sim/episode_reward.py`
- `research/gamification-sim/src/gamification_sim/day_aggregation.py`
- `research/gamification-sim/src/gamification_sim/longitudinal_runner.py`
- `research/gamification-sim/src/gamification_sim/longitudinal_models.py`
- `research/gamification-sim/src/gamification_sim/longitudinal_generator.py`
- `research/gamification-sim/src/gamification_sim/matched_analysis.py`
- `research/gamification-sim/src/gamification_sim/models.py`
- `research/gamification-sim/src/gamification_sim/parameters.py`
- `research/gamification-sim/src/gamification_sim/validation.py`
- `research/gamification-sim/src/gamification_sim/canonical_json.py`
- `research/gamification-sim/src/gamification_sim/output_digest.py`
- `research/gamification-sim/configs/review-longitudinal-v0.1.json`
- `research/gamification-sim/tests/test_episode_reward.py`
- `research/gamification-sim/tests/test_day_aggregation.py`
- `research/gamification-sim/tests/test_longitudinal_runner.py`
- `research/gamification-sim/tests/test_matched_analysis.py`
- `research/gamification-sim/tests/test_scenario_runner.py`

No applicable `AGENTS.md` / `agents.md` was present in the scoped tree.

## Implementation architecture

- `longitudinal_runner.py` exposes one optional observer boundary after runtime
  values are computed and before no decision is changed;
- `diagnostic_attribution.py` owns trace normalization, fixed-trajectory
  counterfactuals, reconciliation, deterministic serialization, safety scans
  and evidence generation;
- tracing-disabled payloads and digests remain identical;
- raw trace uses deterministic synthetic IDs only;
- committed evidence contains normalized aggregates and provenance, not bulk
  episode rows.

## Safe trace contract

Explicit trace grains:

- `aggregate_comparison`: 30;
- `day_window`: 13760;
- `horizon`: 6;
- `policy`: 72;
- `replica`: 11;
- `review_episode`: 9159;
- `run`: 6;
- `synthetic_card_lineage`: 236;

The artifact contains scheduler context, reward decomposition, day-level
components, fixed-trajectory `f(C,M)`, `f(C,0)`, `f(0,M)`, `f(0,0)`
counterfactuals and aggregate matched comparisons. Forbidden-data and path
scans passed.

## Execution environment

- platform: `Windows AMD64`;
- Python: `CPython 3.11.9 x64`;
- Rust declaration/toolchain boundary: `1.97.1-x86_64-pc-windows-msvc`;
- Python dependencies: exact SHA-256 lock replay, wheel-only, no dependency
  declaration or lock change.

## Raw artifact

- workflow run: `29705334586`;
- execution job: `88241257488`;
- artifact ID: `8447755442`;
- name: `g1-2-root-cause-attribution-f85e773eeb2f0fa1dfb0d13267c4ee34cf15e447`;
- digest: `sha256:f18f22d5adc9c5e2cca9314a874ca7de83c1182aa1580dcecda766d64b9a42e9`;
- manifest digest: `60011077cc4301ef479ffe8f268926d02deece592159c1bf2e1fc398f91fe8b4`;
- compressed size: `2250160` bytes;
- expiry: `2026-08-02T21:59:39Z`;
- independent manifest/hash/size/strict-JSON audit: PASS.

## Six-cell reconciliation

| Comparison | Replica | 90-day | 365-day | Delta | Endpoint | Grew |
|---|---:|---:|---:|---:|---|---|
| `intentional-backlog` | 0 | -0.00787729417763 | 0.000563232339029 | 0.00844052651666 | PASS | `true` |
| `intentional-backlog` | 1 | -0.000443460580491 | -0.0156749288563 | -0.0152314682758 | PASS | `false` |
| `retention-high-cycle` | 0 | -0.00377432857741 | 0.0174016940923 | 0.0211760226698 | PASS | `true` |
| `retention-high-cycle` | 1 | -0.0100445928504 | 0.00154388265864 | 0.011588475509 | PASS | `true` |
| `retention-low-cycle` | 0 | 0.0109805792973 | 0.0116238687291 | 0.00064328943173 | PASS | `true` |
| `retention-low-cycle` | 1 | 0.00401739661902 | 0.0136049656519 | 0.00958756903283 | PASS | `true` |

All six values and all three group outcomes exactly reconcile with immutable
G0.7 within absolute and relative tolerance `1e-9`; overall status remains
`FAIL`.

## Count-versus-reward decomposition

The frozen unexplained-advantage formula subtracts `baseline_delta`.
Review-count differences therefore remain visible as legitimate baseline
differences but have zero direct share in unexplained advantage. The residual
advantage is fully reconciled by contextual and day-level credits.

| Comparison | R | Reviews Δ90 | Reviews Δ365 | Baseline Δ90 | Baseline Δ365 |
|---|---:|---:|---:|---:|---:|
| `intentional-backlog` | 0 | -11 | -1 | -8.6 | -0.9 |
| `intentional-backlog` | 1 | -1 | -19 | -0.9 | -13.85 |
| `retention-high-cycle` | 0 | -13 | 40 | -12.35 | 32.1 |
| `retention-high-cycle` | 1 | -28 | -18 | -24.55 | -15.55 |
| `retention-low-cycle` | 0 | 8 | 15 | 7.2 | 12.2 |
| `retention-low-cycle` | 1 | 2 | 8 | 1.8 | 7.85 |

## Challenge, MemoryGain, interaction and day-level attribution

- dominant component: `memory_main` (0.0222607450742, 51.77% of absolute contributions);
- dominant timing window: `post_transition` (0.0431934835622, 94.53% of absolute contributions);
- maximum reconciliation residual: `1.43635103811e-15`.

| Comparison | R | Challenge | Memory | Interaction | Neutral | Support | Volume | Completion |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `intentional-backlog` | 0 | 0.00207649096328 | 0.00336853892753 | -5.85817487492e-19 | 0 | 0.000886989630721 | 0 | 0.00210850699513 |
| `intentional-backlog` | 1 | -0.00553183401112 | -0.00509774278908 | -3.59999588663e-19 | 0 | -0.00185290744384 | 0 | -0.00274898403177 |
| `retention-high-cycle` | 0 | 0.00322253486569 | 0.00959591491827 | -7.69869496923e-20 | 0 | 0.00116579900826 | 0 | 0.00719177387754 |
| `retention-high-cycle` | 1 | 0.00197057066505 | 0.00654743297145 | 1.22151465506e-19 | 0 | 0.000130890811984 | 0 | 0.00293958106054 |
| `retention-low-cycle` | 0 | -0.0023669402174 | 0.000725812059241 | 4.92254306309e-19 | 0 | 0.00110758133172 | 0 | 0.00117683625817 |
| `retention-low-cycle` | 1 | 0.00293715023361 | 0.00539158512523 | 1.44786818414e-19 | 0 | -0.000585750721726 | 0 | 0.00184458439572 |

## Transition timing and concentration

The largest aggregate retention-cycle contribution occurs in
`post_transition`. Replica-specific window values and top-20%
lineage concentration remain recorded in the machine evidence and raw artifact;
no averaging hides replica differences.

## Backlog and interval-neutral controls

Intentional backlog is analyzed separately from retention cycling and retains
its frozen PASS group outcome. A bounded development run traces
`stable-default` and `no-fsrs-neutral` as exploratory controls without adding
them to the canonical six cells.

## Root-cause answers

| # | Question ID | Answer |
|---:|---|---|
| 1 | `review_count_share` | Review-count differences produce baseline deltas, but the frozen unexplained-advantage formula subtracts baseline_delta exactly; their direct share of unexplained advantage is therefore zero. |
| 2 | `per_review_context` | All unexplained advantage is reconciled by contextual and day-level credits after baseline removal. |
| 3 | `component_distribution` | The dominant cross-horizon component is memory_main. |
| 4 | `divergence_timing` | The dominant timing window is post_transition. |
| 5 | `shared_mechanism` | High- and low-retention cycling are compared through the same decomposition; consistency is reported per group rather than assumed. |
| 6 | `replica_difference` | Replica-specific deltas remain visible and are not averaged away. |
| 7 | `lineage_concentration` | Positive contextual contribution concentration is measured as the top 20% lineage share. |
| 8 | `actual_vs_natural_due` | Challenge attribution explicitly separates actual and natural-due retrievability through adjusted challenge and delay credit. |
| 9 | `memory_gain_counterfactual` | MemoryGain is isolated with fixed-trajectory f(0,M)-f(0,0) main effects. |
| 10 | `endpoint_cancellation` | Cells with negative 90-day advantage and positive 365-day advantage are explicitly identified. |
| 11 | `interval_neutral_control` | A bounded development control traces stable-default and no-fsrs-neutral without changing canonical cells. |
| 12 | `cap_suppression` | Cap/blend nonlinearity is isolated in interaction; baseline suppression remains zero. |
| 13 | `intentional_backlog` | Intentional backlog remains separately reported and is not generalized from the retention-cycle mechanism. |
| 14 | `mechanism_class` | The mechanism class is localized only to the level supported by the deterministic decomposition; no coefficient or candidate is selected. |

## Classification

`ROOT_CAUSE_PARTIALLY_LOCALIZED` with `MEDIUM` confidence.

The fixed-trajectory decomposition fully reconciles the observed cross-horizon growth and identifies the dominant component and timing window without selecting a coefficient or candidate.

This is an exploratory mechanism classification, not a new decision gate.

## Tests and checks

- focused: `python -m pytest research/gamification-sim/tests/test_diagnostic_attribution.py research/gamification-sim/tests/test_episode_reward.py research/gamification-sim/tests/test_day_aggregation.py research/gamification-sim/tests/test_longitudinal_runner.py research/gamification-sim/tests/test_matched_analysis.py` — 110 passed;
- full package: `python -m pytest research/gamification-sim/tests` — 839 passed;
- same-seed 90/365 replay: byte-identical normalized trees and trace digests;
- secondary seed: different trajectory with schema/reconciliation PASS;
- schema self-check and evidence validation: PASS;
- artifact independent audit: PASS;
- frozen blob audit: PASS;
- exact seven-path cumulative diff and `git diff --check`: PASS;
- relative links and canonical workflow-path audit: PASS.

## Files changed

- `research/gamification-sim/src/gamification_sim/diagnostic_attribution.py`
- `research/gamification-sim/src/gamification_sim/longitudinal_runner.py`
- `research/gamification-sim/tests/test_diagnostic_attribution.py`
- `research/gamification-sim/schemas/review-cycling-attribution-v1.schema.json`
- `research/gamification-sim/evidence/g1.2-root-cause-attribution-v1.json`
- `roadmap/gamification/g1-root-cause-attribution.md`
- `roadmap/gamification/README.md`

No production, dashboard, API, package, release, CI workflow, config, frozen
contract/schema or G0.7 evidence path changed.

## What was not run

- Docker E2E;
- real-Anki E2E;
- dashboard/frontend tests;
- add-on package build;
- release workflow;
- full G0.7 sweep/sensitivity/population repetition;
- Rust build/tests, because Rust semantics and source were unchanged.

## Git publication and cleanup

- final result is a direct descendant of the canonical input;
- publication uses ordinary non-force fast-forward;
- no merge commit, rebase, force-push or PR to `master`;
- temporary G1.2 refs are deleted after remote SHA verification;
- the successful workflow run and its canonical raw artifact are preserved;
- canonical G0.7 runs and artifact remain preserved.

## Limitations

- Synthetic trajectories do not establish human learning effectiveness or real-user reward gaming.
- Counterfactuals are reward-only post-hoc evaluations on fixed scheduler trajectories.
- This stage localizes mechanism classes and does not select coefficients or candidates.

## Next step

`G1.3 — Candidate hypothesis design` may begin from this localized mechanism
class. It must prospectively define bounded hypotheses before viewing candidate
decision evidence. G1.3 was not started here.

Candidate selected: **NO**. Production approval: **NO**.
