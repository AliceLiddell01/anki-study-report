# Stage 10 — Cards v2 / Problem Triage

**Status:** Next

## Цель

Превратить существующий `#/cards` из отчётной страницы проблемных карточек в рабочее место triage, опирающееся на уже готовые Search, Safe Actions, Signals и Notification Center.

## Почему этап готов к старту

- Search умеет native Cards/Notes query, inspect, selection и Browser handoff.
- Safe Actions дают undoable mutations.
- Signals создают typed причины и локальные entity references.
- Notification Center умеет contextual handoff без ID/query в URL.
- Preview isolation уже существует и не требует нового iframe/JS surface.

## Предлагаемый scope

1. **Unified triage queue**
   - sources: existing card issues, active card signals и явный Search handoff;
   - stable reason codes и severity;
   - deterministic sorting и bounded pagination.
2. **Workflow states**
   - не создавать параллельную remote task system;
   - различать «прочитано», «активная причина» и «действие выполнено»;
   - resolution определяется фактическими данными, а не ручным скрытием проблемы.
3. **Context panel**
   - concise evidence;
   - card/note/deck context;
   - safe existing preview host;
   - переход в Search/Browser.
4. **Actions**
   - переиспользовать Stage 8 action contracts и undo;
   - не создавать второй mutation API.
5. **Bulk triage**
   - bounded selection;
   - явное подтверждение destructive/high-impact actions;
   - typed partial/no-change/failure results.
6. **Signals integration**
   - signal context отображается локально;
   - действие не помечает signal resolved, пока detector evidence не исчезло.

## Out of scope

- full Anki editor clone;
- произвольный JavaScript/iframe preview;
- arbitrary custom rules;
- remote task sync;
- новый Cards payload alias;
- rich preview pipeline, если существующий isolated host решает задачу;
- mobile-first redesign.

## Completion criteria

- Один canonical triage workflow вместо дублирования Cards/Search/Notifications.
- Backend/frontend/API/test parity.
- Bounded performance на large fixture.
- Keyboard/accessibility и RU/EN/light/dark.
- Targeted real-Anki Cards scope и один final full при shared runtime changes.
- Не ослаблены sanitizer, media validation, action allowlists и loopback/token boundaries.

## Документы, которые потребуется обновить

- `docs/dashboard-api.md`
- `docs/frontend-map.md`
- `docs/navigation-ia.md`
- `docs/security-and-safety.md`
- `docs/test-matrix.md`
- новый canonical `docs/cards-v2-problem-triage.md`
