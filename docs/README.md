# Индекс документации

Каталог `docs/` содержит актуальные контракты архитектуры, API, UX, безопасности, конфигурации, тестирования и эксплуатации.

## Границы каталогов

```text
docs/       актуальное поведение и обязательные контракты
roadmap/    положение треков, зависимости и критерии активации/завершения
reports/    исторические аудиты, измерения и closeout evidence
```

Будущее развитие разделено на несколько треков. Компактная карта находится в [`roadmap/README.md`](../roadmap/README.md):

- [Core](../roadmap/core/README.md);
- [Gamification](../roadmap/gamification/README.md);
- [Telemetry operations](../roadmap/operations/README.md);
- [Identity continuity](../roadmap/identity/README.md);
- [Extension ecosystem](../roadmap/extensions/README.md);
- [Platform / CI](../roadmap/platform/README.md).

Gamification research, telemetry admin tooling, optional identity и extension packs не становятся текущими production contracts только потому, что присутствуют в roadmap.

## Основные актуальные контракты

### Обзор и архитектура

- [Обзор проекта](project-overview.md);
- [Архитектура](architecture.md);
- [Dashboard API](dashboard-api.md);
- [Карта frontend](frontend-map.md);
- [Navigation / IA](navigation-ia.md).

### Core: Cards и Inspection Profiles

- [Продуктовый контракт Cards v2](cards-v2-product-contract.md);
- [API Cards v2 Triage](cards-v2-triage-read-api.md);
- [Канонический цикл решения одной карточки](cards-v2-resolution-loop.md);
- [Cards attention inbox](cards-attention-inbox.md);
- [Исторический UI C1.5](cards-v2-workspace-ui.md);
- [Display identity карточки](card-display-identity.md);
- [Formatter display identity v1](card-display-formatter-v1.md);
- [Семантика preview карточки](card-preview-semantics.md);
- [Источники кандидатов Triage v4](triage-candidate-sources-v4.md);
- [Inspection Profiles v1](inspection-profiles-v1.md);
- [UI настроек Inspection Profiles](inspection-profiles-ui.md);
- [Guided Inspection Profiles](guided-inspection-profiles.md).

### Остальные текущие продуктовые контракты

- [Settings Hub](settings-hub.md);
- [Statistics](statistics-v1.md);
- [FSRS analytics](fsrs-analytics.md);
- [Search и Safe Actions](search-v1-and-safe-actions.md);
- [Signals](signals-foundation.md);
- [Notification Center](notification-center.md);
- [Privacy / telemetry](privacy-telemetry.md).

### Безопасность, тестирование и поставка

- [Безопасность и safety model](security-and-safety.md);
- [Матрица тестирования](test-matrix.md);
- [Политика verification runs](verification-run-policy.md);
- [CI/CD](ci-cd.md);
- [GHCR E2E consumer](ghcr-e2e-consumer.md);
- [Packaging / release](packaging-release.md);
- [Decision log](decision-log.md).

### Контекст для агентов

- [AI handoff](ai-handoff.md);
- [Режимы ChatGPT и Codex](ai-work-modes.md);
- [Режим ChatGPT](chatgpt-work-mode.md);
- [Режим Codex](codex-agent-rules.md);
- [Локальное WSL-окружение Codex](codex-local-environment.md).

Historical evidence должно находиться в [`reports/`](../reports/README.md), а не в `docs/`.

## Текущий статус Core

```text
C1.5R.0–R.7 — Complete; owner accepted
C1.6 — Complete; owner accepted; merged into core
C1.6B — Conditional; not started
Core C1 — Complete
C2 — Next; not started
```

## Контракты C1.5R и C1.6

### Preview semantics C1.5R.3

См. [`card-preview-semantics.md`](card-preview-semantics.md). Full preview использует reviewer/native front и answer: Inspector показывает front, expanded dialog — answer, compact identity остаётся неизменной.

### Independent candidate sources C1.5R.4

См. [`triage-candidate-sources-v4.md`](triage-candidate-sources-v4.md). Triage v4 разделяет bounded period learning candidates и current-content candidates.

### Cards attention inbox C1.5R.5

См. [`cards-attention-inbox.md`](cards-attention-inbox.md). Отклонённая table заменена semantic identity-led list, wide Inspector, non-modal drawer, явным learning period и ручным bounded continuation current-content scan.

### Guided Inspection Profiles C1.5R.6

См. [`guided-inspection-profiles.md`](guided-inspection-profiles.md). Unconfigured note type сразу открывает clean generated draft; Basic является normal path, strict v1 editing находится в Advanced.

### Single-card resolution loop C1.6

См. [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md). Успешный Safe Action или Open in Anki переводит item в Awaiting recheck, после чего exact-card canonical recheck выполняет fail-closed reconciliation stable reasons.