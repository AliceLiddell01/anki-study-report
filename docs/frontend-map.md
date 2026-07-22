# Карта frontend dashboard

**Снимок документации:** 2026-07-22

Актуальные контракты находятся в `docs/`, последовательность работ — в `roadmap/`, исторические отчёты и аудиты — в `reports/`.

## Источники истины

```text
web-dashboard/src/app/router.tsx
web-dashboard/src/app/App.tsx
web-dashboard/src/layout/
web-dashboard/src/pages/
web-dashboard/src/components/
web-dashboard/src/hooks/
web-dashboard/src/lib/
web-dashboard/src/types/
web-dashboard/src/i18n/
```

`App.tsx` читает токен dashboard из `window.location.search`. Frontend не читает collection Anki напрямую. Настройки темы и языка RU/EN остаются локальными и независимыми.

## Основные маршруты

```text
Сегодня → Активность → Статистика → Колоды → Поиск → Карточки
```

| Маршрут | Компонент | Данные или API | Главный риск |
| --- | --- | --- | --- |
| `#/home` | `HomePage` | `StudyReport.today` | различие текущего дня и исторического scope |
| `#/calendar` | `CalendarPage` | `activityHub` | доступность даты и scope |
| `#/stats` | страницы Statistics | API Statistics/FSRS | ограниченные запросы с latest-wins |
| `#/decks` | `DecksPage` | `deckHub`, действие Browser | семантика direct и subtree |
| `#/search` | `SearchPage` | Search v2, metadata v1 | строгий parsing и точные ID |
| `#/cards` | лениво загружаемый `CardsPage` | запрос Triage v4, recheck v1, просмотр Search v2 | ограниченное накопление, гонки действий и recheck, фокус и responsive-подробности |
| `#/settings/inspection-profiles` | `InspectionProfilesSettingsPage` | API Inspection Profiles | точные ссылки, жизненный цикл и локальные черновики |

## Каноническая идентичность карточки и предпросмотр

Один backend-projector конкретной карточки предоставляет идентичность строк и подробностей Search и элементов Triage.

`cardDisplayText()` локализует только явные состояния `media_only` и `unavailable` и не анализирует произвольные поля заметки.

```text
запрос и просмотр Search: schema v2
metadata Search: schema v1
запрос Triage: schema v4
перепроверка конкретной карточки Triage: schema v1
```

Только активный элемент Cards запрашивает просмотр Search. `AnkiCardShadowPreview` показывает санитизированную нативную лицевую сторону в Inspector или выдвижной панели. `AccessibleModal` показывает закэшированный ответ или обратную сторону.

Элементы очереди не рендерят полный HTML и не читают media.

## Топология очереди карточек, требующих внимания

```text
CardsPage
├─ компактная сводка, локальные фильтры очереди и отдельный scope запроса
├─ одно disclosure покрытия источников и профилей
└─ CardsInbox — упорядоченный семантический список
   ├─ >= 1200 px: постоянный Inspector CardsDetail
   └─ < 1200 px: очередь на всю ширину + CardsDetailDrawer
```

Основные модули:

```text
components/cards/CardsInbox.tsx
components/cards/CardsDetail.tsx
components/cards/CardsDetailDrawer.tsx
hooks/useCardsTriageWorkspace.ts
hooks/useMediaQuery.ts
lib/cardsWorkspacePolicy.ts
lib/triageApi.ts
lib/triageOrdering.ts
lib/triagePagination.ts
lib/triagePresentation.ts
styles/cardsInbox.css
```

Очередь — обычный `<ol>` с одной нативной кнопкой на элемент. Это не `table`, ARIA `grid`, `listbox` или составной элемент с roving tabindex. Фокус и активный элемент разделены.

В широком режиме первый доступный для просмотра элемент выбирается без перемещения фокуса. При 1024 px постоянный Inspector и автоматический запрос предпросмотра отсутствуют; явная активация открывает подписанную немодальную панель без backdrop, `aria-modal`, inert-оболочки и focus trap.

Граница layout точная: постоянный Inspector существует при `>= 1200 px`, drawer — при `< 1200 px`. Drawer имеет непрозрачную поверхность, явную левую границу, компактный sticky header и внутренний scroll; utility dock перемещается за пределы drawer.

Предпросмотр ответа остаётся единственным модальным диалогом.

