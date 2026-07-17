# Unscheduled — Telemetry Admin Analytics Dashboard

**Status:** Unscheduled future concept; no stage number and no implementation commitment

## Цель

Создать отдельный защищённый web-dashboard, который автоматически читает telemetry backend и показывает владельцу проекта актуальную, человекочитаемую инфографику без ручных `wrangler d1 execute`, SQL-команд, консольных inspection-скриптов и разбора JSON.

Основной сценарий:

```text
владелец открывает защищённый URL
        ↓
проходит server-side авторизацию
        ↓
видит свежую сводку, графики, предупреждения и privacy/retention status
        ↓
dashboard автоматически обновляет данные
```

Это внутренний operational analytics tool. Он не является пользовательской страницей локального Anki dashboard и не должен расширять публичный product navigation.

## Почему это отдельное web-приложение

Локальные файлы add-on находятся под контролем владельца компьютера и не могут безопасно хранить административный secret или обеспечивать доверенную проверку `isAdmin`.

Поэтому:

- admin UI не встраивается в публичную сборку add-on;
- административные credentials, allowlist и D1 bindings не попадают в Python/JavaScript/config локального расширения;
- знание URL, endpoint names или содержимого frontend bundle не даёт доступа к данным;
- все проверки identity и authorization выполняются на серверной стороне для каждого admin API request.

Допустима отдельная development-only ссылка, которая лишь открывает admin URL в системном браузере. Она не передаёт административные полномочия.

## Предлагаемая архитектура

```text
Browser
  │
  │ Cloudflare Access / identity policy
  ▼
Telemetry Admin Web UI
  │
  │ fixed read-only admin API
  ▼
Admin Worker
  │
  │ prepared D1 queries through TELEMETRY_DB binding
  ▼
Telemetry D1
```

Предпочтительно использовать отдельный hostname, например:

```text
telemetry-admin.<project-domain>
```

Публичный ingestion Worker и admin dashboard могут использовать одну D1 database, но обязаны иметь разные HTTP boundaries и разные route policies.

## Security boundary

Обязательные ограничения:

- весь admin hostname закрыт Cloudflare Access;
- policy разрешает вход только явному admin allowlist;
- Worker валидирует Access identity/JWT, а не доверяет frontend;
- D1 доступна только через server-side binding;
- секреты хранятся только как Cloudflare Secrets или platform-managed identity configuration;
- в repository, generated assets, browser storage и add-on files нет admin API keys;
- каждый endpoint имеет фиксированный purpose и allowlist параметров;
- SQL строится только через подготовленные запросы;
- произвольный SQL endpoint запрещён;
- ответы не раскрывают внутренние credentials, full installation secrets или лишние raw identifiers;
- access-denied и admin actions имеют минимальный security audit без записи telemetry payload.

Безопасность не должна зависеть от скрытого URL, отсутствия кнопки или минификации frontend bundle.

## Основной UX

Dashboard должен отвечать на вопросы человеческим языком:

- сколько активных установок использует add-on;
- сколько новых установок появилось;
- сколько событий принято сегодня и за выбранный период;
- какие страницы и функции используются чаще;
- какие версии add-on, Anki и ОС остаются активными;
- насколько быстро запускается dashboard и выполняются операции;
- какие ошибки возникают и на каких версиях;
- работает ли ingestion, aggregation и retention;
- выполняются ли deletion requests;
- есть ли расхождения или аномалии, требующие внимания.

Коды должны переводиться в понятные подписи, например:

```text
settings_privacy              → Настройки конфиденциальности
dashboard_startup.completed   → Запуск панели завершён
under_100_ms                  → Менее 100 мс
over_1000                    → Более 1000 результатов
```

## Разделы dashboard

### 1. Overview

Крупные summary cards:

- active installations;
- new installations;
- events today;
- active installations за выбранный период;
- ingested batches;
- ingestion success/error rate;
- raw event rows;
- daily aggregate freshness;
- deletion requests;
- expired rows awaiting cleanup;
- last event received;
- last aggregation run;
- last retention cleanup.

Каждая карточка по возможности показывает изменение относительно предыдущего сопоставимого периода.

### 2. Activity trends

Графики:

- events by hour/day;
- active installations by day;
- new installations by day;
- events per active installation;
- peak usage windows;
- accepted versus rejected batches, если соответствующие counters существуют.

Периоды:

```text
24 часа | 7 дней | 30 дней | 90 дней | произвольный диапазон
```

### 3. Pages and features

Показывать:

- page opens by `page_code`;
- event distribution by `event_code`;
- feature/action/result distribution;
- долю каждого раздела;
- динамику популярности;
- unique active installations per page, если это можно посчитать без расширения privacy scope.

