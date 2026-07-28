# Core Gamification Economy — candidate protocol G4.3

**Contract ID:** `core-economy-candidate-protocol`
**Version:** `1`
**Stage:** `G4.3 — Candidate economy protocol and hypothesis design`
**Status:** `FROZEN_PRE_SCREENING`
**Stage outcome:** `PROTOCOL_FROZEN`
**Results:** `NOT_AVAILABLE`
**G4.4:** `NEXT / NOT STARTED`
**Production integration:** `PROHIBITED`

Normative machine artifacts:

- [`core-economy-candidate-protocol-v1.json`](../../research/gamification-sim/contracts/core-economy-candidate-protocol-v1.json);
- [`core-economy-candidate-protocol-v1.schema.json`](../../research/gamification-sim/schemas/core-economy-candidate-protocol-v1.schema.json);
- [`core-economy-candidate-scenarios-v1.json`](../../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v1.json);
- [`core-economy-candidate-scenarios-v1.schema.json`](../../research/gamification-sim/schemas/core-economy-candidate-scenarios-v1.schema.json);
- [`core-economy-screening-matrix-v1.json`](../../research/gamification-sim/matrices/core-economy-screening-matrix-v1.json);
- [`core-economy-screening-matrix-v1.schema.json`](../../research/gamification-sim/schemas/core-economy-screening-matrix-v1.schema.json).

## 1. Purpose and stage boundary

G4.3 prospectively freezes the exact policies, hypotheses, non-compensable gates,
metrics, deterministic synthetic traces and dry screening matrix that a separately
authorized G4.4 may execute.

G4.3 does not:

```text
run screening
run simulation
read G4 results
choose a winner
choose a production formula
select a Review winner/default
average Review members
approve a Review/Learn ratio
declare the economy balanced or optimal
start G4.4, G5 or G6
change runtime/dashboard/API/database/package
```

## 2. Dependency ledger

### G4.1

```text
core-economy-problem-contract v1
status: FROZEN_PRE_NORMALIZATION_ANALYSIS
contract blob: dda1336328df7e79bc5ba1978a102faf5ca40e14
schema blob: d124ce0aafccd84c38c142c1fb8319ef91877f87
```

### G4.2

```text
core-economy-input-normalization v1
status: FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
contract blob: 0cf1bbb6f3f088d48b4c78bcc37145dacc8cebc5
schema blob: 6a5c312ac873fdcb86c4ec820842f759061c5253
current final merged human blob: 72478cb841a93fe678e290c7e5ce54502b7420b2
current final merged human SHA-256: 996bce4c2f3e9fadb1d8546f93ef533384769ce568749a9b7de022ca7dd447f9
```

G4.2 provenance chronology:

```text
pre-final stale closeout blob:
b8fd53917eab9a1433d301383c76617de5ebb85f

original final G4.2 merge human blob:
72478cb841a93fe678e290c7e5ce54502b7420b2

current final merged human blob:
72478cb841a93fe678e290c7e5ce54502b7420b2

current final merged human SHA-256:
996bce4c2f3e9fadb1d8546f93ef533384769ce568749a9b7de022ca7dd447f9

G4.2 human document changed:
NO

G4.2 semantics changed:
NO

G4.2 contract/schema changed:
NO
```

The correction changes only the stale identity ledger in the G4.2 closeout.

## 3. Source boundary retained

```text
initial domains:
REVIEW_DOMAIN
LEARN_DOMAIN

excluded:
CREATE_DOMAIN

typed interfaces:
REVIEW_DOMAIN_INPUT
LEARN_DOMAIN_INPUT
NORMALIZATION_INPUT
DOMAIN_CONTRIBUTION_RECORD
DAILY_AGGREGATION_INPUT
DAILY_AGGREGATION_RESULT_PLACEHOLDER

axes:
SESSION
ANKI_DAY
CALENDAR_DAY
```

Review:

```text
axis:
REVIEW_MODEL_AXIS_V1

members:
P-STEP-ZERO
P-TAPER-ZERO-30D

selection/default:
NONE / NONE

evaluation:
PARALLEL_SEPARATE

averaging:
PROHIBITED

winner:
NONE
```

Learn:

```text
model:
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

status:
CONFIRMATORY_INCONCLUSIVE

limitation:
DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE

source unit:
LRU

common economy XP:
false
```

## 4. Owner principle and source distinction

Internal owner decision:

```text
GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF
```

Related non-compensable principles:

```text
FALSE_POSITIVE_TOLERANCE
VERIFIED_BASE_PRESERVATION
SIGNAL_LEVEL_CONFIDENCE
REVERSIBLE_RESTRICTION
RECOVERY_WITHOUT_BONUS_LOOP
EXPLAINABLE_LIMITATION
NO_GLOBAL_USER_GUILT_LABEL
```

