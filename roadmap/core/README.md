# Продуктовая ветка Core

**Трек:** `C`  
**Роль:** единственный обязательный последовательный путь основного add-on  
**Снимок:** 2026-07-22  
**Текущий статус:** `C1 завершён`; `C2 реализован, проверен и влит в core`; ручная приёмка C2 повторно открыта; `C3–C6` образуют новый обязательный путь к Core 1.0; `C1.6B` остаётся условным

Core не зависит от геймификации, аккаунтов, административного UI телеметрии или пакетов расширений. Параллельные треки не меняют критерии завершения Core.

## Модель поставки

Core разрабатывается в долгоживущей ветке `core`.

- один крупный этап решает одну продуктовую или архитектурную задачу;
- внутри этапа допускаются последовательные группы работ, но не создаётся лестница `C3.1.a`;
- merge в `core`, синхронизация с `master`, release и публикация — разные решения;
- merge в `master`, release tag, GitHub Release, `.ankiaddon`, deployment и AnkiWeb требуют отдельного одобрения владельца;
- force-push запрещён без явного одобрения;
- сообщения коммитов описывают фактические изменения;
- новый UI не добавляется как placeholder до соответствующего этапа.

## Обновлённый обязательный путь

```text
C1 Cards v2 / Problem Triage — завершён и принят
→ C2 Core 1.0 Hardening — реализован, проверен и влит в core
   → post-merge manual acceptance remediation — текущая незакрытая граница C2
→ C3 Core UI & Shell Consolidation
→ C4 First-party Data Independence
→ C5 Today v2
→ C6 Profile v2 Foundation
→ owner acceptance Core 1.0
→ отдельное решение о release
```

Не входят в обязательную очередь:

```text
C1.6B limited bulk actions — только при доказанном повторяющемся bulk-сценарии
contextual additions — evidence-triggered backlog без заранее зарезервированного этапа
Gamification G — отдельный продуктовый трек
```

# C1 — Cards v2 / Problem Triage

**Статус:** завершён, принят владельцем

## Завершённые части

