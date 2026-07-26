# O1.5 — Product Metrics v2 и redesign Admin Console

- Дата: `2026-07-27`
- Статус: **integrated in telemetry operations; not deployed**
- Final telemetry head:
  `1ce7c6c848fa4466d6824e965bd9b8f74bd7567f`
- Canonical telemetry review:
  [PR #24](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/24)
- Final telemetry CI:
  [run 30219294751](https://github.com/AliceLiddell01/anki-study-report-telemetry/actions/runs/30219294751)
  — **PASS**, включая contracts, security, 108 Vitest tests, Chromium, axe,
  migration checks, dry-runs, audit и OSV
- Telemetry operations merge:
  `450665efd80de8c38525017a32c82f2b1a55146b`

## Интегрированный результат

O1.5 завершён как product-first owner console, а не как browser для технического
Query Registry:

- 15 active fixed read-only operations;
- шесть маршрутов: Overview, Audience, Features, Reliability, Privacy и
  Infrastructure;
- Product Metrics v2 contracts версии `2.1.0`;
- `product.overview` с фиксированной поверхностью из 19 cells;
- семь primary KPI: active installations за 24 часа, 7 и 30 дней, Dashboard
  attempts и success rate, Search attempts, Entity Actions operations;
- отдельные status groups для Dashboard, Search, Entity Actions и Data health;
- Worker/D1/provider diagnostics остаются на Infrastructure и не подменяют
  product health;
- primary/complementary/exhaustive suppression рассчитывается server-side;
- suppressed и unavailable values остаются `null`, доказанный exact zero
  сохраняется;
- browser не получает installation IDs, raw events, hidden numerator/denominator,
  provider credentials или arbitrary payload;
- raw query/metric codes доступны только в сворачиваемом technical inspector.

## UI и reference boundary

Admin Console использует самостоятельную реализацию, адаптирующую patterns
canonical prototype v3.2.3:

- grouped desktop rail и 1024 px navigation popover;
- appbar, route focus и bounded live status;
- coherent light/dark semantic tokens;
- видимый violet focus ring и reduced motion;
- compact KPI/status hierarchy;
- typed `ok`, `empty`, `suppressed`, `incomplete`, `stale`, `unavailable` и
  `error` states;
- bounded long labels и отсутствие horizontal document overflow.

Owner-provided reference archive прошёл ZIP integrity check. В нём подтверждены
52 файла, обязательные canonical documents и 51/51 checksum match. Reference
comparison не выявил material mismatch. Архив, prototype assets и screenshots в
public repository не копируются.

Owner autonomous merge authorization было предоставлено. Owner screenshot
review и blind review не заявляются как выполненные.

## Verification boundary

Final exact-head telemetry run `30219294751` на
`1ce7c6c848fa4466d6824e965bd9b8f74bd7567f` подтвердил:

- frozen dependency install, format, lint и typecheck;
- remote, operations, Product Metrics и security contracts;
- Admin UI manifest, unit, build и bundle checks;
- полный Vitest suite: 108 tests;
- обе D1 migration suites;
- ingestion, Admin-with-assets и collector dry-runs;
- dependency audit, `git diff --check` и OSV;
- Playwright Chromium и axe;
- exact Overview hierarchy, privacy states, technical inspector, 1024
  navigation и light/dark visual artifacts.

Public sync является docs-only. Он не переносит private hostnames, owner
identity, Access audience/team domain, D1/provider IDs, credentials, GraphQL
documents, JWT fixtures или private screenshots. Real-Anki Docker E2E не
является gate для этой документационной синхронизации.

## Не выполнялось

- Cloudflare Access provisioning или policy mutation;
- deployment, hostname/route или static-assets staging proof;
- remote D1 migration;
- live GraphQL, provider token или Cron activation;
- release или telemetry `master` change;
- merge main/public `operations` в `core`/`master`;
- O1.6;
- non-Chromium browser acceptance.

Следующий возможный этап — O1.6 Verification, Runbook and Production Gate только
по отдельному owner-approved scope.
