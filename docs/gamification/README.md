# Gamification research documentation

## Status

`COMPLETE_CURRENT_EVIDENCE_REPRODUCED_WITH_OPEN_GAP`

The canonical Gamification branch contains selectively recovered Review XP
specifications and an isolated historical research package. Recovery in G0.4
establishes provenance and content placement only. It does not establish
executability, reproduced evidence, formula correctness or production readiness.

## Purpose

This directory is the current documentation entry point for the Gamification
research track. It separates current Review candidates, historical reports,
deferred domains and future verification gates.

## Canonical branch and frozen provenance

- canonical branch: `gamification`;
- frozen historical source: `48298d02c6871df0ffa112d862d9b2af629c523f`;
- historical branch: `chatgpt/gamification-concept-foundation`, read-only;
- recovery manifest:
  [`../../roadmap/gamification/g0-historical-asset-manifest.md`](../../roadmap/gamification/g0-historical-asset-manifest.md);
- recovery ledger:
  [`../../roadmap/gamification/g0-recovery-ledger.md`](../../roadmap/gamification/g0-recovery-ledger.md).

## Current Review candidates

- [Review event taxonomy](anki-review-event-taxonomy.md)
- [Review reward model](anki-review-reward-model.md)
- [Review abuse model](anki-review-abuse-model.md)
- [Review session and Anki-day aggregation](anki-review-session-and-day.md)
- [Review simulation specification](anki-review-simulation-spec.md)

These documents are recovered research candidates. Their provenance headers
qualify historical status and execution. G0.4 changed no reward semantics.

## G1 diagnostic protocol

`G1: IN_PROGRESS`  
`G1.1: COMPLETE`  
`G1.2: NEXT`

- [Review XP cross-horizon cycling problem](review-xp-cycling-problem.md)
- [G1.1 problem and gate freeze](../../roadmap/gamification/g1-problem-gate-freeze.md)
- [Machine-readable diagnostic contract](../../research/gamification-sim/contracts/review-cycling-diagnostic-v1.json)
- [Diagnostic contract schema](../../research/gamification-sim/schemas/review-cycling-diagnostic-v1.schema.json)

G1.1 froze the observed problem and analysis contract before new diagnostics.
It changed no reward semantics and implemented no tracing.

## Recovered package

The isolated package is documented in
[`../../research/gamification-sim/README.md`](../../research/gamification-sim/README.md).
Source, tests, scenarios, fixtures, schemas, configs, contracts and the Rust
oracle are recovered. G0.5 established a Windows AMD64 / CPython 3.11 and exact
Rust 1.97.1 environment baseline, documented in
[`../../research/gamification-sim/environment/README.md`](../../research/gamification-sim/environment/README.md).
G0.6 verified the functional baseline. G0.7 reproduced the canonical current evidence on Windows AMD64, independently verified the raw artifact and reconciled the historical and Linux supporting claims.

## Historical evidence

Historical reports are archived under
[`../../reports/gamification/historical-source/`](../../reports/gamification/historical-source/).
They are chronology and provenance, not current reproduced evidence. The later
calibration correction has precedence over conflicting COMPLETE-era claims.

## Deferred domains

- Learn XP: not started.
- Create XP: not started.
- Global conversion, levels, streak, Momentum and cross-domain economy:
  deferred to G4.
- `progression-foundation.md` was intentionally not imported in G0.4.

## Evidence and execution status

`CURRENT_EVIDENCE_REPRODUCED`

The normalized canonical record is
[`../../research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json`](../../research/gamification-sim/evidence/g0.7-windows-amd64-py311-rust-1.97.1.json).
The raw artifact remains in GitHub Actions and passed independent integrity
verification.

## Open cross-horizon cycling gap

The 90→365-day retention-cycling growth issue remains open. `R-CURRENT` is a
regression reference, not an approved production candidate.

## G0.5–G0.7 gates

1. G0.5 — Complete: Windows AMD64 / CPython 3.11.9, hash-locked offline replay and exact Rust toolchain; declarations unchanged.
2. G0.6 — Complete: installed package, CLI, full tests, deterministic corpus, Rust parity and FSRS reference verified.
3. G0.7 — Complete: canonical current evidence reproduced and reconciled.

G1 is In Progress. G1.1 froze the problem and diagnostic contract; G1.2 root-cause attribution is Next.

## Production integration boundary

No production add-on, dashboard, payload, API, workflow, package or release
integration is approved. Research assets remain outside Fast CI and
`.ankiaddon` contents.

## Document precedence

```text
current production code/tests
→ current repository contracts and Gamification roadmap
→ recovered Review candidate specifications
→ reproduced G0.7 evidence
→ historical reports
→ superseded/deferred source material
```