This decision makes graceful degradation the preferred research direction, not
a selected winner.

External official design references:

- [NIST AI Risk Management Framework Core](https://www.nist.gov/itl/ai-risk-management-framework);
- [Cloudflare Bot scores](https://developers.cloudflare.com/bots/concepts/bot-score/);
- [Cloudflare challenge bad bots](https://developers.cloudflare.com/waf/custom-rules/use-cases/challenge-bad-bots/);
- [Stripe Radar](https://docs.stripe.com/radar);
- [Stripe Radar rules](https://docs.stripe.com/radar/rules).

External patterns support documenting uncertainty/limitations, graded responses,
monitoring, explanation and recovery. They are not evidence for Anki XP, do not
supply thresholds and do not authorize cloud scoring, surveillance, account
punishment or proprietary risk models.

Project-specific hypotheses and numeric values below remain synthetic research
design.

## 5. Architecture and candidate budget

Independent dimensions:

```text
A. Review source model
B. Learn source model
C. Cross-domain normalization/conversion
D. Uncertainty response
E. Daily bounded contribution
F. Productive-day classification
G. Level curve
H. Streak and planned rest
I. Momentum
J. Recovery
```

Primitive policies: **20**. Curated bundles: **24**.
The full primitive Cartesian product would contain
**1296** combinations and is
prohibited.

Design rule:

```text
CURATED_BOUNDED_FACTORIAL_DESIGN
```

No dimension is fully crossed with every other dimension. Each dimension is
first isolated; only these load-bearing interactions are crossed:

```text
REVIEW_AXIS_X_NORMALIZATION
UNCERTAINTY_X_FALSE_POSITIVE
DAILY_BOUNDING_X_VOLUME
PRODUCTIVE_DAY_X_REST
MOMENTUM_X_RECOVERY
```

Four integrated compositions test coherent end-to-end behavior. Omitted
combinations are redundant for invariant screening and would create a post-hoc
optimization surface.

## 6. Review source transition is not uncertainty response

`P-STEP-ZERO` and `P-TAPER-ZERO-30D` remain
`REVIEW_SOURCE_TRANSITION_MODEL` variants.

```text
P-STEP-ZERO:
day < 60 -> MemoryGain multiplier 1.0
day >= 60 -> 0.0

P-TAPER-ZERO-30D:
day <= 60 -> 1.0
60 < day < 90 -> linear 1.0 to 0.0
day >= 90 -> 0.0
```

They do not contain suspicion, WATCH, restriction, recovery, appeal or
user-facing guilt semantics. G4.3 introduces an independent
`UNCERTAINTY_RESPONSE_POLICY` dimension.

Every matched Review scenario runs under both members. Results are never mixed.
A hard failure under one member cannot be hidden by the other or by an average.

## 7. Verified base and confidence-dependent context

For Review source decomposition:

```text
VERIFIED_BASE_CONTRIBUTION =
AttemptCredit
+ Pass * OutcomeCredit
+ Pass * NeutralContextCredit

CONFIDENCE_DEPENDENT_CONTEXT_CONTRIBUTION =
max(ContextCredit - NeutralContextCredit, 0)

NEGATIVE_CONTEXT_DELTA =
min(ContextCredit - NeutralContextCredit, 0)
```

Mandatory behavior:

- verified base multiplier is always `1.0`;
- honest `Again` keeps its valid attempt contribution;
- uncertainty may taper only the positive contextual component;
- negative contextual evidence is not converted into a positive bonus;
- missing evidence withholds only the unavailable positive contextual component;
- Review anomaly cannot suppress Learn contribution;
- past earned progression is never removed;
- negative XP, XP debt and level loss are prohibited;
- restriction state is signal/component scoped, never a user guilt label.

## 8. Candidate families

### Cross-domain normalization/conversion

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `N-EXPLICIT-IDENTITY-CONTROL` | `review_cru = clamp(review_unit,0,1.32); learn_cru = clamp(lru,0,1.0)` | Control mapping preserves source magnitudes explicitly; it is not a production exchange rate. |
| `N-BOUNDED-MAX-ANCHOR` | `review_cru = clamp(review_unit/1.32,0,1); learn_cru = clamp(lru/1.0,0,1)` | Uses frozen research anchors, not empirical percentiles; anchor optimality is unproven. |
| `N-LOG-SENSITIVITY` | `normalized = log1p(3*clamp(source,0,anchor))/log1p(3*anchor)` | Log shape is a prospective sensitivity contrast; no human-value interpretation. |

All mappings keep source units explicit and emit `CORE_RESEARCH_UNIT` only as a
research comparison unit. No candidate is production pricing.

### Uncertainty response

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `U-ABRUPT-CUTOFF-CONTROL` | `contribution = verified_base + negative_context_delta + positive_context_delta * (0 if anomaly else 1)` | Abrupt comparison control; expected to fail false-positive maximum-harm gate and cannot be recommended. |
| `U-FIXED-LINEAR-TAPER` | `positive contextual multiplier after trigger on evidence-bearing days = [0.75,0.50,0.25,0.25]; then +0.25 per normal day to 1.0` | Triggered by uncertainty evidence, not by Review source transition day; distinct from P-TAPER-ZERO-30D. |
| `U-CONFIDENCE-TAPER-RECOVERY` | `contribution = verified_base + negative_context_delta + positive_context_delta * state_multiplier` | Signal/component state only; no user guilt label, account punishment, appeal claim, or production scoring. |

`U-ABRUPT-CUTOFF-CONTROL` is control-only and not recommendation eligible.
`U-FIXED-LINEAR-TAPER` is independent from the temporal source transition in
`P-TAPER-ZERO-30D`.

`U-CONFIDENCE-TAPER-RECOVERY` freezes:

```text
states:
NORMAL
WATCH
RESTRICTED
RECOVERING

NORMAL -> WATCH:
one confidence < 0.60 or one non-severe conflict

NORMAL/WATCH -> RESTRICTED:
at least two of last three evidence signals confidence < 0.40 or conflicting

WATCH -> NORMAL:
two consecutive confidence >= 0.80 signals

RESTRICTED -> RECOVERING:
two consecutive confidence >= 0.80 signals

RECOVERING multipliers:
0.50 -> 0.75 -> 1.00 -> NORMAL
```

Missing evidence does not fabricate suspicion or advance state.

### Daily bounded contribution

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `D-HARD-CAP-CONTROL` | `bounded_day = min(precompression_total, 6.0)` | Abrupt cap control; preserves low volume but may create a hard boundary. |
| `D-SQRT-SOFT-CAP` | `if z<=2: z; else min(6, 2 + sqrt(z-2))` | Square-root shape is prospective; no claim that 2 or 6 CRU is optimal. |
| `D-PIECEWISE-DIMINISH` | `first 2 CRU at 1.0x; next 4 at 0.5x; next 8 at 0.25x; above 14 at 0x` | Band boundaries are research contrasts, not production limits. |

All candidates preserve legitimate low volume, compress extreme volume and make
session boundaries/backlog/configuration irrelevant.

### Productive day

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `P-DAY-BOUNDED-050` | `PRODUCTIVE iff planned_rest=false and bounded_day_total >= 0.50 CRU` | Sub-threshold contribution remains earned; classification never deletes contribution. |
| `P-DAY-DOMAIN-EVIDENCE` | `PRODUCTIVE iff planned_rest=false and (review_verified_base>=0.50 CRU or confirmed_learn>=0.50 CRU or total>=0.75 CRU)` | Uses bounded domain evidence; does not infer productivity from event count or app activity. |

```text
productive day != calendar activity
productive day != app open
productive day != time spent
productive day != streak preservation
planned rest != productive day
```

### Level curve

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `L-QUADRATIC-LEVELS` | `level = max n>=0 such that cumulative_cru >= 2*n^2` | Presentation only; threshold optimality and user response are untested. |
| `L-POWER-1_6-LEVELS` | `threshold(n)=ceil(3*n^1.6*1000)/1000; level=max n with cumulative_cru>=threshold(n)` | Fractional power is a research contrast; migration/storage remain G5. |
| `L-PIECEWISE-LEVELS` | `levels 1..10 cost 5 CRU each; 11..20 cost 10 each; 21+ cost 20 each` | Discrete bands are intentionally simple and research-only. |

All curves are monotonic, nonnegative, research-only presentations. No curve
modifies scheduler/FSRS, proves mastery or defines G5 migration/storage.

### Streak and planned rest

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `S-STRICT-PLANNED-REST` | `productive day -> streak+1; predeclared planned rest -> preserve; other nonproductive eligible day -> reset to 0` | Planning mechanism and UI are deferred; no premium freezes or consumables. |
| `S-ONE-GRACE-14D` | `productive -> +1; planned rest -> preserve; first unplanned nonproductive day in rolling 14 -> preserve without growth; next -> reset` | Grace is a research candidate, not an entitlement, consumable, or XP source. |

Frozen planned-rest invariant:

```text
no XP
no streak growth
no streak break
no debt
```

Streak is never an XP or Momentum multiplier.

### Momentum

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `M-EMA-025` | `if planned_rest: m_t=m_prev; else m_t=0.75*m_prev+0.25*q_t; q=1 productive, 0.5 ambiguous, 0 absent` | Indicator only; no spend, XP multiplier, scheduler effect, or motivation claim. |
| `M-ROLLING-7-NONREST` | `m_t = mean(last up to 7 non-rest q values); planned rest excluded; q=1 productive,0.5 ambiguous,0 absent` | Window is research-only; planned rest is neutral rather than positive or negative. |

Momentum is bounded to `[0,1]`, non-spendable, explainable and never a direct XP
multiplier. Planned rest is neutral and cannot create recursive positive
feedback.

### Recovery

| Candidate | Formula / transition | Key boundary |
|---|---|---|
| `R-LINEAR-3-NORMAL-DAYS` | `recovery_indicator advances 1/3 per productive non-rest day; contribution multiplier always 1.0` | Recovery changes indicator state only; it never increases XP or repays debt. |
| `R-STEPWISE-2-NORMAL-DAYS` | `first productive non-rest day -> RECOVERING; second consecutive -> NORMAL; contribution multiplier always 1.0` | State-only comparison; an intervening absence resets recovery count but creates no debt. |

Recovery changes presentation state only. Contribution multiplier remains
`1.0`; no return bonus, backlog multiplier, debt, level loss or permanent
disadvantage is allowed.

## 9. Candidate bundles

| Bundle | Purpose | Control | Recommendation eligible |
|---|---|---:|---:|
| `B-INTEGRATED-ABRUPT-CONTROL` | Integrated abrupt/control composition | `true` | `false` |
| `B-INTEGRATED-FIXED-TAPER` | Integrated fixed temporal taper composition | `false` | `true` |
| `B-INTEGRATED-GRACEFUL-ROBUST` | Preferred-direction integrated robust composition | `false` | `true` |
| `B-INTEGRATED-GRACEFUL-LOG` | Preferred-direction integrated log sensitivity composition | `false` | `true` |
| `B-NORM-EXPLICIT-IDENTITY-CONTROL` | Isolated CROSS_DOMAIN_NORMALIZATION contrast for N-EXPLICIT-IDENTITY-CONTROL | `true` | `false` |
| `B-NORM-BOUNDED-MAX-ANCHOR` | Isolated CROSS_DOMAIN_NORMALIZATION contrast for N-BOUNDED-MAX-ANCHOR | `false` | `true` |
| `B-NORM-LOG-SENSITIVITY` | Isolated CROSS_DOMAIN_NORMALIZATION contrast for N-LOG-SENSITIVITY | `false` | `true` |
| `B-UNC-ABRUPT-CUTOFF-CONTROL` | Isolated UNCERTAINTY_RESPONSE contrast for U-ABRUPT-CUTOFF-CONTROL | `true` | `false` |
| `B-UNC-FIXED-LINEAR-TAPER` | Isolated UNCERTAINTY_RESPONSE contrast for U-FIXED-LINEAR-TAPER | `false` | `true` |
| `B-UNC-CONFIDENCE-TAPER-RECOVERY` | Isolated UNCERTAINTY_RESPONSE contrast for U-CONFIDENCE-TAPER-RECOVERY | `false` | `true` |
| `B-DAILY-HARD-CAP-CONTROL` | Isolated DAILY_BOUNDED_CONTRIBUTION contrast for D-HARD-CAP-CONTROL | `true` | `false` |
| `B-DAILY-SQRT-SOFT-CAP` | Isolated DAILY_BOUNDED_CONTRIBUTION contrast for D-SQRT-SOFT-CAP | `false` | `true` |
| `B-DAILY-PIECEWISE-DIMINISH` | Isolated DAILY_BOUNDED_CONTRIBUTION contrast for D-PIECEWISE-DIMINISH | `false` | `true` |
| `B-PDAY-DAY-BOUNDED-050` | Isolated PRODUCTIVE_DAY contrast for P-DAY-BOUNDED-050 | `false` | `true` |
| `B-PDAY-DAY-DOMAIN-EVIDENCE` | Isolated PRODUCTIVE_DAY contrast for P-DAY-DOMAIN-EVIDENCE | `false` | `true` |
| `B-LEVEL-QUADRATIC-LEVELS` | Isolated LEVEL_CURVE contrast for L-QUADRATIC-LEVELS | `false` | `true` |
| `B-LEVEL-POWER-1_6-LEVELS` | Isolated LEVEL_CURVE contrast for L-POWER-1_6-LEVELS | `false` | `true` |
| `B-LEVEL-PIECEWISE-LEVELS` | Isolated LEVEL_CURVE contrast for L-PIECEWISE-LEVELS | `false` | `true` |
| `B-STREAK-STRICT-PLANNED-REST` | Isolated STREAK_PLANNED_REST contrast for S-STRICT-PLANNED-REST | `false` | `true` |
| `B-STREAK-ONE-GRACE-14D` | Isolated STREAK_PLANNED_REST contrast for S-ONE-GRACE-14D | `false` | `true` |
| `B-MOM-EMA-025` | Isolated MOMENTUM contrast for M-EMA-025 | `false` | `true` |
| `B-MOM-ROLLING-7-NONREST` | Isolated MOMENTUM contrast for M-ROLLING-7-NONREST | `false` | `true` |
| `B-REC-LINEAR-3-NORMAL-DAYS` | Isolated RECOVERY contrast for R-LINEAR-3-NORMAL-DAYS | `false` | `true` |
| `B-REC-STEPWISE-2-NORMAL-DAYS` | Isolated RECOVERY contrast for R-STEPWISE-2-NORMAL-DAYS | `false` | `true` |

All bundles retain `production_status: RESEARCH_ONLY`.

## 10. Hypotheses

- **`H-FP-01`** — One isolated false-positive signal must not cause maximum immediate loss of all otherwise verified contribution.
- **`H-FP-02`** — Graceful-degradation candidates must produce lower cumulative legitimate contribution loss than abrupt control under matched false-positive traces.
- **`H-FP-03`** — Verified base contribution remains invariant across confidence states.
- **`H-FP-04`** — Normal subsequent evidence can restore confidence without manual reset.
- **`H-FP-05`** — Recovery cannot create more cumulative contribution than an equivalent always-normal path.
- **`H-FP-06`** — Restriction and recovery remain explainable at source/component level.
- **`H-FP-07`** — No user-level guilt state is required.
- **`H-FP-08`** — Repeated genuinely conflicting signals can reach stronger restriction than one isolated anomaly.
- **`H-FP-09`** — Missing evidence fails closed without fabricating suspicion.
- **`H-FP-10`** — False-positive tolerance cannot be achieved by allowing an exploit advantage.
- **`H-NORM-01`** — Explicit source-unit mappings preserve domain decomposition and do not silently coerce REVIEW_UNIT or LRU.
- **`H-NORM-02`** — Bounded robust mappings reduce extreme-volume dominance while preserving low-volume legitimate contribution.
- **`H-NORM-03`** — Review-axis sensitivity remains visible under every cross-domain mapping.
- **`H-DAILY-01`** — Daily compression is session-split neutral and bounded under extreme raw volume.
- **`H-DAILY-02`** — Low-volume legitimate work is preserved exactly before the frozen soft-cap onset.
- **`H-DAILY-03`** — Intensive legitimate work remains positive after compression.
- **`H-PDAY-01`** — Productive-day classification uses bounded evidence rather than calendar activity, app open, time spent, or raw count.
- **`H-PDAY-02`** — Planned rest remains distinct from productive day and cannot mint XP or streak growth.
- **`H-LEVEL-01`** — Every level curve is monotonic, nonnegative, observable early, and meaningful at long horizon without claiming mastery.
- **`H-STREAK-01`** — Streak growth, preservation, XP, planned rest, and Momentum remain separate state transitions.
- **`H-MOMENTUM-01`** — Momentum remains bounded, non-spendable, explainable, and unable to recursively multiply progression.
- **`H-RECOVERY-01`** — Absence and return create neither XP debt nor a return bonus loop.
- **`H-REPLAY-01`** — Forward and reverse replay of identical typed traces produces byte-identical result identities.
- **`H-EXPLAIN-01`** — Every contribution, limitation, restriction, and recovery transition is decomposable to source/component reason codes.

Hypotheses do not claim human learning, motivation or retention benefit.

## 11. Non-compensable hard gates

- **`HG-CREATE-EXCLUDED`** — CREATE_DOMAIN is rejected and never contributes.. Non-compensable.
- **`HG-REVIEW-AXIS-PRESERVED`** — Both Review members are evaluated separately; no default, averaging, or hidden winner.. Non-compensable.
- **`HG-LEARN-LIMITATION-PRESERVED`** — Learn status and identity limitation remain visible in all outputs.. Non-compensable.
- **`HG-VERIFIED-BASE-PRESERVED`** — Absolute verified-base delta across confidence states is <= 1e-12.; metric `M-VERIFIED-BASE-PRESERVATION`. Non-compensable.
- **`HG-HONEST-AGAIN-NOT-PUNISHED`** — Honest Again retains its eligible verified base and receives no extra uncertainty penalty.. Non-compensable.
- **`HG-NO-NEGATIVE-XP`** — Every contribution and cumulative progression value is >= 0.. Non-compensable.
- **`HG-NO-LEVEL-LOSS`** — Level and cumulative progression never decrease within protocol version.. Non-compensable.
- **`HG-NO-SESSION-SPLIT-GAIN`** — Absolute matched session-split delta is <= 1e-12.; metric `M-SESSION-SPLIT-DELTA`. Non-compensable.
- **`HG-NO-BACKLOG-SIZE-GAIN`** — Backlog-only matched delta is <= 1e-12.; metric `M-BACKLOG-DELTA`. Non-compensable.
- **`HG-NO-NEW-MATERIAL-FLOOD-GAIN`** — Exposure/new-material-only matched delta is <= 1e-12.; metric `M-NEW-MATERIAL-FLOOD-DELTA`. Non-compensable.
- **`HG-NO-CONFIGURATION-GAIN`** — Configuration-only matched delta is <= 1e-12.; metric `M-EXPLOIT-ADVANTAGE`. Non-compensable.
- **`HG-NO-TIMEZONE-CLOCK-GAIN`** — Timezone/clock-only matched delta is <= 1e-12.; metric `M-EXPLOIT-ADVANTAGE`. Non-compensable.
- **`HG-PLANNED-REST-NEUTRAL`** — Planned rest has zero XP, zero streak growth, zero break, and zero debt.; metric `M-PLANNED-REST-DELTA`. Non-compensable.
- **`HG-STREAK-NO-XP-MULTIPLIER`** — Streak state never appears in a contribution formula.. Non-compensable.
- **`HG-MOMENTUM-NO-XP-MULTIPLIER`** — Momentum state never appears in a contribution formula.. Non-compensable.
- **`HG-MOMENTUM-NO-SNOWBALL`** — Matched cumulative progression delta caused only by Momentum is <= 1e-12.. Non-compensable.
- **`HG-RECOVERY-NO-BONUS-LOOP`** — Absence-return cumulative progression is <= always-normal matched progression + 1e-12.; metric `M-RECOVERY-LOOP-DELTA`. Non-compensable.
- **`HG-FALSE-POSITIVE-MAX-HARM-BOUNDED`** — For recommendation-eligible candidates, isolated-anomaly immediate legitimate loss ratio is <= 0.25; abrupt control may fail and is never recommendation-eligible.; metric `M-FALSE-POSITIVE-IMMEDIATE-LOSS`. Non-compensable.
- **`HG-DETERMINISTIC-REPLAY`** — Forward/reverse replay digests are identical.. Non-compensable.
- **`HG-DECOMPOSABLE-EXPLANATION`** — All included/excluded values and transitions carry source/component reason codes.; metric `M-EXPLANATION-DECOMPOSABILITY`. Non-compensable.
- **`HG-NO-REAL-USER-DATA`** — All identities and traces are synthetic and real_user_data is false.. Non-compensable.
- **`HG-RESEARCH-ONLY`** — All candidates and outputs are RESEARCH_ONLY.. Non-compensable.
- **`HG-NO-PRODUCTION-APPROVAL`** — Production approval/integration flags remain false and G4.4 remains not started.. Non-compensable.

No weighted overall score exists. A failed hard gate cannot be compensated by
another metric, persona, Review member or aggregate average.

## 12. Metrics

| Metric | Formula | Direction | Threshold |
|---|---|---|---|
| `M-FALSE-POSITIVE-IMMEDIATE-LOSS` | `(matched_normal_day - isolated_anomaly_day) / max(matched_normal_day, 1e-12)` | `MINIMIZE` | `<= 0.25` (`RECOMMENDATION_ELIGIBLE`) |
| `M-FALSE-POSITIVE-CUMULATIVE-LOSS` | `sum(normal_path - candidate_path) / max(sum(normal_path), 1e-12) over 7 evidence-bearing days` | `MINIMIZE` | `<= 0.2` (`RECOMMENDATION_ELIGIBLE`) |
| `M-TIME-TO-RECOVERY` | `count of subsequent normal evidence-bearing days until NORMAL state and multiplier 1.0` | `MINIMIZE` | `<= 4` (`U-CONFIDENCE-TAPER-RECOVERY`) |
| `M-MAX-ONE-DAY-DISCONTINUITY` | `max(abs(day_total[t]-day_total[t-1])) / max(reference_day_total[t],1e-12)` | `MINIMIZE` | `<= 0.25` (`RECOMMENDATION_ELIGIBLE_FALSE_POSITIVE_TRACES`) |
| `M-VERIFIED-BASE-PRESERVATION` | `max(abs(verified_base_state - verified_base_normal))` | `TARGET_ZERO` | `<= 1e-12` (`ALL`) |
| `M-LEGITIMATE-CONTRIBUTION-PRESERVATION` | `sum(candidate_legitimate_path) / max(sum(always_normal_path),1e-12)` | `MAXIMIZE` | `>= 0.8` (`RECOMMENDATION_ELIGIBLE`) |
| `M-EXPLOIT-ADVANTAGE` | `sum(exploit_path) - sum(matched_legitimate_path)` | `MINIMIZE` | `<= 1e-12` (`ALL`) |
| `M-SESSION-SPLIT-DELTA` | `split_path_total - unsplit_path_total` | `TARGET_ZERO` | `ABS<= 1e-12` (`ALL`) |
| `M-BACKLOG-DELTA` | `backlog_metadata_path_total - same_work_no_backlog_metadata_total` | `TARGET_ZERO` | `ABS<= 1e-12` (`ALL`) |
| `M-NEW-MATERIAL-FLOOD-DELTA` | `exposure_only_flood_total - matched_no_exposure_total` | `TARGET_ZERO` | `ABS<= 1e-12` (`ALL`) |
| `M-PLANNED-REST-DELTA` | `tuple(xp_delta, streak_growth_delta, streak_break_delta, debt_delta)` | `TARGET_ZERO` | `EQUALS [0,0,0,0]` (`ALL`) |
| `M-RECOVERY-LOOP-DELTA` | `absence_return_total - always_normal_equivalent_work_total` | `MINIMIZE` | `<= 1e-12` (`ALL`) |
| `M-DOMAIN-CONTRIBUTION-SHARE` | `domain_contribution / max(total_contribution,1e-12)` | `DESCRIPTIVE` | `NONE DESCRIPTIVE` (`ALL`) |
| `M-REVIEW-AXIS-SENSITIVITY` | `abs(total_P_STEP_ZERO - total_P_TAPER_ZERO_30D) with no averaging` | `DESCRIPTIVE` | `NONE NO_AVERAGING_AND_PER_MEMBER_GATES` (`ALL`) |
| `M-LOW-VOLUME-PRESERVATION` | `bounded_day_total / max(precompression_total,1e-12) for precompression_total <= 2.0` | `TARGET_ONE` | `ABS-1<= 1e-12` (`ALL_DAILY_CANDIDATES`) |
| `M-INTENSIVE-DAY-PRESERVATION` | `bounded_day_total / max(precompression_total,1e-12) for legitimate intensive trace` | `MAXIMIZE` | `> 0.0` (`ALL_DAILY_CANDIDATES`) |
| `M-EXPLANATION-DECOMPOSABILITY` | `explained_value / max(total_value,1e-12)` | `TARGET_ONE` | `ABS-1<= 1e-12` (`ALL`) |
| `M-STATE-TRANSITION-COUNT` | `count of uncertainty, streak, Momentum, and recovery state transitions` | `MINIMIZE` | `NONE DESCRIPTIVE` (`ALL`) |
| `M-POLICY-COMPLEXITY` | `count of named states + transition predicates + numeric parameters` | `MINIMIZE` | `<= 24` (`RECOMMENDATION_ELIGIBLE`) |

Each metric records formula, units, direction, prospective threshold,
aggregation, missing behavior and scenario coverage. Review-member aggregation
is always separate.

## 13. Exact deterministic scenario registry

The registry contains **40** scenarios and
**615** ordered synthetic inputs.
Every scenario has explicit persona, threats, invariants, hypotheses, day axes,
session structure, Review records where applicable, Learn limitations,
expected dispositions, expected hard-gate outcomes, metric applicability and
deterministic replay identity.

### `FALSE_POSITIVE`

- `SC-FP-ISOLATED-ANOMALY`
- `SC-FP-BOUNDARY-ERROR`
- `SC-FP-NORMAL-AFTER-ANOMALY`
- `SC-FP-REPEATED-ANOMALY`
- `SC-FP-OSCILLATING-SIGNALS`
- `SC-FP-RECOVERY`
- `SC-FP-MISSING-EVIDENCE`
- `SC-FP-CONFLICTING-EVIDENCE`
### `INTEGRATED`

- `SC-CROSS-DOMAIN-REVIEW-HEAVY`
- `SC-CROSS-DOMAIN-LEARN-HEAVY`
- `SC-CROSS-DOMAIN-BALANCED`
- `SC-LEVEL-LONG-HORIZON`
- `SC-STREAK-REST`
- `SC-MOMENTUM-SNOWBALL`
- `SC-RECOVERY-BONUS-LOOP`
### `LEARN`

- `SC-LEARN-LIMITATION-PRESERVED`
- `SC-LEARN-IDENTITY-AMBIGUOUS`
- `SC-LEARN-CONFIRMATION-ONLY`
- `SC-LEARN-NEW-MATERIAL-FLOOD`
### `MANIPULATION`

- `SC-SESSION-SPLIT`
- `SC-BACKLOG-RETURN`
- `SC-BACKLOG-FARM`
- `SC-RAW-VOLUME-FARM`
- `SC-CONFIGURATION-FARM`
- `SC-TIMEZONE-CLOCK-SHIFT`
- `SC-DUPLICATE-EVENT`
### `PERSONA_RHYTHM`

- `SC-BEGINNER-HEAVY`
- `SC-MATURE-DECK`
- `SC-BALANCED`
- `SC-LOW-VOLUME-CONSISTENT`
- `SC-INTENSIVE-LEGITIMATE`
- `SC-ALTERNATING-HEAVY-LIGHT`
- `SC-PLANNED-REST`
- `SC-IRREGULAR-LEGITIMATE`
- `SC-ABSENCE-RETURN`
### `REVIEW_UNCERTAINTY`

- `SC-REVIEW-PARALLEL-MATCHED`
- `SC-REVIEW-STEP-BOUNDARY`
- `SC-REVIEW-TAPER-WINDOW`
- `SC-REVIEW-MEMBER-MISSING`
- `SC-REVIEW-SENSITIVITY`

All traces have:

```text
real_user_data: false
results: NOT_AVAILABLE
```

No random unfrozen data, card text, note fields, media, profile path, username,
token or raw revlog is present.

## 14. Exact screening matrix

Frozen matrix:

```text
protocol version:
1

candidate bundles:
24

scenarios:
40

rows expected:
762

rows unique:
762

duplicates:
0

missing:
0

extra:
0

result status:
NOT_RUN

seed:
DETERMINISTIC_NO_SEED
```

Review-member coverage:

```text
P-STEP-ZERO:
370

P-TAPER-ZERO-30D:
362

NOT_APPLICABLE:
30
```

Coverage:

```text
candidate bundles: 24 / 24
scenarios: 40 / 40
hard gates: 23 / 23
metrics: 19 / 19
personas: 9 / 9
threats: 15 / 15
invariants: 31 / 31
```

Rows contain no result values beyond `NOT_RUN`.

## 15. Reproducibility and evidence firewall

Canonical serialization:

```text
UTF-8
JSON without BOM
sorted object keys
compact separators
newline terminated
duplicate keys rejected
NaN/Infinity rejected
```

Identity:

```text
row_id:
ROW- + SHA-256(canonical typed row identity)

scenario replay:
FORWARD and REVERSE where required

seed:
DETERMINISTIC_NO_SEED

scenario registry digest:
9f53c8e6af181a0106a74f0bb52d1695a00e158a6ad15cb656c91bf6670881a3

matrix digest:
9f0ad95f8e99b3e25d19d859f88afa13a0b5b3b9efc99427facde336e146241c
```

The protocol publication commit SHA becomes the mandatory G4.4 source identity.
G4.4 evidence must bind protocol SHA, protocol artifact digest, scenario digest,
matrix digest, implementation SHA, manifest digest and evidence digest.

After any result access it is prohibited to change candidates, thresholds,
gates, metrics, scenarios or matrix rows to improve outcome. A substantive
correction invalidates affected runs, requires a separate publication and a
full replacement run; old and new evidence cannot be mixed.

## 16. Claims boundary

Allowed after G4.3:

- candidate protocol prospectively frozen;
- graceful degradation operationalized as candidates/hypotheses;
- abrupt control retained;
- taper/recovery direction included;
- exact gates, metrics, scenarios and matrix published;
- results remain unavailable;
- G4.4 is ready only for separate authorization;
- production is unchanged.

Prohibited:

```text
TAPER proven superior
adaptive recovery proven safe
Review winner selected
economy balanced or optimal
ratio correct
levels optimal
streak improves discipline
Momentum improves motivation
recovery improves retention
all farming prevented
production ready
```

## 17. Privacy and security

Only synthetic IDs, records, personas, scenarios and research formulas are
allowed. User-level guilt states, remote AI scoring, cloud upload, content
fingerprints, real-user data and behavioral surveillance are prohibited.

Unchanged:

```text
loopback boundary
token validation
sanitizer
media validation
action allowlists
frontend collection access
scheduler
FSRS
due dates
```

## 18. Unresolved selections

```text
Review winner:
NONE

production normalization/conversion:
NONE

production XP amount:
NONE

production daily policy:
NONE

productive-day winner:
NONE

level winner:
NONE

streak/rest winner:
NONE

Momentum winner:
NONE

recovery winner:
NONE

final G4 outcome:
NONE
```

## 19. G4.4 entry contract

```text
G4.4 — Bounded core-economy screening and simulation
status: NEXT / NOT STARTED
```

Entry requirements:

1. exact protocol publication SHA;
2. exact candidate registry;
3. exact scenario registry;
4. exact screening matrix;
5. all schemas valid;
6. all hard gates frozen;
7. all metrics frozen;
8. Review sensitivity mandatory;
9. Learn limitation propagated;
10. evidence output format bound to exact digests;
11. detached validator required;
12. no real-user data;
13. no production code;
14. separate owner authorization.

G4.4 does not start automatically.

## 20. Final stage state

```text
G3:
DEFERRED / POST-MVP / NOT STARTED

G4:
IN PROGRESS

G4.1:
COMPLETE

G4.2:
COMPLETE

G4.3:
COMPLETE

candidate protocol:
FROZEN_PRE_SCREENING

preferred research direction:
GRACEFUL_DEGRADATION / TAPER WITH RECOVERY

abrupt model:
RETAINED AS CONTROL

Review winner:
NONE

results:
NOT_AVAILABLE

G4.4:
NEXT / NOT STARTED

simulation:
NOT_STARTED

production:
PROHIBITED
```
