# G1.1 — Review XP cycling problem and gate freeze

## Status

`G1.1 — Complete`

`G1 — In Progress`

`G1.2 — Next`

`production integration — PROHIBITED`

## Recorded refs

- canonical branch: `gamification`;
- G1.1 input/publication baseline: `cece52120b04e75d8ec937c56c9575283ec479c5`;
- G0.7 executable evidence source: `9716b3f98bc4a975031a078f42e38a7d8fb109a6`;
- evidence record blob: `6d08e6d701d6b57b5e24992223185764bc29e66e`;
- longitudinal config blob: `e8b30247b83f8d466cacaec93e9842f9ff23e257`.

The final G1.1 commit is the direct descendant of the recorded canonical input.
No `master` or `core` change and no Pull Request are part of this stage.

## Scope

G1.1 freezes the observed Review XP cycling problem, current metric and gate
semantics, protected invariants, G1.2 attribution requirements, analysis
classification, candidate mutation boundary, decision outcomes and versioning.
It creates no candidate and performs no new simulator execution.

## Sources read

- `README.md`
- `docs/ai-handoff.md`
- `roadmap/README.md`
- `roadmap/gamification/README.md`
- `roadmap/gamification/g0-evidence-reproduction.md`
- `roadmap/gamification/g0-reconciliation-closure.md`
- `docs/gamification/README.md`
- `docs/gamification/anki-review-event-taxonomy.md`
- `docs/gamification/anki-review-reward-model.md`
- `docs/gamification/anki-review-abuse-model.md`
- `docs/gamification/anki-review-session-and-day.md`
- `docs/gamification/anki-review-simulation-spec.md`
- `research/gamification-sim/README.md`
- `research/gamification-sim/evidence/README.md`
- `research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json`
- `research/gamification-sim/configs/review-longitudinal-v0.1.json`
- `research/gamification-sim/src/gamification_sim/matched_analysis.py`
- `research/gamification-sim/src/gamification_sim/longitudinal_runner.py`
- `research/gamification-sim/src/gamification_sim/episode_reward.py`
- `research/gamification-sim/src/gamification_sim/validation.py`
- `research/gamification-sim/src/gamification_sim/canonical_json.py`
- `research/gamification-sim/src/gamification_sim/output_digest.py`
- `research/gamification-sim/src/gamification_sim/reporting.py`
- `research/gamification-sim/tests/test_matched_analysis.py`
- `research/gamification-sim/tests/test_longitudinal_runner.py`
- `research/gamification-sim/tests/test_episode_reward.py`
- `research/gamification-sim/tests/test_day_aggregation.py`
- `research/gamification-sim/tests/test_scenario_runner.py`
- `research/gamification-sim/schemas/review-scenario-v0.2.schema.json`
- `docs/verification-run-policy.md`
- `docs/test-matrix.md`

`AGENTS.md` and `agents.md` were checked and were not present.

## External methodology

Primary/official references reviewed:

- OSF official registration guidance for time-stamped read-only plans and
  confirmatory/exploratory separation;
- Ng, Harada and Russell for the limited policy-invariance warning under formal
  MDP assumptions;
- Google DeepMind specification-gaming examples for proxy-objective analogy;
- Skalse et al. for reward-hacking vocabulary;
- official Git worktree documentation for isolated checkout practice.

The resulting document is described as an **internal pre-analysis protocol for
G1 diagnostics**, not an external preregistration.

These reward-hacking and policy-invariance references are methodological
analogies. They do not model human motivation or prove that Anki users will
optimize the system in the same way as an RL agent.

## Canonical reproduced defect

Under `R-CURRENT`, both retention-cycle pairs have 90→365 unexplained-advantage
growth in both matched replicas. Every 365-day cell remains below the current
one-sided 3% cap. Intentional backlog has one growing and one non-growing replica
and therefore does not show the same observed two-replica pattern.

This stage records that evidence without changing the immutable G0.7 record.

## Policy pairs

- `temporary-high-cycle` versus `stable-high`;
- `temporary-low-cycle` versus `stable-low`;
- `intentional-backlog` versus `timely-control`;
- `honest-backlog-return` versus `timely-control` remains a protected fairness
  comparison.

Config timelines, delay interval `[30, 45)`, review limit `1000`, mode sizes and
replicas are copied exactly into the machine contract and checked against the
current config.

## Metric semantics

The contract freezes:

```text
baseline_delta = left.core_baseline - right.core_baseline
total_delta = left.total_review_units - right.total_review_units
unexplained_units = total_delta - baseline_delta
unexplained_advantage =
    0 when right.total_review_units == 0
    otherwise unexplained_units / right.total_review_units
delta = advantage_365 - advantage_90
```

Numbers in the contract are fractions. Human documentation may render them as
percentages.

## Frozen tolerances

- validation close tolerance: absolute `1e-9`, relative `1e-9`;
- 365-day endpoint: `unexplained_advantage <= 0.03 + 1e-9`;
- replica growth: `delta > 1e-9`;
- baseline suppression comparison: episode baseline plus `1e-9`;
- suppression event count: exactly zero.

