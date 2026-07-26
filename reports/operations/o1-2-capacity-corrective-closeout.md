# O1.2 — public capacity corrective integration

- Дата: `2026-07-26`
- Статус: **integrated in telemetry operations; not deployed**
- O1.1 telemetry merge:
  `8ef613d61c7b8672d9143b0c3b710c2d81b2fa6b`
- O1.2 final telemetry head:
  `86dcdae38c0044dee7e839ee2ff190d539b7cf57`
- O1.2 telemetry merge:
  `bb1ae3c7e42da22f917128b9becde04ba7b0b4d8`
- Final telemetry CI:
  [run 30193694403](https://github.com/AliceLiddell01/anki-study-report-telemetry/actions/runs/30193694403)
  — **PASS**, включая OSV

## Corrective result

Owner review отклонил прежнее утверждение, что maintenance cost bounded только
потому, что normal run обрабатывал восемь дней. High-cardinality aggregates
делали delete/reinsert cost зависимым от числа dimension combinations.

Интегрированный O1.2:

- выбирает dirty/missing complete days, а не переписывает восемь неизменённых;
- использует server-owned received/deletion evidence и atomic per-day
  checkpoint;
- ограничивает bootstrap одним day/run и backfill семью candidates;
- делит 20,000 rows-written maintenance budget между aggregation, backfill и
  retention;
- оставляет 80,000-row allocation reserve для ordinary ingestion;
- различает retryable capacity defer и atomic single-day oversize;
- записывает actual D1 metadata без private identifiers или raw errors.

Public repository не копирует private schema, Metric Registry или SQL.

## Evidence boundary

Exact local steady-state fixture после bootstrap:

```text
rows_read=3369
rows_written=11
changes=7
selected=0
rebuilt=0
deferred=0
```

Final telemetry gate: 7 test files / 46 tests, fresh/upgrade migrations,
security/static checks, Wrangler dry-run и OSV — PASS.

Application cap 20,000 accepted events остаётся abuse limit, не гарантией
совместимости с Workers Free. Production Dashboard/GraphQL actuals, lower cap
или paid plan требуют отдельного решения.

## Не выполнялось

- staging/production deployment;
- remote D1 migration или Cloudflare resource mutation;
- Admin API/UI/Access;
- provider collector/GraphQL token;
- O1.3;
- merge telemetry `operations` в `master`;
- merge main `operations` в `core` или `master`.
