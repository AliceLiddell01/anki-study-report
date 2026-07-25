# G1.4 — Bounded screening full report

## Executive summary

G1.4 is complete.

The stage recovered and integrated the previously unfinished Review XP candidate mechanism, proved that the default `R-CURRENT` behavior remained unchanged, published the implementation before viewing screening results, executed exactly the frozen 160-unit matrix and recorded one survivor in each candidate family.

```text
G1.4: COMPLETE
G1.5: NEXT / READY; NOT STARTED
final candidate selected: NO
production integration: PROHIBITED
```

The two family-level survivors are:

```text
F-POST-TRANSITION-MG-STEP
→ P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER
→ P-TAPER-ZERO-30D
```

The two neutral-ratio parameterizations were rejected solely by `GATE-NO-CYCLING-GROWTH`. All their other hard gates and protected invariants passed.

G1.4 does not rank STEP against TAPER, does not select a final Review XP candidate and does not authorize production integration.

For the implemented command surface and operational contract, see the [G1.4 technical reference](../../docs/gamification/review-xp-bounded-screening.md).

## Final repository and delivery state

```text
canonical branch:
gamification

pre-G1.4 base SHA:
54dd47cc2817b9c07fad81da29fa666a0423c4e7

screened implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

closeout commit SHA:
678ca6a229218a2a7c301aab3d38d4e0105b24cb

PR:
#146

canonical G1.4 merge SHA:
d855baf7355bba3f4014370cafba3fdc6d0c0e3c
```

PR #146 was merged with a normal two-parent merge commit. The task branch was removed remotely, the local task branch and remote-tracking ref were removed, and the linked task worktree was deleted after canonical merge verification.

The owner's unrelated canonical checkout remained on its existing Core remediation branch and was not switched, reset or cleaned by the G1.4 workflow.

## Stage purpose

G1.3 froze two post-transition MemoryGain mechanism families and four predefined parameterizations. G1.4 had one bounded responsibility:

> Implement the frozen mechanism without changing protocol semantics, execute exactly the registered matrix and retain at most one passing parameterization per family for later confirmatory work.

The stage was not allowed to:

- alter the protocol, schema, coefficient endpoints or thresholds after observing results;
- add variants, seeds, replicas, horizons, policy pairs or populations;
- perform adaptive or rescue search;
- select a final candidate between the two families;
- change FSRS or scheduling behavior;
- modify production add-on, dashboard, API, package or release surfaces;
- begin G1.5 automatically.

## Authoritative inputs

The following frozen inputs governed the stage:

- [G1.3 human protocol](../../docs/gamification/review-xp-candidate-protocol.md);
- [machine protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json);
- [strict Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json);
- current longitudinal configuration `configs/review-longitudinal-v0.1.json`;
- current matched policy-pair catalog;
- current research source and tests on `gamification`.

The machine protocol had higher authority than historical fallback wording when resolving the day-60 boundary.

## Scientific starting point

G1.2a left the Review XP root cause only partially localized:

```text
classification: ROOT_CAUSE_PARTIALLY_LOCALIZED
confidence: MEDIUM
largest component: memory_main
memory_main share: 0.4552230855238075
dominant timing window: post_transition
post_transition share: 0.8565121323195105
Challenge direction-consistent: false
```

The attribution was synthetic and post-hoc. It supported bounded prospective hypotheses but did not establish one uniquely correct reward formula.

## Recovery and integration history

### Missing original worktree

The earlier local implementation worktree and branch no longer existed when G1.4 resumed. The following recovery sources remained:

- implementation backup;
- worktree metadata backup;
- old baseline worktree;
- task-specific Python 3.11.9 environment.

No destructive repair, reset, clean or blind patch application was performed.

### Backup integrity

The recovery bundle was independently checked before use:

```text
recorded working files: 8
manifest files: 8
snapshot files: 8
missing files: 0
extra files: 0
artifact hash failures: 0
working-file hash failures: 0
patch failures: 0
result: BACKUP_INTEGRITY_PASS
```

