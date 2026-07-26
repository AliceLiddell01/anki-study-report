# O1.4 — public Provider Metrics Collector integration

- Дата: `2026-07-26`
- Статус: **corrected / integrated in telemetry operations; not deployed**
- O1.3 telemetry basis:
  `1acb7abc6d9f2347ce59e3f2b52da3a0728140bb`
- O1.4 final telemetry head:
  `03ad15c15917c192878a6fa4900430772964c95c`
- Canonical telemetry review:
  [PR #22](https://github.com/AliceLiddell01/anki-study-report-telemetry/pull/22)
- Final telemetry CI:
  [run 30200494159](https://github.com/AliceLiddell01/anki-study-report-telemetry/actions/runs/30200494159)
  — **PASS**, включая OSV
- O1.4 telemetry merge:
  `ebae6f71ec0dcf2ba044faf9dff2a58cde474263`

## Интегрированный результат

Private telemetry repository содержит отдельный Provider Metrics Collector:

- provider token доступен только no-route Collector Worker и отсутствует в
  Admin API Worker;
- provider snapshots сохраняются в изолированном `ADMIN_DB`, а public ingestion
  Worker и локальный add-on не получают к нему доступ;
- collector использует только fixed pre-reviewed GraphQL templates, bounded
  timeout, response size, retry и fail-closed parsing;
- незавершённые provider intervals исключаются, backfill и retention ограничены;
- scheduled runs идемпотентны, а components имеют независимые checkpoints и
  freshness;
- Admin API возвращает typed unavailable/incomplete состояния и не подменяет
  отсутствие provider data нулём;
- provider-reported estimates не объявляются exact при неизвестной sampling
  metadata.

В том же integration исправлен O1.3: registry-wide differencing paths закрыты,
exact zero отделён от empty, а source coverage и причины неполноты уточнены.

Последующий corrective в telemetry PR #23 ограничил provider queries только
native stored intervals: Worker `previous_24h/hour` (96 ≤ 100 rows), D1
`previous_7d/day` или `previous_30d/day` (180 ≤ 180 rows). Snapshot overlap,
новые points и checkpoint теперь заменяются атомарно; корректный empty очищает
старый overlap, rollback и соседние окна проверены. Timeout охватывает полный
bounded response body и decode.

Public repository не копирует private query bodies, D1 schema, identifiers,
секретную конфигурацию или закрытые fixtures.

## Verification boundary

Telemetry exact-head gate:

- canonical `pnpm check` — PASS;
- 12 Vitest files / 89 tests — PASS;
- operations, Admin и provider contracts — PASS;
- telemetry и Admin migrations fresh/repeat/upgrade — PASS;
- ingestion, Admin и collector Wrangler dry-run — PASS;
- dependency audit и OSV — PASS.

Public docs sync:

| Проверка                                    | Статус  |
| ------------------------------------------- | ------- |
| `git diff --check`                          | PASS    |
| `python -m compileall -q anki_study_report` | PASS    |
| [Fast CI run 30200709904](https://github.com/AliceLiddell01/anki-study-report/actions/runs/30200709904) | PASS |
| Docker / real-Anki E2E                      | NOT RUN |

Docs-only sync не меняет Python/frontend/runtime/package behavior, поэтому
Docker/real-Anki E2E не является gate.

## Не выполнялось

- создание или использование real Cloudflare API token;
- live GraphQL query или schema introspection;
- remote D1 migration;
- Cloudflare Access, Worker, route или Cron resource mutation;
- staging или production deployment;
- O1.5 deployment;
- merge telemetry `operations` в `master`;
- merge main `operations` в `core` или `master`.

Следующий Operations этап — O1.6 verification/runbook/production gate, только
отдельным scope и owner decision.
