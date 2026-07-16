# Stage 9.0.1 telemetry reliability handoff

Снимок: 2026-07-17. Это отдельный corrective production-readiness этап поверх
Stage 9 foundation. Он не является release и не расширяет telemetry taxonomy.

## Статус при подготовке PR

- code/tests complete: локальные focused add-on/service suites PASS;
- cloud synthetic acceptance: PENDING до merge, staging и production workflow;
- manual real-profile acceptance: PENDING, требуется явный checkpoint владельца.

Synthetic service proof не заменяет доставку из реального Anki-профиля. Stage
нельзя считать полностью закрытым, пока ниже не зафиксирован PASS реального
профиля или честный PENDING.

## Add-on reliability contract

- What’s New X, Escape и «Понятно» закрывают modal оптимистично и потребляют
  manual-open signal ровно один раз даже при delayed/failed mark-seen;
- закрытие возвращает фокус invoker, а следующий отдельный manual signal снова
  открывает modal;
- language tooltip отсутствует в DOM, пока открыт language menu;
- periodic timer разрешает active-profile client в момент tick;
- enrollment attempt/error/next retry/success и retry counter сохраняются в
  per-profile SQLite и переживают restart;
- queue threshold не обходит backoff; ручной check/send получает только один
  one-shot enrollment bypass и не создаёт telemetry event о себе;
- Privacy различает queued, retry/failure, enrolled pending и confirmed
  delivery, не показывая installation ID, token или remote credential.

## Service hardening contract

- enrollment: не более 5 на HMAC abuse pseudonym за UTC day и 10 за rolling
  30 days; raw IP/User-Agent не сохраняются;
- exact per-installation quotas и 20 000 accepted events/UTC day enforced в D1;
- global counter не содержит installation ID и получает не более одной записи
  на accepted batch; duplicate, invalid и rolled-back batch quota не тратят;
- `ENROLLMENT_DISABLED` и `INGESTION_DISABLED` независимы, absent/false означает
  enabled; health и authenticated deletion остаются доступны;
- migration повторно применима как no-op; старые quota/counter rows удаляются;
- R2, Queues, KV, Durable Objects и новый D1 не добавлены.

Оценка D1 write amplification для полного batch из 50 новых events: 1 batch
idempotency row + 1 minute quota update + 1 global counter update + 1
installation update + 50 raw rows + 50 daily-usage updates = около 104
table-row writes, до учёта index/internal storage writes. Два явных raw-event
indexes добавляют примерно ещё 100 index writes, поэтому operational estimate —
около 204 writes, или 4,08 на event. При global budget 20 000 events это около
81 600 writes для full batches; фактические D1 metrics остаются обязательным
операционным сигналом.

## Emergency controls

В staging и production переключатели управляются независимо. Команды содержат
только secret names; значение вводится интерактивно и не попадает в docs/logs:

```powershell
pnpm exec wrangler secret put ENROLLMENT_DISABLED --env staging
pnpm exec wrangler secret delete ENROLLMENT_DISABLED --env staging
pnpm exec wrangler secret put INGESTION_DISABLED --env staging
pnpm exec wrangler secret delete INGESTION_DISABLED --env staging
pnpm exec wrangler secret put ENROLLMENT_DISABLED --env production
pnpm exec wrangler secret delete ENROLLMENT_DISABLED --env production
pnpm exec wrangler secret put INGESTION_DISABLED --env production
pnpm exec wrangler secret delete INGESTION_DISABLED --env production
```

## Acceptance sequence

```text
focused tests
→ telemetry CI
→ staging migration/deploy
→ sanitized synthetic lifecycle
→ production manual deploy
→ sanitized synthetic lifecycle
→ authenticated deletion
→ zero residue
→ explicit real-profile checkpoint
```

После cloud acceptance владелец вручную устанавливает development build,
принимает consent, открывает Privacy, нажимает «Проверить соединение и отправить
сейчас» и ждёт обновления status. Ожидается enrollment, уменьшение queue,
confirmed-delivery timestamp и отсутствие bounded error. Затем разрешена только
агрегированная read-only проверка before/after; installation IDs, token
verifiers, IP и user-specific raw rows не запрашиваются.

Автотесты используют loopback fake или isolated staging и не отправляют в
production. Public evidence исключает production endpoint, Authorization,
installation ID, write token, raw body, dashboard token, `telemetry.sqlite3` и
`privacy.json`.
