# Platform / CI roadmap

Platform work evolves GitHub Actions, packaging, release delivery and real-Anki E2E. It is an independent track: it neither renumbers product work nor blocks Core, Gamification, Operations, Identity or Extensions unless a specific stage names a delivery dependency.

## State

| Stage | Status | Result / goal |
| --- | --- | --- |
| [CI 1](ci-01-gated-delivery-baseline.md) | Complete | gated delivery baseline |
| [CI 2](ci-02-exact-fast-package.md) | Complete | exact Fast CI package producer |
| [CI 3](ci-03-exact-package-e2e-handoff.md) | Complete | exact-package E2E handoff |
| [CI 4](ci-04-package-reuse-measurement.md) | Complete | package reuse measurement |
| [CI 5](ci-05-ghcr-environment-image.md) | Complete | stable GHCR environment producer |
| [CI 5A/5B](ci-05a-05b-fast-ci-observability.md) | Complete | timing and duplicate typecheck removal |
| [CI 6A/6B](ci-06-ghcr-consumer-cutover.md) | **Complete** | digest-pinned GHCR-only cloud consumer |
| [CI 7](ci-07-post-cutover-optimization.md) | Conditional | rolling baseline and one measured bottleneck |
| [CI 8](ci-08-fast-ci-critical-path.md) | Conditional | Fast CI critical-path optimization |
| [CI 9](ci-09-real-anki-e2e-efficiency.md) | Conditional | real-Anki E2E efficiency |
| [CI 10](ci-10-reliability-and-flake-governance.md) | Conditional | failure/flake governance |
| [CI 11](ci-11-release-reproducibility.md) | Conditional | reproducible release evidence |
| [CI 12](ci-12-scale-and-delivery-operations.md) | Deferred / conditional | contributor/runner scale only when needed |

## Current invariant

```text
cloud E2E environment: immutable GHCR digest only
manual package source: exact Fast CI artifact
release package source: exact release artifact
local Docker build: development/diagnostic fallback
cloud BuildKit/GHA cache: removed
```

## Activation

`CI 7` is a measurement gate, not automatic permission to change caches, runners, retries, splitting or coverage.

```text
CI 7 measurement
├─ Fast CI bottleneck       → consider CI 8
├─ real-Anki/E2E bottleneck → consider CI 9
├─ repeated flake/failures  → consider CI 10
└─ no material problem      → defer
```

Choose at most one optimization candidate with a baseline, expected benefit, cost, risk and stop condition. `CI 11` may activate independently after release contracts stabilize. `CI 12` requires actual contributor/volume pressure and a security model.

## Shared rules

- use ordinary run history before creating controlled runs;
- separate scopes, direct savings and observational deltas;
- track p50/p95, first-run pass rate, minutes and artifact footprint;
- do not repeat a successful same-SHA gate without a relevant contract change;
- a new cache/runner/retry/split must beat its setup and maintenance cost;
- never trade away Anki Desktop, exact identity, sanitizer/token/media/action/APKG or release gates.

This track remains independent from [Core](../core/README.md), [Gamification](../gamification/README.md), [Operations](../operations/README.md), [Identity](../identity/README.md) and [Extensions](../extensions/README.md).
