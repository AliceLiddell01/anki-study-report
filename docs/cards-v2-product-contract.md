# Продуктовый контракт Cards v2

## Статус и scope

**Статус:** `C1.5R` и `C1.6` завершены и приняты владельцем  
**Ветка:** `core`  
**Merge C1.6:** `928e3fe749ce6aa4b9c414641c4ef66ac46a694b`  
**Core C1:** Complete  
**C1.6B:** Conditional; not started

Технические контракты:

- [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md);
- [`cards-v2-resolution-loop.md`](cards-v2-resolution-loop.md);
- [`inspection-profiles-v1.md`](inspection-profiles-v1.md).

Cards — локальное рабочее пространство problem triage. Оно показывает карточки, требующие внимания, объясняет причины, предоставляет безопасный context и ведёт к существующему Safe Action либо нативному редактированию Anki.

Текущий workflow `#/cards` зафиксирован в [`cards-attention-inbox.md`](cards-attention-inbox.md). [`cards-v2-workspace-ui.md`](cards-v2-workspace-ui.md) является историческим документом отклонённого C1.5 UI.

Не приняты assignment, snooze/archive, remote collaboration, manual resolve и persistent completion state.

## Пользовательская проблема

Cards v1 повторял одну классификацию в hero copy, KPI, tabs, problem filter и row chips. Представления `Risk`, `Gaps`, `Patterns` и `Check` перекрывались; numeric `riskScore` не объяснялся; table/tiles/Anki preview дублировали одну очередь с разной плотностью; full previews создавали чрезмерно длинные страницы.

Цель пользователя — не «закрыть inbox», а:

1. понять проблему карточки;
2. выбрать безопасное действие либо открыть карточку в Anki;
3. явно перепроверить результат;
4. получить канонический вывод о том, осталась ли проблема активной.

## Jobs to be done

**Основная задача:** понять обнаруженную проблему карточки и выбрать следующий безопасный шаг, не превращая dashboard во второй editor Anki.

Точки входа:

- прямой переход;
- notification карточки;
- explicit Search selection;
- возврат из Anki Browser.

Happy path:

1. Открыть `Требуют внимания / Requires attention`.
2. Просмотреть priority, primary reason и short evidence.
3. Активировать item; Inspector открывается без перемещения keyboard focus.
4. Изучить safe preview, все reasons и recommended next step.
5. Выполнить существующий Safe Action либо Open in Anki.
6. Увидеть `Ожидает перепроверки / Awaiting recheck`.
7. Запустить explicit recheck.
8. Получить `Still active`, `Partially resolved`, `Resolved`, `Recheck failed` или `Evidence stale`.

Opening/editing in Anki никогда автоматически не означает resolved. Успешная mutation и `action.no_changes` также не являются resolution proof.

Для unknown note types learning issues сохраняются, а content-quality issues подавляются до confirmation Inspection Profile.

## Границы поверхностей

| Surface | Основная задача | За что отвечает | Handoff | Что не должна дублировать |
| --- | --- | --- | --- | --- |
| Cards | triage обнаруженных проблем | bounded queue, active Inspector/drawer, lifecycle action/recheck | Safe Action или Anki Browser | общий Search, full editor, notification history, arbitrary actions |
| Search | поиск произвольных cards/notes | query, results, selection, Search Inspector | Cards workset или Anki Browser | detector priority/lifecycle и automatic queue |
| Notification Center | уведомление и local history | notification/read/history state | Cards для card issues; Decks/Stats для остальных | triage, editing, manual resolve |
| Anki Browser | native search/edit/advanced operations | authoritative collection UI/edit state | возврат в Cards/Search | dashboard diagnosis или web editor clone |

Anki note types имеют разные fields и templates. Cards не предполагает universal card schema и не копирует Anki editor.

## Каноническая очередь

Automatic dataset:

```text
Требуют внимания / Requires attention
```

Это одна bounded queue с filters. Reason families не являются tabs, потому что фильтруют тот же dataset и тот же workflow.