| Часть | Статус | Основной источник |
| --- | --- | --- |
| C1.0 — исходное состояние | завершено | [`reports/core/c1-0-baseline.md`](../../reports/core/c1-0-baseline.md) |
| C1.1 — продуктовый контракт | завершено | [`docs/cards-v2-product-contract.md`](../../docs/cards-v2-product-contract.md) |
| C1.2 — Triage и API чтения | завершено | [`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md) |
| C1.3 — Inspection Profiles runtime | завершено | [`docs/inspection-profiles-v1.md`](../../docs/inspection-profiles-v1.md) |
| C1.4 — Inspection Profiles UI | завершено | [`docs/inspection-profiles-ui.md`](../../docs/inspection-profiles-ui.md) |
| C1.5 — исторический Cards workspace | техническое подтверждение сохранено; продуктовая приёмка отозвана | [`reports/core/c1-5-cards-workspace.md`](../../reports/core/c1-5-cards-workspace.md) |
| C1.5R — UX recovery | R0–R7 завершены и приняты | отчёты C1.5R |
| C1.6 — exact-card resolution loop | завершено, принято и влито в `core` | [`docs/cards-v2-resolution-loop.md`](../../docs/cards-v2-resolution-loop.md) |
| C1.6B — ограниченные массовые действия | условный этап, не начат | отдельное решение владельца |

C1.6 закрепил канонический lifecycle одной карточки:

```text
проблема
→ Safe Action или Open in Anki
→ результат действия
→ Awaiting recheck
→ exact-card recheck
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

C1.6B не требуется для завершения C1, Core 1.0 или следующих обязательных этапов.

# C2 — Core 1.0 Hardening

**Статус реализации:** завершено  
**Статус интеграции:** влито в `core`  
**Merge commit:** `edb140b1197910aae31500a40e4a8287cc46b760`  
**Статус владельца:** ручная приёмка повторно открыта после post-merge проверки

## Выполнено

- parser-backed политика CSS карточек и browser defense in depth;
- локальная exact-card authority без влияния unrelated profiles;
- generation-safe query, inspect, cache и mutations;
- bounded add-on Search work и concurrency gate;
- минимальный public status и корректный idle lifecycle;
- extraction только доказанных policy seams;
- behavior-based E2E helpers;
- targeted remediation Cards и Inspection Profiles;
- исправление Fast CI → E2E handoff для advisory PR associations;
- CSP-safe Vite theme bootstrap;
- exact-SHA Fast CI, targeted `standard/cards` с restart и final `standard/full`.

Полный ledger:

- [`reports/core/c2-core-hardening-ui-remediation.md`](../../reports/core/c2-core-hardening-ui-remediation.md).

## Незакрытая ручная приёмка C2

После merge владелец обнаружил регрессии и системные UX-проблемы:

- нативный фон карточки не применяется в compact и expanded preview;
- compact preview перехватывает wheel вместо page scroll;
- wide Inspector оставляет повторный нижний safe-area;
- результат Safe Actions/Open in Anki/Recheck недостаточно заметен;
- Inspection Profiles одновременно показывает Basic и Advanced как дублирующие формы;
- notices перегружены и повторяются;
- editor реагирует на viewport, а не на фактическую ширину контейнера;
- field-role inference пропускает осмысленные названия;
- refresh и state transitions ощущаются резкими;
- shape/surface grammar C2 недостаточна.

Это не новый numbered stage. Это append-only closure C2 перед началом C3.

### Критерии закрытия ручной приёмки

- preview fidelity восстановлена без ослабления CSS/CSP boundary;
- wheel ownership соответствует решению владельца;
- actions подтверждены на synthetic real-Anki fixture и имеют локальный feedback;
- Basic и Advanced взаимоисключающие;
- container-aware layout и улучшенные bounded suggestions работают;
- shared motion/shape foundation не создаёт декоративную анимацию;
- targeted и final real-Anki gates проходят;
- владелец принимает новые screenshots и ручной smoke.

# C3 — Core UI & Shell Consolidation

**Статус:** следующий обязательный этап после закрытия ручной приёмки C2

## Цель

Перестроить общую визуальную, текстовую и композиционную систему dashboard без изменения продуктовой роли Today и Profile, которые получают отдельные этапы.

C3 начинается с независимого site-wide UI/content review, затем реализует единый foundation в одном основном PR. Review не является отдельным numbered stage.

## Обязательный scope

### Полноширинный desktop layout

- App Shell и рабочие страницы используют всю доступную ширину;
- глобальный узкий centered `max-width` для dashboard запрещён;
- внешние gutters адаптивны;
- локальный `max-width` остаётся только у длинного текста, коротких форм, dialogs и других конкретных компонентов;
- на 1920 px и ultrawide дополнительная ширина даёт новые колонки или рабочее пространство, а не бессмысленно растягивает controls;
- на 1440/1280/1024 и при zoom layout перестраивается без horizontal overflow.

### Единая композиционная система

- один shared `PageHeader` contract;
- одна typography hierarchy;
- общие spacing, shape, surface и motion tokens;
- понятные роли `page`, `region`, `soft group`, `interactive item`, `status`;
- не более трёх–четырёх различимых уровней surfaces;
- без `card inside card inside card` и без плоских полотен текста;
- Refresh сохраняет старое содержимое до получения нового;
- `prefers-reduced-motion` обязателен;
- light/dark и RU/EN используют одну semantic hierarchy.

### Content cleanup

Для каждого текста требуется хотя бы одна функция:

```text
изменяемое состояние
→ объяснение неочевидного действия
→ предупреждение о реальном риске
→ помощь в решении
→ следующий шаг
```

Декоративные eyebrow-надписи, повторы route/title и общие фразы без информации удаляются.

### Shell и navigation cleanup

- удалить страницу `Инструменты`, route, API/UI glue, тесты, переводы и docs;
- перенести единственно полезные действия в Cards/Decks/Today только при наличии реального сценария;
- удалить surface `Отчёт` из Settings;
- dashboard scope сохранить и перенести в подходящую общую настройку;
- не выполнять broad payload rename только из-за исторического слова `report`;
- Search оставить route, но показать как icon-only utility action справа с accessible name/tooltip/active state;
- не полировать страницы, заранее назначенные на удаление в C4.

## Вне scope C3

- функциональная перестройка Today;
- Profile v2 и игровая система;
- удаление Sources до переноса полезных данных;
- новый frontend framework;
- mobile-first redesign;
- новые product features.

## Критерии завершения

- все сохраняемые routes прошли site-wide UI/content review;
- shared primitives используются вместо локальных page-specific inventions;
- рабочая ширина экрана используется функционально;
- obsolete Tools/Report surfaces и связанный мёртвый код удалены;
- Search перенесён в utility navigation;
- текстовое дублирование устранено;
- light/dark, RU/EN, 1920/1440/1280/1024 и keyboard/focus проверены;
- owner принимает representative screenshots всех route classes.

# C4 — First-party Data Independence

**Статус:** обязательный этап после C3

## Цель

Убрать runtime-зависимость основной функциональности Core от сторонних Anki add-ons и удалить страницу `Источник данных` только после безопасного переноса полезных возможностей.

## Последовательность

```text
inventory интеграций
→ определить фактически используемые данные
→ реализовать first-party bounded extractor через поддерживаемые Anki APIs/runtime
→ синхронизировать backend/frontend/tests/docs
→ удалить fallback на сторонний add-on
→ удалить Sources UI, legacy redirect и status endpoint
```

## Правила

- не копировать сторонний код без проверки лицензии и архитектуры;
- не заменять зависимость raw SQL или generic RPC;
- внешняя функция без first-party источника либо реализуется самостоятельно, либо честно удаляется;
- собственные logs/diagnostics остаются в Logs/Diagnostics, а не в Integrations;
- обычные pinned libraries проекта не считаются запрещёнными «чужими расширениями».

## Критерии завершения

- основная функциональность работает без сторонних Anki add-ons;
- полезные данные имеют first-party источник и bounded contract;
- неиспользуемые integrations удалены;
- `#/settings/sources`, legacy `/integrations`, API status, tests, translations и docs удалены;
- отключение любого внешнего add-on не ломает Core smoke.

# C5 — Today v2

**Статус:** обязательный этап после C4

## Продуктовая задача

`Сегодня` отвечает только на четыре вопроса:

```text
что у меня сегодня
сколько уже сделано
что требует внимания
что лучше сделать следующим
```

## Основной состав

- дата и компактный daily context;
- остаток/выполнение дневного плана;
- время, новые карточки и повторения;
- одно главное действие `Продолжить обучение в Anki`;
- ограниченный блок внимания;
- progress дня, серия и прогноз завершения;
- короткие переходы в Cards/Decks/Activity при необходимости.

## Удалить с Today

- большие исторические графики;
- таблицу всех колод;
- подробную статистику;
- FSRS calibration;
- технические сведения;
- длинные рекомендации, уже имеющие отдельные surfaces.

## Критерии завершения

- страница не дублирует Statistics, Activity, Decks, Cards или FSRS;
- пользователь за несколько секунд понимает текущий daily state и следующий шаг;
- используются shared C3 primitives и полноширинная responsive-композиция;
- empty/complete/overdue/error states проверены.

# C6 — Profile v2 Foundation

**Статус:** обязательный этап после C5

## Цель

Сделать профиль полноценной локальной identity/progress surface и подготовить безопасную основу для будущей геймификации без фиктивных игровых функций.

## Identity

- редактируемый nickname;
- короткое описание;
- локальный avatar;
- локальный banner;
- редактируемая дата начала обучения;
- fallback initials/avatar;
- MIME/size validation и безопасное удаление старых media.

## Композиция

- полноширинный banner;
- avatar + identity + edit action;
- краткая progress line;
- activity и milestones;
- реальные учебные показатели и колоды;
- layout использует всю страницу и перестраивается по ширине.

## Gamification boundary

Разрешено подготовить реальные данные:

- текущая и лучшая серия;
- активные дни;
- объём повторений;
- время обучения;
- milestones;
- stable local identity for future progress.

Не добавлять заранее:

- фиктивный `Level 1`;
- пустой XP;
- achievements/skills/quests «скоро»;
- игровую экономику без принятого трека G.

## Критерии завершения

- identity редактируется и сохраняется локально;
- avatar/banner безопасны и не используют внешние URL;
- профиль имеет полноширинную зрелую композицию;
- реальные metrics подготовлены для будущего G-track;
- Profile не дублирует Statistics и Activity.

# Core 1.0 — owner acceptance и release gate

Core 1.0 не считается готовым только потому, что C2 назывался hardening.

Перед release должны быть завершены и приняты:

```text
C2 manual acceptance remediation
C3 Core UI & Shell Consolidation
C4 First-party Data Independence
C5 Today v2
C6 Profile v2 Foundation
```

Release gate:

- production tree сопоставлен с проверенными candidates;
- все mandatory stages имеют owner acceptance;
- public navigation и docs соответствуют коду;
- package/CI/real-Anki gates проходят по актуальной policy;
- release, GitHub Release и AnkiWeb publication выполняются отдельным одобрением.

# Условные будущие дополнения

## C1.6B — limited bulk actions

Активируется только если на реальном профиле несколько сессий подряд повторяется один Safe Action минимум для 5–10 карточек и Anki Browser заметно хуже решает сценарий.

## Contextual additions

Прежний `C3 Contextual Additions` отменён как слишком общий заранее зарезервированный этап.

Любое contextual addition допускается только как отдельное доказанное предложение:

- конкретное пользовательское решение;
- доступные данные;
- bounded query;
- место в IA;
- правила интерпретации;
- критерии проверки;
- доказательство, что существующие Today, Statistics, FSRS, Search, Cards и Triage не отвечают на вопрос.

При отсутствии такого пробела работа не активируется.

## Следующее точное действие Core

```text
выполнить post-C2 manual acceptance remediation
→ owner acceptance Cards/Inspection Profiles/motion
→ начать C3 с site-wide UI/content review
```

Не начинать C1.6B, gamification production, release или merge в `master` автоматически.
