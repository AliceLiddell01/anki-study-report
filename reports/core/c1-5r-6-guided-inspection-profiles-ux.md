# C1.5R.6 — Guided Inspection Profiles UX

## Status before merge

```text
C1.5R.0–R.6 — technically verified
C1.5R.7 — blocked until R6 merge/cleanup
C1.6 — blocked
Owner product acceptance — pending
```

Final merge and cleanup evidence is appended after the PR merge.

## Baseline

- initial `core`: `cbdeadcc46a3cfd3a923521f7c08996337991f3b`;
- `core` relative to `master`: 0 behind / 83 ahead;
- task branch: `c1-5r-6-guided-inspection-profiles`;
- local clone/worktree: unavailable because the execution container could not
  resolve `github.com`; implementation and verification used the GitHub connector
  and disposable GitHub-hosted runners;
- PR: #50, task branch -> `core`, non-draft.

The baseline selected an unconfigured type with `draft == null`, displayed a
machine-first suggestion panel and required a separate `Use suggestion` action.
Confirmed/review profiles mounted display name, template scope, raw mappings, raw
checks and all tools in one permanently expanded flow.

Baseline screenshots outside Git:

- `r6-baseline-japanese-1440-light.png` — 1192 px page;
- `r6-baseline-programming-1440-light.png` — 1192 px;
- `r6-baseline-confirmed-1440-dark.png` — 2162 px;
- `r6-baseline-needs-review-1440-light.png` — 2260 px;
- `r6-baseline-long-editor-1024-light.png` — 6436 px.

Exact baseline control counts were not retained by the browser harness and are not
reconstructed from screenshots.

## Sources actually read

Project sources included README, AI handoff, roadmap/root and roadmap/core,
C1.5R.0–R.5 reports, remediation report, Inspection Profiles v1/UI, Cards/Triage/
formatter contracts, API, architecture, frontend map, navigation, localization,
security, test/verification/release contracts, Docker E2E README, package metadata,
the page, hook, editors, API/types/locales/styles/router, backend profile runtime,
store/service/note intelligence, focused Python tests and browser harness.

External primary-source checks covered the current Anki Manual note types, fields,
templates and template errors, plus W3C WAI forms, grouping, instructions,
validation, disclosure and notification guidance.

## Component topology

Before:

```text
InspectionProfilesSettingsPage
-> SuggestionPanel
-> display name
-> TemplateScopeEditor
-> FieldMappingsEditor
-> ChecksEditor
-> check-ID-first preview
-> all actions
```

After:

```text
InspectionProfilesSettingsPage
-> lifecycle header/guidance
-> BasicProfileEditor
   -> suggested setup
   -> friendly field mappings
   -> friendly requirements
   -> friendly template scope
-> ProfileValidationResult
-> lifecycle primary actions
-> AdvancedProfileDisclosure
   -> existing strict editors
-> Profile tools disclosure
```

## Draft-state model

The hook now tracks strict draft, protected baseline, explicit origin and
`userEdited` separately. Origins are `none`, `generated`, `stored`, `imported` and
`empty`. Dirty means user-owned changes differ from the protected baseline.

- clean generated drafts switch/rebuild without a discard modal;
- opening the page does not arm `beforeunload`;
- any Basic or Advanced profile edit becomes protected user work;
- import/start-empty are dirty immediately;
- clean stored profiles reload from server;
- dirty reload preserves user work;
- latest-wins reads, validation abort, mutation serialization and exact expected
  revision remain intact;
- conflicts preserve the local draft and expose explicit reconciliation.

## Product decisions

Basic is the normal path and is one projection over strict v1. Friendly roles and
every existing check kind are editable without exposing slugs/IDs. Duplicate field
claims are prevented. Template names replace ordinal-first copy. Machine-level
editing, diagnostics and IDs remain available in collapsed Advanced. Import/export,
reset, start-empty, disable and delete are separated into Profile tools.

Japanese uses backend `detectedKind`/suggestion and visibly includes Audio when
mapped. Programming displays Question/Answer and does not invent an Audio default.
No frontend note-type-name heuristic was introduced.

## Lifecycle and validation

Unconfigured/suggested profiles use Confirm and enable. Confirmed unchanged shows
Enabled. Confirmed edits validate/reconfirm; saving as draft requires confirmation.
Needs-review profiles explain the structural reason and remain fail closed until
reconfirmed. Disabled profiles require review/validation before enable.

Check setup sends validate v2 sample limit 10. Confirm validates before update v1
and sends no mutation after invalid validation. Results group failures by friendly
requirement and remain privacy-safe. No-card samples are reported honestly.

## Accessibility

