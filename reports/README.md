# Исторические отчёты и подтверждения

Эта папка хранит снимки состояния, передачи контекста, аудиты, измерения, инвентаризации и подтверждения завершения. Эти файлы полезны для воспроизводимости решений, но **не являются источником истины для текущего production-поведения**.

При противоречиях используется следующий приоритет:

```text
актуальные production-код и тесты
→ актуальные docs/
→ roadmap/
→ reports/
→ старые планы и предположения
```

## Отчёты Core

- [C1.0 — исходное состояние ветки Core](core/c1-0-baseline.md);
- [C1.5 — историческое рабочее пространство Cards](core/c1-5-cards-workspace.md);
- [C1.5R — основной отчёт о выполнении](core/c1-5r-main-execution-report.md);
- [C1.5R — исправление UX Cards и Inspection Profiles](core/c1-5r-cards-profiles-ux-remediation.md);
- [C1.5R.0 — восстановление и исходное состояние](core/c1-5r-0-recovery-baseline.md);
- [C1.5R.1 — каноническая идентичность отображения](core/c1-5r-1-canonical-card-display-identity.md);
- [C1.5R.2 — декларативный runtime компактного форматтера](core/c1-5r-2-declarative-compact-formatter-runtime.md);
- [C1.5R.3 — семантика предпросмотра лицевой и обратной стороны](core/c1-5r-3-front-back-preview-semantics.md);
- [C1.5R.4 — независимые источники кандидатов Triage](core/c1-5r-4-independent-triage-candidate-sources.md);
- [C1.5R.5 — переработка очереди Cards](core/c1-5r-5-cards-attention-inbox-redesign.md);
- [C1.5R.6 — пошаговая настройка Inspection Profiles](core/c1-5r-6-guided-inspection-profiles-ux.md);
- [C1.5R.7 — комплексная приёмка](core/c1-5r-7-integrated-acceptance-closeout.md);
- [C1.6 — канонический цикл решения проблемы одной карточки](core/c1-6-canonical-single-card-resolution-loop.md).

## Отчёты продуктовых этапов

- [Передача контекста после удаления legacy](product/legacy-cleanup-handoff.md);
- [Stage 7.5 — визуальная поставка FSRS](product/stage-7-5-fsrs-visual-delivery-report.md);
- [Stage 7.6 — финальная проверка FSRS](product/stage-7-6-fsrs-final-pass-report.md);
- [Stage 9 — основа телеметрии](product/stage-9-telemetry-foundation-handoff.md);
- [Stage 9.0.1 — надёжность телеметрии](product/stage-9-0-1-telemetry-reliability-handoff.md);
- [Stage 9.3–9.5 — передача контекста](product/stage-9-3-to-9-5-handoff.md).

## Отчёты CI

- [Исходные измерения оптимизации CI](ci/ci-optimization-baseline.md);
- [Stage 4 — повторное использование пакета](ci/ci-optimization-stage-4-package-reuse.md);
- [Stage 5A — измерения Fast CI](ci/ci-optimization-stage-5a-fast-ci-timing.md);
- [Stage 5B — устранение повторного typecheck](ci/ci-optimization-stage-5b-typecheck-dedup.md);
- [Stage 5 — завершение публикации GHCR](ci/ci-optimization-stage-5-ghcr-publication-closeout.md);
- [Stage 6A — проверка потребителя GHCR](ci/ci-optimization-stage-6a-ghcr-consumer-validation.md);
- [Stage 6B — переход cloud E2E на GHCR](ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md).

## Аудиты

- [Аудит alias карточки](audits/card-alias-audit.md);
- [Инвентаризация удаления legacy](audits/legacy-cleanup-inventory.md);
- [Исправление результатов code scanning от 2026-07-13](audits/code-scanning-remediation-2026-07-13.md);
- [Готовность публичного репозитория](audits/public-repository-readiness.md).

## Исследовательские инвентаризации

- [Инвентаризация справочных материалов FSRS](research/fsrs-helper-reference-inventory.md);
- [Инвентаризация референсов Statistics](research/statistics-reference-inventory.md).

Новые отчёты не добавляются в `docs/`. Они должны указывать дату и scope, проверенный SHA или идентичность запуска и честный список того, что не проверялось.
