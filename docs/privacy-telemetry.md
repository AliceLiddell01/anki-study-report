# Privacy и telemetry data contract

Снимок: 2026-07-15. Это техническое описание и не является юридической
консультацией или сертификатом соответствия.

## Текущий shipping status

Consent-gated client, bounded SQLite queue, enrollment/delivery и authenticated
deletion реализованы. Production endpoint в публичной конфигурации add-on пока
отсутствует, поэтому обычная `.ankiaddon` не выполняет внешних запросов.
Loopback fake разрешён только в явном E2E mode.

Перед включением production endpoint должны быть проверены hosted service,
retention/backup/deletion, controller/контактная информация и финальный Privacy
Notice. UI уже поддерживает operational deletion contract: offline удаление
честно остаётся `pending`, а credentials уничтожаются только после remote
2xx/404. Детали клиента — `docs/telemetry-client.md`.

## Цели

`reliabilityDiagnostics` допускает только версии/семейство ОС, bounded result,
error и duration codes/buckets. Raw exceptions и stack traces запрещены.

`featureUsage` допускает только locale/theme, allowlisted page/feature/action
codes и широкие result-count/collection-size buckets. Search text и названия
сущностей запрещены.

Ни одна цель не выбрана заранее. В первом consent modal пустой affirmative
выбор сохранить нельзя: отказ оформляется отдельной кнопкой, X или Escape.
Отзыв остаётся таким же доступным, как принятие: `#/settings/privacy` позволяет
отключить ранее разрешённые цели.

Privacy page показывает product-owned timestamps через локализованный RU/EN
formatter в часовом поясе пользователя, сохраняя исходный ISO только в
семантическом `dateTime`/диагностическом `title`. Действия отключения и
удаления недоступны с объяснением, когда они не могут изменить состояние.

## Никогда не собирать

- содержимое карточек/записей, имена или значения полей;
- названия колод, note types, templates, tags и Search queries;
- card/note/deck/note-type IDs;
- имя Anki-профиля, имя пользователя и email;
- dashboard token, token-bearing URL, report payload и clipboard;
- абсолютные пути, media filenames и произвольный текст;
- raw exception, полный stack trace, IP и User-Agent в application storage.

Запрет применяется одинаково к collection, local queue, outbound payload,
server persistence и normal logs.

## Версии и re-consent

```text
privacy schema:  1
consent schema:  1
Privacy Notice:  2026-07-15
```

Обычное обновление add-on не вызывает consent повторно. Материальное изменение
целей, получателей, разрешённых данных или retention требует новой версии
consent/notice. До нового affirmative choice effective purposes выключены.

Consent persistence и modal описаны в `docs/product-notices-and-consent.md`,
queue/network/deletion — в `docs/telemetry-client.md`.
