# Profile MVP

Статус: implemented in Stage 3.

## Product role

`#/profile` — локальная read-only витрина долгосрочного учебного пути текущего
Anki-профиля. Она показывает identity, lifetime totals, компактную историю
активности и спокойный обзор колод. Profile не даёт рекомендаций и не
диагностирует проблемы.

Разделение ответственности:

- Today — текущий локальный день и ближайший шаг;
- Calendar — подробная история по датам;
- Decks — состояние отдельных колод;
- Cards — конкретные карточки внимания;
- Profile — identity и lifetime view всей коллекции;
- Statistics — будущая глубокая аналитика, не часть Stage 3.

Profile не содержит внутренних tabs, social/account model, achievements,
goals, Activity Feed или controls будущего avatar/banner upload.

## Page structure

1. Theme-aware встроенный banner и avatar с детерминированными initials.
2. Имя текущего Anki profile; fallback — `Пользователь Anki`.
3. Нейтральный label `Локальный профиль` и даты учебной истории.
4. Ровно шесть lifetime KPI.
5. Mini heatmap последних максимум 182 календарных дней доступной активности.
6. Семь последних активных дней, newest first.
7. До восьми canonical current-deck rows и selector сортировки.

В hero нет внешних изображений. Длинное имя переносится и сохраняется целиком
в `title`; avatar initials стабильны между renders.

## Lifetime metrics

Все метрики строятся backend-side из исходного all-collection stats-cache
snapshot до применения dashboard scope.

| KPI | Семантика |
| --- | --- |
| Всего повторений | Реальные revlog rows после существующего `REVLOG_REVIEW_FILTER_SQL` |
| Активных дней | Уникальные локальные cache dates с `reviews > 0` |
| Текущая серия | Последовательность до сегодня; если сегодня пуст, серия до вчера сохраняется |
| Лучшая серия | Максимальная последовательность активных локальных дней |
| Время учёбы | Capped сумма времени ответа из revlog; подписана как оценка |
| Средняя успешность | `pass_count / (pass_count + fail_count)` по Pass/Fail semantics cache |

Unavailable time/pass rate остаются `null` и отображаются как `Нет данных`, а
не как искусственный ноль.

## All-collection semantics

`StudyReport.profile` строится из `StatsCacheManager.report_snapshot()`:

```text
snapshot.daily
snapshot.deckDaily
        │
        └─ build_profile_payload(...)
```

В builder не передаются dashboard period, selected deck IDs/names, report
scope или include-children. Поэтому изменение Settings Hub не меняет totals,
streaks, dates, activity или decks Profile. Это отдельный contract от
top-level historical report и `StudyReport.today`.

Deck overview использует canonical rows текущей deck association из
`deck_daily_aggregates`. Descendants не агрегируются скрыто. Ограничение cache
сохраняется: historical review может быть отнесён к текущей колоде карточки.

## Study start override

Profile различает:

```text
detectedStartedOn  первая cache date с реальным review
customStartedOn    локальный пользовательский override
displayedStartedOn customStartedOn ?? detectedStartedOn
statsAvailableFrom detectedStartedOn
```

Override валидируется frontend и backend, не может быть future date и не
создаёт activity, totals, streaks или study time. Если даты расходятся, hero
отдельно сообщает, с какой даты реально доступна статистика. Dialog поддерживает
initial focus, Tab trap, Escape, возврат focus, inline error и reset.

## Persistence

Source of truth для editable profile preferences:

```text
<profile>/addon_data/<addon_id>/profile.json
```

Текущая schema:

```json
{
  "schemaVersion": 1,
  "customStudyStartedOn": null,
  "deckOverviewSort": "name"
}
```

`ProfilePreferencesStore` использует UTF-8, normalized JSON, process lock,
temporary file + `fsync` + `os.replace`. Corrupt/missing file даёт defaults;
unknown future storage keys сохраняются при update. Runtime file не входит в
Git или `.ankiaddon`. Fallback `user_files` возможен только когда Anki profile
runtime недоступен; штатный Anki path изолирован per profile.

Future customization может добавить `displayName`, `bio`, `avatar`, `banner`.
Media должно храниться отдельными безопасно именованными файлами и отдаваться
только token-protected endpoint после type/size/dimension validation; blobs и
absolute paths не должны попадать в JSON.

## Public payload and API

`StudyReport.profile` содержит sections:

```text
identity
studyHistory
activity
decks
preferences
```

Он JSON-safe, не содержит token, collection/profile paths или card content.
Frontend type: `ProfileModel` в `web-dashboard/src/types/report.ts`.

`GET /api/profile` возвращает актуальную public model. `POST /api/profile`
принимает только partial allowlist:

```text
customStudyStartedOn: ISO date | null
deckOverviewSort: name | reviews | active_days
```

Computed metrics, Anki profile name и unknown fields отклоняются. Invalid input
получает `400`, `invalid_profile_preferences` и typed `fieldErrors`. Оба метода
требуют текущий dashboard token.

## Deck sorting

Default — `name`; также доступны `reviews` и `active_days`. Backend сортирует
case-insensitive Unicode names, использует name и deck id как deterministic
tie-breakers, затем ограничивает ответ восемью rows. Preference сохраняется
per Anki profile, не в browser localStorage.

## Empty and low-data states

- нет profile name → `Пользователь Anki`;
- нет history → нулевые count KPI, unavailable time/pass rate, явные empty
  blocks для activity/recent/decks;
- один день → один heatmap cell, без огромной пустой сетки;
- один deck → обычная одна row;
- custom start не расширяет heatmap пустыми годами.

## Explicit non-goals

Accounts, cloud sync, social/public profile, sharing, uploads, bio editor,
achievements, goals, notifications, Activity Feed, Statistics/FSRS, Calendar
redesign, Decks/Cards v2, Search и mobile-first redesign не входят в Stage 3.

## Verification

Основные tests:

```text
tests/test_profile_service.py
tests/test_dashboard_server.py
web-dashboard/src/pages/ProfilePage.test.tsx
web-dashboard/src/lib/profileApi.test.ts
```

Docker browser smoke открывает реальный `#/profile`, проверяет identity, шесть
KPI, activity/recent/decks, save/reload двух preferences и сохраняет Profile
light/dark screenshots. Artifact manifest индексирует их как обычные page
screenshots; DOM assertion запрещает raw dashboard token.