## Состояние периода и продолжения

Hook хранит локальный для сессии период обучения:

```text
7 дней
30 дней
90 дней
```

Изменение периода запускает один автоматический запрос v4 с `contentCursor: null`, отменяет устаревшую работу, очищает накопленные страницы текущего содержимого и сохраняет локальные фильтры.

Ручное продолжение доступно только при согласованном состоянии cursor. Одна активация отправляет один запрос.

Накопление:

- дедуплицирует элементы, причины и источники;
- сохраняет канонический порядок;
- ограничено 500 уникальными элементами;
- ограничено 10 дополнительными страницами;
- сохраняет прежние пригодные элементы после ошибки;
- не запускает автоматический цикл cursor.

## Состояние жизненного цикла C1.6

`useCardsTriageWorkspace` отвечает за жизненный цикл одной карточки:

```text
idle
→ action/open handoff
→ awaiting_recheck
→ rechecking
→ still_active | partially_resolved | resolved | failed | stale
```

- mutations сериализуются и не отменяются;
- чтения используют latest-wins и защищённые sequence ID;
- mutation operation хранится независимо от query generation и остаётся глобально видимой до фактического завершения;
- refresh, период и deck могут начать новое чтение, но не скрывают pending operation; конфликтующие actions/Open/Recheck остаются отключёнными;
- inspect cache привязан к generation, ограничен 50 записями и очищается при refresh или изменении scope; устаревшее завершение не заселяет новую generation;
- успех действия не удаляет элемент;
- `recheckTriageCard()` вызывает строгий `/api/triage/recheck` v1;
- reconciliation сравнивает стабильные `reasonId`;
- оставшиеся и новые причины обновляют элемент на месте;
- элемент удаляется только после полностью авторитетного ответа без причин;
- после удаления фокус выбирает следующий или предыдущий элемент либо заголовок очереди.

Safe Actions и Open in Anki остаются существующими путями. Массовое и ручное определение устранения отсутствует.

## Рабочее пространство пошаговой настройки Inspection Profiles

`InspectionProfilesSettingsPage` объединяет:

```text
BasicProfileEditor
ProfileValidationResult
AdvancedProfileDisclosure
useInspectionProfilesWorkspace
```

Catalog имеет ширину 280–320 px на широком layout и складывается над editor при 1024 px. Обычный Basic — одна поверхность с семью смысловыми разделами: состояние, suggestion, поля, требования, scope, validation и confirmation. Advanced и Profile tools остаются отдельными disclosures; lifecycle предоставляет не более одного primary action.

`inspectionProfileBasicView.ts` — чистая понятная проекция строгого v1.

Hook отвечает за происхождение черновика, исходное состояние и пользовательские изменения, чтения latest-wins, отмену validation, сериализованные mutations и конфликты revision.

## Граница безопасности

- frontend не имеет доступа к collection;
- строгие parsers v4, v1 и v2 отклоняют неизвестные и несогласованные payload;
- точные ID карточек используются для inspect, recheck и Open in Anki;
- отображаемый текст не превращается в нативный запрос;
- sanitizer, проверенные URL media и изоляция Shadow DOM сохраняются;
- определение устранения проблемы на клиенте отсутствует;
- C1.6 не добавляет второй стек детекторов или действий.

## Профильные тесты

```text
pages/CardsPage.test.tsx
pages/CardsVisualContract.test.ts
hooks/useCardsTriageWorkspace.test.tsx
components/cards/CardsInbox.test.tsx
components/cards/CardsDetailDrawer.test.tsx
lib/triageApi.test.ts
lib/triagePagination.test.ts
lib/triageOrdering.test.ts
hooks/useMediaQuery.test.tsx
components/AnkiCardShadowPreview.test.tsx
pages/InspectionProfilesVisualContract.test.ts
pages/LocalizationSmoke.test.tsx
```

Набор frontend-тестов C1.6:

```text
342 теста — PASS
TypeScript typecheck — PASS
production-сборка — PASS
ограничение bundle — PASS, entry 430 646 байт
```

## Текущий статус Core

```text
C1.5R.0–R.7 — завершено; принято владельцем
C1.6 — завершено; принято владельцем; влито в core
C1.6B — условный этап; не начат
Core C1 — завершён
C2 — implementation candidate; exact-SHA integration closeout pending
```