The endpoint cap is the current source's one-sided upper bound, not an
absolute-value bound.

## Hard gates

Technical completeness requires exact horizons, policy pairs, replicas, finite
numbers, matched inputs/cohorts/latent streams, deterministic replay where
required, and complete G1.2 attribution.

Research gates freeze endpoint cap, retention-group cross-horizon growth,
current intentional-backlog semantics, baseline preservation, zero suppression,
session invariance, direct button neutrality and candidate evidence
completeness.

The current implementation applies `systematic_growth` only to comparison IDs
beginning with `retention-`. A stronger intentional-backlog growth rule is
therefore marked `PARTIAL`, not misrepresented as an existing automated gate.

## Protected invariants

Twelve non-negotiable invariants are recorded in the human specification and
machine contract, including honest `Again` credit, successful-button neutrality,
ordinary/no-FSRS baseline, backlog fairness, session invariance, non-positive
response validity, decomposable output, research-only status and the rule that
cycling PASS alone is not production readiness.

Each invariant records source paths, current automation status and future
verification requirement.

## Confirmatory plan

The current pairs, horizons, replicas, formulas, endpoint/growth tolerances,
protected invariants, evidence completeness and decision states are frozen
before new attribution or candidate evidence.

Any post-result change requires a new version, rationale, field-level diff,
rerun matrix and owner-visible disclosure.

## Exploratory boundary

G1.2 may perform component attribution, time localization, cohort segmentation,
diagnostic ablations, hypothesis generation, visualizations and non-decision
metrics. Exploratory results cannot select a candidate until promoted into a
new versioned confirmatory candidate protocol before decision evidence.

## Diagnostic attribution contract

G1.2 output is required at run, policy, replica, horizon, day/window, synthetic
card lineage, review episode and aggregate-comparison grains.

The contract freezes scheduler/state, reward-component and aggregation fields,
including transition markers, actual/natural-due memory context, Challenge and
MemoryGain decomposition, total/control/candidate units and cumulative deltas.
Tracing is not implemented in G1.1.

Only synthetic identifiers are allowed. Real Anki collections, profile paths,
tokens, usernames, card content and production revlog are forbidden.

## Candidate mutation boundary

Later explicit candidate stages may modify contextual Challenge/MemoryGain
calculation, their interaction/blending, retention-transition treatment,
counterfactual reference state and contextual caps.

AttemptCredit existence, direct successful-button neutrality, Event Taxonomy
eligibility, ResponseValidity's non-positive role, Learn/Create XP, global
economy and Anki scheduler behavior remain protected without a new owner scope.

No numeric candidate value is selected.

## Decision policy

Allowed G1 outcomes:

- `RECOMMEND_RESEARCH_CANDIDATE`;
- `REJECT_REVIEW_MODEL`;
- `DEFER_REVIEW_MODEL`.

Recommendation requires all confirmatory gates and protected invariants,
complete sensitivity/fairness/abuse evidence, deterministic replay, no
unapproved protocol change and a research-only label.

Gate weakening, least-bad selection, production approval for `R-CURRENT` and
endpoint-only success are forbidden.

## Versioning

Version `review-cycling-diagnostic-v1` becomes immutable after G1.1 except
through an explicit correction stage. Substantive changes require v2 contract
and schema, rationale, field diff, prior-evidence impact, rerun matrix and
roadmap decision. G0.7 evidence remains immutable.

## Validation

Required lightweight validation:

- strict duplicate-key JSON parsing;
- Draft 2020-12 schema self-check;
- contract validation against schema;
- finite-number traversal;
- deterministic sorted two-space serialization;
- exact equality of baseline cells with G0.7 evidence;
- exact equality of normalized policies with current config;
- relative Markdown link validation;
- security/path scan;
- `git diff --check`;
- exact seven-path Git audit.

## What was not run

Intentionally not run:

- sweep;
- sensitivity;
- population;
- longitudinal;
- full pytest;
- Rust tests;
- Fast CI;
- Docker E2E;
- real-Anki E2E;
- production tests.

G1.1 changes documentation and frozen contracts only; no executable research
input changes.

## Limitations

The defect is based on bounded synthetic evidence. It does not prove human
optimization behavior or learning effectiveness. The 365-day evidence remains
limited to `R-CURRENT`, 20 cards and two replicas. Current intentional-backlog
growth semantics are only partially decision-grade. Attribution fields are a
future G1.2 requirement, not a current trace implementation.

## G1.2 entry conditions

G1.2 may start only from the committed v1 contract and must:

- preserve G0.7 evidence and all G1.1 confirmatory items;
- emit safe synthetic attribution at every required grain;
- answer root-cause questions without choosing coefficients;
- classify new analysis as exploratory unless a new confirmatory protocol is
  frozen before decision evidence.

## Next step

`G1.2 — Root-cause attribution`
