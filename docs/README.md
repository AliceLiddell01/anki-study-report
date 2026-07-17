# Documentation index

`docs/` содержит только актуальные архитектурные, API, UX, security, configuration, testing и operational contracts проекта.

## Границы папок

```text
docs/       текущее устройство и обязательные контракты
roadmap/    завершённые/будущие этапы и их зависимости
reports/    исторические отчёты, audits, measurements и handoff
```

Historical report не должен оставаться в `docs/` только потому, что на него есть старая ссылка. При переносе ссылка обновляется на `reports/`, а current behavior описывается профильным документом.

## Основные входы

- [Project overview](project-overview.md)
- [Architecture](architecture.md)
- [Dashboard API](dashboard-api.md)
- [Frontend map](frontend-map.md)
- [Navigation / IA](navigation-ia.md)
- [Settings Hub](settings-hub.md)
- [Security and safety](security-and-safety.md)
- [Test matrix](test-matrix.md)
- [Verification policy](verification-run-policy.md)
- [CI/CD](ci-cd.md)
- [GHCR E2E consumer](ghcr-e2e-consumer.md)
- [Packaging and release](packaging-release.md)
- [Decision log](decision-log.md)
- [AI handoff](ai-handoff.md)

Product-specific contracts перечислены в корневом `README.md` и соответствующих файлах `roadmap/product/`.
