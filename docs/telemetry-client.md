# Telemetry client

Снимок контракта: 2026-07-15. Python runtime использует проверенный production
endpoint `https://anki-study-report-telemetry.anki-study-report.workers.dev`.
Enrollment и отправка всё равно невозможны до актуального affirmative consent
хотя бы для одной цели. При `ANKI_STUDY_REPORT_E2E=1` production host заменяется
только на явный `ANKI_STUDY_REPORT_TELEMETRY_E2E_ENDPOINT`; это сохраняет
изолированный loopback fake для CI/E2E.

## Граница доверия

React создаёт только allowlisted semantic event и отправляет его на локальный
token-protected `POST /api/telemetry/events`. React не знает installation ID,
write token или внешний endpoint и не обращается к Cloudflare напрямую.
Python заново валидирует точную event union, добавляет доверенные версии,
coarse OS/locale/theme и только затем записывает событие в очередь.

`anki_study_report/telemetry_contract.json` — общий schema v1 contract. Любое
unknown поле, raw exception, произвольный текст или значение вне enum
отклоняется до очереди. `eventId` создаётся Python как UUID и обеспечивает
идемпотентный ack. `occurredAt` нормализуется до UTC-минуты.

## Per-profile storage

```text
<profile>/addon_data/<addon_id>/telemetry.sqlite3
```

SQLite schema v1 хранит очередь, retry state, bounded delivery metadata и одну
пару installation credentials. База использует `journal_mode=DELETE`,
`synchronous=FULL`, `foreign_keys=ON`, migration через `PRAGMA user_version` и
`quick_check`. Повреждённая база закрывается и переносится в
`telemetry.sqlite3.corrupt-<UTC>`. Public status никогда не возвращает ID или
token.

Ограничения contract:

```text
queue:       5000 событий, максимум 7 дней
batch:       50 событий
request:     64 KiB
event input: 4 KiB
database:    защитный max_page_count около 64 MiB
```

При переполнении удаляются самые старые события. При отзыве одной цели
синхронно удаляется только её очередь. При полном отказе очередь очищается.

## Enrollment и delivery

Enrollment разрешён только после актуального affirmative consent хотя бы для
одной цели:

```text
POST   /v1/installations
POST   /v1/events
DELETE /v1/installations/current
```

Внешний endpoint обязан быть HTTPS. Исключение — явно включённый loopback E2E.
Production endpoint является reviewable Python constant и не хранится в
`config.json`; пользователь не может незаметно перенаправить telemetry на
произвольный host.
Сетевые операции выполняются в одном daemon worker, не в UI thread. Отправка
запрашивается после consent, при 25 queued events, на старте и bounded timer не
чаще 15 минут. Один запрос имеет конечный timeout 10 секунд.

Успешно подтверждённые IDs удаляются только после ack. 408, 425, 429, 5xx и
network failures получают exponential backoff с jitter; `Retry-After`
уважается в пределах суток. Non-retryable 4xx удаляет отклонённый batch, 401
удаляет недействительные credentials и оставляет события для нового enrollment.
Ни body, token, URL с token, content или arbitrary exception не логируются.

## Отзыв и удаление

`POST /api/telemetry/delete` принимает только `{}`. Отзыв немедленно выключает
обе effective purposes и event delivery, очищает очередь и отправляет
authenticated DELETE. При offline/5xx credentials остаются только для будущего
DELETE, а UI честно показывает `deletionPending` и следующий bounded retry.
После 2xx/404 локальные credentials уничтожаются. Новое consent не возобновляет
event sending, пока pending deletion не подтверждено.

## Локальный API

Все маршруты loopback-only и требуют dashboard token:

```text
GET  /api/telemetry/status
POST /api/telemetry/events
POST /api/telemetry/delete
```

Status содержит только schema/endpoint/enrollment/sender states, размеры
очереди, bounded error codes и timestamps. Installation ID и write token не
являются частью local API.

## Проверки

Unit/service suites покрывают strict schema, purpose gating, cap/TTL/migration,
batch bounds, ack, retry/jitter/Retry-After, credential secrecy, re-consent,
withdrawal и deletion. Frontend tests проверяют quiet no-op, relative local API,
accepted/declined/pending UI и RU/EN parity.

Real-Anki Docker использует только `fake-telemetry-server.py` на loopback. Он
доказывает zero requests после decline, purpose isolation, batch delivery,
offline queue, restart persistence, pending/confirmed deletion и отсутствие UI
freeze. Fake сохраняет лишь агрегированные counts/codes; tokens и bodies не
попадают в artifacts. CI/E2E не обращается к production telemetry.
