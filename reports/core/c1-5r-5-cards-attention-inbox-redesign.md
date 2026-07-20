# C1.5R.5 — Cards attention inbox redesign

## Confirmed state

- initial `core` HEAD: `b2d812b4dd303965030108991858fb4bc779e73e`
- tested implementation HEAD: `a30f4db66e73f3f836e69ba90cfc06974ce3df47`
- tested implementation tree: `ff771c1ad6dd50466b46af8ba66cfc50c0e57424`
- final verification run: `29740393142` — PASS
- post-transfer verification run: `29741098965` — PASS
- pre-transfer closeout HEAD: `4324ecba6fa4b994fd7ea80f7230accf8776b369`
- isolated visual run: `29738841012` — PASS
- visual trigger: `5db6561f5467bd305cc01000317f61725928d1bb`
- visual artifact: `8459497217`
- visual artifact digest: `sha256:06073aa2578d750bcdc13409cd1f0cb29bc761dabf3459f8ba32b74f93ffb02d`
- PR / merge to `master` / release / deployment / AnkiWeb publication: none

## Sources actually read

The implementation and closeout inspected the repository entrypoint, current AI
handoff and Core roadmap; Cards product/UI/preview/candidate contracts; current
Cards page/hook/types/parsers/styles/locales/tests; Search inspect and strict
response validators; modal/Shadow DOM preview boundaries; verification policy,
test matrix and prior R0–R4 reports. The R4 production code and tests remained
authoritative for schema/source behavior.

The browser evidence was opened manually after the successful run. Failed
attempt screenshots covered by the product What’s New modal were explicitly
rejected as acceptance evidence.

## Product and interaction result

The product-rejected C1.5 spreadsheet table is removed. `#/cards` now implements
Variant A:

```text
>= 1200 CSS px
semantic identity-led inbox | persistent Inspector

< 1200 CSS px
full-width inbox
explicit activation → labelled non-modal detail drawer
```

The queue is an ordinary ordered list with one native button per issue. It has no
`table`, ARIA grid/listbox/option semantics, checkbox, nested row action or
preview host. Priority, compact identity, primary reason, bounded evidence,
deck/state and note scope form the stable scan path.

Wide mode selects the first inspectable item without moving focus. Narrow mode
starts with no active preview request. The drawer uses no backdrop, `aria-modal`,
inert application shell or focus trap; Escape/close returns focus to the
activator. The existing answer `AccessibleModal` remains the only modal.

## Detail and preview

`CardsDetail` is shared by Inspector and drawer. It shows all canonical reasons,
bounded evidence, native sanitized front, recommended read-only next step,
exact-ID Anki handoff and collapsed technical identity. The expanded modal uses
the cached native answer/back. Queue rows perform no full preview or media reads.

At most one detail preview host exists in the normal workspace. While the true
answer modal is open, the underlying front plus modal answer produce the expected
two isolated Shadow DOM hosts.

## Period and current-content continuation

Learning scope is explicit session state with 7/30/90-day presets. It changes only
period-bound learning evidence. Each scope change aborts stale work and starts one
v4 automatic request with `contentCursor: null`; local filters are preserved.

Current-content continuation is manual. One activation sends one request with the
coherent current cursor. Accumulation deduplicates item/reason/source/evidence,
retains deterministic backend-equivalent ordering and is bounded to 500 unique
items and 10 additional pages. Failure preserves prior usable items and cursor;
there is no automatic cursor loop.

## Accessibility and responsive behavior

- native list/button semantics and one tab stop per item;
- focus is independent from active item;
- textual active and priority state, not color alone;
- labelled/described detail region;
- 1200 px breakpoint chosen from measured queue/Inspector balance;
- 1024 px queue remains full-width before activation;
- drawer remains non-modal and queue remains operable;
- answer modal preserves inert background, focus containment and Escape order;
- light/dark and RU/EN copy are covered by focused tests and visual fixtures.

## Visual evidence

The successful artifact contains six historical baseline frames and twelve R5
frames:

