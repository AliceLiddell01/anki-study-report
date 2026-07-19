# Roadmap Anki Study Report

Snapshot: **2026-07-19**.

The roadmap has one mandatory core path and several independent or conditional
tracks. A larger stage number does not create a global queue across unrelated
tracks. Current production code/tests and current contracts outrank roadmap and
historical reports when they disagree.

## Current position

The accepted product contour through **Stage 9.5** remains complete:

```text
Foundation / IA / Settings / Profile / Activity / Decks
→ Statistics / FSRS / Localization
→ Search / Safe Actions
→ Notices / opt-in Telemetry / Signals / Notifications
```

The next mandatory add-on work remains inside Core:

```text
C1 Cards v2 / Problem Triage
  └─ C1.5R remediation is active
→ C2 Core 1.0 Hardening
→ C3 Contextual Additions, only for a proven gap
```

Current core status:

```text
C1.5 technical implementation evidence — retained historically
C1.5 owner product acceptance — withdrawn
C1.5R.0 Recovery and corrective baseline — Complete
C1.5R.1 Canonical card display identity — Complete
C1.5R.2 Declarative compact formatter runtime — Complete
C1.5R.3 Front/back preview semantics — Next, not started
C1.6 — Blocked, not started
Core C1 — In progress
```

See the [C1.5R.0 recovery report](../reports/core/c1-5r-0-recovery-baseline.md),
the [C1.5R.1 implementation report](../reports/core/c1-5r-1-canonical-card-display-identity.md),
and the [C1.5R.2 implementation report](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md).

Parallel tracks do not block `C1` or `C2`:

- `G` — Gamification research/product;
- `O` — Telemetry operations;
- `I` — Identity continuity, conditional;
- `E` — Extension ecosystem, deferred/conditional;
- `CI` — platform, delivery and real-Anki verification.

## Track map

| Track | Role | Current status | Does not block |
| --- | --- | --- | --- |
| [Core `C`](core/README.md) | only critical path for the add-on | `C1.5R.1–R.2` Complete; `C1.5R.3` Next; `C1.6` blocked | — |
| [Gamification `G`](gamification/README.md) | parallel research → optional product | `G0` Next; production not approved | C1, C2 |
| [Operations `O`](operations/README.md) | protected telemetry admin tooling | `O1` Planned | C1, C2 |
| [Identity `I`](identity/README.md) | optional continuity gate | `I1` Conditional | telemetry, C1, C2, local gamification |
| [Extensions `E`](extensions/README.md) | first-party extension discovery | `E1` Conditional | core release/maturity |
| [Platform `CI`](platform/README.md) | CI/CD/E2E/release | CI 6B Complete; future work measured | all product tracks |

## Dependency view

```text
Completed Stage 0–9.5
        │
        └──────────────→ C1 → C2 → C3?
                           │
                           ├─ C1.5R.2 is Complete; C1.5R.3 is Next, not started
                           ├─ all C1.5R stages must finish before C1.6
                           ├─ owner product acceptance is a separate C1.5R gate
                           └─ does not wait for G/O/I/E

G0 → G1 → G2 → G3 → G4 → G5 → G6 → G7?/G8?
                         │
                         └─ G5 may wait for stable C2 contracts

O1 may run independently after telemetry query/authorization contracts exist.
I1 activates only for a proven cross-installation requirement.
E1 starts only with a concrete reference pack and stable C2 contracts.
CI 7 measurement permits at most one justified CI 8/9/10 optimization.
```

## Completed product history

Historical Stage 0–9.5 files remain under
[`roadmap/product/`](product/README.md). They are not mass-renamed because their
accepted sequence and links remain useful.

C1.5's successful Fast CI and real-Anki runs are preserved in historical
reports. They are not reclassified as failures merely because the product
acceptance was later withdrawn.

## Old to new future mapping

| Previous placement | New placement |
| --- | --- |
| Stage 10 Cards v2 | `C1` Core track |
| Stage 10.5 Core 1.0 Hardening | `C2` Core track |
| Stage 11 Contextual Analytics | `C3` conditional contextual additions |
| Stage 12 Extension Foundation | `E1` discovery → `E2` minimal foundation |
| Stage 13 Analytics Pack | `E3` conditional |
| Unscheduled Telemetry Admin Dashboard | `O1` planned operational stage |
| Unscheduled Identity continuity | `I1` conditional gate |
| Gamification branch without main-roadmap placement | `G0–G8` parallel track |

Previous future-stage paths remain compatibility pointers.

## Status vocabulary

- **Complete** — the named increment's required result exists; product acceptance
  is explicit where it is a separate gate.
- **Implemented, focused verification pending** — the implementation candidate,
  synchronized contracts and focused tests exist, but required execution
  evidence has not yet passed.
- **Next** — recommended next stage inside its track.
- **Planned** — sequenced after explicit dependencies.
- **Conditional** — activates only when named evidence or trigger exists.
- **Blocked** — a dependency or acceptance gap prevents start.
- **Deferred** — intentionally outside the current planning horizon.
- **Research-only** — not production-ready and not included in package/CI.

## Folder boundaries

```text
docs/       current architecture/API/UX/security/operations contracts
roadmap/    tracks, stages, dependencies and activation criteria
reports/    historical handoff, audits, measurements and closeout evidence
```

- [Documentation index](../docs/README.md)
- [Historical reports](../reports/README.md)
- [Decision log](../docs/decision-log.md)
- [AI handoff](../docs/ai-handoff.md)

## Rules for roadmap changes

1. Production code/tests outrank roadmap claims.
2. Every stage states goal, status, dependencies, scope, out of scope,
   activation, and completion criteria.
3. Parallel work does not become a core blocker without a documented dependency.
4. No placeholder route, setting, account, pack, or gamification UI appears
   before its implementation stage.
5. Payload/public behavior changes remain synchronized across backend, frontend
   types, tests, and docs.
6. Research candidates are not production commitments.
7. Historical evidence remains under `reports/`; generated/runtime artifacts do
   not enter git.
8. Verification follows `docs/test-matrix.md` and
   `docs/verification-run-policy.md`; docs-only work does not justify Docker E2E.

## C1.5R.3 complete

Core C1 remains in progress. C1.5R.3 is complete; C1.5R.4 is next and not started; C1.6 remains blocked.
