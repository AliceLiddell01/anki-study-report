# Product roadmap index

Продуктовая последовательность описывает пользовательские и core-runtime этапы. Платформенные CI/E2E изменения ведутся отдельно в `roadmap/platform/`.

## Завершённая линия

```text
Stage 0   Foundation / Legacy Cleanup
Stage 1   Navigation / IA
Stage 2   Settings Hub
Stage 3   Profile MVP
Stage 4   Activity / Calendar v2
Stage 5   Decks v2
Stage 5.5 UI Polish & Global Controls
Stage 6   Statistics v1
Stage 7   FSRS Analytics & Localization Closure
Stage 8   Search Query / Search v1 / Safe Actions
Stage 9   Notices / Telemetry / Signals / Notifications
```

## Следующая линия

```text
Stage 10   Cards v2 / Problem Triage
Stage 10.5 Core 1.0 Hardening
Stage 11   Contextual Analytics v1.1
Stage 12   Extension Pack Foundation
Stage 13   Analytics Pack
```

## Ненумерованные будущие концепты

- [Identity continuity and optional account linking](unscheduled-identity-continuity.md) — отдельная opt-in модель `installation_id` / `person_id`, recovery и multi-device continuity без IP/MAC/hardware fingerprinting. Получает номер Stage только после подтверждённой пользовательской необходимости.
- [Telemetry Admin Analytics Dashboard](unscheduled-telemetry-admin-analytics-dashboard.md) — защищённый read-only web-dashboard поверх telemetry D1 с автоматическим обновлением, инфографикой, performance/error breakdowns, privacy/retention/deletion status и server-side Cloudflare Access. Не встраивается в локальный add-on и не получает номер Stage до стабилизации telemetry backend и появления регулярной operational необходимости.

Каждый stage-файл фиксирует разницу между первоначальным планом и фактическим результатом. Canonical implementation details остаются в `docs/`.
