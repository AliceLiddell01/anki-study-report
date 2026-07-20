# Review XP candidate protocol — G1.3

**Protocol ID:** `review-xp-candidate-protocol`
**Version:** `1`
**Status:** `FROZEN_PRE_SCREENING`
**G1.4 protocol readiness:** `READY`
**G1.4 execution readiness:** `BLOCKED_ON_IMPLEMENTATION`

The normative source is the [machine-readable protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json), validated by its [Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json). This document explains the frozen design; it does not contain screening results.

## Scientific boundary

G1.2a classified the root cause as `ROOT_CAUSE_PARTIALLY_LOCALIZED` with `MEDIUM` confidence. `memory_main` is the largest component under cell-level absolute aggregation (`0.4552230855238075`), and `post_transition` is the dominant timing window (`0.8565121323195105`). Challenge is not direction-consistent across all retention cells. These are synthetic, post-hoc attribution facts, not proof of human learning effectiveness or real-user reward gaming.

No candidate, coefficient or production economy is selected.

## Frozen candidate families

1. `F-POST-TRANSITION-MG-STEP` — step-scale only MemoryGain after the final day-60 retention transition.
2. `F-POST-TRANSITION-MG-TAPER` — linearly taper MemoryGain over the source-derived 30-day transition interval, then hold the endpoint multiplier.

Each family has exactly two predefined parameterizations. The only multiplier endpoints are `0.0` (the existing `R-NO-GAIN` endpoint) and `0.10 / 0.12 = 0.8333333333333334` (derived from current `neutral_context_credit` and `memory_gain_cap`). Adaptive search and unregistered values are forbidden.

`R-CURRENT` is a regression/reference control and is not survivor-eligible.

## Frozen matrix and budget

A screening unit is the full tuple:

```text
(candidate_or_reference,
 parameterization,
 policy_pair,
 control_condition,
 horizon,
 replica,
 seed,
 population_variant)
```

The matrix contains five variants (reference plus four parameterizations), four explicit policy pairs, horizons `90` and `365`, replicas `0` and `1`, seeds `20260716` and `20260717`, and one canonical synthetic population variant. The maximum is:

```text
5 × 4 × 1 × 2 × 2 × 2 × 1 = 160 execution units
```

No adaptive extra units are allowed.

## Hard-gate policy

Hard gates are evaluated individually. No weighted, Pareto or generalized score may compensate for a failure. Missing required data fails closed or blocks the result according to the frozen predicate.

Promotion requires, among other gates:

- every 365-day retention cell at or below the existing one-sided `0.03` cap;
- no required retention replica with `delta_365_minus_90 > 1e-9`;
- core baseline preserved within `1e-9` Review Units;
- zero suppression events;
- no worse honest backlog-return differential than `R-CURRENT` beyond `1e-9`;
- no intentional-backlog advantage increase beyond `1e-9`;
- ordinary `1.00 Review Unit`, `Again` credit `0.25`, direct-button neutrality, session invariance, deterministic replay and evidence completeness;
- at most one survivor per family.

The complete typed predicates, aggregation, operators, units, rounding and missing-data behavior are in the machine protocol.

## Falsification and stopping

A family/parameterization is falsified when target growth remains, expected direction reverses, fairness or invariant gates fail, support exists only in one replica, or an unregistered parameterization/source/config change is required. G1.4 must not start if protocol/schema/semantic validation, exact bounds, thresholds, falsification or budget recomputation fails.

## Implementation boundary

The current simulator accepts a static `RewardParameterSet`, while `evaluate_episode()` has no day/transition-window input. The catalog also does not register the four frozen parameterizations. Therefore G1.3 is scientifically complete, but G1.4 execution is blocked until a separate G1.4 implementation change exposes the frozen post-transition mechanism without changing the protocol.

That implementation must not inspect screening results before registering the frozen matrix.

## Production boundary

G1.4 has not started. Candidate selection is `false`. Production approval and integration remain prohibited. Scheduler/FSRS behavior, due dates, button semantics, add-on runtime, dashboard, API, package and release paths are unchanged.
