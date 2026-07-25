# Review XP bounded screening — G1.4 technical reference

**Stage:** `G1.4 — Bounded screening`  
**Status:** `COMPLETE`  
**Research package:** `research/gamification-sim/`  
**Production integration:** `PROHIBITED`  
**Next stage:** `G1.5`, ready but not started

This document explains the implemented G1.4 screening harness and its operational contract. It is not a replacement for the frozen G1.3 protocol and does not select a final Review XP candidate.

## Source hierarchy

Use the following order when resolving conflicts:

1. current research source code and tests;
2. the [machine-readable candidate protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json);
3. the [strict Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json);
4. the frozen [human protocol explanation](review-xp-candidate-protocol.md);
5. the [G1.4 closeout report](../../roadmap/gamification/g1-bounded-screening.md).

The human protocol is a frozen pre-screening G1.3 design document. Its historical readiness text must not be interpreted as the current repository status. Current execution status and results are recorded in the G1.4 closeout and track README.

## Purpose

G1.4 answers one bounded question:

> Under the frozen G1.3 matrix and non-compensable hard gates, which predefined post-transition MemoryGain parameterizations remain eligible for later confirmatory work?

It does not:

- tune coefficients after observing results;
- search outside the four registered parameterizations;
- select a final candidate between families;
- prove human learning effectiveness or motivation;
- approve production reward behavior;
- change FSRS, due dates, scheduling or Anki runtime behavior.

## Implemented components

### Candidate mechanism registry

`src/gamification_sim/review_candidate_mechanisms.py` defines:

- `FrozenReviewCandidate` — immutable typed parameterization identity;
- `RewardExecutionContext` — simulation day and structural retention-transition days;
- `FROZEN_REVIEW_CANDIDATES` — exactly four registered parameterizations;
- `memory_gain_multiplier()` — the only mechanism-specific multiplier calculation;
- semantic validation against the frozen machine protocol.

The registry contains exactly:

| Family | Parameterization | Endpoint | Shape |
|---|---|---:|---|
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-ZERO` | `0.0` | immediate step |
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-NEUTRAL-RATIO` | `0.8333333333333334` | immediate step |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-ZERO-30D` | `0.0` | linear 30-day taper |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-NEUTRAL-RATIO-30D` | `0.8333333333333334` | linear 30-day taper |

`R-CURRENT` is the regression reference. It is not a candidate and cannot survive or be promoted.

### Reward wiring

The candidate path is threaded through:

- `episode_reward.py`;
- `day_aggregation.py`;
- `longitudinal_runner.py`.

Only the MemoryGain contribution is scaled. Attempt credit, outcome credit, support credit, completion credit, volume credit and all scheduling behavior remain unchanged.

When no candidate parameterization is supplied, the runner calls the original default path. Clean-HEAD parity demonstrated that `R-CURRENT` produces the same trajectory, final-cohort, report and full payload digests with and without the G1.4 wiring.

### Screening harness

`src/gamification_sim/bounded_screening.py` provides:

- protocol/schema loading and semantic validation;
- typed `ScreeningExecutionUnit` identities;
- deterministic 160-unit manifest construction;
- per-unit matched policy execution;
- compact evidence extraction;
- protected-invariant evaluation;
- 16 non-compensable hard gates per candidate;
- result validation and canonical evidence digesting;
- external report writing.

### CLI surface

The research CLI exposes two G1.4 commands:

```text
validate-bounded-screening
run-bounded-screening
```

## Day and transition semantics

The machine protocol is authoritative.

### STEP family

```text
day < 60  → multiplier 1.0
day >= 60 → registered endpoint multiplier
```

### TAPER family

```text
day <= 60     → multiplier 1.0
60 < day < 90 → linear interpolation from 1.0 to the endpoint
day >= 90     → registered endpoint multiplier
```

The final transition must structurally occur on day `60`. If the supplied retention timeline does not end at the candidate's registered start day, the multiplier remains `1.0`.

The mechanism uses simulation day and the policy retention timeline. It never derives applicability from:

- session boundaries;
- wall-clock time;
- UI state;
- response duration;
- Anki profile data.

Boundary tests cover days `59`, `60`, `61`, `89`, `90` and `91`.

## Frozen execution matrix

A `ScreeningExecutionUnit` is the tuple:

```text
(candidate_or_reference,
 policy_pair,
 control_condition,
 horizon,
 replica,
 seed,
 population_variant)
```

The axes are:

| Axis | Values | Count |
|---|---|---:|
| candidate/reference | `R-CURRENT` + four registered parameterizations | 5 |
| policy pair | four frozen cases | 4 |
| control condition | `MATCHED_CONTROL_FROM_CASE` | 1 |
| horizon | `90`, `365` | 2 |
| replica | `0`, `1` | 2 |
| seed | `20260716`, `20260717` | 2 |
| population | `CANONICAL_SYNTHETIC_COHORT` | 1 |

```text
5 × 4 × 1 × 2 × 2 × 2 × 1 = 160 units
```

`required_invariant_checks` is metadata evaluated against evidence; it is not an execution axis.

Each unit receives a canonical digest-based `unit_id`. The manifest fails closed unless it contains exactly 160 units, 160 unique IDs and zero missing, extra or duplicate units.

## Policy cases

The four protocol cases map to current matched-analysis policy pairs:

| Protocol case | Matched pair |
|---|---|
| `CASE-RETENTION-HIGH` | `retention-high-cycle` |
| `CASE-RETENTION-LOW` | `retention-low-cycle` |
| `CASE-INTENTIONAL-BACKLOG` | `intentional-backlog` |
| `CASE-HONEST-BACKLOG-RETURN` | `honest-backlog-return` |