The recovered implementation consisted of six modified files and two new files in the research package.

### Integration onto current `gamification`

The old implementation was based on an earlier repository state. It was not copied wholesale over the current branch.

A fresh linked worktree was created from exact `origin/gamification` SHA `54dd47cc2817b9c07fad81da29fa666a0423c4e7`. The tracked patch was first validated against that base, then the six tracked changes and two new files were restored. The resulting dirty set was required to contain exactly those eight paths.

### `R-CURRENT` compatibility proof

One restored regression test contained digest constants from the old base. Those constants initially failed on the current base.

The implementation was not changed to satisfy the stale checkpoint. Instead, a clean copy of current `HEAD` and the restored implementation were executed in separate Python processes with the same config, seed and `R-CURRENT` parameter set.

The following values matched exactly:

- manifest trajectory digest;
- final-cohort digest;
- report digest;
- every policy trajectory digest;
- full serialized payload SHA-256;
- absence of candidate metadata.

```text
DEFAULT_R_CURRENT_PARITY_PASS
```

Only after this proof were the regression-test constants refreshed to the current pre-wiring digests.

## Implementation architecture

The published implementation commit changed only 11 research source/test paths:

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

### Frozen candidate registry

`review_candidate_mechanisms.py` introduced:

- immutable typed candidate definitions;
- exact family and parameterization identities;
- registered endpoint multipliers;
- typed simulation execution context;
- day/window multiplier evaluation;
- semantic reconciliation with the machine protocol.

The registry rejects unknown parameterizations, invalid bounds, wrong mechanism classes and candidate use with anything other than `R-CURRENT`.

### Reward-path wiring

The candidate identity and execution context are threaded through episode evaluation, daily aggregation and longitudinal policy execution.

Only MemoryGain is scaled. The implementation leaves unchanged:

- ordinary attempt credit;
- successful outcome credit;
- Again attempt credit;
- support and supplemental reward terms;
- completion and volume credit;
- scheduler and FSRS semantics;
- due dates and intervals;
- direct button behavior;
- response-time behavior;
- default `R-CURRENT` execution.

### Bounded screening harness

`bounded_screening.py` introduced:

- protocol/schema validation;
- exact registry validation;
- typed deterministic execution-unit identities;
- exact 160-unit manifest construction;
- matched policy-pair execution;
- compact unit evidence and canonical digests;
- protected invariant checks;
- 16 hard gates per candidate;
- fail-closed result validation;
- external evidence writer and human-readable summary.

### CLI

The research command surface gained:

```text
validate-bounded-screening
run-bounded-screening
```

The run command requires exact implementation and base SHAs and records the exact command in evidence provenance.

## Day-60 semantics

The frozen machine protocol defines the following behavior.

### STEP

```text
day < 60  → multiplier 1.0
day >= 60 → frozen endpoint
```

### TAPER

```text
day <= 60     → multiplier 1.0
60 < day < 90 → linear interpolation from 1.0 to the endpoint
day >= 90     → frozen endpoint
```

The mechanism is active only when the policy's final structural retention transition is day `60`. It uses simulation day and the retention timeline, never wall clock or session boundaries.

Boundary tests cover days `59`, `60`, `61`, `89`, `90` and `91`.

## Publication barrier

The implementation was committed and pushed before any canonical screening result was viewed.

```text
published implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

local/remote SHA equality:
PASS

result files present in implementation commit:
NO
```

After publication, the mechanism, matrix, thresholds, seeds, replicas, horizons, population and hard-gate semantics were frozen for the run.

## Verification ledger

### Recovery and compatibility

```text
backup integrity: PASS
restore onto current gamification base: PASS
git diff --check after restore: PASS
R-CURRENT clean-HEAD parity: PASS
single R-CURRENT regression: 1 passed
```

### Focused verification

```text
mechanism/reward/runner focused suite: 161 passed
focused suite after screening harness: 173 passed
protocol/schema semantic validation: PASS
exact manifest recomputation: 160 unique units
git diff --check: PASS
```

