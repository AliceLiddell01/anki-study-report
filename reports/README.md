# Historical reports and evidence

Эта папка хранит snapshots, handoff, audits, measurements, inventories и
closeout evidence. Эти файлы полезны для воспроизводимости решений, но **не
являются source of truth для текущего production behavior**.

При конфликте использовать приоритет:

```text
production code/tests
→ current docs/
→ roadmap/
→ reports/
→ old plans/assumptions
```

## Core reports

- [c1-0-baseline.md](core/c1-0-baseline.md)
- [c1-5-cards-workspace.md](core/c1-5-cards-workspace.md)
- [c1-5r-0-recovery-baseline.md](core/c1-5r-0-recovery-baseline.md)
- [c1-5r-1-canonical-card-display-identity.md](core/c1-5r-1-canonical-card-display-identity.md)
- [c1-5r-2-declarative-compact-formatter-runtime.md](core/c1-5r-2-declarative-compact-formatter-runtime.md)
- [c1-5r-3-front-back-preview-semantics.md](core/c1-5r-3-front-back-preview-semantics.md)
- [c1-5r-4-independent-triage-candidate-sources.md](core/c1-5r-4-independent-triage-candidate-sources.md)
- [c1-5r-5-cards-attention-inbox-redesign.md](core/c1-5r-5-cards-attention-inbox-redesign.md)
- [c1-5r-6-guided-inspection-profiles-ux.md](core/c1-5r-6-guided-inspection-profiles-ux.md)
- [c1-5r-main-execution-report.md](core/c1-5r-main-execution-report.md)
- [c1-5r-7-integrated-acceptance-closeout.md](core/c1-5r-7-integrated-acceptance-closeout.md)
- [c1-6-canonical-single-card-resolution-loop.md](core/c1-6-canonical-single-card-resolution-loop.md)

## Product reports

- [legacy-cleanup-handoff.md](product/legacy-cleanup-handoff.md)
- [stage-7-5-fsrs-visual-delivery-report.md](product/stage-7-5-fsrs-visual-delivery-report.md)
- [stage-7-6-fsrs-final-pass-report.md](product/stage-7-6-fsrs-final-pass-report.md)
- [stage-9-telemetry-foundation-handoff.md](product/stage-9-telemetry-foundation-handoff.md)
- [stage-9-0-1-telemetry-reliability-handoff.md](product/stage-9-0-1-telemetry-reliability-handoff.md)
- [stage-9-3-to-9-5-handoff.md](product/stage-9-3-to-9-5-handoff.md)

## CI reports

- [ci-optimization-baseline.md](ci/ci-optimization-baseline.md)
- [ci-optimization-stage-4-package-reuse.md](ci/ci-optimization-stage-4-package-reuse.md)
- [ci-optimization-stage-5a-fast-ci-timing.md](ci/ci-optimization-stage-5a-fast-ci-timing.md)
- [ci-optimization-stage-5b-typecheck-dedup.md](ci/ci-optimization-stage-5b-typecheck-dedup.md)
- [ci-optimization-stage-5-ghcr-publication-closeout.md](ci/ci-optimization-stage-5-ghcr-publication-closeout.md)
- [ci-optimization-stage-6a-ghcr-consumer-validation.md](ci/ci-optimization-stage-6a-ghcr-consumer-validation.md)
- [ci-optimization-stage-6b-ghcr-cloud-cutover.md](ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md)

## Audits

- [card-alias-audit.md](audits/card-alias-audit.md)
- [legacy-cleanup-inventory.md](audits/legacy-cleanup-inventory.md)
- [code-scanning-remediation-2026-07-13.md](audits/code-scanning-remediation-2026-07-13.md)
- [public-repository-readiness.md](audits/public-repository-readiness.md)

## Research inventories

- [fsrs-helper-reference-inventory.md](research/fsrs-helper-reference-inventory.md)
- [statistics-reference-inventory.md](research/statistics-reference-inventory.md)

Новые отчёты не добавляются в `docs/`. Они получают дату/scope, tested SHA/run
identity и честный список непроверенного.
