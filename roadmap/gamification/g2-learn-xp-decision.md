# G2.6 — Финальное решение по Learn XP и закрытие G2

## Статус

```text
Mode: ChatGPT
G2.6: COMPLETE
G2: COMPLETE
G2 final outcome: RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended research candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
production approved: NO
production integration: PROHIBITED
G3: PLANNED / NOT STARTED
```

G2.6 рекомендует `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` как bounded Learn XP research model. Это final-stage product/research governance decision, а не изменение G2.5 outcome, confirmatory eligibility, научное доказательство superiority или разрешение production integration.

## Repository / delivery

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
starting gamification HEAD: ef953149972229f5ec08bfb2da2bbdd4a28a0fbb
task branch: g2-6-learn-xp-decision
PR: PENDING_UNTIL_CREATED
final merge SHA: PENDING_UNTIL_VERIFIED_MERGE
master changed: NO
```

Точный PR, commit sequence и resulting `gamification` HEAD проверяются после публикации branch и записываются в финальном ChatGPT-отчёте. Self-referential final commit/merge identity не подставляется в pre-merge document.

## Decision policy

### Gate 1 — Repository continuity

```text
current G2.1–G2.5 closeouts coherent: PASS
expected candidates and outcomes present: PASS
later contradictory G2 decision found: NO
hidden production integration found: NO
```

`gamification` перед mutation точно совпадал с `ef953149972229f5ec08bfb2da2bbdd4a28a0fbb`. `AGENTS.md` отсутствовал и зафиксирован как `NOT FOUND`; это не blocker для docs-only G2.6.

### Gate 2 — Evidence integrity

```text
repository-confirmed:
- current G2.1–G2.5 contracts, schemas, code, tests and closeouts
- G2.4 family-local survivors and descriptive contrasts
- G2.5 outcomes, reason and evidence identities
- production/research boundaries

report-confirmed:
- owner-run G2.4/G2.5 raw-bundle validation
- detached validation and byte-identical reproduction
- G2.5 merge and cleanup chronology

independently revalidated in G2.6:
- current repository/branch continuity
- current contracts, code, tests and documentation consistency
- allocation and state-surface contrasts used by the decision