For each unit, left and right policy executions must share the same initial cohort digest and latent stream ID. A mismatch aborts evidence generation.

## Validation command

From `research/gamification-sim/` with `src` importable:

```bash
python -m gamification_sim \
  --research-root . \
  validate-bounded-screening
```

A valid result reports:

```text
VALID review-xp-bounded-screening-manifest-v1 160 unique units <manifest-digest>
```

This command validates protocol/schema semantics and recomputes the exact manifest. It does not execute the simulations.

## Screening command

The canonical G1.4 run used the published implementation commit before the results were viewed:

```bash
python -m gamification_sim \
  --research-root . \
  run-bounded-screening \
  --implementation-sha a8857f111849e2e98744adda8e06fe1910bdf805 \
  --base-sha 54dd47cc2817b9c07fad81da29fa666a0423c4e7 \
  --output-dir <external-output-root>
```

The runner requires:

- both SHAs to be lowercase 40-character hexadecimal values;
- current `HEAD` to equal `--implementation-sha`;
- `--base-sha` to be an ancestor of the implementation;
- the frozen protocol, schema, config and candidate registry to validate;
- exactly 160 manifest units.

The canonical result must not be regenerated from the post-merge `gamification` HEAD, because the screened identity is the published implementation commit, not the later merge commit. Use the recorded evidence identities for review. Any future reproduction should use an isolated checkout of the screened implementation and must not be confused with a new G1.5 experiment.

## Evidence output

The writer creates:

```text
<output-root>/bounded-screening/<evidence-digest-prefix>/
  evidence.json
  manifest.json
  summary.md
  run-metadata.json
```

### `evidence.json`

Contains:

- implementation/base/branch and environment provenance;
- the complete manifest;
- all 160 compact unit results;
- per-candidate gate evidence;
- the canonical `evidence_digest`.

### `manifest.json`

Contains the protocol/schema/config identities, frozen axes, exact accounting and all unit definitions.

### `summary.md`

Contains the human-readable PASS/REJECT table. It is a projection of evidence, not the normative artifact.

### `run-metadata.json`

Contains write-time metadata and the evidence identity. Its timestamp is not part of the scientific result digest.

Generated screening output remains outside Git. Repository documentation records immutable digests and bounded summaries instead of committing the raw payload.

## Hard gates

Every candidate must pass all 16 gates independently:

1. `GATE-ENDPOINT-CAP`;
2. `GATE-NO-CYCLING-GROWTH`;
3. `GATE-BASELINE-PRESERVED`;
4. `GATE-ZERO-SUPPRESSION`;
5. `GATE-HONEST-BACKLOG-FAIRNESS`;
6. `GATE-NO-BACKLOG-GAIN`;
7. `GATE-ORDINARY-UNIT`;
8. `GATE-AGAIN-CREDIT`;
9. `GATE-BUTTON-NEUTRAL`;
10. `GATE-SESSION-INVARIANT`;
11. `GATE-NO-RESPONSE-TIME-REWARD`;
12. `GATE-RESPONSE-VALIDITY`;
13. `GATE-DETERMINISTIC-REPLAY`;
14. `GATE-SECONDARY-SEED`;
15. `GATE-EVIDENCE-COMPLETE`;
16. `GATE-RESEARCH-ONLY`.

There is no aggregate score, weighted compensation, Pareto rescue or least-bad promotion. One failed hard gate produces `REJECT`.

## Result interpretation

G1.4 produced one survivor in each family:

```text
F-POST-TRANSITION-MG-STEP
→ P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER
→ P-TAPER-ZERO-30D
```

The neutral-ratio variants were rejected only by `GATE-NO-CYCLING-GROWTH`. This means their other safety, baseline, fairness and evidence gates passed, but the original cross-horizon growth problem remained in required cells.

A G1.4 survivor means only:

- the parameterization passed the frozen bounded screening gates;
- it is eligible for separately authorized G1.5 confirmatory work;
- at most one parameterization survived in its family.

It does not mean:

- final candidate selection;
- superiority between STEP and TAPER;
- production readiness;
- human learning or motivation benefit;
- approval to alter the add-on reward economy.

## Reproducibility identities

```text
base SHA:
54dd47cc2817b9c07fad81da29fa666a0423c4e7

screened implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

canonical merge SHA:
d855baf7355bba3f4014370cafba3fdc6d0c0e3c

manifest digest:
40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c

evidence digest:
836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694

external evidence bundle SHA-256:
bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be
```

## Testing boundary

The implementation was verified with:

- clean-HEAD `R-CURRENT` parity;
- boundary and registry tests;
- focused reward/aggregation/runner tests;
- manifest and gate-evaluator tests;
- the complete research pytest suite after the final code change;
- independent evidence and unit-digest validation.

Fast CI, Docker/real-Anki E2E and `.ankiaddon` packaging were intentionally not run because the change is isolated to research/docs and does not alter production/package surfaces.

## Production and security boundary

The G1.4 implementation has no path into:

- the add-on runtime;
- dashboard payloads or APIs;
- Anki collection access;
- local server/token handling;
- sanitizer or preview behavior;
- package/release workflows;
- telemetry or remote services.

The simulator consumes deterministic synthetic inputs. It must not receive real profile exports, collection data, tokens or user-identifying records.

## G1.5 handoff

G1.5 remains a separate stage and must be explicitly started. It may use only the two recorded survivors and the frozen confirmatory boundary. G1.5 must not silently:

- revive rejected neutral-ratio variants;
- alter G1.4 thresholds after seeing results;
- treat the two families as already ranked;
- call either survivor production-ready;
- merge `gamification` into `master`.

See the [G1.4 full report](../../roadmap/gamification/g1-bounded-screening.md) for the implementation history, verification ledger, result analysis and final repository state.
