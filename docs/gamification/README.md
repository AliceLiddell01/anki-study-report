# Gamification research documentation

## Current state

```text
G0: Complete
G1: In Progress
G1.1 and correction: Complete
G1.2 and G1.2a correction: Complete
G1.3: Complete
G1.4 protocol readiness: Ready
G1.4 execution readiness: Blocked on implementation
G1.4 started: No
candidate selected: No
production integration: Prohibited
```

The canonical `gamification` branch contains the isolated Review XP research package and current evidence. Research candidates are not production economies.

## Current G1 contracts

- [Review XP cross-horizon cycling problem](review-xp-cycling-problem.md)
- [G1.1 problem and gate freeze](../../roadmap/gamification/g1-problem-gate-freeze.md)
- [G1.1 contract correction](../../roadmap/gamification/g1-contract-correction.md)
- [G1.2 root-cause attribution](../../roadmap/gamification/g1-root-cause-attribution.md)
- [G1.2a attribution correction](../../roadmap/gamification/g1-root-cause-attribution-correction.md)
- [G1.3 candidate protocol](review-xp-candidate-protocol.md)
- [G1.3 stage report](../../roadmap/gamification/g1-candidate-protocol.md)
- [Machine-readable candidate protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json)
- [Candidate protocol schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json)

G1.3 froze two post-transition MemoryGain families, four parameterizations, a 160-unit matrix and non-compensable hard gates. No screening or candidate selection occurred. Current execution is blocked until the simulator implements the frozen day/window-conditioned mechanism and registry.

## Review research specifications

- [Review event taxonomy](anki-review-event-taxonomy.md)
- [Review reward model](anki-review-reward-model.md)
- [Review abuse model](anki-review-abuse-model.md)
- [Review session and Anki-day aggregation](anki-review-session-and-day.md)
- [Review simulation specification](anki-review-simulation-spec.md)

These remain research specifications. G1.3 changes no reward semantics, scheduler behavior, production code, dashboard, API, package or release workflow.

## Evidence boundary

The corrected current attribution is synthetic and post-hoc. It partially localizes the mechanism but does not prove human learning effectiveness, real-user gaming or a unique coefficient. Historical reports under `reports/gamification/historical-source/` remain chronology/provenance, not current reproduction.

## Deferred domains

Learn XP and Create XP are not started. Global conversion, levels, streak, Momentum and cross-domain economy remain deferred to G4.

## Production integration boundary

No production add-on, dashboard, payload, API, workflow, package or release integration is approved. Research assets remain outside Fast CI and `.ankiaddon` contents.
