# Review XP cross-horizon cycling problem

## Status

`G1.1_PROBLEM_AND_GATE_FROZEN`

`G1: IN_PROGRESS`

`G1.2: NEXT`

`production integration: PROHIBITED`

## Purpose

This document is the human-readable companion to the frozen
[Review cycling diagnostic contract](../../research/gamification-sim/contracts/review-cycling-diagnostic-v1.json).
It is an **internal pre-analysis protocol for G1 diagnostics**. G0 evidence was
already observed; this freeze is created before new attribution, ablation or
candidate experiments. It is not an external preregistration.

## Canonical provenance

- current publication commit: `cece52120b04e75d8ec937c56c9575283ec479c5`;
- G0.7 executable evidence source: `9716b3f98bc4a975031a078f42e38a7d8fb109a6`;
- canonical evidence status: `COMPLETE_CURRENT_EVIDENCE_REPRODUCED_WITH_OPEN_GAP`;
- evidence record:
  [`g0.7-windows-amd64-py311-rust-1.97.1.json`](../../research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json);
- longitudinal config:
  [`review-longitudinal-v0.1.json`](../../research/gamification-sim/configs/review-longitudinal-v0.1.json);
- machine schema:
  [`review-cycling-diagnostic-v1.schema.json`](../../research/gamification-sim/schemas/review-cycling-diagnostic-v1.schema.json).

G0.7 remains immutable. G1.1 records no new simulator result.

## Observed behavior

Under the current R-CURRENT Review XP model, temporary desired-retention
cycling produces systematic growth in unexplained XP advantage between the
90-day and 365-day matched horizons for both high- and low-retention policy
pairs, while the intentional-backlog control does not show the same
systematic two-replica growth.

This statement is deliberately narrow. It does not mean that all scheduler
changes are exploits, all desired-retention changes are bad, the model is
unsafe, or human users will farm XP.

## Why this is a problem

The current 365-day endpoint cap is necessary but insufficient. A candidate can
remain below the one-sided 3% endpoint cap while its matched advantage grows
systematically from 90 to 365 days. A small recurring advantage may accumulate
into a persistent strategy signal. Scheduler settings must not become a durable
XP optimization mechanism, but legitimate settings and honest recovery from
backlog must remain usable.

G1 must explain and correct the mechanism, reject the Review model, or defer it.
It must not weaken the gate merely because candidate hypotheses fail.

## What is already confirmed

- the G0 environment is reproducible and the functional baseline is verified;
- current evidence is reproduced from the frozen executable source;
- required same-seed evidence repeats deterministically;
- the high- and low-retention cycling groups fail the current cross-horizon gate;
- all current 365-day cells pass the one-sided endpoint cap;
- current intentional-backlog cells pass the endpoint cap and do not both grow;
- baseline preservation is approximately 1.0 with zero honest suppression events;
- no Review candidate is recommended and `R-CURRENT` is a regression reference.

## What is not known

G1.1 does not determine when divergence begins, whether it is caused by review
count or reward per review, which component dominates, whether both cycling
directions share one mechanism, or whether card-level positive and negative
effects cancel at the endpoint. It does not select a formula or coefficient.

## Canonical policies

| Policy | Scheduler | Desired-retention timeline | Delay | Review limit | Role |
|---|---|---|---|---:|---|
| `stable-high` | `py-fsrs` | day 0 → 0.95 | none | 1000 | high-cycle control |
| `temporary-high-cycle` | `py-fsrs` | day 0 → 0.95; day 30 → 0.90; day 60 → 0.95 | none | 1000 | high-cycle changed policy |
| `stable-low` | `py-fsrs` | day 0 → 0.80 | none | 1000 | low-cycle control |
| `temporary-low-cycle` | `py-fsrs` | day 0 → 0.80; day 30 → 0.90; day 60 → 0.80 | none | 1000 | low-cycle changed policy |
| `timely-control` | `py-fsrs` | day 0 → 0.90 | none | 1000 | backlog control |
| `intentional-backlog` | `py-fsrs` | day 0 → 0.90 | reviews disabled on days 30–44 | 1000 | deliberate-delay comparison |
| `honest-backlog-return` | `py-fsrs` | day 0 → 0.90 | reviews disabled on days 30–44 | 1000 | fairness comparison |

The exact source-of-truth definitions remain in the current config. The
normalized entries above are frozen with its blob identity in the JSON contract.

## Canonical horizons and cohorts

| Mode | Horizon | Cohort per replica | Replicas |
|---|---:|---:|---:|
| `calibration-90` | 90 days | 24 cards | 2 |
| `calibration-365` | 365 days | 20 cards | 2 |

The confirmatory cross-horizon comparison uses parameter set `R-CURRENT`,
master seed `20260716`, replicas `0` and `1`, and matched policy pairs.

