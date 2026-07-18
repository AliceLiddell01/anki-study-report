# Обзор проекта

Снимок: **2026-07-18**.

Anki Study Report — local add-on for Anki 26.05+ that explains study progress, workload and problems through a Markdown/HTML report and a React dashboard.

## Runtime contours

1. Python add-on: `anki_study_report/`
2. React/TypeScript dashboard: `web-dashboard/`
3. tests/build/E2E: `tests/`, `scripts/`, `docker/anki-e2e/`
4. separate private opt-in telemetry service: `anki-study-report-telemetry`

Python owns collection access and server-side logic. Frontend receives bounded payloads and invokes allowlisted APIs; it never reads the Anki collection directly. Real-Anki Docker E2E verifies integration risks that unit tests cannot cover.

## Current product

Settings route `#/settings/inspection-profiles` provides local declarative
per-note-type quality configuration with explicit confirmation, bounded safe
preview, revision conflicts, and strict import/export. It does not mutate Anki
objects; the future Cards v2 queue/Inspector remains a separate C1.5 surface.

The accepted product contour includes:

- local report/dashboard and cache-backed history;
- Profile, Activity and Deck hierarchy;
- Statistics and read-only FSRS analytics;
- native Cards/Notes Search;
- allowlisted undoable Safe Actions;
- isolated/sanitized card preview;
- local per-profile Signals and Notification Center;
- opt-in bounded technical telemetry through a separate service.

Current primary navigation:

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

## Roadmap

Completed product work remains recorded as Stage 0–9.5. Future work is multi-track:

- [Core](../roadmap/core/README.md): `C1 Cards v2`, then `C2 Core 1.0`; `C3` only for proven gaps.
- [Gamification](../roadmap/gamification/README.md): parallel research/product direction, not production-ready.
- [Telemetry operations](../roadmap/operations/README.md): separate protected internal tooling.
- [Identity](../roadmap/identity/README.md): conditional continuity gate.
- [Extensions](../roadmap/extensions/README.md): conditional/deferred first-party ecosystem.
- [Platform](../roadmap/platform/README.md): independent CI/CD/E2E/release work.

Core does not depend on gamification, accounts, telemetry admin UI or extension packs.

## Source-of-truth boundaries

Dashboard payload:

- `anki_study_report/dashboard_payload.py`
- `web-dashboard/src/types/report.ts`
- payload/server/frontend tests
- `docs/dashboard-api.md`

Packaging:

- `scripts/package_addon.py`
- `tests/test_package_build.py`
- `docs/packaging-release.md`

Real-Anki E2E:

- `docker/anki-e2e/README.md`
- `scripts/run_anki_e2e_docker.ps1`
- `scripts/run_full_check.ps1`
- reviewed workflow artifacts

Signals/notifications:

- `anki_study_report/signal_detection.py`
- `anki_study_report/notification_store.py`
- `docs/signals-foundation.md`
- `docs/notification-center.md`

Telemetry:

- local client contracts in this repo;
- ingestion/retention/deletion/deployment contracts in the separate private telemetry repo.

## Important invariants

- no one-sided payload/public-contract changes;
- no direct frontend collection access;
- loopback/token boundary remains;
- no arbitrary SQL/RPC/action/plugin surface;
- no weakened sanitizer/media/preview isolation;
- no generated/runtime artifacts in git/package;
- local signal evidence is not telemetry;
- research candidates are not production features;
- release remains exact-artifact, manual and approval-gated.

For current details use [Architecture](architecture.md), [Security](security-and-safety.md), [Decision log](decision-log.md), [Roadmap](../roadmap/README.md) and [AI handoff](ai-handoff.md).
