# Cards v2 Product Contract

## Status and scope

**Status:** Accepted product contract; canonical workspace implemented in `C1.5`
**Branch:** `core`
**Production status:** `#/cards` consumes canonical triage v2 through a compact queue and persistent Inspector

Technical contracts: [`cards-v2-triage-read-api.md`](cards-v2-triage-read-api.md)
and [`inspection-profiles-v1.md`](inspection-profiles-v1.md).

Cards is a local problem-triage workspace: it shows which cards require attention, explains why, provides safe context, and hands the user to an existing Safe Action or native Anki editing.

This contract defines the `#/cards` workflow. C1.5 resolves the queue/Inspector layout and accessibility behavior in [`cards-v2-workspace-ui.md`](cards-v2-workspace-ui.md). Assignment, snooze/archive, remote collaboration and manual resolve are not adopted.

## User problem

Cards v1 repeats one classification in hero copy, five KPIs, tabs, a problem filter and row chips. `Risk`, `Gaps`, `Patterns` and `Check` are overlapping views; numerical `riskScore` is unexplained; table/tiles/Anki preview repeat one queue at different densities; full previews create pages up to 18,329 px high.

The outcome is not “finish an inbox”. The user understands an issue, acts safely or edits in Anki, then canonical reevaluation decides whether it remains active.

## Jobs to be done

**Primary job:** understand a detected card problem and choose the next safe step without turning the dashboard into another editor.

Entry: direct navigation, card notification, explicit Search selection, return from Anki Browser, or bounded batch triage.

Happy path:

1. Open `Требуют внимания / Requires attention`.
2. Scan priority, primary reason and short evidence.
3. Activate a row; Inspector opens without moving keyboard focus.
4. Inspect safe preview, all reasons and recommended next step.
5. Run an existing Safe Action or open Anki Browser.
6. See `Ожидает перепроверки / Awaiting recheck`.
7. Recheck; item stays active or resolves canonically.

Opening/editing in Anki never marks resolved. On return, evidence may be stale; context/focus is restored when possible. Bulk actions operate only on explicitly selected bounded IDs. For unknown note types, learning issues remain; content-quality issues are suppressed until an Inspection Profile is confirmed.

## Surface boundaries

| Surface | Primary task | Owns | Handoff | Must not duplicate |
| --- | --- | --- | --- | --- |
| Cards | triage detected card problems | bounded queue presentation, active Inspector, temporary Search workset | Safe Action or Anki Browser | general Search, full editor, notification history, arbitrary actions |
| Search | find arbitrary cards/notes | query/results/selection/Search Inspector | Cards workset or Anki Browser | detector priority/lifecycle and Cards queue |
| Notification Center | notify and preserve local history | notification/read/history state | Cards for card issues; Decks/Stats otherwise | triage/editing/manual resolve |
| Anki Browser | native search/edit/advanced operations | authoritative collection UI/edit state | return to Cards/Search | dashboard diagnosis or duplicate web editor |

Anki note types may have different fields, and templates determine generated cards/front/back. Cards cannot assume one universal schema or clone Anki's editor.

## Canonical queue

Automatic dataset:

```text
Требуют внимания / Requires attention
```

It is one bounded queue with filters. Reason families are not tabs because they filter the same set/workflow.

When Search explicitly hands off IDs, a second dataset selector appears:

```text
Требуют внимания | Выбрано в поиске
Requires attention | Selected in Search
```

Automatic sources: canonical attention-card issues and active card-level Signals. Notification is activation context for a canonical issue, not another queue source. Search creates a separate session-only workset and never receives invented reason/priority.

Duplicate automatic card IDs become one card-anchored item with merged reasons and visible provenance. Equivalent evidence is deduplicated.

## Item and reason model

One row is anchored to one card and aggregates reasons. Primary reason is selected by priority and deterministic reason order; additional reasons appear by count and in Inspector.

Card-level reasons concern scheduling/review/card state. Note-level reasons concern shared content/profile requirements. A note-level-only issue uses one deterministic representative card and states sibling impact; siblings remain separate when they have independent card reasons. Note actions explicitly name note scope.

Reason families:

| Family | Meaning | Examples |
| --- | --- | --- |
| Learning behavior | observed review behavior | leech, repeated Again, low pass rate, slow answer |
| Content quality | confirmed profile requirement unmet | missing meaning/audio/example/image/part of speech |
| System/profile state | confidence/configuration incomplete | profile not configured/needs review, stale/unavailable source |
| Manual context | explicit user workset | selected in Search |