### Full research verification

```text
full research pytest suite after final code change: PASS
Cargo-dependent skips shown by configured suite: 2
implementation local/remote SHA equality: PASS
```

The quiet full-suite output did not provide a reliable exact pass count, so none is invented here.

### Evidence verification

After the canonical run:

- the bundle SHA-256 matched the recorded value;
- the archive contained only the expected result files;
- `evidence.json` validated through the implementation validator;
- standalone `manifest.json` equaled the embedded manifest;
- all 160 unit digests were recomputed and matched;
- evidence provenance matched the published implementation and base SHAs;
- evidence and run-metadata identities matched;
- repository `HEAD` and working state remained unchanged by the run.

## Screening identity

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

The raw evidence is approximately 1 MiB and remains outside Git. The repository records immutable identities and a bounded semantic summary rather than duplicating the machine payload in Markdown.

## Frozen matrix accounting

A screening unit is:

```text
(candidate_or_reference,
 policy_pair,
 control_condition,
 horizon,
 replica,
 seed,
 population_variant)
```

Matrix dimensions:

```text
candidate/reference variants: 5
policy pairs: 4
control conditions: 1
horizons: 2
replicas: 2
seeds: 2
population variants: 1

5 × 4 × 1 × 2 × 2 × 2 × 1 = 160
```

Final accounting:

```text
expected units: 160
actual units: 160
actual unique units: 160
missing: 0
extra: 0
duplicates: 0
```

`required_invariant_checks` was correctly treated as metadata, not as an additional matrix axis.

## Hard-gate policy

Every candidate had to pass all 16 non-compensable gates:

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

No weighted score, Pareto compensation, least-bad choice or post-hoc threshold adjustment was permitted.

## Screening results

| Family | Parameterization | Result | Gate result |
|---|---|---|---|
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-ZERO` | PASS | 16/16 PASS |
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-NEUTRAL-RATIO` | REJECT | only `GATE-NO-CYCLING-GROWTH` failed |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-ZERO-30D` | PASS | 16/16 PASS |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-NEUTRAL-RATIO-30D` | REJECT | only `GATE-NO-CYCLING-GROWTH` failed |

### Passing STEP parameterization

`P-STEP-ZERO` passed all gates.

```text
required cross-horizon growth range:
-0.0371046033 to -0.0004580763
```

Every required retention growth cell was non-positive under the frozen tolerance.

### Rejected STEP parameterization

`P-STEP-NEUTRAL-RATIO` failed only the cycling-growth gate.

```text
positive required growth cells: 5 / 8
maximum positive growth: +0.0175703395
```

Its baseline, suppression, fairness, backlog, unit-credit, button, session, response-validity, replay, seed, completeness and research-only gates passed.

### Passing TAPER parameterization

`P-TAPER-ZERO-30D` passed all gates.

```text
required cross-horizon growth range:
-0.0406010767 to -0.0024101933
```

Every required retention growth cell was non-positive under the frozen tolerance.

### Rejected TAPER parameterization

`P-TAPER-NEUTRAL-RATIO-30D` failed only the cycling-growth gate.

```text
positive required growth cells: 5 / 8
maximum positive growth: +0.0172449867
```

Its remaining 15 gates passed.

## Protected invariants

