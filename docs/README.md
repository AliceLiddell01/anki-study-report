# Индекс документации

Каталог `docs/` содержит актуальные контракты архитектуры, API, UX, безопасности, конфигурации, тестирования и эксплуатации.

## Границы каталогов

```text
docs/       актуальное поведение и обязательные контракты
roadmap/    состояние треков, зависимости и критерии активации и завершения
reports/    исторические аудиты, измерения и итоговые подтверждения
```

Будущее развитие разделено на несколько треков. Компактная карта находится в [`roadmap/README.md`](../roadmap/README.md):

- [Core](../roadmap/core/README.md);
- [Геймификация](../roadmap/gamification/README.md);
- [Эксплуатация телеметрии](../roadmap/operations/README.md);
- [Непрерывность идентификации](../roadmap/identity/README.md);
- [Экосистема расширений](../roadmap/extensions/README.md);
- [Платформа и CI](../roadmap/platform/README.md).

Исследования геймификации, административные инструменты телеметрии, необязательная идентификация и пакеты расширений не становятся актуальными production-контрактами только потому, что присутствуют в roadmap.

## Основные актуальные контракты

### Обзор и архитектура

- [Обзор проекта](project-overview.md);
- [Архитектура](architecture.md);
- [Dashboard API](dashboard-api.md);
- [Карта frontend](frontend-map.md);
- [Навигация и информационная архитектура](navigation-ia.md).

### Core: Cards и Inspection Profiles

- [Продуктовый контракт Cards v2](cards-v2-product-contract.md);
- [API чтения Triage для Cards v2](cards-v2-triage-read-api.md);
- [Канонический цикл решения проблемы одной карточки](cards-v2-resolution-loop.md);
- [Очередь карточек, требующих внимания](cards-attention-inbox.md);
- [Исторический UI рабочего пространства C1.5](cards-v2-workspace-ui.md);
- [Идентичность отображения карточки](card-display-identity.md);
- [Декларативный форматтер отображения v1](card-display-formatter-v1.md);
- [Семантика предпросмотра карточки](card-preview-semantics.md);
- [Источники кандидатов Triage v4](triage-candidate-sources-v4.md);
- [Inspection Profiles v1](inspection-profiles-v1.md);
- [UI настроек Inspection Profiles](inspection-profiles-ui.md);
- [Пошаговая настройка Inspection Profiles](guided-inspection-profiles.md).

### Остальные актуальные продуктовые контракты

- [Центр настроек](settings-hub.md);
- [Статистика](statistics-v1.md);
- [Аналитика FSRS](fsrs-analytics.md);
- [Поиск и Safe Actions](search-v1-and-safe-actions.md);
- [Сигналы](signals-foundation.md);
- [Центр уведомлений](notification-center.md);
- [Конфиденциальность и телеметрия](privacy-telemetry.md).

### Безопасность, тестирование и поставка

- [Безопасность и модель защиты](security-and-safety.md);
- [Матрица тестирования](test-matrix.md);
- [Политика проверочных запусков](verification-run-policy.md);
- [CI/CD](ci-cd.md);
- [Потребитель GHCR-образа для E2E](ghcr-e2e-consumer.md);
- [Сборка пакета и выпуск](packaging-release.md);
- [Журнал решений](decision-log.md).

### Контекст для агентов

- [Передача контекста ИИ](ai-handoff.md);
- [Режимы работы ChatGPT и Codex](ai-work-modes.md);
- [Режим ChatGPT](chatgpt-work-mode.md);
- [Режим Codex](codex-agent-rules.md);
- [Локальное WSL-окружение Codex](codex-local-environment.md).

Исторические подтверждения должны находиться в [`reports/`](../reports/README.md), а не в `docs/`.

## Текущий статус Core

```text
C1.5R.0–R.7 — завершено; принято владельцем
C1.6 — завершено; принято владельцем; влито в core
C1.6B — условный этап; не начат
Core C1 — завершён
C2 — следующий этап; не начат
```

## Контракты C1.5R и C1.6

### Семантика предпросмотра C1.5R.3

См. [`card-preview-semantics.md`](card-preview-semantics.md). Полный предпросмотр использует нативные лицевую и обратную стороны reviewer: Inspector показывает лицевую сторону, расширенный диалог — обратную, а компактная идентичность остаётся неизменной.

### Независимые источники кандидатов C1.5R.4

См. [`triage-candidate-sources-v4.md`](triage-candidate-sources-v4.md). Triage v4 разделяет кандидатов по учебной активности за ограниченный период и кандидатов по текущему содержимому.

### Очередь карточек, требующих внимания, C1.5R.5

См. [`cards-attention-inbox.md`](cards-attention-inbox.md). Отклонённая таблица заменена семантическим списком, построенным вокруг идентичности карточки, широким Inspector, немодальной выдвижной панелью, явным периодом обучения и ручным ограниченным продолжением проверки текущего содержимого.

### Пошаговая настройка Inspection Profiles C1.5R.6

См. [`guided-inspection-profiles.md`](guided-inspection-profiles.md). Для ненастроенного типа заметки сразу создаётся чистый несохранённый черновик; обычный путь проходит через Basic, а строгий редактор v1 находится в Advanced.

### Цикл решения проблемы одной карточки C1.6

См. [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md). Успешный Safe Action или Open in Anki переводит элемент в состояние Awaiting recheck, после чего каноническая перепроверка конкретной карточки выполняет fail-closed-сопоставление стабильных причин.