## Metric definitions

Contract numbers use **fractions**. Human tables may display percentages.
For example, `0.01740169409234382` equals `1.740169409234382%`.

For a matched policy cell:

```text
baseline_delta = candidate.core_baseline - control.core_baseline
total_delta = candidate.total_review_units - control.total_review_units
unexplained_units = total_delta - baseline_delta
unexplained_advantage =
    0.0 when control.total_review_units == 0
    otherwise unexplained_units / control.total_review_units
```

Cross-horizon semantics:

```text
delta_365_minus_90 = advantage_365 - advantage_90
replica_grew = delta_365_minus_90 > 1e-9
endpoint_pass = advantage_365 <= 0.03 + 1e-9
```

For comparison IDs beginning with `retention-`:

```text
systematic_growth = every matched replica grew
group_pass = every endpoint passes and systematic_growth is false
overall_pass = every required group passes
```

The current implementation does **not** apply the systematic-growth predicate to
`intentional-backlog`; its executable group status is endpoint-based. The
observed G0.7 baseline additionally records one growing and one non-growing
replica. Any stronger decision-grade backlog-growth rule requires a new
confirmatory contract version before candidate results.

Baseline preservation uses `math.isclose` with absolute and relative tolerance
`1e-9`. Honest baseline suppression events must equal zero. NaN and Infinity are
rejected.

## Current per-replica baseline

| Comparison | Replica | 90-day | 365-day | Delta | Endpoint | Grew |
|---|---:|---:|---:|---:|---|---|
| `intentional-backlog` | 0 | -0.787729417762993% | 0.0563232339029468% | 0.84405265166594% | PASS | `true` |
| `intentional-backlog` | 1 | -0.0443460580490553% | -1.56749288562931% | -1.52314682758025% | PASS | `false` |
| `retention-high-cycle` | 0 | -0.377432857740813% | 1.74016940923438% | 2.1176022669752% | PASS | `true` |
| `retention-high-cycle` | 1 | -1.00445928503794% | 0.154388265864154% | 1.1588475509021% | PASS | `true` |
| `retention-low-cycle` | 0 | 1.09805792973217% | 1.16238687290513% | 0.0643289431729617% | PASS | `true` |
| `retention-low-cycle` | 1 | 0.40174042320942% | 1.36049686510937% | 0.958756441899951% | PASS | `true` |

## Group gate semantics

- `retention-high-cycle`: `FAIL`; both replicas grow although endpoints pass.
- `retention-low-cycle`: `FAIL`; both replicas grow although endpoints pass.
- `intentional-backlog`: `PASS`; current endpoint gate passes and the observed
  replicas do not show two-replica growth.
- overall current research gate: `FAIL`.

Endpoint pass alone is not sufficient for a cycling candidate.

## Hard invariants

G1 candidate work must preserve:

1. `Again` retains non-zero honest attempt credit.
2. `Hard`, `Good` and `Easy` do not gain different direct game rewards.
3. An ordinary successful review remains around `1.00 Review Unit`.
4. The no-FSRS path retains ordinary baseline reward.
5. Intentional backlog is not an optimal XP strategy.
6. Honest return from backlog is not punished merely for being late.
7. Session splitting does not create reward.
8. Response time does not create positive reward.
9. Response validity may reduce suspicious context reward but may not increase it.
10. Candidate output remains decomposable into understandable components.
11. Review XP remains research-only.
12. Cycling PASS alone never makes a candidate production-ready.

The machine contract records the current automation status and future
verification requirement for each invariant. Partial or normative invariants
must not be described as already automated.

## Confirmatory questions

Before candidate decision evidence, G1 freezes:

- policy pairs, horizons and replicas;
- metric formulas and fraction representation;
- the one-sided 3% endpoint cap and `1e-9` tolerances;
- the retention-group systematic-growth rule;
- protected invariants and evidence-completeness requirements;
- final decision states.

Changing any of these after viewing candidate results requires a new contract
version, rationale, field-level diff, rerun matrix and owner-visible disclosure.

## Exploratory diagnostic questions

G1.2 may explore component attribution, time localization, cohort segmentation,
diagnostic ablations, alternative visualizations and additional non-decision
metrics. It must treat the twelve root-cause questions in the machine contract
as questions rather than conclusions.

Exploratory findings cannot select a candidate until promoted into a new
versioned confirmatory candidate protocol before decision evidence is viewed.

## Required attribution fields

G1.2 must produce attribution at run, policy, replica, horizon, day/window,
synthetic card lineage, review episode and aggregate-comparison grains.

Required scheduler/state context covers desired retention, transition markers,
natural due and actual review day, delay, retrievability at actual and natural
due, stability, Good counterfactual stability, difficulty, model confidence and
outcome.