not currently available:
- raw G2.4/G2.5 archives for fresh byte-level recomputation
- disposable runtime-compatible Anki identity probe
```

Недоступность raw archives сохраняется как documented confidence limitation. Она не создаёт cross-family distinction и не является blocker для bounded governance choice: G2.5 ранее проверил G2.4 continuity, предыдущий независимый аудит принял repository state с documented limitations, а обе models имеют один и тот же identity-evidence blocker.

### Gate 3 — Candidate viability

| Candidate | G2.4 | G2.5 | Falsified | Production ready |
|---|---|---|---|---|
| `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` | family-local survivor | `CONFIRMATORY_INCONCLUSIVE` | NO | NO |
| `C-PENDING-SPLIT-D1-NOTE-SIBLING` | family-local survivor | `CONFIRMATORY_INCONCLUSIVE` | NO | NO |

Shared G2.5 reason:

```text
DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
```

### Gate 4 — Shared blocker interpretation

The missing disposable identity probe applies equally to both `S-NOTE-SIBLING` candidates. It blocks `CONFIRMATORY_ELIGIBLE` and production-readiness claims, but it does not falsify either allocation family, prove equality across product/architecture dimensions or prohibit a bounded research recommendation.

### Gate 5 — Evidence-supported contrasts

| Dimension | `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` | `C-PENDING-SPLIT-D1-NOTE-SIBLING` |
|---|---|---|
| confirmed bounded total | `1.0 LRU` | `1.0 LRU` |
| pending allocation | `0.0 LRU` | `0.25 LRU` provisional |
| confirmation settlement | `1.0 LRU` | `0.75 LRU`, total settles to `1.0 LRU` |
| G2.4 unconfirmed provisional exposure | `0` | `3561.75` |
| active pending peak | `0` | `1` |
| terminal non-confirmed value | `0` | provisional value must be voided to `0` |
| explanation complexity fields | `5` | `7` |
| reward-bearing pending state | absent | present, idempotent and non-spendable |
| reconciliation surface | smaller | expiry/cancel/invalidate settlement and void semantics |
| auditability / rollback | simpler | additional provisional ledger/state paths |
| frozen farming advantages | none observed | none observed |
| supported human-learning benefit | none | none |
| supported motivation benefit | none | none |

Both models preserve the same frozen confirmed total and passed the applicable synthetic safety/accounting gates. The available evidence does not establish a user benefit from exposing `0.25 LRU` provisionally.

### Gate 6 — Final governance principle

```text
MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE
```

> Когда candidates одинаково сохраняют bounded confirmed reward и frozen hard-gate safety, а human benefit дополнительной provisional state не подтверждён, выбирается model с меньшей provisional exposure, accounting complexity и explanation surface.

This principle is applied symmetrically, is compatible with G2.1 protected invariants, does not rewrite G2.4/G2.5 outcomes and does not introduce a synthetic winner score, weighted ranking or post-hoc simulation metric.

### Gate 7 — Outcome selection

The recommendation gate passes:

```text
at least one viable, non-falsified candidate: YES
repository continuity sufficient: YES
explicit non-arbitrary governance principle available: YES
shared limitations preserved: YES
```

Selected allowed outcome:

```text
RECOMMEND_LEARN_XP_RESEARCH_MODEL
```

`DEFER_LEARN_XP_MODEL` is not selected because the current governance principle distinguishes the candidates without inventing a human-learning or motivation claim. `REJECT_LEARN_XP_MODEL` is not selected because neither model was falsified and the Learn XP contract remains coherent.

## Candidate status ledger

### Recommended research candidate

```text
candidate: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
G2.4: family-local survivor
G2.5: CONFIRMATORY_INCONCLUSIVE
G2.5 reason: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
selected by: explicit G2.6 product/research governance decision
confirmatory eligible: NO
falsified: NO
production ready: NO
production approved: NO
```

### Non-selected candidate

```text
candidate: C-PENDING-SPLIT-D1-NOTE-SIBLING
G2.4: family-local survivor
G2.5: CONFIRMATORY_INCONCLUSIVE
G2.5 reason: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
selected: NO
falsified: NO
rejected as invalid: NO
production ready: NO
production approved: NO
```

Non-selection does not invalidate the pending-split family. It records only that its additional provisional reward state is not justified by current evidence for the bounded research default.

## Evidence identities retained from G2.4 and G2.5

### G2.4

```text
screened implementation SHA: 548b27de6283b32fb27541db02ce6c8b65c29756
expected / actual / unique: 340 / 340 / 340
missing / extra / duplicates: 0 / 0 / 0
manifest digest: fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a
evidence digest: 5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6
valid bundle SHA-256: a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78
```

### G2.5

```text
base SHA: 93be5ebac17c42d09272d0195a8b07f19af18274
protocol publication SHA: 903604245aaa540674f650b998d32f497b018f49
expected / actual / unique: 216 / 216 / 216
missing / extra / duplicates: 0 / 0 / 0
identity evidence mode: SYNTHETIC_CONTRACT_ONLY
manifest digest: 6224c9b363f18662328a89981dd2e8f303f14a10ac43771e74be220dc27d3f27
evidence digest: d2d5327e382ae85b1fea575f9efed5604ed11905aff56ec19a005546726badbe
canonical archive SHA-256: 4e96835f5517d8bd2e9ce350776b8e3bc24dc8878c74f1e5c0897d216506678e
canonical evidence.json SHA-256: cc275780dfc98eaa8e683188815606568a7aaca80720e3ddeb5584914da61a4a
detached validation: PASS
byte-identical reproduction: PASS
```

G2.6 does not rerun either matrix and does not modify these frozen identities or outcomes.

## Supported and unsupported claims

Supported:

- both candidates remain non-falsified G2.4 family-local survivors;
- both retain `CONFIRMATORY_INCONCLUSIVE` under the same missing identity evidence;
- both settle to the same bounded `1.0 LRU` after valid confirmation;
- confirmation-only creates no provisional reward exposure and has a smaller accounting/explanation surface;
- G2 may close with a bounded research recommendation under an explicit governance principle.

Unsupported:

- that either model improves learning, retention or motivation;
- that confirmation-only is scientifically superior or universally optimal;
- that provisional feedback has no possible user value;
- that `S-NOTE-SIBLING` is runtime-confirmed against a disposable Anki identity probe;
- that the recommended model is production-ready or safe to integrate without later design and evidence stages;
- that all gaming is prevented.

## Production boundary

```text
production approved: NO
production integration: PROHIBITED
add-on runtime changed: NO
dashboard / API / payload changed: NO
scheduler / FSRS changed: NO
database / ledger changed: NO
workflow / Fast CI changed: NO
package / release changed: NO
master changed: NO
```

The recommendation authorizes only bounded future design/research use of the selected model. Any production amount, ledger, persistence, API, UI, scheduler interaction, package inclusion or release requires a separate explicit stage and owner decision.

## Documentation scope

Expected docs-only G2.6 path set:

```text
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
research/gamification-sim/README.md
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g2-learn-xp-decision.md
```

Frozen G2.1–G2.5 contracts, schemas, source code, tests and historical closeouts are unchanged.

## Verification

Required final verification before merge:

```text
starting branch/HEAD guard
changed-path allowlist
full PR diff review
whitespace / conflict-marker check
Markdown code-fence balance
relative-link target audit
status consistency and stale-wording search
private absolute path scan
secret/token scan
no production paths changed
no machine contract/schema/code changed
merge ancestry and resulting gamification HEAD verification
```

Not run by design:

```text
G2.4 matrix
G2.5 matrix
full research pytest
Fast CI
frontend tests
production build
Docker real-Anki E2E
package / .ankiaddon validation
```

Reason: G2.6 is a docs-only decision/closure stage; production and research execution code are unchanged.

## Next-stage boundary

```text
G3: PLANNED / NOT STARTED
```

G2 completion does not automatically activate G3. This task does not define G3 implementation, production XP amount, level curve, Review/Learn conversion or economy calibration.
