# Индекс документации

Каталог `docs/` содержит актуальные контракты архитектуры, API, UX, безопасности, конфигурации, тестирования и эксплуатации.

## Границы каталогов

```text
docs/       актуальное поведение и обязательные контракты
roadmap/    состояние треков, зависимости и критерии активации/завершения
reports/    исторические аудиты, измерения и итоговые подтверждения
```

Будущее развитие разделено на независимые треки. Карта: [`roadmap/README.md`](../roadmap/README.md).

- [Core](../roadmap/core/README.md)
- [Геймификация](../roadmap/gamification/README.md)
- [Эксплуатация телеметрии](../roadmap/operations/README.md)
- [Непрерывность идентификации](../roadmap/identity/README.md)
- [Экосистема расширений](../roadmap/extensions/README.md)
- [Платформа и CI](../roadmap/platform/README.md)

Roadmap presence не превращает исследование или условный трек в production contract.

## Основные актуальные контракты

### Обзор и архитектура

- [Обзор проекта](project-overview.md)
- [Архитектура](architecture.md)
- [Dashboard API](dashboard-api.md)
- [Карта frontend](frontend-map.md)
- [Навигация и информационная архитектура](navigation-ia.md)

### UI foundation и визуальная приёмка

- [Процесс UI-прототипирования и визуальной приёмки](ui-prototype-visual-acceptance.md)

### Core: Cards и Inspection Profiles

- [Продуктовый контракт Cards v2](cards-v2-product-contract.md)
- [API чтения Triage для Cards v2](cards-v2-triage-read-api.md)
- [Канонический цикл решения проблемы одной карточки](cards-v2-resolution-loop.md)
- [Очередь карточек, требующих внимания](cards-attention-inbox.md)
- [Исторический UI рабочего пространства C1.5](cards-v2-workspace-ui.md)
- [Идентичность отображения карточки](card-display-identity.md)
- [Декларативный форматтер отображения v1](card-display-formatter-v1.md)
- [Семантика предпросмотра карточки](card-preview-semantics.md)
- [Источники кандидатов Triage v4](triage-candidate-sources-v4.md)
- [Inspection Profiles v1](inspection-profiles-v1.md)
- [UI настроек Inspection Profiles](inspection-profiles-ui.md)
- [Пошаговая настройка Inspection Profiles](guided-inspection-profiles.md)

### Остальные продуктовые контракты

- [Центр настроек](settings-hub.md)
- [Статистика](statistics-v1.md)
- [Аналитика FSRS](fsrs-analytics.md)
- [Поиск и Safe Actions](search-v1-and-safe-actions.md)
- [Сигналы](signals-foundation.md)
- [Центр уведомлений](notification-center.md)
- [Конфиденциальность и телеметрия](privacy-telemetry.md)

### Безопасность, тестирование и поставка

- [Безопасность и модель защиты](security-and-safety.md)
- [Матрица тестирования](test-matrix.md)
- [Политика проверочных запусков](verification-run-policy.md)
- [CI/CD](ci-cd.md)
- [Docker real-Anki E2E](docker-e2e.md)
- [Повторное использование Fast CI package при изменениях E2E harness](e2e-package-harness-reuse.md)
- [Потребитель GHCR-образа для E2E](ghcr-e2e-consumer.md)
- [Fixtures и тестовые данные](fixtures-and-test-data.md)
- [Справочник конфигурации](config-reference.md)
- [Сборка пакета и выпуск](packaging-release.md)
- [Журнал решений](decision-log.md)

### Контекст для агентов

- [Передача контекста ИИ](ai-handoff.md)
- [Режимы работы ChatGPT и Codex](ai-work-modes.md)
- [Режим ChatGPT](chatgpt-work-mode.md)
- [Режим Codex](codex-agent-rules.md)
- [Локальное WSL-окружение Codex](codex-local-environment.md)

Исторические подтверждения находятся в [`reports/`](../reports/README.md), а не в `docs/`.

## Текущий platform/E2E contract

```text
collection source: three committed real APKG
cloud environment: immutable GHCR digest
manual package source: exact successful Fast CI artifact
release package source: exact release artifact
package tested commit and E2E harness commit: separate identities
harness-only package reuse: fail-closed ancestry + complete-diff allowlist
```

Новый Fast CI не запускается только из-за allowlisted E2E harness change. Package-impacting diff требует новый exact package. Docs-only commit после успешных gates не требует повторного Fast CI/Docker без отдельной причины.

Исторический closeout: [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md).

## Текущий статус Core

```text
C1 — завершён
C2 implementation/integration — завершены и влиты в core
C2 owner acceptance — повторно открыта после ручной проверки
следующее действие — одна bounded post-C2 manual acceptance remediation
C3–C6 — обязательный будущий путь к Core 1.0
```

Точное состояние и ограничения смотрите в [`ai-handoff.md`](ai-handoff.md) и актуальном production-коде.
