# Privacy и telemetry data contract

Снимок: 2026-07-15. Это активное RU/EN product notice и проверяемый технический
контракт продукта. Он не является юридической консультацией или сертификатом
соответствия.

## Текущий shipping status

Consent-gated client, bounded SQLite queue, enrollment/delivery и authenticated
deletion реализованы. Проверенный production endpoint закреплён в Python
runtime: `https://anki-study-report-telemetry.anki-study-report.workers.dev`.
Loopback fake по-прежнему разрешён только в явном E2E mode. React не знает
внешний endpoint token или installation credential и не обращается к
Cloudflare напрямую.

Контроллер и разработчик указан ровно как публично предоставлено:
`AliceLiddell01`; контакт: `leaf.fairy@proton.me`. Cloudflare предоставляет
Worker и D1 как инфраструктурный обработчик. При доставке запросов Cloudflare
может обрабатывать connection metadata, включая IP и User-Agent, но сервис не
записывает эти поля в application D1 или normal application logs.

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

Страница отдельно показывает очередь, состояние enrollment, последнюю попытку,
следующий retry, последний enrollment success и последнюю подтверждённую
доставку. «Проверить соединение и отправить сейчас» запускает ровно одну
асинхронную попытку, не обещает доставку до server ack и не генерирует событие
о самом действии.

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

## Installation, retention и удаление

Enrollment создаёт случайную псевдонимную installation отдельно для каждого
Anki-профиля и устройства. Она не содержит AnkiWeb identity и не
синхронизируется через AnkiWeb.

- raw event rows: 60 дней;
- суточные агрегаты: 24 месяца;
- primary storage: D1 с EU jurisdiction;
- provider-managed D1 Time Travel: 7 дней;
- recovery drill: временный D1 export/import внутри GitHub runner; SQL удаляется
  в том же job и никогда не загружается в artifacts.

R2 и независимые 30-дневные бэкапы не входят в активную инфраструктуру или
обещания хранения. Они относятся только к future infrastructure work; их
включение потребует обновлённого уведомления и нового согласия.

Отзыв немедленно выключает effective purposes и очищает локальную очередь.
Удаление уже собранных данных подтверждается authenticated remote DELETE; при
offline состояние остаётся `pending`, а credentials уничтожаются только после
2xx/404.

## Версии и re-consent

```text
privacy schema:  1
consent schema:  1
Privacy Notice:  2026-07-15-production
```

Обычное обновление add-on не вызывает consent повторно. Материальное изменение
целей, получателей, разрешённых данных или retention требует новой версии
consent/notice. До нового affirmative choice effective purposes выключены.

Consent persistence и modal описаны в `docs/product-notices-and-consent.md`,
queue/network/deletion — в `docs/telemetry-client.md`.
