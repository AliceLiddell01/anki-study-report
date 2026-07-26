# Индекс документации

`docs/` содержит **актуальные контракты** проекта. Текущие планы находятся в `roadmap/`, а исторические аудиты, измерения и closeout — в `reports/`.

```text
docs/       текущее поведение, архитектура и обязательные правила
roadmap/    будущие этапы, зависимости и criteria
reports/    исторические evidence и завершённые проверки
```

## Начать отсюда

- [Обзор проекта](project-overview.md)
- [Архитектура](architecture.md)
- [Передача актуального контекста ИИ](ai-handoff.md)
- [Карта roadmap](../roadmap/README.md)
- [Исторические отчёты](../reports/README.md)

## Product и UX

- [Навигация и информационная архитектура](navigation-ia.md)
- [UI prototyping и visual acceptance](ui-prototype-visual-acceptance.md)
- [Settings Hub](settings-hub.md)
- [Statistics v1](statistics-v1.md)
- [FSRS analytics](fsrs-analytics.md)
- [Search и Safe Actions](search-v1-and-safe-actions.md)
- [Signals foundation](signals-foundation.md)
- [Notification center](notification-center.md)
- [Privacy и telemetry](privacy-telemetry.md)

### Cards и Inspection Profiles

- [Cards v2 product contract](cards-v2-product-contract.md)
- [Triage read API](cards-v2-triage-read-api.md)
- [Canonical single-card resolution loop](cards-v2-resolution-loop.md)
- [Cards attention inbox](cards-attention-inbox.md)
- [Card display identity](card-display-identity.md)
- [Declarative formatter v1](card-display-formatter-v1.md)
- [Card preview semantics](card-preview-semantics.md)
- [Triage candidate sources v4](triage-candidate-sources-v4.md)
- [Inspection Profiles v1](inspection-profiles-v1.md)
- [Inspection Profiles UI](inspection-profiles-ui.md)
- [Guided Inspection Profiles](guided-inspection-profiles.md)

Исторический C1.5 UI сохранён отдельно: [Cards workspace UI](cards-v2-workspace-ui.md).

## Gamification research

- [Индекс Gamification research](gamification/README.md)
- [Learn XP problem contract](gamification/learn-xp-problem-contract.md)
- [Review XP candidate protocol](gamification/review-xp-candidate-protocol.md)
- [Review XP confirmatory protocol](gamification/review-xp-confirmatory-protocol.md)

Gamification contracts являются research-only и не разрешают production integration.

## Architecture и API

- [Dashboard API](dashboard-api.md)
- [Frontend map](frontend-map.md)
- [Configuration reference](config-reference.md)
- [Fixtures и test data](fixtures-and-test-data.md)
- [Decision log](decision-log.md)

## Security, testing и delivery

- [Security and safety](security-and-safety.md)
- [Test matrix](test-matrix.md)
- [Verification run policy](verification-run-policy.md)
- [CI/CD](ci-cd.md)
- [Docker real-Anki E2E](docker-e2e.md)
- [Run-event protocol](run-event-protocol.md)
- [Failure diagnostics](failure-diagnostics.md)
- [Preflight и cancellation](e2e-preflight-cancellation.md)
- [Fast CI package / E2E harness reuse](e2e-package-harness-reuse.md)
- [Идентичность нерелизной сборки](non-release-build-identity.md)
- [Каноническая итоговая сводка E2E и bounded history](e2e-final-summary-history.md)
- [GHCR E2E consumer](ghcr-e2e-consumer.md)
- [Packaging и release](packaging-release.md)

## Работа ИИ-агентов

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [ChatGPT manual operations](chatgpt-manual-operations.md)
- [Codex agent rules](codex-agent-rules.md)
- [Codex local WSL environment](codex-local-environment.md)

`ai-handoff.md` хранит только текущий срез. Подробные run IDs, SHA и результаты завершённых этапов должны оставаться в `reports/`, а не дублироваться в этом индексе.