Не собирать названия колод, содержимое карточек, search query text или другие content-level данные ради этой страницы.

### 4. Versions and environment

Распределения:

- add-on version;
- Anki version;
- OS family;
- locale;
- theme;
- telemetry schema version;
- consent schema version;
- Privacy Notice version;
- installation status.

Dashboard должен помогать находить stale versions и коррелировать версии с ошибками, не идентифицируя конкретного пользователя.

### 5. Performance

Показывать bucket-based метрики:

- dashboard startup duration;
- search duration;
- report generation duration;
- другие bounded operation durations;
- success/failure rate;
- slow bucket share;
- performance breakdown by add-on/Anki version.

Точные timings не требуются, если telemetry contract использует privacy-preserving buckets.

### 6. Search analytics

Без хранения поискового текста:

- number of searches;
- success/failure rate;
- duration buckets;
- result-count buckets;
- zero-result share;
- high-result share;
- distribution by add-on/Anki version при достаточном объёме данных.

### 7. Errors and system health

Показывать:

- errors by `error_code`;
- errors by event/feature/action;
- errors by add-on version, Anki version и OS;
- rejected or invalid batches;
- rate-limit and quota pressure;
- aggregation failures;
- retention cleanup failures;
- expired raw rows;
- unexpected event-volume drops or spikes.

Healthy state должен быть явно виден, например:

```text
System healthy
Critical errors: 0
Ingestion errors: 0
Expired raw events: 0
```

### 8. Privacy, consent and deletion

Показывать:

- installations by Privacy Notice version;
- consent schema distribution;
- telemetry purposes distribution;
- deletion request count;
- deleted installation rows;
- deleted raw event rows;
- current configured/effective retention;
- rows approaching expiry;
- rows expired but not deleted;
- latest deletion and cleanup results.

Dashboard не должен превращать deletion audit в способ восстановить удалённые telemetry данные.

## Human-readable diagnostics

Помимо графиков dashboard должен строить объясняющие notices по детерминированным правилам.

Примеры:

- `global_daily_usage` больше текущего числа raw rows: вероятно, usage counter учитывает ранее принятые, но затем удалённые события;
- raw events существуют, но `daily_aggregates` не обновлялись: aggregation job не запускалась, задержалась или завершилась ошибкой;
- появились expired raw rows: retention cleanup требует внимания;
- новая версия имеет существенно повышенный error rate;
- event volume резко упал относительно обычного baseline;
- в production долго отсутствуют новые события;
- telemetry schema/consent versions расходятся с ожидаемым rollout.

Такие сообщения должны обозначаться как rule-based inference, а не как доказанная root cause.

## Обновление данных

### При открытии

Dashboard всегда загружает актуальную server-side сводку, а не ранее экспортированный inspection JSON.

### Пока страница открыта

Предлагаемый polling interval: 30–60 секунд, с:

- отметкой `updated at`;
- состоянием loading/error/stale;
- кнопкой `Refresh now`;
- отменой предыдущего request при смене периода;
- отсутствием агрессивного real-time polling без необходимости.

### Background aggregation

По мере роста объёма данных использовать scheduled jobs:

```text
каждые 15 минут  оперативные агрегаты, если это оправдано объёмом
раз в сутки      финальный aggregate предыдущего дня
раз в сутки      retention cleanup и consistency checks
```

Точный schedule определяется после измерений. Малый объём может обслуживаться прямыми bounded queries к `raw_events`.

## Data-query model

Frontend не должен скачивать всю `raw_events` и агрегировать её в браузере.

Admin Worker возвращает только готовые bounded datasets:

```text
GET /api/admin/overview
GET /api/admin/activity?period=7d&interval=day
GET /api/admin/pages?period=30d
GET /api/admin/events?period=30d
GET /api/admin/versions?period=30d
GET /api/admin/platforms?period=30d
GET /api/admin/performance?period=30d
GET /api/admin/search?period=30d
GET /api/admin/errors?period=7d
GET /api/admin/privacy
GET /api/admin/deletions?period=90d
GET /api/admin/aggregation-status
```

Endpoint contracts должны ограничивать:

- разрешённые periods и intervals;
- maximum date range;
- result-row limit;
- allowed sort/filter fields;
- timeout/query complexity;
- cache policy;
- response schema.

## Aggregates and retention

`raw_events` используются для свежей ограниченной аналитики и расследования агрегированных аномалий в пределах retention window.

`daily_aggregates` используются для долгих диапазонов, истории и дешёвого построения графиков после удаления raw events.

Необходимо определить:

