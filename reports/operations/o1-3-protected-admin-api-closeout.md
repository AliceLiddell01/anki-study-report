# O1.3 — public protected Admin API integration

- Дата: `2026-07-26`
- Статус: **integrated in telemetry operations; not deployed**
- O1.2 telemetry basis:
  `bb1ae3c7e42da22f917128b9becde04ba7b0b4d8`
- O1.3 final telemetry head:
  `755511ce20ffc65046503b2504d9edf6d7564e4f`
- Canonical telemetry review:
  [PR #21](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/21)
- Final telemetry CI:
  [run 30196888155](https://github.com/AliceLiddell01/anki-study-report-telemetry/actions/runs/30196888155)
  — **PASS**, включая OSV
- O1.3 telemetry merge:
  `1acb7abc6d9f2347ce59e3f2b52da3a0728140bb`

## Интегрированный результат

Private telemetry repository содержит отдельный Admin Worker/API:

- Access assertion проверяется до route dispatch и до D1;
- RS256 remote JWKS, exact issuer/audience/environment, bounded time claims,
  `type=app` и exact normalized owner identity fail closed;
- machine-readable map покрывает 21 canonical operation;
- 17 active operations используют fixed SELECT-only prepared templates;
- 4 future operations возвращают typed `unavailable` без D1/provider fallback;
- server владеет UTC periods, dimensions, sort и hard row/byte bounds;
- seven-state envelope различает error/unavailable/stale/incomplete/
  suppressed/empty/ok;
- primary и deterministic complementary suppression выполняются до
  serialization;
- static validator и authorized before/after snapshots всех application tables
  доказывают no-mutation для каждой active operation.

Public ingestion Worker, routes, payload, Cron, runtime switches и retention
contract не менялись. Public repository не копирует private SQL, D1 schema,
Access configuration или owner identity.

## Verification boundary

Telemetry exact-head gate:

- canonical `pnpm check` — PASS;
- 9 Vitest files / 58 tests — PASS;
- generated Admin Env types — PASS;
- 21-query map / 12 SELECT-only SQL templates — PASS;
- fresh/upgrade migrations — PASS;
- ingestion и Admin Wrangler dry-run — PASS;
- dependency audit и OSV — PASS.

Public docs sync:

| Проверка                                      | Статус  |
| --------------------------------------------- | ------- |
| `git diff --check`                            | PASS    |
| `python -m compileall -q anki_study_report`   | PASS    |
| exact-head Fast CI                            | PENDING |
| Docker / real-Anki E2E                        | NOT RUN |

Docs-only sync не меняет Python/frontend/runtime/package behavior, поэтому
Docker/real-Anki E2E не является gate.

## Не выполнялось

- remote D1 migration;
- Cloudflare Access application/policy/hostname mutation;
- staging или production Admin Worker deployment;
- provider collector/GraphQL token;
- Admin UI;
- merge telemetry `operations` в `master`;
- merge main `operations` в `core` или `master`.

Следующий Operations этап — O1.4 provider metrics collector, только отдельным
scope и owner decision.