Search handoff создаёт отдельный selector:

```text
Требуют внимания | Выбрано в поиске
Requires attention | Selected in Search
```

Automatic sources:

- canonical attention-card learning issues;
- active card-level Signals;
- confirmed-profile current-content issues.

Notification является activation context, а не новым queue source. Search workset остаётся session-only и не получает invented reasons или priority.

Duplicate automatic card IDs объединяются в один card-anchored item с merged reasons и visible provenance. Equivalent evidence дедуплицируется.

## Модель item и reason

Один item привязан к одной card и агрегирует до четырёх stable reasons.

Primary reason выбирается по categorical priority и deterministic reason order. Additional reasons показываются count в queue и полностью в Inspector.

Card-level reasons относятся к scheduling/review/card state. Note-level reasons относятся к shared content/profile requirements.

Для note-level-only issue используется одна deterministic representative card с указанием sibling impact. Siblings остаются отдельными, если у них есть независимые card-level reasons.

Reason families:

| Family | Значение | Примеры |
| --- | --- | --- |
| Learning behavior | наблюдаемое review behavior | leech, repeated Again, low pass rate, slow answer |
| Content quality | нарушено confirmed profile requirement | missing text/audio/image, text too short |
| System/profile state | configuration/evidence не authoritative | profile needs review, source unavailable/stale |
| Manual context | explicit user workset | selected in Search |

Stable IDs:

```text
learning:<code>
profile:<profileId>:check:<checkId>
```

## Priority и evidence

Visible priority:

```text
Высокий / Средний / Низкий
High / Medium / Low
```

Priority отвечает, что проверить первым; reason объясняет почему. Отдельного Critical и visible numeric score нет. Priority назначается canonical backend sources, а не вычисляется UI.

Queue показывает одно bounded evidence sentence. Inspector показывает details, window, freshness и source.

Insufficient, stale и unavailable evidence обозначается явно. Raw queries, IDs, tokens, paths, card content и full evidence исключены из normal logs, public artifacts и remote telemetry.

Default order:

```text
priority → canonical reason order → evidence recency → stable card ID
```

Focus/selection не меняют order. Explicit refresh или authoritative recheck может обновить position при изменении reasons/priority.

## Product model Inspection Profile

Profiles — local declarative requirements конкретного note type. Они не выполняют user code.

| State | Значение | Authoritative content issues |
| --- | --- | --- |
| Not configured | profile отсутствует | нет |
| Suggested | inferred mapping ожидает review | нет |
| Confirmed | requirements/mapping приняты | да |
| Needs review | structure note type изменилась | нет; fail closed |
| Disabled | content checks отключены | нет |

Suggestion не становится authority автоматически. Confirmation явное. Несовместимые изменения fields/templates переводят profile в Needs review. Learning issues не зависят от profile lifecycle.

## Основное рабочее пространство

Канонический layout:

```text
wide desktop >= 1200 px
compact summary/filters
semantic ordered inbox | persistent Inspector

narrow desktop < 1200 px
compact summary/filters
full-width inbox
non-modal detail drawer после explicit activation
```

Spreadsheet table, tiles и equal display-mode switcher отсутствуют.

Initial response ограничен 100 issues. Full preview загружается только для active item. Learning period явный: 7/30/90 дней. Current-content continuation ручной, cursor-coherent и client-bounded.

Checkbox отсутствует. Bounded bulk actions относятся только к conditional C1.6B.

## Inspector

Sections:

1. safe front preview;
2. card/note identity;
3. все scoped reasons;
4. evidence и freshness;
5. Inspection Profile source;
6. current lifecycle state;
7. recommended step;
8. применимые Safe Actions;
9. Open in Anki;
10. explicit recheck и reconciliation result.

Full answer открывается через существующий accessible modal. Field/template editor отсутствует.

## Search workset и Notification handoff

Search workset является explicit session-only dataset, визуально отделённым от automatic queue. Он безопасно истекает, имеет return-to-Search и clear actions и получает canonical reasons только при independent detection.

