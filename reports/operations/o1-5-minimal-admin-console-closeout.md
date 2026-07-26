# O1.5 — public Minimal Admin Console integration

- Дата: `2026-07-26`
- Статус: **integrated in telemetry operations; not deployed**
- O1.5 final telemetry head:
  `f21cd48ac03c555467a15676dc8af90fa14a7525`
- Canonical telemetry review:
  [PR #23](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/23)
- Final telemetry CI:
  [run 30203326707](https://github.com/AliceLiddell01/anki-study-report-telemetry/actions/runs/30203326707)
  — **PASS**, включая Chromium, axe, audit и OSV
- O1.5 telemetry merge:
  `0d19bfda61fe2fe30d1e2e8652c5015f6a7915a6`

## Интегрированный результат

Private telemetry repository содержит отдельную owner-only Admin Console:

- Overview, Usage, Reliability и Privacy — единственные UI routes;
- browser manifest содержит ровно 20 active fixed-query operations и не
  содержит future ingestion-rejections query;
- Admin Worker проверяет Access JWT, exact owner и origin до API и
  Worker-first Static Assets;
- SPA fallback не применяется к `/api`, unknown API остаётся bounded JSON;
- все семь API states, exact zero, suppression `<5`, incomplete/stale и
  provider estimate отображаются без реконструкции;
- client использует только same-origin relative requests, bounded response,
  timeout, concurrency ≤3, in-flight dedupe и stale abort без polling/storage;
- strict CSP, light/dark/reduced-motion, keyboard landmarks, accessible SVG и
  table fallback входят в contract;
- production bundle: JS gzip 68,251 B, CSS gzip 2,690 B, sourcemaps 0,
  external runtime origins 0, committed dist 0.

Public repository не копирует private hostnames, owner identity, Access
audience/team domain, D1/provider IDs, token, GraphQL documents, JWT fixtures
или private screenshots.

## Verification boundary

Telemetry exact-head evidence:

- canonical `pnpm check` — PASS;
- full Worker/backend Vitest: 96 tests — PASS;
- UI unit tests: 11 — PASS;
- Playwright Chromium: 10 tests на 1440×900 и 1024×768 — PASS;
- axe на всех четырёх pages, serious/critical violations — 0;
- обе D1 migration suites fresh/repeat/upgrade — PASS;
- ingestion/Admin-with-assets/collector dry-runs — PASS;
- dependency audit и pinned OSV — PASS.

Public sync является docs-only. Обязательные проверки — `git diff --check`,
Python compile и exact-head docs/Fast CI. Docker/real-Anki E2E не является gate
и не выполняется.

## Не выполнялось

- Cloudflare Access provisioning или policy mutation;
- deployment, hostname/route и static-assets staging proof;
- remote D1 migration;
- live GraphQL, provider token или Cron;
- release, O1.6 или merge в telemetry `master`;
- merge main/public `operations` в `core`/`master`;
- non-Chromium browser acceptance.

Следующий возможный этап — O1.6 verification, runbook and production gate только
по отдельному owner-approved scope.
