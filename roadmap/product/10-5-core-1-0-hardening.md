# Stage 10.5 — Core 1.0 Hardening

**Status:** Planned after Stage 10

## Цель

Подготовить существующий core к стабильному 1.0 contract. CI/CD уже построен; этот этап не создаёт новую release pipeline, а проверяет и укрепляет существующую.

## Scope

### API and schema freeze

- inventory публичных/local API contracts;
- versioning/deprecation rules;
- freeze stable routes, action codes, signal codes и payload fields;
- запрет односторонних backend/frontend изменений.

### Migration policy

Проверить update/recovery для:

```text
config.json
profile.json
product_notices.json
privacy.json
telemetry.sqlite3
notifications.sqlite3
stats cache schemas
```

- forward migrations;
- future-schema fail-closed behavior;
- corruption quarantine;
- per-profile isolation;
- downgrade expectations.

### Performance

- startup/dashboard/report budgets;
- Search/Cards/Signals query bounds;
- notification-history pruning;
- bundle/chunk budgets;
- real-Anki E2E duration/flake budget.

### Accessibility

- App Shell, menus, modals, tables, filters, panel, Center, toasts и triage;
- focus return, reduced motion, live regions, contrast и keyboard completeness.

### Install/update/recovery

- clean install;
- update from supported previous versions;
- profile switch/restart;
- missing/corrupt generated assets;
- server restart/token lifecycle;
- telemetry offline/withdraw/delete;
- cache and notification recovery.

### Packaging/security/release

- exact artifact inventory;
- no runtime/secret/profile data;
- action/media/sanitizer/token boundaries;
- current gated release and AnkiWeb publishing verification;
- rollback and release checklist.

## Out of scope

- создание ещё одной CI/CD системы;
- feature expansion;
- marketplace/DLC UI;
- analytics additions без продукта Stage 11.

## Completion criteria

- Published compatibility/migration policy.
- Stable API inventory and explicit deprecation process.
- Performance/accessibility budgets с evidence.
- Install/update/recovery matrix проходит.
- Existing Fast CI, exact-package E2E и gated release используются без дублирования.