Notification handoff:

```text
notification → Cards → referenced card active → matching reason expanded
```

Entity IDs не записываются в URL или persistent storage.

## Resolution semantics C1.6

```text
issue
→ existing Safe Action or Open in Anki
→ action result
→ Awaiting recheck
→ exact-card canonical bounded recheck
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

Recheck использует `POST /api/triage/recheck` schema v1 и те же canonical detectors, что Triage v4.

Reason reconciliation:

- remaining reasons обновляют item на месте;
- removed + remaining дают Partially resolved;
- new reasons показываются явно;
- zero reasons удаляют item только при fully authoritative response;
- partial/unavailable/stale/missing/changed состояния работают fail closed.

После удаления focus переходит на следующий item, затем предыдущий, затем queue heading.

Запрещены actions `Done`, `Resolve`, `Hide forever`, `Ignore permanently`, `Archive`, `Snooze`.

## Empty, error и stale states

| State | Поведение |
| --- | --- |
| no problems | positive empty state + last successful evaluation |
| no filtered results | filters сохраняются; clear/reset доступен |
| collection unavailable | blocking explanation/retry; stale не выдаётся за current |
| evidence stale | warning + bounded recheck/refresh |
| profile not configured/needs review | affected content issues suppressed + settings path |
| preview unavailable | text/reasons/actions сохраняются |
| detector unavailable | family unavailable; отсутствие не означает resolved |
| Search workset expired | explanation, safe clear, return to Search |
| card deleted/changed | exact identity revalidation и безопасное focus recovery |
| action pending | conflicting mutations disabled; progress announced |
| recheck failed | item остаётся active/stale; retry; resolved не заявляется |

## Keyboard и accessibility

Focus, active item и будущая bulk selection являются отдельными states.

- Tab order охватывает filters, queue и Inspector;
- activation item не перемещает focus;
- queue использует semantic ordered list и native buttons;
- `table`, ARIA `grid`, `listbox`, `option`, roving tabindex не используются;
- drawer non-modal и без focus trap;
- answer modal сохраняет trap/inert semantics;
- action/recheck используют busy state и polite live announcements;
- post-resolution focus recovery deterministic;
- state/priority не выражаются только цветом.

## Responsive boundary

- `1200 CSS px+`: split inbox/Inspector;
- ниже 1200 px: full-width inbox + non-modal drawer;
- mobile-first redesign вне scope.

## RU/EN terminology

| RU | EN |
| --- | --- |
| Требуют внимания | Requires attention |
| Причина | Reason |
| Приоритет | Priority |
| Основание | Evidence |
| Выбрано в поиске | Selected in Search |
| Перепроверить | Recheck |
| Ожидает перепроверки | Awaiting recheck |
| Всё ещё требует внимания | Still active |
| Частично устранено | Partially resolved |
| Устранено после перепроверки | Resolved after recheck |
| Не удалось перепроверить | Recheck failed |
| Основание устарело | Evidence stale |

## Security, privacy и boundedness

Frontend не читает collection напрямую. Сохраняются loopback/token protection, sanitizer, media validation, Shadow DOM isolation и action allowlists.

Запрещены arbitrary SQL/RPC/JavaScript/Python/iframe, second detector/action stack и client-side resolution inference.

IDs, raw queries, content, paths, tokens и full evidence не попадают в normal logs, public artifacts или remote telemetry.

Queue, continuation, recheck и result payloads имеют strict bounds. Reads latest-wins; mutations serialized; long collection work использует Anki background operations; writes используют official undoable wrappers.

## Явно отклонённые альтернативы

- tabs по reason families;
- смешанная automatic/Search queue;
- table/tiles/Anki-preview как равноправные modes;
- preview для каждой строки;
- visible numeric risk score;
- manual resolve/hide/archive/snooze;
- unconfirmed heuristic content checks;
- arbitrary user rules/code;
- full editor внутри Cards;
- automatic cursor loop;
- bulk actions без отдельного C1.6B activation decision.