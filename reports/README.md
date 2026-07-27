# Исторические отчёты и подтверждения

`reports/` хранит snapshots, audits, measurements и closeout evidence. Эти файлы не являются источником истины для текущего production-поведения.

```text
production code и tests
→ docs/
→ roadmap/
→ reports/
```

## Core

- [C1.0 baseline](core/c1-0-baseline.md)
- [C1.5 historical Cards workspace](core/c1-5-cards-workspace.md)
- [C1.5R main execution](core/c1-5r-main-execution-report.md)
- [C1.5R integrated acceptance](core/c1-5r-7-integrated-acceptance-closeout.md)
- [C1.6 single-card resolution loop](core/c1-6-canonical-single-card-resolution-loop.md)
- [C2 Core hardening](core/c2-core-hardening-ui-remediation.md)
- [C2 post-merge manual acceptance remediation — Stage 1](core/c2-manual-acceptance-remediation-closeout.md)
- [C2 Cards Prototype v3.2.3 production integration — Stage 2](core/c2-cards-v323-production-integration.md)
- [C2 Cards final AV/audio/media evidence closeout](core/c2-cards-final-av-media-evidence-closeout.md)
- [C2 Inspection Profiles corrected screenshot-first audit](core/c2-inspection-profiles-screenshot-audit.md)

Остальные C1.5R reports остаются в [`reports/core/`](core/).

## Product

- [Legacy cleanup handoff](product/legacy-cleanup-handoff.md)
- [FSRS visual delivery](product/stage-7-5-fsrs-visual-delivery-report.md)
- [FSRS final pass](product/stage-7-6-fsrs-final-pass-report.md)
- [Telemetry foundation](product/stage-9-telemetry-foundation-handoff.md)
- [Telemetry reliability](product/stage-9-0-1-telemetry-reliability-handoff.md)
- [Stage 9.3–9.5 handoff](product/stage-9-3-to-9-5-handoff.md)

## CI / E2E

- [CI optimization baseline](ci/ci-optimization-baseline.md)
- [Package reuse](ci/ci-optimization-stage-4-package-reuse.md)
- [Fast CI timing](ci/ci-optimization-stage-5a-fast-ci-timing.md)
- [Typecheck deduplication](ci/ci-optimization-stage-5b-typecheck-dedup.md)
- [GHCR publication](ci/ci-optimization-stage-5-ghcr-publication-closeout.md)
- [GHCR consumer validation](ci/ci-optimization-stage-6a-ghcr-consumer-validation.md)
- [GHCR cloud cutover](ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md)
- [Real-deck E2E foundation](ci/real-deck-e2e-foundation-closeout.md)
- [E2E-I1 run events](ci/e2e-i1-unified-live-run-protocol-closeout.md)
- [E2E-I2 browser progress](ci/e2e-i2-browser-smoke-progress-closeout.md)
- [E2E-I3 failure diagnostics](ci/e2e-i3-stable-failure-diagnostics-closeout.md)
- [E2E-I4 cancellation/preflight](ci/e2e-i4-cancellation-preflight-closeout.md)
- [E2E-I4 post-merge docs sync](ci/e2e-i4-post-merge-documentation-sync.md)
- [E2E-I5 — идентичность нерелизной сборки](ci/e2e-i5-non-release-build-identity-closeout.md)
- [E2E-I6 — каноническая итоговая сводка и bounded history](ci/e2e-i6-final-summary-history-closeout.md)
- [E2E-I6 post-merge documentation sync](ci/e2e-i6-post-merge-documentation-sync.md)
- [E2E-I6 bounded corrective fix](ci/e2e-i6-corrective-fix-closeout.md)

## Research

- [Gamification source audit — 2026-07-18](research/gamification-track-source-audit-2026-07-18.md)
- [FSRS helper reference inventory](research/fsrs-helper-reference-inventory.md)
- [Statistics reference inventory](research/statistics-reference-inventory.md)

## Audits

- [Card alias audit](audits/card-alias-audit.md)
- [Legacy cleanup inventory](audits/legacy-cleanup-inventory.md)
- [Code scanning remediation](audits/code-scanning-remediation-2026-07-13.md)
- [Public repository readiness](audits/public-repository-readiness.md)

## Правила

Новый report обязан указывать дату, scope, проверенные SHA/run identities, честный список непроверенного и ссылку на актуальный contract в `docs/`. Актуальные rules и behavior не переносятся из `docs/` в reports.
