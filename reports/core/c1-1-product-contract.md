# C1.1 Cards v2 Product Contract report

**Date:** 2026-07-18
**Repository:** `AliceLiddell01/anki-study-report`
**Active branch:** `core`
**Stage:** `C1.1 — Product contract`

## Repository baseline

| Item | Verified value |
| --- | --- |
| Core HEAD before work | `2b99b3468de0a46b00ce5be71e7c95da0930fb12` |
| Core commit | `docs: establish the long-lived core branch baseline` |
| Base branch | `master` |
| Master/base SHA | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Divergence before C1.1 | ahead 1, behind 0 |
| Pre-existing Core diff | C1.0 documentation only |
| Open PRs before write | none |

The branch ref and divergence were rechecked before the documentation write. No post-C1.0 production change was present in `core`.

## Capability matrix

| Capability | Status |
| --- | --- |
| GitHub read/branch/compare | available and used |
| GitHub documentation write/commit/push | available and used only for `core` |
| Attachments and ZIP extraction | available; `cards.zip` extracted |
| Image viewing | available; all 12 PNGs visually reviewed without OCR |
| Web search | available; official/primary sources used |
| Local shell | available for attachment inventory and Markdown checks, not a repository checkout |
| Local Git checkout | unavailable |
| Project test/runtime execution | not run; not required for docs-only C1.1 |
| Docker/real Anki | not run; not required |

## Project files read

Current project entrypoints/contracts:

- `README.md`
- `docs/ai-handoff.md` from `core`
- `roadmap/README.md`
- `roadmap/core/README.md` from `core`
- `reports/core/c1-0-baseline.md`
- `docs/project-overview.md`
- `docs/architecture.md`
- `docs/frontend-map.md`
- `docs/dashboard-api.md`
- `docs/search-v1-and-safe-actions.md`
- `docs/signals-foundation.md`
- `docs/notification-center.md`
- `docs/security-and-safety.md`
- `docs/test-matrix.md`
- `docs/verification-run-policy.md`
- `docs/README.md`

Production/contract inventory:

- `web-dashboard/src/pages/CardsPage.tsx`
- `web-dashboard/src/lib/cardAttention.ts`
- `web-dashboard/src/types/report.ts`
- Cards tests and RU/EN i18n locations
- `anki_study_report/metrics.py`
- `anki_study_report/note_intelligence.py`
- `anki_study_report/signal_detection.py`
- `anki_study_report/entity_actions.py`
- `web-dashboard/src/hooks/useSearchWorkspace.ts`
- `web-dashboard/src/pages/SearchPage.tsx`
- `web-dashboard/src/lib/notificationHandoff.ts`
- `web-dashboard/src/components/AnkiCardShadowPreview.tsx`
- related backend/frontend contract-test locations identified by current docs/search.

No source was claimed as read solely because it appeared in the task list.

## `cards.zip` inventory

The owner clarified that these are the original/pre-change screenshots of the current Cards section. All expected combinations are present.

| File | Fixture | Theme | Mode | Dimensions | Approx. size | Key state |
| --- | --- | --- | --- | --- | --- | --- |
| `cards/apkg/table/dark.png` | APKG | dark | table | 1440×3133 | 517 KiB | dense table, current filters/tabs/actions |
| `cards/apkg/table/light.png` | APKG | light | table | 1440×3133 | 628 KiB | same structure, light parity |
| `cards/apkg/tiles/dark.png` | APKG | dark | tiles | 1440×3826 | 580 KiB | large repeated cards |
| `cards/apkg/tiles/light.png` | APKG | light | tiles | 1440×3826 | 693 KiB | same structure, light parity |
| `cards/apkg/anki-preview/dark.png` | APKG | dark | Anki preview | 1440×9877 | 973 KiB | answer preview repeated for queue |
| `cards/apkg/anki-preview/light.png` | APKG | light | Anki preview | 1440×9877 | 1078 KiB | same structure, light parity |
| `cards/synthetic/table/dark.png` | synthetic | dark | table | 1440×5543 | 749 KiB | heterogeneous long rows/chips |
| `cards/synthetic/table/light.png` | synthetic | light | table | 1440×5543 | 888 KiB | same structure, light parity |
| `cards/synthetic/tiles/dark.png` | synthetic | dark | tiles | 1440×7133 | 870 KiB | very long tile queue |
| `cards/synthetic/tiles/light.png` | synthetic | light | tiles | 1440×7133 | 1035 KiB | same structure, light parity |
| `cards/synthetic/anki-preview/dark.png` | synthetic | dark | Anki preview | 1440×18328 | 1303 KiB | extreme variable-height preview page |
| `cards/synthetic/anki-preview/light.png` | synthetic | light | Anki preview | 1440×18329 | 1459 KiB | extreme variable-height preview page |

