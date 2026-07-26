# G1.6 — Решение по candidate Review XP и закрытие G1

## Статус

```text
Mode: ChatGPT
G1.6: COMPLETE
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended research candidate: NONE
production approved: NO
production integration: PROHIBITED
G2: PLANNED / NOT STARTED
```

G1 закрыт допустимым machine-protocol outcome `DEFER_REVIEW_MODEL`. Это не отклонение Review model: оба survivor остаются `CONFIRMATORY_ELIGIBLE`, но G1.6 не получил доступ к обязательным raw bundles G1.4/G1.5 и поэтому не мог заново подтвердить evidence continuity. Даже по принятым canonical summaries кандидаты неразличимы без нового post-hoc ranking criterion.

## Repository / branch / PR

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
starting origin/gamification HEAD: 2b4b6a39dacb66732349211ebe553e9ab02d78a9
starting comparison: exact identity with origin/gamification
G1.4 PR: #146
G1.5 PR: #153
G1.6 PR: recorded by the merge that adds this closeout
```

Основной WSL checkout владельца и Windows Downloads не были доступны в исполняемой среде ChatGPT. GitHub state проверялся через GitHub connector; mutation выполнена на отдельной task branch от exact starting HEAD без force push и без изменения `master`.

## G1.4 / G1.5 evidence identities

### G1.4

```text
published implementation: a8857f111849e2e98744adda8e06fe1910bdf805
historical merge SHA: d855baf7355bba3f4014370cafba3fdc6d0c0e3c
matrix: 160 / 160 unique
missing / extra / duplicates: 0 / 0 / 0
manifest digest: 40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c
evidence digest: 836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694
bundle SHA-256: bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be
evidence.json SHA-256: 976e728df07fdf46c8e6037f79a5b81fd5ee3b0293d70f6ab03e4a0259483b5c
```

### G1.5

```text
published implementation: 7ae7a26cf0591dfc7f004f3b378eb3bff8b7d2c8
merge SHA: 2b4b6a39dacb66732349211ebe553e9ab02d78a9
matrix: 840 / 840 unique
missing / extra / duplicates: 0 / 0 / 0
replay groups: 420
replay mismatches: 0
manifest digest: eea4e2ed6da087f7ac45eb56d9390b23e44ce52837b5f1d015afb3276049c728
evidence digest: 9b4d6aa41bf2392aac273784b45b28ff88210e05ea04533bf440d6522ad75afa
evidence.json SHA-256: e19854893b6b0b035b4ed34a8888ab8b8b331faaf8623b4a5f658aaaeb9fe6b4
bundle SHA-256: 90b2132cbe46edeb2a28e6f9ae81de311807353dd5e0826cbe8d3a6af41a85fb
```

Эти identities согласуются с current code/docs, PR #146/#153 и canonical closeouts. Они не заменяют read-only проверку самих raw bundles.

## Bundle validation

Bounded read-only search выполнен только в доступных roots этой ChatGPT-сессии: mounted uploads, доступные project/output roots и заявленные WSL/Windows paths. Ожидаемый WSL checkout и Windows Downloads в среде отсутствовали; среди mounted uploads raw bundle candidates, `FILES.sha256` и canonical `evidence.json` не найдены.

Поэтому в G1.6 не выполнены:

```text
G1.4 raw bundle SHA-256 recomputation
G1.4 FILES.sha256 / inventory validation
G1.4 detached validator
G1.5 raw bundle SHA-256 recomputation
G1.5 FILES.sha256 / inventory validation
G1.5 detached validator
```

Original bundles не изменялись и не копировались в Git. Classification blocker: `EVIDENCE_CONTINUITY`.

## Decision input ledger

| Dimension | `P-STEP-ZERO` | `P-TAPER-ZERO-30D` |
|---|---|---|
| identity / family | `F-POST-TRANSITION-MG-STEP` | `F-POST-TRANSITION-MG-TAPER` |
| mechanism semantics | `day < 60 → 1.0`; `day >= 60 → 0.0` | `day <= 60 → 1.0`; `60 < day < 90 → linear 1.0→0.0`; `day >= 90 → 0.0` |
| G1.4 outcome | survivor; `16/16 PASS` | survivor; `16/16 PASS` |
| G1.5 outcome | `CONFIRMATORY_ELIGIBLE`; `19/19 PASS` | `CONFIRMATORY_ELIGIBLE`; `19/19 PASS` |
| worst existing endpoint value | `-0.01545876751445053` versus cap `0.03` | `-0.014261856317041764` versus cap `0.03` |
| worst existing 90→365 growth | `-0.008160610762557667` versus allowed `<= 1e-9` | `-0.008898854267061052` versus allowed `<= 1e-9` |
| baseline delta | maximum absolute `0.0` | maximum absolute `0.0` |
| suppression | `0` | `0` |
| backlog fairness | honest differential `0.0..0.0`; intentional-backlog delta `0.0..0.0` | honest differential `0.0..0.0`; intentional-backlog delta `0.0..0.0` |
| session / button invariants | PASS / PASS | PASS / PASS |
| persona / model coverage | 16 personas; three model conditions; no failures | 16 personas; three model conditions; no failures |
| abuse-probe coverage | 12 probes; PASS | 12 probes; PASS |
| known uncertainties | synthetic/post-hoc attribution; abrupt day-60 discontinuity; human effects unknown | synthetic/post-hoc attribution; linear-shape assumption unvalidated; human effects unknown |
| fairness risks | immediate post-transition removal may be unnecessarily abrupt near boundary | taper still reduces honest contextual reward and adds a 30-day temporal surface |
| implementation complexity | one structural boundary and one endpoint | structural boundary, duration, interpolation and end boundary |
| explainability | very simple rule; abrupt behavior must be explained | smoother narrative; exact linear shape and window require explanation |
| reversibility | simple candidate disable/rollback | reversible, but window state and interpolation need additional checks |
| future observability | clear day-60 breakpoint | day-60..90 trajectory must be observed as a curve |
| unvalidated claims | optimality, learning benefit, motivation, gaming resistance, production readiness | optimality of linear taper/window, learning benefit, motivation, gaming resistance, production readiness |

No new score, weighted ranking, Pareto ordering, seed preference or threshold was introduced.

## Decision policy

### Gate 1 — Evidence integrity

`FAIL_CLOSED` for G1.6 decision continuity: canonical identities are present, but raw bundles were unavailable, so hashes, inventory and detached validators could not be re-executed. This blocks `RECOMMEND_RESEARCH_CANDIDATE` and does not establish a model-level reason for `REJECT_REVIEW_MODEL`.

### Gate 2 — Eligibility

Based on accepted G1.4/G1.5 records, both candidates satisfy the eligibility predicate:

```text
G1.4 survivor
AND G1.5 CONFIRMATORY_ELIGIBLE
AND all required gates PASS
```

### Gate 3 — Non-negotiable boundaries

Accepted evidence records PASS for baseline preservation, zero suppression, backlog fairness, button neutrality, session invariance, no response-time reward, abuse probes and research-only isolation. Scheduler/FSRS and production surfaces remain untouched.

### Gate 4 — Evidence-supported distinguishability

STEP is simpler and more directly observable; TAPER is smoother but adds an unvalidated linear-shape assumption and temporal state surface. These are real engineering differences, but current project contracts do not define either simplicity or smoothness as a mandatory winner criterion. The partially localized evidence supports removing late post-transition MemoryGain, not one uniquely correct transition shape.

### Gate 5 — Tie handling

Without verified bundle continuity and without a pre-existing non-compensable principle that resolves STEP versus TAPER, selecting either candidate would be arbitrary. The required outcome is therefore `DEFER_REVIEW_MODEL`.

### Gate 6 — Model rejection

Not satisfied. The accepted synthetic evidence does not show fundamental invalidity of the Review model, and both candidates remain eligible under the frozen gates.

## Candidate assessments

### `P-STEP-ZERO`

Supported: smallest mechanism surface, exact day-60 breakpoint, all accepted G1.4/G1.5 gates PASS.

Not established: that the abrupt boundary is preferable for real users, safer for motivation, or optimal for learning.

### `P-TAPER-ZERO-30D`

Supported: gradual transition, all accepted G1.4/G1.5 gates PASS, no observed synthetic fairness regression.

Not established: that a linear 30-day shape is causally correct, easier for users to understand, or safer in production.

## Selected allowed outcome

```text
final G1 outcome: DEFER_REVIEW_MODEL
recommended research candidate: NONE
```

Exact unresolved dependency:

> The canonical G1.4 and G1.5 raw bundles were not available to G1.6 for required hash, `FILES.sha256`, inventory and detached-validator continuity checks; accepted aggregate evidence also leaves STEP and TAPER tied under the frozen non-compensable criteria.

## Status of both candidates

```text
P-STEP-ZERO: CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D: CONFIRMATORY_ELIGIBLE; not selected; not falsified
```

Neither candidate is promoted to production or called production-ready.

## Supported and unsupported claims

Supported:

- frozen synthetic G1.4/G1.5 summaries record both zero-endpoint candidates as eligible;
- all recorded required gates passed for both;
- both preserve the recorded baseline, suppression, fairness, session and button invariants;
- G1 may close with `DEFER_REVIEW_MODEL` without creating a new stage.

Unsupported:

- human learning effectiveness;
- real-user motivation or gaming resistance;
- superiority of STEP over TAPER or TAPER over STEP;
- production readiness, production approval or integration safety;
- optimality of day 60, the abrupt boundary, the linear taper or 30-day duration outside the frozen synthetic design.

## Production boundary

```text
production approved: NO
production integration: PROHIBITED
add-on runtime changed: NO
dashboard / API / payload changed: NO
scheduler / FSRS changed: NO
package / release changed: NO
```

## No new simulations

G1.6 is a decision/closure stage. No G1.4 or G1.5 matrix, seed, replica, persona, model condition, candidate family, parameter search or simulation was added or rerun.

## Verification

Performed:

- `origin/gamification` exact identity check against `2b4b6a39dacb66732349211ebe553e9ab02d78a9`;
- PR #146/#153 identity and merge-state inspection;
- current G1 source, protocol, code and test review;
- allowed final outcomes read from the machine protocol;
- candidate mechanism boundary review in `review_candidate_mechanisms.py`;
- confirmatory registry/gate review in `confirmatory.py` and `test_confirmatory.py`;
- relative-link and Markdown/code-fence validation for task documents;
- changed-path allowlist, whitespace and secret/private-path scan.

Not run:

```text
G1.4 matrix
G1.5 matrix
Fast CI
Docker real-Anki E2E
frontend tests
.ankiaddon / package build
full pytest
```

Reason: docs-only G1.6 closure; production/research code and test files are unchanged, while raw evidence continuity could not be revalidated because the bundles were unavailable.

## Changed paths

```text
docs/ai-handoff.md
research/gamification-sim/README.md
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g1-review-xp-decision.md
```

## Cleanup

No raw evidence, task logs, temporary extracted payloads, runtime outputs or private paths were added to Git. Task branch cleanup is performed after verified merge. Original external G1.4/G1.5 bundles remain owner-managed and were not deleted.

## G1 final status

```text
G1: COMPLETE
G1.6: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended research candidate: NONE
production integration: PROHIBITED
G2: PLANNED / NOT STARTED
```

G2 was not started.
