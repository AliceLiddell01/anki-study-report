# Gamification research documentation

## Current state

```text
G0: COMPLETE
G1: COMPLETE
G1 final outcome: DEFER_REVIEW_MODEL
recommended Review XP research candidate: NONE
G2: IN PROGRESS
G2.1: COMPLETE
G2.2: NEXT / NOT STARTED
production integration: PROHIBITED
```

The canonical `gamification` branch contains isolated research contracts, fixtures, simulator code and accepted synthetic evidence. Research candidates and research outcomes are not production economies.

## Current G2 contracts

- [Learn XP problem contract](learn-xp-problem-contract.md)
- [G2.1 closeout](../../roadmap/gamification/g2-learn-xp-problem-contract.md)
- [Machine-readable Learn XP contract](../../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json)
- [Learn XP contract schema](../../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json)

G2.1 freezes Learn XP terminology, scheduler/reward boundaries, four identity candidates, pending/confirmation minimum requirements, six anti-farming threat families, 19 protected invariants, privacy/claims boundaries and the G2.2 entry contract.

G2.1 does not select an identity winner, lifecycle, reward amount, pending ratio, confirmation delay, candidate family or simulation matrix. G2.2 is not started.

## Current G1 contracts

- [Review XP cross-horizon cycling problem](review-xp-cycling-problem.md)
- [G1.1 problem and gate freeze](../../roadmap/gamification/g1-problem-gate-freeze.md)
- [G1.1 contract correction](../../roadmap/gamification/g1-contract-correction.md)
- [G1.2 root-cause attribution](../../roadmap/gamification/g1-root-cause-attribution.md)
- [G1.2a attribution correction](../../roadmap/gamification/g1-root-cause-attribution-correction.md)
- [G1.3 candidate protocol](review-xp-candidate-protocol.md)
- [G1.3 stage report](../../roadmap/gamification/g1-candidate-protocol.md)
- [G1.4 bounded screening](../../roadmap/gamification/g1-bounded-screening.md)
- [G1.5 confirmatory protocol](review-xp-confirmatory-protocol.md)
- [G1.5 confirmatory evidence](../../roadmap/gamification/g1-confirmatory-evidence.md)
- [G1.6 decision and G1 closeout](../../roadmap/gamification/g1-review-xp-decision.md)
- [Machine-readable candidate protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json)
- [Candidate protocol schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json)

G1 closed with `DEFER_REVIEW_MODEL`. `P-STEP-ZERO` and `P-TAPER-ZERO-30D` remain confirmatory-eligible, not selected and not falsified. Production remains prohibited.

## Review research references

- [Review event taxonomy](anki-review-event-taxonomy.md)
- [Review reward model](anki-review-reward-model.md)
- [Review abuse model](anki-review-abuse-model.md)
- [Review session and Anki-day aggregation](anki-review-session-and-day.md)
- [Review simulation specification](anki-review-simulation-spec.md)

These are references for terminology, research discipline and protected invariants. Their Review XP formulas, candidates and matrices do not define Learn XP automatically.

## Evidence and privacy boundary

G1 evidence is synthetic. G2.1 introduces no simulation evidence and uses only contract/schema validation. No real card text, note fields, media, profile paths, usernames, tokens, raw revlog or identifiable learning history enter G2 research artifacts.

## Production integration boundary

No production add-on, dashboard, payload, API, scheduler, FSRS, database, workflow, package, release or telemetry integration is approved. Research assets remain outside Fast CI and `.ankiaddon` contents.