Basic groups controls with fieldset/legend, uses native selects/checkboxes and
visible labels, and keeps catalog entries as native buttons. Native disclosures are
keyboard-operable. Collapsed Advanced reports an error count. Explicit failed
actions focus the error summary and links reveal strict controls. Status, alert,
state and priority semantics are textual. RU/EN share the same strict model.

## Security review

Confirmed unchanged:

```text
no direct collection access
no raw note values or HTML
no template source or media filenames
no filesystem paths or tokens
no arbitrary code/query/regex surface
no autosave or autoconfirm
no unvalidated enable
no silent revision overwrite
no profile-content telemetry
```

Basic emits only the hard-coded Inspection Profile v1 union.

## Verification

Tested implementation/content head before temporary visual infrastructure:
`5c0b3e64b7da8d953c79fe99255a9ec65a435d2d`.

Canonical verification run `29747390152` on exact head:

| Contour | Result | Duration |
| --- | --- | --- |
| Page test | PASS | individual duration not exposed by connector |
| Hook test | PASS | not separately exposed |
| Basic editor test | PASS | not separately exposed |
| Advanced disclosure test | PASS | not separately exposed |
| Validation-result test | PASS | not separately exposed |
| Projection test | PASS | not separately exposed |
| Inspection API regression | PASS | not separately exposed |
| TypeScript typecheck | PASS | not separately exposed |
| Production `build:addon` and bundle guard | PASS | not separately exposed |
| Focused backend | PASS — 71 tests | not separately exposed |
| Package `--check` and `--check-only` | PASS | not separately exposed |
| `run_full_check.ps1 -SkipDocker` | PASS | not separately exposed |
| Git hygiene | PASS | not separately exposed |

The connector did not expose reliable per-step durations, so none are invented.

Browser run `29749495305`, artifact `8463904480`, digest
`sha256:de8ce6c6927bd1917014644b76515fd73438549831ca9def940aca08b92b627f`:

- 20 baseline/current states captured in real Chromium;
- light/dark and 1440/1024 covered;
- no horizontal overflow assertion failures;
- Advanced collapsed initially;
- no current normal-path `Use suggestion`;
- generated draft visible without mutation;
- Japanese Audio visible;
- Programming configured requirements contain no Audio;
- no Basic check ID or role slug;
- one primary action;
- collapsed Advanced error represented.

Current page heights:

| State | Viewport | Theme | Height |
| --- | ---: | --- | ---: |
| Japanese Basic | 1440x1000 | light/dark | 2546 px |
| Programming Basic | 1440x1000 | light | 1965 px |
| Programming Basic | 1024x900 | light | 3147 px |
| Confirmed | 1440x1000 | light | 1529 px |
| Confirmed edited | 1440x1000 | light | 1579 px |
| Needs review | 1440x1000 | light | 1562 px |
| Disabled | 1440x1000 | dark | 1541 px |
| Advanced open | 1440x1000 | light | 6819 px |
| Validation success/errors | 1440x1000 | light | 2758/2862 px |
| Preview unavailable | 1024x900 | light | 3386 px |
| Conflict | 1440x1000 | light | 2884 px |
| Ambiguous | 1440x1000 | light | 1654 px |
| Profile tools | 1440x1000 | dark | 2613 px |

The Advanced-open height is intentional strict capability; it is collapsed in the
normal path. Screenshots, logs, runtime harnesses and packages were not committed.

## Performance evidence

Browser assertions recorded zero mutation calls before explicit actions. Selection
and catalog load perform no validation and no mutation. The hook performs one
bounded catalog query rather than per-note-type requests. Only the selected editor
renders. Basic is materially shorter than the old 1024 strict editor; exact DOM
control counts and render timings were not measured and are not invented.

## Failures and fixes

- setup-node cache lookup before corepack: temporary workflow fixed;
- combined PowerShell Vitest argument composition: replaced with explicit test
  steps; all focused files passed;
- flaky jsdom native-details auto-toggle assertion: changed to controlled open-state
  coverage, production unchanged;
- test-only `Array.at` exceeded project target: replaced with compatible indexing;
- missing pytest and missing built dashboard assets: runner dependency/order fixed;
- browser startup subshell path: temporary runner fixed;
- Playwright strict locators, safe Audio-option distinction and expected DEV 404
  noise: harness assertions narrowed without weakening product assertions;
- legacy baseline lacked Basic by design: baseline wait used the legacy contract.

## Durable changed area

Durable production changes are limited to the Inspection Profiles page, hook,
guided components/projection helper, focused tests and dedicated styles, plus
synchronized current documentation. No backend production/schema change occurred.

## Not verified in R6

- Docker / real-Anki E2E;
- owner private profile;
- owner product acceptance;
- R7 integrated package;
- C1.6.

These belong to the next stage and are not upgraded into claims.

<!-- R6_FINAL_CLOSEOUT -->