- canonical aggregate dimensions;
- идемпотентный aggregation algorithm;
- late-arriving batch policy;
- backfill/rebuild procedure;
- consistency checks между raw, aggregate и usage counters;
- retention для агрегатов отдельно от raw events;
- deletion semantics для данных, которые уже вошли в aggregate.

## MVP scope

Первый этап должен быть read-only и включать:

1. отдельное React web-приложение;
2. hosting через Cloudflare Workers Static Assets или эквивалентный server-controlled deployment;
3. отдельный Admin Worker API;
4. Cloudflare Access на весь admin hostname;
5. дополнительную server-side identity/allowlist validation;
6. Overview;
7. activity trend;
8. page/event popularity;
9. add-on, Anki и OS distributions;
10. performance buckets;
11. errors/system health;
12. privacy, retention и deletion audit;
13. date-range filters;
14. auto-refresh и last-updated indicator;
15. человекочитаемые labels и rule-based warnings;
16. loading, empty, stale и error states;
17. responsive desktop-first layout;
18. automated API/schema/auth tests.

## Out of scope первого этапа

- arbitrary SQL console;
- просмотр или редактирование secrets;
- ручное изменение database rows;
- изменение retention policy из UI;
- изменение enrollment/rate-limit quotas;
- ручной запуск migrations;
- массовое удаление данных;
- управление installations;
- пользовательская account/admin-role system;
- включение admin routes в локальную product navigation;
- публичный analytics dashboard;
- content-level telemetry;
- real-time streaming без измеримой необходимости.

Любые destructive operations рассматриваются только отдельным hardening этапом с audit log, typed confirmation, least privilege и rollback/recovery policy.

## Privacy constraints

- Dashboard визуализирует только уже согласованный telemetry contract.
- Новый UI не является основанием собирать дополнительные поля.
- Raw installation identifiers по умолчанию сокращаются, хешируются для presentation или не отображаются.
- Нельзя показывать search text, deck/card content, file paths или произвольные строки.
- Small-cohort breakdowns должны скрываться или объединяться, если они повышают re-identification risk.
- Access logs минимизируются и не содержат query payload/credentials.
- Export/download отсутствует в MVP или ограничен агрегированными данными с отдельным review.
- Privacy Notice и consent schema обновляются только при фактическом изменении telemetry purpose/data/retention/recipients, а не из-за одной визуализации существующих данных.

## Зависимости

До реализации должны быть стабильны:

- production telemetry ingestion;
- D1 schema and migrations;
- retention cleanup;
- deletion endpoint and audit semantics;
- event-code registry and human-readable labels;
- daily aggregation contract либо доказанная возможность безопасных bounded raw queries;
- Cloudflare Access configuration and deployment ownership;
- admin threat model;
- observability для самого Admin Worker.

Этот концепт следует развивать после стабилизации основного product roadmap и накопления достаточного объёма telemetry, при котором ручной inspection становится регулярным operational burden.

## Completion criteria будущего этапа

Этап может считаться завершённым, когда:

- admin hostname недоступен без server-side authorization;
- никакой admin secret не присутствует в add-on files или frontend bundle;
- dashboard показывает согласованный набор метрик из production D1;
- значения сверены с reference SQL/inspection fixture;
- графики корректны для empty/small/large datasets;
- filters и periods bounded;
- auto-refresh не создаёт заметной D1/request нагрузки;
- aggregation freshness и retention status видны;
- rule-based warnings имеют тестируемые условия;
- raw identifiers и запрещённые content fields не раскрываются;
- Access bypass, direct API access и malformed parameter tests отклоняются;
- deployment, rollback и incident-access procedure документированы;
- privacy/security review подтверждает отсутствие расширения telemetry scope.

## Verification policy

Обязательны:

- unit tests для metric calculations и label mapping;
- API schema/allowlist tests;
- auth denial tests без Access identity и с неразрешённой identity;
- prepared-query and parameter-bound tests;
- seeded D1 integration fixture;
- comparison с trusted reference queries;
- UI tests для period switching, empty/error/stale states и auto-refresh;
- performance checks на реалистичном объёме raw/aggregate rows;
- security review маршрутов и headers;
- privacy review отображаемых dimensions;
- manual production smoke test через защищённый hostname.

## Условия назначения номера Stage

Концепт получает номер только когда одновременно выполнены условия:

- telemetry backend стабилен;
- ручной inspection действительно стал повторяющейся задачей;
- определён canonical MVP metric set;
- подтверждена схема Cloudflare Access/admin identity;
- понятно место этапа относительно Core hardening и extension-pack work;
- реализация не создаёт placeholder route или secret в локальном add-on.