- 1440 light and dark inbox/Inspector;
- 1280 with 100 items;
- 1024 initial queue, light/dark drawer and answer modal;
- partial coverage and Profiles-needs-review warnings;
- continuation ready/loaded;
- successful empty state.

Measured R5 frames all reported `documentWidth == bodyWidth == viewport width`.
The 100-item frame rendered 100 semantic items and one active preview. The 1024
initial queue rendered zero preview hosts; drawer frames rendered one. Manual
continuation changed the loaded count from 10 to 15. Empty state rendered zero
items and previews.

A real production defect was found by the visual assertion: the original drawer
entry transform widened the document by 16 px at 1024. The animation was changed
to opacity-only; the final visual matrix then passed without weakening the
no-overflow assertion.

## Focused verification

- TypeScript typecheck: PASS
- focused frontend: 9 files / 25 tests PASS
- focused backend: 106 tests PASS (including package-marker regression)
- production Vite build and bundle guard: PASS
- bundle: 17 JS chunks; entry 487,382 bytes; total 1,321,380 bytes
- package build/validation and `--check-only`: PASS
- canonical `run_full_check.ps1 -SkipDocker`: PASS
- git diff/denylist/hygiene: PASS

Exact contour timings and full canonical counts are retained in the final workflow
status log for run `29740393142`.

## Failure classification

Temporary attempts exposed harness/test-contract defects before producing valid
evidence:

- stale table test mocks and strict fixture timing;
- invalid synthetic `profileId` rejected by the strict parser;
- baseline waiting for an R5 selector;
- Vite preview process/port isolation;
- same-document hash navigation retaining a prior fixture;
- What’s New modal covering the intended page.

Those were fixed in disposable verification infrastructure. Runtime UI code
changed only for the confirmed 16 px drawer overflow; the package validator and
its regression fixture were migrated from the removed `.cards-v2-table` marker
to `.cards-inbox-page`. No backend contract or security boundary was weakened.

## Cleanup

The post-transfer run `29741098965` verified exact `core` and then neutralized the
surviving temporary refs by adding ordinary fast-forward commits whose tree is
identical to the final clean Core tree. No force-push or ref deletion was used.

```text
c1-5r-5-cards-inbox — neutralized
c1-5r-5-status — neutralized
c1-5r-5-visual-status — neutralized
c1-5r-5-final-status — neutralized
c1-5r-5-verified — synchronized to final core
```

The GitHub connector exposes no workflow-run/artifact deletion action. Completed
run records and the seven-day visual artifact remain immutable until normal
expiry; no temporary workflow remains runnable at a surviving R5 ref tip.
Canonical workflows were not changed.

## Security and privacy

- frontend still has no direct collection access;
- Triage v4 and Search v2 strict parsing remain unchanged;
- loopback/token/content-type/body-size enforcement remains backend-owned;
- exact card IDs, not display text, drive inspect/Anki handoff;
- sanitizer, trusted media validation and Shadow DOM isolation are unchanged;
- no token-bearing URL, owner profile data, screenshots, logs or package output is
  committed;
- R5 adds no mutation, selection, manual resolve, editor or arbitrary query/code
  surface.

## Durable changed files

The clean implementation contains Cards frontend source, localized copy,
focused tests, the package validator marker migration and current documentation.
Disposable workflows, apply/closeout scripts, triggers, visual binaries, logs,
generated package output and status files are excluded from the durable tree.

## Not verified

- Fast CI;
- Docker / real-Anki E2E;
- owner private Anki profile;
- owner product acceptance;
- Guided Inspection Profiles UX (R6);
- integrated R7 acceptance;
- C1.6 action/resolution loop.

These omissions are intentional for R5 and must not be upgraded into claims.

## Git boundary

```text
pushed to origin/core: yes — ordinary fast-forward
PR: no
merge into master: no
force-push: no
release: no
deployment: no
AnkiWeb publication: no
```

## Status

```text
C1.5R.0–R.5 — Complete
C1.5R.6 — Next, not started
C1.5R.7 — Not started
C1.6 — Blocked
Core C1 — In progress
owner product acceptance — Pending
```