Required reward decomposition covers Attempt and Outcome credit, neutral
context, raw/due/extra/adjusted challenge, delay credit, raw and credited memory
gain, pre/post-blend context, response validity, core units and cap/suppression
reason.

Required aggregation covers review counts, successful/Again counts, component
sums, candidate/control totals, unexplained advantage, cumulative daily delta
and transition-window delta.

Only deterministic synthetic IDs are allowed. Real collection data, profile
paths, tokens, usernames, card content and production revlog are forbidden.

## Candidate mutation boundary

Later explicit candidate stages may alter ChallengeCredit, MemoryGainCredit,
their interaction or confidence blending, retention-transition treatment,
counterfactual reference state, and contextual budgeting or capping.

Without a new owner-approved scope they may not alter AttemptCredit existence,
direct successful-button neutrality, Event Taxonomy eligibility,
ResponseValidity as a non-positive multiplier, Learn XP, Create XP, global
levels/economy, or Anki scheduler behavior. G1.1 chooses no numeric candidate.

## Decision outcomes

G1 may end only as:

- `RECOMMEND_RESEARCH_CANDIDATE`;
- `REJECT_REVIEW_MODEL`;
- `DEFER_REVIEW_MODEL`.

Recommendation requires cycling PASS, every protected invariant, complete
sensitivity/fairness/abuse evidence, same-seed reproducibility, unchanged
confirmatory semantics and an explicit research-only label.

It is forbidden to weaken the gate because candidates failed, select the least
bad candidate, call `R-CURRENT` production-ready, or treat endpoint cap alone as
success.

## Versioning and change control

`review-cycling-diagnostic-v1` becomes immutable after G1.1 except through an
explicit correction stage. A substantive change requires v2 contract and schema,
change rationale, field-level diff, impact analysis, rerun matrix and roadmap
decision. A prose typo cannot rewrite numerical baselines or gate semantics in
place.

## G1.1 contract correction

The explicit-correction rule was used to repair two metadata defects without
changing the frozen decision protocol. First, attribution requirements remain
frozen and mandatory for G1.2, but their current completeness gate is now
`NORMATIVE_NOT_YET_EXECUTABLE` because G1.1 implemented no trace. Second, metric
value kinds now match their actual outputs:

| Metric | Representation | Unit | Tolerance semantics |
|---|---|---|---|
| `endpoint_pass` | `boolean` | `boolean` | `1e-9` applies to the ratio predicate input |
| `replica_grew` | `boolean` | `boolean` | `1e-9` is the ratio predicate threshold |
| `group_systematic_growth` | `boolean` | `boolean` | not applicable to the aggregate boolean |
| `overall_research_gate` | `status` | `status` | not applicable to the aggregate status |

No evidence cell, group result, formula, threshold, tolerance, policy pair,
horizon, replica, invariant or decision outcome changed. The protocol remains
`review-cycling-diagnostic-v1` because decision semantics are unchanged. G1.2
may begin only from the corrected and validated contract/schema pair.

## Methodological references and caveats

- [OSF Registrations](https://help.osf.io/article/330-welcome-to-registrations)
  informs the time-stamped, read-only planning analogy and the separation of
  confirmatory from exploratory work. This repository does not claim an OSF
  registration.
- [Ng, Harada and Russell, Policy Invariance Under Reward Transformations](https://ai.stanford.edu/~ang/papers/shaping-icml99.ps)
  is a warning that reward changes can alter optimized policy under specific MDP
  assumptions; it is not a theorem about human Anki behavior.
- [Google DeepMind, Specification gaming](https://deepmind.google/discover/blog/specification-gaming-the-flip-side-of-ai-ingenuity/)
  provides a proxy-objective analogy for unintended high-reward strategies.
- [Skalse et al., Defining and Characterizing Reward Hacking](https://arxiv.org/abs/2209.13085)
  supplies conceptual vocabulary for proxy reward versus intended objective.
- [Git worktree documentation](https://git-scm.com/docs/git-worktree.html)
  supports isolated temporary checkout practice.

These reward-hacking and policy-invariance references are methodological
analogies. They do not model human motivation or prove that Anki users will
optimize the system in the same way as an RL agent.

AI-safety terminology from these references is not product UI language.

## Out of scope

G1.1 changes no reward formula, coefficient, threshold, candidate, simulator
source, tests, config, evidence, scenario, fixture, Anki scheduling, Learn/Create
XP, global economy, dashboard, production integration, CI or E2E behavior.

## Next step: G1.2

`G1.2 — Root-cause attribution` implements synthetic diagnostic tracing and
answers the frozen questions without changing this v1 contract or selecting a
candidate.
