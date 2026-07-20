# Roadmap Anki Study Report

Снимок: **2026-07-21**.

Roadmap contains one mandatory Core path and independent or conditional tracks. Production code/tests and current contracts outrank roadmap and historical reports.

## Current map

| Track | Role | Current status | Does not block |
| --- | --- | --- | --- |
| [Core `C`](core/README.md) | mandatory add-on path | `C1` Next | — |
| [Gamification `G`](gamification/README.md) | parallel research → optional product | `G0 Complete`; `G1 In Progress`; `G1.3 Complete`; G1.4 protocol `Ready`; execution `Blocked on implementation`; production not approved | C1, C2 |
| [Operations `O`](operations/README.md) | protected telemetry admin tooling | `O1` Planned | C1, C2 |
| [Identity `I`](identity/README.md) | optional continuity gate | `I1` Conditional | telemetry, C1, C2, local gamification |
| [Extensions `E`](extensions/README.md) | first-party extension discovery | `E1` Conditional | core release/maturity |
| [Platform `CI`](platform/README.md) | CI/CD/E2E/release | CI 6B Complete; future measured | all product tracks |

## Mandatory Core path

```text
Completed Stage 0–9.5
→ C1 Cards v2 / Problem Triage
→ C2 Core 1.0 Hardening
→ C3? only for a demonstrated gap
```

Gamification, accounts, telemetry administration and extensions do not block Core.

## Gamification state

```text
G0 Complete
G1 In Progress
G1.3 Complete
G1.4 protocol readiness: READY
G1.4 execution readiness: BLOCKED_ON_IMPLEMENTATION
G1.4 started: No
candidate selected: No
production not approved
```

Do not collapse the two readiness states into an ambiguous `G1.4 Ready`.

## Track dependencies

```text
G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7?/G8?
C1 → C2 independently
O1 independent after telemetry query/auth contracts
I1 only after a proven continuity requirement
E1 only with a concrete pack and stable contracts
```

Historical Stage 0–9.5 files remain under [roadmap/product/](product/README.md). Previous future-stage compatibility pointers remain valid.

## Status vocabulary

- **Complete** — accepted implementation/evidence exists.
- **Next** — recommended next stage inside its track.
- **Planned** — sequenced after explicit dependencies.
- **Conditional** — activates only when named evidence/trigger exists.
- **Blocked** — dependency, implementation or research gap prevents execution.
- **Research-only** — not production-ready and not included in package/CI.

## Boundaries

1. Payload/public behavior changes stay synchronized across backend, frontend types, tests and docs.
2. Parallel work does not become a Core blocker without a documented dependency.
3. No placeholder route, setting, account, pack or gamification UI before its implementation stage.
4. Research candidates are not production economies.
5. Historical evidence remains in `reports/`; generated/runtime artifacts never enter git.
6. Verification follows [test matrix](../docs/test-matrix.md) and [run policy](../docs/verification-run-policy.md).
