# Signals Foundation

Снимок контракта: 2026-07-17. Signals Foundation — полностью локальный,
read-only относительно коллекции слой. Он вычисляет консервативные учебные
сигналы из уже построенного cache snapshot, Deck Hub и одного bounded запроса к
`revlog`, а затем сохраняет только ограниченные агрегаты в per-profile SQLite.

## Хранилище и жизненный цикл

Файл профиля: `<profile>/addon_data/<addon_id>/notifications.sqlite3`.
Schema v1 содержит `schema_metadata`, `signals`, `notifications` и
`notification_preferences`. Используются `quick_check`, `PRAGMA user_version`,
`journal_mode=DELETE`, `synchronous=FULL`, foreign keys, quarantine повреждённой
базы и лимит 64 MiB. История ограничена 180 днями и 5000 notifications;
evidence — allowlist полей, не более 2048 bytes.

`active/resolved` относится к сигналу, `read/unread` — к notification. Эти оси
независимы. Первый кандидат создаёт сигнал и notification; рост severity создаёт
`severity_escalated`; повторная активация — `signal_reactivated`. Сигнал
разрешается только после двух последовательных успешных оценок без кандидата.
Ошибка одного detector не засчитывается как отсутствие и не разрешает другие
сигналы.

## Detector registry v1

| Code | Условие warning | Условие critical | Ограничение данных |
| --- | --- | --- | --- |
| `workload.review_pressure` | current load ≥ `max(1.5× median, median+30)` | ≥ `max(2× median, median+100)` | минимум 14 активных дней из предыдущих 28 |
| `retention.recent_drop` | падение ≥ 8 п. п. | падение ≥ 15 п. п. | 7 недавних дней, ≥50 недавних и ≥200 baseline ответов |
| `deck.health_decline` | aggregate health `warning` | aggregate health `danger` | только реальные Deck Hub nodes |
| `card.repeated_again` | ≥3 Again при ≥4 ответах за 7 дней | ≥5 Again | один grouped query, максимум 50 cards |

Порогами нельзя управлять из UI: custom rules и редактируемые thresholds не
входят в этот этап. Entity ID используется только локально для dedupe и
контекстного перехода; card/note content в evidence не записывается.

## Запуск и производительность

Оценка выполняется из существующего report/cache lifecycle и пропускается для
уже обработанного `cache:<updatedAt>:revlog:<lastRevlogId>:day:<date>`.
Одновременные оценки блокируются. Логи содержат только detector code, bounded
duration bucket, counts и диагностический code — без evidence и entity IDs.

## Проверки

Основные unit tests: `tests/test_signal_detection.py`,
`tests/test_notification_store.py`, `tests/test_notification_integration.py`.
Real-Anki доказательство — scope `standard/notifications`: normal state,
warning/critical, escalation, two-pass resolution, reactivation, bounded API и
restart persistence.

Signal/notification данные не добавляются в remote telemetry taxonomy и не
передаются Cloudflare.
