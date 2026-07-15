# Privacy и telemetry data contract

Снимок: 2026-07-15. Это техническое описание и не является юридической
консультацией или сертификатом соответствия.

## Текущий shipping status

Product-notice/consent foundation работает офлайн. Сейчас add-on не создаёт
очередь telemetry, не выполняет enrollment и не отправляет данные во внешний
сервис. Сохранённый выбор — необходимое, но само по себе недостаточное условие
будущей отправки.

До включения production telemetry должны быть готовы и проверены client
contract, endpoint, deletion flow, retention, controller/контактная информация
и финальный Privacy Notice. UI не обещает удаление remote data, пока эта
операция реально не существует.

## Цели

`reliabilityDiagnostics` допускает только версии/семейство ОС, bounded result,
error и duration codes/buckets. Raw exceptions и stack traces запрещены.

`featureUsage` допускает только locale/theme, allowlisted page/feature/action
codes и широкие result-count/collection-size buckets. Search text и названия
сущностей запрещены.

Ни одна цель не выбрана заранее. Отзыв остаётся таким же доступным, как
принятие: `#/settings/privacy` позволяет сохранить пустой выбор.

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

Persistence, UI и local endpoints описаны в
`docs/product-notices-and-consent.md`.