Canonical learning/content codes, stable reason identity and safe evidence are
defined in triage schema v2; user meaning/scope remain fixed here.

## Priority and evidence

Visible priority is `Высокий / Средний / Низкий` (`High / Medium / Low`). It answers what to inspect first; reason answers why. No separate Critical level and no visible numeric score. Canonical sources assign priority; UI does not infer it.

A row shows one evidence sentence. Inspector shows bounded details, window, freshness and source. Examples: `5 Again из 8 за 7 дней`; `успешность 42% при 12 ответах`; `Confirmed profile requires Audio; mapped field is empty/no [sound:…]`.

Insufficient/stale/unavailable evidence is explicit. Raw queries, IDs, tokens, paths, card content and full evidence are excluded from normal logs/public artifacts/remote telemetry.

Default order:

```text
priority → reason order → evidence recency → stable entity tie-breaker
```

Rows do not jump due to focus/selection. Explicit refresh may reorder when evidence changes, while preserving the active card when possible. Stable user sorts may include priority, newest evidence, deck and primary text.

## Inspection Profile product model

Profiles are local, declarative, per-note-type requirements for content checks; they never execute user code.

| State | Meaning | Authoritative content issues |
| --- | --- | --- |
| Not configured | absent | no |
| Suggested | inferred mapping awaiting review | no |
| Confirmed | requirements/mapping accepted | yes |
| Needs review | note-type structure changed incompatibly | no; fail closed |
| Disabled | user disabled content checks | no |

Suggestion explains required roles and mapped fields; confirmation is explicit. Incompatible rename/add/remove/reorder/template-reference change moves to Needs review. Cards explains suppression and links to settings. Disabling content checks does not disable learning issues. C1.3 owns the versioned schema, fingerprint, profile-local store, allowlisted runtime and API; the final editor belongs to C1.4.

## Main workspace

Три равноправных режима `table`, `tiles` и `Anki preview` больше не являются
канонической навигацией Cards. Основной workflow строится вокруг одной
компактной очереди и Inspector выбранной карточки. Сама очередь может быть
реализована как плотная таблица, структурированный список или гибридный
интерактивный grid — окончательный вариант определяется прототипированием и
accessibility-тестами. Anki preview сохраняется для активной карточки и при
необходимости может разворачиваться. Tiles не входят в обязательный C1
workflow, но отдельный визуальный режим допустим в будущем только при доказанной
пользовательской задаче.

Desktop layout:

```text
header + compact summary
filters/sorting
bounded compact queue | Inspector
contextual bulk toolbar when selection exists
```

Replace five KPI cards with one cap-aware summary (active total, high priority, profile warning). Counters represent the bounded result, not loaded page, and disclose truncation. The first row should normally appear in the initial desktop viewport; template/display diagnostics leave the main path.

Always-visible filters: text, reason family, priority, deck, sort. Advanced: exact reason, note type, source, card state, freshness/profile state. Summary counters are shortcuts only when active-filter state is explicit.

## Queue row

Required in C1.5: compact front/primary text, deck, categorical priority,
primary reason, additional-reason count, short evidence and relevant card state.
The checkbox is intentionally absent until C1.6 owns bounded bulk actions.

Excluded from scan path: full answer preview, template catalog, opaque score, every metric, repeated query text and several always-visible actions. Row activation opens Inspector; checkbox changes bulk selection only. A quick row action is allowed only after usability/accessibility evidence.

## Inspector

Wide desktop default: persistent right pane. Narrow desktop: stacked detail or non-modal drawer. Modal/inline expansion are not defaults.

Sections: safe preview; card/note identity; all scoped reasons; evidence/freshness; Inspection Profile source; current state; recommended step; existing Safe Actions; Open in Anki; recheck/result.

No field/template editor. Preview reuses existing sanitized, token-protected Shadow DOM and renders fully only for the active item.

## Filters and summary

One filter system replaces tabs/KPIs/dropdowns that classify the same set. Family and exact reason are dependent. Summary is compact and cap-aware. Filtered empty state preserves controls and offers clear/reset.

## Search workset