Coverage: `APKG/synthetic × table/tiles/Anki preview × light/dark` = **12/12**.

## Visual audit

Confirmed observations:

1. too much non-actionable material precedes the first queue item: hero, five KPI blocks, display explanation, template diagnostics, filters and overlapping categories;
2. KPI, tabs, problem dropdown and row chips repeat the same classification;
3. `Risk` and `Check` do not create different workflows; code confirms Check only adds deck selection;
4. `Gaps` and `Patterns` are preset filters over the same rows;
5. risk numbers look authoritative but do not explain the decision;
6. tiles consume more area without a separate task;
7. Anki preview for every item creates 9,877–18,329 px pages;
8. full safe preview is valuable for one selected item, not every queue item;
9. repeated per-row actions add noise and keyboard stops;
10. long deck names/chips and heterogeneous content reduce table comparability;
11. structural findings reproduce in light and dark themes;
12. synthetic fixtures demonstrate why one universal content schema is unsafe.

## External sources and applied conclusions

### Official Anki

Read official Manual pages for notes/note types/card types, templates, Browser, Search and editing, plus Writing Anki Add-ons background-operation guidance.

Applied:

- note types and templates are heterogeneous;
- templates determine generated cards and front/back presentation;
- Anki Browser already owns native search/edit/advanced operations;
- Cards must not clone the editor;
- potentially long collection reads must not block UI; existing QueryOp/CollectionOp patterns remain authoritative.

### W3C WAI-ARIA APG

Read Tabs, Listbox, Table, Grid and Toolbar patterns.

Applied:

- reason categories do not justify tabs because they do not open distinct panels;
- focus, active row and bulk selection are separate states;
- listbox is not assumed because options cannot accessibly contain the required interactive descendants;
- grid/table/list semantics remain prototype-and-test decisions.

### Triage references

Read official Linear Triage/Inbox and Sentry Issue Details documentation.

Applied only:

- compact intake queue;
- quick review/prioritization;
- active item opens detailed context/evidence.

Not adopted: assignment, accept/decline, snooze, archive, comments, remote collaboration or manual resolution.

## Accepted product decisions

1. Cards is a local problem-triage workspace, separate from Search, Notification Center and Anki Browser.
2. One automatic `Требуют внимания / Requires attention` queue replaces four category tabs.
3. Search creates a separate session-only `Выбрано в поиске / Selected in Search` workset.
4. One row is card-anchored and aggregates multiple reasons; note-level scope/sibling impact is explicit.
5. Reasons are grouped as Learning behavior, Content quality, System/profile state and Manual context.
6. Visible priority is High/Medium/Low; opaque numeric risk is not shown.
7. One short evidence sentence belongs in the row; full bounded evidence/freshness belongs in Inspector.
8. Default order is priority → reason order → evidence recency → stable entity tie-breaker.
9. Compact queue + active-item Inspector replaces table/tiles/Anki-preview parity.
10. Five KPI cards become a compact cap-aware summary.
11. Inspection Profiles are confirmed, declarative and fail closed; learning issues remain profile-independent.
12. Notification activates the card/reason; deck-level signals remain outside Cards.
13. Resolution is detector-driven: Active → Awaiting recheck → Still active/Resolved after recheck.
14. Focus, active item and bulk selection remain separate.
15. Desktop split view is default; narrow desktop uses stacked/drawer fallback; mobile-first is out of scope.

