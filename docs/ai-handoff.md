# Передача контекста новому чату/нейронке

Снимок: **2026-07-21**.

## Начать отсюда

1. `README.md`
2. `roadmap/README.md`
3. `docs/project-overview.md`
4. `docs/architecture.md`
5. профильный current-contract документ
6. `reports/README.md` только для historical evidence

При конфликте:

```text
production code/tests
→ current docs
→ roadmap
→ current evidence
→ historical reports
→ old plans/assumptions
```

## Product state

Anki Study Report — local add-on for Anki 26.05+ with Python runtime, React/TypeScript dashboard and token-protected loopback server. Frontend does not access the collection directly. The accepted product contour is complete through Stage 9.5.

Future work is organized by independent tracks. Only `C1 Cards v2 → C2 Core 1.0` is the mandatory add-on path. Gamification, telemetry operations, identity and extensions do not block Core.

## Gamification

Canonical branch: `gamification`. It is independent and research-only; no `gamification → master` PR or production integration is approved.

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

G1.2a leaves the root cause partially localized with medium confidence. `memory_main` is the dominant component and `post_transition` the dominant window, but Challenge is not direction-consistent and no unique corrective formula is proven.

G1.3 freezes the [candidate protocol](gamification/review-xp-candidate-protocol.md), machine contract and strict schema. The next step is only `G1.4 — Bounded screening`. Before screening, implement the frozen post-transition MemoryGain mechanism and parameter registry without changing the protocol or viewing results. Gamification does not block Core.

## Technical invariants

1. Payload/public behavior changes synchronize backend, frontend types/validators, tests and docs.
2. Frontend never reads Anki collection directly.
3. Server remains loopback-only and token-protected.
4. Sanitizer, media validation, action allowlists and preview isolation are not weakened.
5. Generated assets/runtime artifacts/profile data/tokens are not committed.
6. Signals/evidence/entity refs stay local and outside telemetry taxonomy.
7. Telemetry/admin/identity/gamification data purposes remain separated.
8. Research packages do not silently enter Fast CI or `.ankiaddon`.
9. Release uses exact artifacts and never occurs automatically after merge.

## Verification

Use focused checks first and follow `docs/test-matrix.md` plus `docs/verification-run-policy.md`. Docs/contracts-only Gamification work does not justify Docker or real-Anki E2E. Before closing, verify branch/base/head, exact changed paths, relative links, no production/research source/test/config/evidence/workflow diff, and actual check evidence.