`Выбрано в поиске / Selected in Search` is explicit, session-only, visually marked and separate from the automatic queue. It has return-to-Search and clear actions, expires safely, and gains canonical reasons/priority only when independently detected. Otherwise it is neutral manual context, not Low priority. Storage/TTL shape is deferred.

## Notification handoff

```text
notification → Cards → referenced card active → matching reason expanded
```

Reuse the existing session handoff; IDs do not enter URL/persistent storage. Changed/resolved/deleted state is explained rather than recreated. Deck signals stay in Decks; workload/retention stay in Statistics.

## Resolution semantics

```text
Active → Action in progress → Awaiting recheck → Still active | Resolved after recheck
```

Mutation success does not prove resolution. Native edits make evidence potentially stale. A row leaves the automatic queue only when canonical reevaluation no longer reports the reason. Brief session feedback is allowed; durable notification history remains. `Done`, `Resolve`, `Hide forever`, `Ignore permanently` are prohibited.

## Empty/error/stale states

| State | Behavior |
| --- | --- |
| no problems | positive empty state + last successful evaluation |
| no filtered results | preserve filters; clear/reset |
| collection unavailable | blocking explanation/retry; do not present stale as current |
| report/evidence stale | freshness warning + bounded refresh |
| profile not configured/needs review | suppress affected content issues + settings path |
| preview unavailable | keep text/reasons/actions |
| detector unavailable | mark family unavailable; absence does not resolve |
| Search workset expired | explain, clear safely, return to Search |
| card deleted/changed | revalidate identity; preserve focus safely |
| action pending | disable conflicting mutations; announce progress |
| recheck failed | keep active/stale; retry; never claim resolved |

## Keyboard and accessibility contract

Focus and the active Inspector item are independent in C1.5. Future C1.6 bulk
selection must become a third independent state rather than reuse either one.

Tab order covers filters, queue and Inspector. Row activation does not move
focus. Escape closes expanded preview and returns focus. Refresh keeps the
active item when it survives and otherwise chooses the first inspectable row.
Filters have persistent labels/state. Mutation, recheck, checkbox selection and
bulk toolbar semantics are deferred to C1.6.

Do not assume `listbox`: options cannot accessibly contain required links/buttons/checkboxes. Native table, structured list and grid remain prototype alternatives; grid requires a complete composite focus model. Final roles are deferred to keyboard/screen-reader testing.

## Responsive boundary

- about `1180 CSS px+`: split queue/Inspector;
- about `900–1179 px`: narrow split or stacked/drawer;
- below about `900 px`: functional stacking only; mobile-first redesign is out of scope.

## RU/EN terminology

| RU | EN |
| --- | --- |
| Требуют внимания | Requires attention |
| Причина | Reason |
| Приоритет | Priority |
| Основание | Evidence |
| Выбрано в поиске | Selected in Search |
| Перепроверить | Recheck |
| Профиль проверки | Inspection Profile |
| Ожидает перепроверки | Awaiting recheck |
| Всё ещё требует внимания | Still active |
| Устранено после перепроверки | Resolved after recheck |

`Основание` is the preferred user-facing Russian label; it sounds less forensic than a literal `Доказательства`.

## Security and privacy boundaries

Frontend never reads collection directly; loopback/token protection stays. Reuse Search/Safe Actions/Signals/Notifications; no duplicate stack. No arbitrary SQL/RPC/JavaScript/Python/iframe. Sanitizer, media validation and Shadow DOM isolation remain. Profiles are local/declarative. IDs, raw queries, content, paths, tokens and full evidence stay out of normal logs/public artifacts/remote telemetry. Screenshot binaries/runtime artifacts are not committed.

## Performance/boundedness expectations

Queue has explicit cap and cap-aware total/truncation. Details/full preview load for active item, not all rows. Pagination/windowing is chosen from measured fixtures. Typing/filtering does not start unbounded collection scans. Reads remain cancellable/latest-wins where relevant. Long collection work uses Anki background operations; writes reuse official serialized/undoable operations.

## Explicitly rejected alternatives

- reason-family tabs;
- mixed automatic/Search queue;
- three equal table/tiles/Anki-preview modes as canonical Cards navigation;
- preview for every row;
- visible numeric score;
- reason-only ordering;
- manual Done/Resolve/Hide/Ignore;
- universal/unconfirmed heuristic content checks;
- arbitrary user rules/code;
- full editor in Cards;
- automatic listbox semantics;
- modal/inline expansion as wide-desktop default.