## Rejected alternatives

- tabs by reason family;
- mixing Search workset into automatic queue;
- three equal display modes;
- full preview for all rows;
- visible numerical risk score;
- manual Done/Resolve/Hide/Ignore;
- universal or unconfirmed heuristic content checks;
- arbitrary user code/rules;
- full web editor;
- premature listbox/grid commitment;
- modal/inline expansion as wide-desktop default.

## Open technical questions

- minimal C1.2 read operation/model and source composition;
- exact queue cap, pagination/windowing and total semantics;
- source precedence across equivalent evidence/freshness;
- representative card for note-level-only issues;
- Search workset TTL/return behavior;
- exact reason-to-priority mapping;
- whether one row quick action survives prototyping;
- final list/table/grid semantics after keyboard/screen-reader tests;
- profile fingerprint/schema/migration in C1.3;
- non-blocking recheck after native edits.

## Created or updated

- `docs/cards-v2-product-contract.md` — canonical current contract;
- `reports/core/c1-1-product-contract.md` — this evidence report;
- `roadmap/core/README.md` — C1.1 complete, C1.2 next, C1 remains in progress;
- `docs/ai-handoff.md` — active contract/invariants/next step;
- `docs/README.md` — current-contract index link.

## Checks actually performed

- verified pre-work Core commit and `master...core` divergence;
- verified no open PR before write;
- extracted ZIP and inventoried 12 PNG paths, dimensions and sizes;
- visually reviewed all 12 screenshots and representative full-height crops without OCR;
- re-read current Core baseline/roadmap/handoff/index and relevant production/contracts;
- performed current web research using official/primary sources;
- removed trailing whitespace from drafted Markdown;
- reviewed Markdown links/paths against known repository/current-doc structure;
- confirmed no screenshot binary is included in the documentation tree;
- prepared one logical documentation-only commit.

## Not performed

- local repository `git status`/`git diff --check` (no checkout);
- project tests, frontend build/typecheck or package validation;
- Fast CI;
- Docker/real-Anki E2E;
- runtime/API/UI implementation.

No unexecuted command or CI run is reported as passing. Documentation-only C1.1 does not require Fast CI or Docker E2E.

## Production-change declaration

- production frontend/backend changed: **no**
- API/payload/types changed: **no**
- tests changed: **no**
- workflows/build/release changed: **no**
- screenshot/runtime/generated artifact committed: **no**

## Exact prerequisites for C1.2

C1.2 must:

1. continue only on `core`;
2. use one automatic queue and separate Search workset;
3. define the minimal bounded card-anchored read model;
4. define source precedence/deduplication without duplicate storage/API stacks;
5. define reason scope, evidence/freshness and categorical priority fields;
6. define deterministic ordering, totals/caps and stale identity behavior;
7. define Notification/Search handoff inputs without IDs in URL;
8. carry Inspection Profile states as requirements without final schema/editor;
9. preserve detector-driven resolution/recheck;
10. specify backend/frontend/types/validators/tests/docs parity;
11. preserve loopback/token/sanitizer/media/Shadow DOM/action boundaries;
12. choose focused tests/Fast CI/real-Anki scope from the actual future diff;
13. not implement the full workspace UI, new mutations or profile editor in C1.2.

## Delivery-policy confirmation

- Pull request created: **no**
- Merge to `master`: **no**
- Force-push: **no**
- Tag/GitHub Release: **no**
- `.ankiaddon`/AnkiWeb publication: **no**
- Deployment: **no**
- C1 declared complete: **no**
- C1.2 implemented: **no**

## Stage status

```text
C1.1 — complete
C1.2 — not started
```
