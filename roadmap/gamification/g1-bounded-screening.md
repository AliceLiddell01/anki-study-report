# G1.4 — Bounded screening closeout

## Status

```text
G1.4: COMPLETE
G1.5 started: NO
final candidate selected: NO
production integration: PROHIBITED
```

G1.4 implemented the frozen Review XP candidate mechanism, published it before viewing results, executed exactly the registered bounded matrix and recorded one survivor per family.

## Git and delivery identity

```text
base gamification SHA:
54dd47cc2817b9c07fad81da29fa666a0423c4e7

screened implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

task branch:
research/g1-4-bounded-screening

PR:
#146

final canonical gamification SHA:
recorded by the normal merge and final verification; not self-referentially embedded in this pre-merge closeout commit
```

The implementation commit was pushed and its local/remote SHA equality was verified before the screening command ran.

## Protocol, schema and evidence identities

```text
machine protocol Git blob:
6bfec56821045b6d383f2926fab79f151157ad13

strict schema Git blob:
f211dc2099d6c1ea6fbe760b7693e66119127fa6

manifest digest:
40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c

evidence digest:
836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694

external evidence bundle SHA-256:
bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be

evidence.json SHA-256:
976e728df07fdf46c8e6037f79a5b81fd5ee3b0293d70f6ab03e4a0259483b5c
```

The raw 1 MiB evidence remains external to Git. Repository documentation records the immutable identities and result summary rather than duplicating the machine payload in Markdown.

## Day-60 decision

The frozen machine protocol had higher authority than historical fallback wording.

```text
STEP:
day < 60  → multiplier 1.0
day >= 60 → frozen endpoint

TAPER:
day <= 60     → multiplier 1.0
60 < day < 90 → linear interpolation
day >= 90     → frozen endpoint
```

Applicability is derived from simulation day and the policy's structural retention-transition timeline, never from session boundaries or wall clock. Boundary tests cover days 59, 60, 61, 89, 90 and 91.

## Implementation scope

The implementation commit changed only 11 research source/test paths:

```text
research/gamification-sim/src/gamification_sim/bounded_screening.py
research/gamification-sim/src/gamification_sim/cli.py
research/gamification-sim/src/gamification_sim/day_aggregation.py
research/gamification-sim/src/gamification_sim/episode_reward.py
research/gamification-sim/src/gamification_sim/longitudinal_runner.py
research/gamification-sim/src/gamification_sim/review_candidate_mechanisms.py
research/gamification-sim/tests/test_bounded_screening.py
research/gamification-sim/tests/test_day_aggregation.py
research/gamification-sim/tests/test_episode_reward.py
research/gamification-sim/tests/test_longitudinal_runner.py
research/gamification-sim/tests/test_review_candidate_mechanisms.py
```

Production add-on, dashboard, API/payload, package, workflows, dependencies, configs, protocol/schema, scenarios, personas and Rust oracle were not changed.

## Verification

Confirmed checks:

```text
backup integrity: PASS
R-CURRENT clean-HEAD parity: PASS
single R-CURRENT regression: 1 passed
focused mechanism/reward/runner suite: 161 passed
focused suite after screening harness: 173 passed
protocol/schema semantic validation: PASS
manifest recomputation: 160 unique units
git diff --check: PASS
full research suite after final code change: PASS
Cargo-dependent skips shown by the configured suite: 2
implementation local/remote SHA equality: PASS
```

The quiet full-suite configuration did not emit an exact pass count, so this closeout records PASS without inventing one.

## Screening accounting

```text
variants including R-CURRENT: 5
policy pairs: 4
control conditions: 1
horizons: 2
replicas: 2
seeds: 2
population variants: 1

expected units: 160
actual units: 160
actual unique units: 160
missing: 0
extra: 0
duplicates: 0
```

## Hard-gate result

Each candidate had 16 non-compensable gates.

| Family | Parameterization | Result | Gate summary |
|---|---|---|---|
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-ZERO` | PASS | 16/16 PASS; cross-horizon growth range `-0.0371046033` to `-0.0004580763` |
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-NEUTRAL-RATIO` | REJECT | only `GATE-NO-CYCLING-GROWTH` failed; 5/8 required growth cells positive; maximum `+0.0175703395` |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-ZERO-30D` | PASS | 16/16 PASS; cross-horizon growth range `-0.0406010767` to `-0.0024101933` |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-NEUTRAL-RATIO-30D` | REJECT | only `GATE-NO-CYCLING-GROWTH` failed; 5/8 required growth cells positive; maximum `+0.0172449867` |

All four candidate parameterizations preserved:

```text
ordinary successful review: 1.00 RU
Again AttemptCredit: 0.25 RU
baseline delta vs R-CURRENT: 0
suppression events: 0
honest backlog differential vs reference: 0
intentional backlog advantage delta vs reference: 0
direct-button neutrality: PASS
session invariance: PASS
no response-time reward: PASS
response-validity proportionality: PASS
deterministic replay: PASS
research-only classification: PASS
```

## G1.4 survivors

Exactly one survivor is recorded per family:

```text
F-POST-TRANSITION-MG-STEP:
P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER:
P-TAPER-ZERO-30D
```

`R-CURRENT` is only the regression reference and is not survivor-eligible. G1.4 does not compare the two surviving families to select a final candidate.

## What was not run

```text
Fast CI: not run — research-only diff is outside package/Fast CI scope
Docker / real-Anki E2E: not run — production runtime and integration surfaces unchanged
.ankiaddon build: not run — package contents unchanged
G1.5 confirmatory evidence: not started
rescue/adaptive sweep: prohibited and not run
extra seeds, replicas, horizons, populations or parameterizations: not run
master/release/deployment: untouched
```

## Cleanup state

Before merge:

```text
implementation branch/worktree: retained for PR and merge
external evidence bundle: retained and hash-verified
historical implementation backup: retained until canonical merge is verified
task Python environment: retained until canonical merge is verified
```

After verified normal merge, task-only worktree, merged local/remote branch, obsolete backup copies and task-only environment/output may be removed with bounded path-specific commands. No global clean/prune is allowed.

## Remaining scientific limits

- Evidence is synthetic and does not prove human learning effectiveness, motivation or real-user gaming behavior.
- The matrix uses one canonical synthetic population, two seeds and two replicas.
- G1.2a attribution remains `ROOT_CAUSE_PARTIALLY_LOCALIZED` with `MEDIUM` confidence.
- Passing G1.4 is only survivor eligibility for later confirmatory work.
- Neither survivor is production-ready and no production economy is approved.
- G1.5 must remain a separate explicitly started task.
