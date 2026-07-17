# Stage 9 — Notices, Telemetry, Signals and Notifications

**Status:** Complete

## Старый план

Stage 9 изначально описывался только как **Signals v1**:

```text
stable domain codes
structured arguments
entity references
taxonomy
severity
evidence
deduplication
```

## Почему scope расширился

Перед пользовательскими signals потребовалось закрыть update-safe product communication, privacy choice, optional technical telemetry и диагностируемую delivery chain. Поэтому Stage 9 стал umbrella-этапом с явными подэтапами вместо скрытого смешивания нескольких систем.

## Фактически выполнено

### Stage 9.0 — Product Notice & Consent Foundation

- Update-safe per-profile notice/privacy state.
- Structured RU/EN changelog и What’s New.
- Accessible modal sequencing.
- Granular opt-in/decline и Privacy Settings.

### Stage 9.1 — Telemetry Client

- Python-only remote transport; React работает через token-protected loopback API.
- Bounded local SQLite queue, batch/idempotency/backoff.
- Per-purpose collection gate, withdrawal и authenticated deletion.
- Product User-Agent исправляет Cloudflare 1010 без отключения Browser Integrity Check.

### Stage 9.2 — Telemetry Service

- Отдельный private Cloudflare Worker repository.
- EU D1, strict allowlist, installation tokens, quotas, retention и deletion.
- R2 исключён из текущего бесплатного contract; recovery — D1 Time Travel и ephemeral export/import drill.
- Gated staging/production deployment и synthetic lifecycle.

### Stage 9.0.1 — Reliability corrective pass

- One-shot What’s New close.
- Language menu tooltip correction.
- Profile-safe timer binding.
- Persisted enrollment diagnostics/backoff и manual check/send.
- D1 abuse hardening и emergency switches.

### Stage 9.3 — Signals Foundation

- Per-profile `notifications.sqlite3`.
- Four bounded detector families: workload, retention, deck health, repeated Again.
- Stable codes, evidence schemas, severity, dedupe, escalation, resolution и reactivation.
- Signal data остаются локальными и не расширяют telemetry taxonomy.

### Stage 9.4 — Notification Center

- Bell + compact panel.
- Durable `#/notifications`, filters, pagination, read state и contextual navigation.
- Active/resolved независимо от read/unread.
- Release notifications reuse What’s New source.

### Stage 9.5 — Preferences & Toast Delivery

- `#/settings/notifications`.
- Per-profile badge/toast/category settings.
- One visible toast, bounded queue/summary, no-repeat marker.
- Polite warning toast и persistent critical alert без focus stealing, sound или OS notifications.

### Post-stage production correction — telemetry wire envelope

После Stage 9 production smoke выявил точное несовпадение client/Worker allowlist. Исправлено без расширения taxonomy:

- individual events содержат только Worker-accepted common/event fields;
- telemetry, consent и privacy versions остаются в enrollment/batch envelopes, а не дублируются в каждом event;
- прямой wire-contract test фиксирует enrollment, batch root и event keys;
- manual smoke failure evidence ограничено allowlisted `failureStage`/`failureCode` и не публикует endpoint, request body, traceback или arbitrary exception text.

## Отличие от плана

Signals v1 не был отменён; он стал подэтапом 9.3 после создания необходимых user-control и operational foundations. Stage 9 завершился локальным notification workflow, но не превратился в remote account/push platform. Последующая production correction укрепила уже принятый telemetry contract и не стала новым feature stage.

## Canonical docs

- `docs/product-notices-and-consent.md`
- `docs/telemetry-client.md`
- `docs/privacy-telemetry.md`
- `docs/signals-foundation.md`
- `docs/notification-center.md`
- `docs/notification-preferences-and-toasts.md`

## Historical evidence

- `reports/product/stage-9-telemetry-foundation-handoff.md`
- `reports/product/stage-9-0-1-telemetry-reliability-handoff.md`
- `reports/product/stage-9-3-to-9-5-handoff.md`
