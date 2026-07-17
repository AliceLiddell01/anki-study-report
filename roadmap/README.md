# Roadmap Anki Study Report

Снимок: **2026-07-17**.

Эта область — единая карта уже выполненных и будущих продуктовых и платформенных этапов. Она не заменяет production code, tests или профильные документы из `docs/`: при конфликте фактический код и тесты имеют приоритет.

## Текущее положение

Основной продуктовый контур завершён до **Stage 9.5** включительно:

- Navigation / IA, Settings Hub, Profile, Activity, Decks, Statistics и FSRS;
- native Search и безопасные действия;
- product notices, opt-in telemetry и Cloudflare ingestion;
- локальные Signals, Notification Center и управляемые in-app toasts.

Следующий основной продуктовый этап — **Stage 10: Cards v2 / Problem Triage**.

Параллельный платформенный CI/E2E-контур завершён до **CI Stage 6B**: cloud real-Anki E2E permanently использует exact digest-pinned GHCR environment, а локальная Docker build path остаётся development/diagnostic fallback. Следующие CI-изменения относятся к условному Stage 7 и требуют новых измерений; они не смешиваются с Cards v2.

## Статусы

- **Complete** — реализовано и принято; roadmap фиксирует итоговый scope.
- **Next** — рекомендуемый следующий продуктовый этап.
- **Planned** — согласованное направление после обязательных зависимостей.
- **Conditional** — выполняется только при подтверждённой необходимости или измеримом пробеле.
- **Unscheduled** — идея не получила номера и не должна появляться placeholder-функцией.

## Продуктовый roadmap

| Этап | Статус | Результат / цель |
| --- | --- | --- |
| [Stage 0](product/00-foundation-and-legacy-cleanup.md) | Complete | Архитектурная основа, security boundaries и завершённый legacy cleanup |
| [Stage 1](product/01-navigation-and-information-architecture.md) | Complete | Учебная IA, avatar menu и разделение продукта/настроек/диагностики |
| [Stage 2](product/02-settings-hub.md) | Complete | Canonical Settings Hub и typed persistence/actions |
| [Stage 3](product/03-profile-mvp.md) | Complete | Локальный all-collection Profile MVP |
| [Stage 4](product/04-activity-calendar-v2.md) | Complete | Activity / Calendar v2 и day details/feed |
| [Stage 5](product/05-decks-v2.md) | Complete | Decks v2 master-detail hierarchy и health model |
| [Stage 5.5](product/05-5-ui-polish-and-global-controls.md) | Complete | Global theme/language controls и presentation polish |
| [Stage 6](product/06-statistics-v1.md) | Complete | Statistics v1, bounded query API и canonical metrics |
| [Stage 7](product/07-fsrs-and-localization.md) | Complete | Read-only FSRS analytics, visual closure и localization cleanup |
| [Stage 8](product/08-search-and-safe-actions.md) | Complete | Native query foundation, Search v1 и undoable safe actions |
| [Stage 9](product/09-notices-telemetry-signals-notifications.md) | Complete | Notices/consent, telemetry, Signals, Center и toast delivery |
| [Stage 10](product/10-cards-v2-problem-triage.md) | **Next** | Problem-triage workspace поверх Search, Actions и Signals |
| [Stage 10.5](product/10-5-core-1-0-hardening.md) | Planned | API/schema freeze, migration/recovery, performance, accessibility и release hardening |
| [Stage 11](product/11-contextual-analytics-v1-1.md) | Conditional | Только доказанные contextual analytics gaps после Cards v2 |
| [Stage 12](product/12-extension-pack-foundation.md) | Planned | Минимальные безопасные extension points и first-party reference pack |
| [Stage 13](product/13-analytics-pack.md) | Planned | First-party Analytics Pack поверх Stage 12 |

### Ненумерованные будущие концепты

- [Identity continuity and optional account linking](product/unscheduled-identity-continuity.md) — добровольная continuity между установками через recovery/account flow, с раздельными `installation_id` и `person_id`; IP, MAC и hardware fingerprinting явно исключены. Концепт остаётся Unscheduled до появления подтверждённого cross-device/recovery сценария.
- [Telemetry Admin Analytics Dashboard](product/unscheduled-telemetry-admin-analytics-dashboard.md) — отдельный защищённый read-only web-dashboard поверх production D1: человекочитаемая инфографика, автоматическое обновление, health/privacy/retention diagnostics и Cloudflare Access без admin secrets в локальном add-on.

Подробный индекс: [roadmap/product/README.md](product/README.md).

## Платформенный roadmap

Платформенные CI/CD/E2E этапы не перенумеровывают продуктовые Stage 0–13 и не являются пользовательскими функциями.

- [Индекс платформенных этапов](platform/README.md)
- [CI Stage 1 — gated delivery baseline](platform/ci-01-gated-delivery-baseline.md)
- [CI Stage 2 — exact Fast package producer](platform/ci-02-exact-fast-package.md)
- [CI Stage 3 — exact-package E2E handoff](platform/ci-03-exact-package-e2e-handoff.md)
- [CI Stage 4 — package reuse measurement](platform/ci-04-package-reuse-measurement.md)
- [CI Stage 5 — stable GHCR environment image](platform/ci-05-ghcr-environment-image.md)
- [CI Stage 5A/5B — Fast CI observability and dedup](platform/ci-05a-05b-fast-ci-observability.md)
- [CI Stage 6 — GHCR consumer validation and permanent cloud cutover](platform/ci-06-ghcr-consumer-cutover.md)
- [CI Stage 7 — post-cutover optimization](platform/ci-07-post-cutover-optimization.md)

## Где лежит другая информация

```text
docs/       актуальные архитектурные, API, UX, security и operational contracts
roadmap/    последовательность, зависимости и planned/completed scope
reports/    исторические handoff, audits, measurements и closeout evidence
```

- [Индекс документации](../docs/README.md)
- [Индекс исторических отчётов](../reports/README.md)
- [Decision log](../docs/decision-log.md)
- [AI handoff](../docs/ai-handoff.md)

## Правила изменения roadmap

1. Не объявлять этап Complete только по плану или локальному отчёту: нужны production code/tests и принятые gates.
2. Не добавлять route, setting, integration или DLC placeholder до реализации соответствующего workflow.
3. При изменении публичного payload синхронно обновлять backend, frontend validators/types, tests и docs.
4. Новый этап должен иметь цель, зависимости, scope, out of scope, completion criteria и verification policy.
5. Historical evidence не возвращается в `docs/`; оно добавляется в `reports/` и связывается из stage-файла.
6. CI/CD уже существует. Stage 10.5 его harden-ит, но не проектирует заново.