All four candidate parameterizations preserved the following observed invariants:

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
secondary seed present: PASS
evidence completeness: PASS
research-only classification: PASS
```

The rejected variants were not unsafe on these dimensions; they were rejected because they failed to close the original cross-horizon cycling-growth gap.

## Survivor decision

Exactly one survivor is recorded in each family:

```text
F-POST-TRANSITION-MG-STEP:
P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER:
P-TAPER-ZERO-30D
```

`R-CURRENT` remains a regression/reference control and is not survivor-eligible.

A survivor means only that the registered parameterization passed the G1.4 bounded screening gates and may enter separately authorized G1.5 confirmatory work.

G1.4 makes no claim that:

- STEP is better than TAPER;
- TAPER is better than STEP;
- either survivor is the final Review XP candidate;
- either survivor improves human learning or motivation;
- either survivor is appropriate for production.

## Scientific interpretation

The result supports a narrow conclusion:

> Under the current synthetic model and frozen matrix, complete post-transition removal of MemoryGain closed the required cross-horizon growth gate in both the immediate-step and 30-day-taper families, while the neutral-ratio endpoints did not.

This is evidence about the tested synthetic mechanism, not proof of a universal causal rule.

The result does not resolve the earlier uncertainty around partial root-cause localization. It narrows later confirmatory work to two zero-endpoint variants, but the reason those two pass may still combine MemoryGain effects with model-specific dynamics.

## Production boundary

No production surface changed.

```text
add-on runtime: unchanged
dashboard: unchanged
API/payload: unchanged
Anki collection access: unchanged
local server/token behavior: unchanged
preview/sanitizer: unchanged
package contents: unchanged
release workflows: unchanged
telemetry/remote services: unchanged
```

The simulator remains research-only and uses deterministic synthetic inputs. No real user profile, collection, token or identifiable learning data was used.

## Checks intentionally not run

```text
Fast CI:
not run — research-only diff outside package/Fast CI scope

Docker / real-Anki E2E:
not run — runtime and integration surfaces unchanged

.ankiaddon build:
not run — package contents unchanged

G1.5 confirmatory matrix:
not started

adaptive/rescue sweep:
prohibited and not run

extra variants, seeds, replicas, horizons or populations:
not run

master/release/deployment:
untouched
```

## Merge and cleanup

PR #146 was merged into `gamification` with merge commit:

```text
d855baf7355bba3f4014370cafba3fdc6d0c0e3c
```

Post-merge verification confirmed:

- the merge had exactly the expected base and head parents;
- the canonical diff contained exactly the 15 expected research/docs paths;
- the merged closeout contained the expected survivor and boundary markers;
- `origin/gamification` pointed to the merge commit;
- the unrelated canonical checkout branch, HEAD and dirty state were unchanged.

Cleanup completed:

```text
remote task branch: removed automatically after merge
linked task worktree: removed
local task branch: removed
stale remote-tracking task ref: removed
```

The external evidence bundle remains intentionally outside Git. Historical recovery backups and the task Python environment are local, non-canonical artifacts and may be removed separately with exact path-specific commands when no longer needed.

## Remaining limitations and risks

- Evidence is synthetic and does not prove human learning effectiveness, motivation or real-user reward-gaming behavior.
- Only one canonical synthetic population variant was used.
- The matrix used two seeds and two replicas.
- G1.2a remains `ROOT_CAUSE_PARTIALLY_LOCALIZED` with `MEDIUM` confidence.
- Both survivors use a zero post-transition MemoryGain endpoint; confirmatory work must assess whether this is robust rather than an artifact of the current synthetic model.
- Passing G1.4 is survivor eligibility, not production readiness.
- The external raw bundle must remain available if future independent audit needs unit-level evidence.
- G1.5 must remain separately scoped and explicitly started.

## G1.5 handoff boundary

G1.5 may start only under a separate task. Its eligible inputs are exactly:

```text
P-STEP-ZERO
P-TAPER-ZERO-30D
```

G1.5 must not:

- revive the rejected neutral-ratio variants without a new protocol amendment;
- change G1.4 thresholds or reinterpret failed gates;
- add post-hoc screening units to the completed G1.4 matrix;
- assume an ordering between STEP and TAPER;
- call either survivor production-ready;
- integrate Gamification into `master`.

## Final decision

```text
G1.4 outcome:
TWO_FAMILY_LEVEL_SURVIVORS

STEP survivor:
P-STEP-ZERO

TAPER survivor:
P-TAPER-ZERO-30D

final Review XP candidate:
NOT_SELECTED

G1.5:
READY_BUT_NOT_STARTED

production integration:
PROHIBITED
```
