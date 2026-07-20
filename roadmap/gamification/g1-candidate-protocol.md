# G1.3 — Candidate protocol and hypothesis design

## Status

```text
G1.3: Complete
G1.4 protocol readiness: Ready
G1.4 execution readiness: Blocked on implementation
G1.4 started: No
candidate selected: No
production integration: Prohibited
canonical publication: Complete
cleanup: Partial — terminal temp-ref deletion exception
```

## Baseline and delivery

- repository: `AliceLiddell01/anki-study-report`;
- canonical branch: `gamification`;
- expected baseline commit: `fa4650240b1bba51c75057fe4f683c52362b8e0f`;
- actual baseline commit before G1.3: `fa4650240b1bba51c75057fe4f683c52362b8e0f`;
- baseline divergence: none;
- merge base with `master`: `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e`;
- open PRs from `gamification`: none observed;
- `temp/g1-3-*` refs at run-manifest capture: none observed;
- local checkout at start: unavailable; work used connector-backed reads and locally validated generated content.

Post-publication provenance:

```text
primary publication commit: 4212b2274c827a59d901294a85fc36973c76999e
schema hardening commit: baa3390448fd21c311c361b93cd66618302cd40e
machine protocol blob: 6bfec56821045b6d383f2926fab79f151157ad13
protocol schema blob: f211dc2099d6c1ea6fbe760b7693e66119127fa6
```

These identities are intentionally absent from the self-contained machine contract, avoiding publication self-reference. The schema-hardening commit adds an explicit machine-enforced maximum of two parameterizations per frozen family; protocol decision semantics and contract data are unchanged.

A temporary `temp/g1-3-publish` branch was created after manifest capture when testing a stage-only publication path. No workflow run was used as validation or publication evidence. The workflow, archive chunks and trigger were removed; their cleanup tip is `60b14b3cb57bb7bd9d85b02f79c73af4631079ee`. The connector exposes no delete-ref action, so the now-inactive branch ref remains as a terminal cleanup exception.

## Result

G1.3 freezes two defensible post-transition MemoryGain families with four total parameterizations, an explicit 160-unit screening matrix, typed metrics/predicates, exact thresholds, protected invariants, promotion/falsification rules, stop conditions, amendment rules and the three allowed G1 outcomes.

The protocol is [human-readable](../../docs/gamification/review-xp-candidate-protocol.md) and [machine-readable](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json), with a strict [Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json).

## Scientific boundary

The protocol uses the corrected G1.2a facts only: `memory_main` is the dominant component, `post_transition` is the dominant timing window, Challenge is not direction-consistent, cap/blend interaction is negligible, and review-count delta is removed by baseline subtraction. It does not claim a unique causal formula, human learning effectiveness or real-user gaming.

## Readiness decision

Protocol readiness is `READY`: hypotheses, bounds, parameterizations, matrix, budget, thresholds, gates, falsification and stop conditions are frozen and machine-verifiable.

Execution readiness is `BLOCKED_ON_IMPLEMENTATION`: the current static reward parameter model and runner cannot apply a day/window-conditioned MemoryGain rule, and the four parameterizations are not registered. This is an implementation gap, not a scientific failure. No G1.4 execution occurred.

## Validation performed before publication

- strict JSON parse and duplicate-key-safe generation;
- finite-number traversal and `allow_nan=False` serialization;
- deterministic sorted compact serialization;
- Draft 2020-12 schema self-check and contract validation;
- schema-enforced limits of two frozen families and no more than two parameterizations per family;
- semantic checks for unique IDs/references, family/parameterization limits, bound membership, budget recomputation, predicate completeness, non-compensable hard gates and false decision/production flags;
- thirteen required negative samples plus a same-total third-parameterization-per-family rejection;
- relative-link and allowlist audit over the generated delivery;
- forbidden-path/secret pattern and trailing-whitespace scan.

Docker, real-Anki E2E, frontend/dashboard tests, add-on package build, Fast CI, G0.7 simulations, Rust oracle, G1.4 screening and G1.5 evidence were not run because no production/runtime/research source/test/config/evidence path changed.

## Changed-path allowlist

```text
docs/ai-handoff.md
docs/gamification/README.md
docs/gamification/review-xp-candidate-protocol.md
research/gamification-sim/README.md
research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json
research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g1-candidate-protocol.md
```

## Next step

Only `G1.4 — Bounded screening`: first implement the frozen mechanism/registry without changing protocol semantics, then execute exactly the registered 160-unit matrix. Production integration remains prohibited.