## Screenshot evidence matrix

All files are original pre-change evidence and are not committed.

| Decision | Evidence | Observation |
| --- | --- | --- |
| one queue + filters | all 12, especially table tops | KPIs/tabs/dropdown/chips repeat classification |
| remove four tabs | all modes/themes + code | Gaps/Patterns are presets; Risk/Check overlap |
| compact summary | all top sections | five KPIs delay first row |
| queue + Inspector | table/tiles | context useful for one item; repetition harms scanning |
| tiles are not required in C1 | APKG/synthetic tiles | larger area without a separate proven task; a future visual mode remains possible |
| selected-card preview, expandable when needed | APKG preview 9,877 px; synthetic 18,328–18,329 px | full preview for every row creates extreme page length |
| hide score | risk pills in all modes | exact values do not explain decisions |
| preserve theme parity | every light/dark pair | same structural findings |
| profile-aware content | synthetic set | heterogeneous Japanese/programming/fallback content |

Inventory coverage: `APKG/synthetic × table/tiles/Anki preview × light/dark` = **12/12**. Heights: table 3,133/5,543 px; tiles 3,826/7,133 px; preview 9,877/18,328–18,329 px.

## Decision log

| Decision | Evidence | Alternatives | Why selected | Deferred implementation question |
| --- | --- | --- | --- | --- |
| one automatic queue | overlapping code/screens; tabs require distinct panels | family tabs | one job/set; filters express facets | exact filter controls |
| separate Search workset | different provenance/semantics | merge/no handoff | avoids invented priority | TTL/transfer shape |
| card-anchored aggregation | card scheduling + note content scopes | row per reason/note row | compact with explicit scope | representative/source precedence |
| categorical priority | opaque score screenshots | numeric/reason-only/critical | understandable, localizable | mapping per reason |
| confirmed profiles | arbitrary Anki fields/templates | universal/unconfirmed/code | explainable, fail closed | schema/fingerprint/editor |
| detector resolution | action ≠ issue gone | Done/Hide/Ignore | preserves truth | recheck scheduling/failures |
| queue form remains prototype-driven | table/list/grid accessibility trade-offs | freeze table or ban it | preserves the compact queue contract without prematurely fixing semantics | density, roles and focus model |
| semantics after prototype | listbox conflict; grid complexity | freeze role now | avoids premature inaccessible choice | roles/focus/AT matrix |

## Remaining open questions after C1.3

1. Search TTL/return token without persistent IDs;
2. optional quick row action;
3. final list/table/grid semantics after accessibility tests;
4. non-blocking recheck after Browser edits;
5. C1.4 profile configuration UX and separately scoped import/export policy.

## Acceptance criteria

Accepted: one clear job/boundaries; automatic queue vs Search workset; aggregation/reason/priority/evidence/order; compact queue + Inspector; profile lifecycle/fail-closed checks; handoffs; detector-driven resolution; state/accessibility/security/boundedness contracts; 12/12 screenshot evidence; no production/test/workflow/release/E2E change.

## Increment closure

C1.2 established the bounded card-anchored read model. C1.3 completed the
profile schema/store/fingerprint/runtime and triage v2 content source. C1.4 may
build configuration UI on those APIs; it must not change authority, sibling,
fail-closed or arbitrary-code boundaries without a versioned contract change.

## External references

- [Anki Manual — Getting Started](https://docs.ankiweb.net/getting-started.html)
- [Anki Manual — Card Templates](https://docs.ankiweb.net/templates/intro.html)
- [Anki Manual — Browsing](https://docs.ankiweb.net/browsing.html)
- [Writing Anki Add-ons — Background Operations](https://addon-docs.ankiweb.net/background-ops.html)
- [WAI-ARIA APG — Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)
- [WAI-ARIA APG — Listbox](https://www.w3.org/WAI/ARIA/apg/patterns/listbox/)
- [WAI-ARIA APG — Table](https://www.w3.org/WAI/ARIA/apg/patterns/table/)
- [WAI-ARIA APG — Grid](https://www.w3.org/WAI/ARIA/apg/patterns/grid/)
- [WAI-ARIA APG — Toolbar](https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/)
- [Linear Docs — Triage](https://linear.app/docs/triage)
- [Linear Docs — Inbox](https://linear.app/docs/inbox)
- [Sentry Docs — Issue Details](https://docs.sentry.io/product/issues/issue-details/)
