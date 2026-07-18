# C1.5R.0 — Recovery and corrective baseline

**Status:** `C1.5R.0 — Complete`

**Branch:** `core`

**Next:** `C1.5R.1 — Canonical card display identity`

## 1. Purpose

This stage recovers the useful C1.5R Phase A findings, corrects the official
project status, and establishes a documentation-only starting point for the
remediation sequence. It does not implement production behavior, add a new API,
change schemas, or begin C1.5R.1.

The historical C1.5 implementation remains valid technical evidence. Its owner
product acceptance is withdrawn.

## 2. Execution environment

Execution was connector-first from ChatGPT with GitHub read/write access.

```text
repository: AliceLiddell01/anki-study-report
active remote branch: core
local project checkout: unavailable
local project working tree: unavailable
shell/git against the project checkout: unavailable
GitHub connector write capability: available
```

Only `origin/core` state was inspected. No claim is made about a previous
chat's local index, unstaged changes, untracked files, stash, or worktree.

## 3. Initial repository state

Observed before the corrective commits:

```text
origin/core HEAD: b3055ac4992c1658101d6d837a9aa74ab1274d9a
origin/master HEAD: 359c26f82a9ee78c8e27603f9ded5ca9bef2c71e
origin/master...origin/core: 0 behind / 26 ahead
open pull requests from core: none
```

The prompt's earlier reference point
`101103585149aa0a30d411ad538fbcc06641a05b` was two commits behind the observed
`origin/core` head.

Remote branches are not described as clean or dirty; those terms apply to a
working tree, which was unavailable.

## 4. Local and remote distinction

| State | Result |
| --- | --- |
| local HEAD | unavailable |
| local branch | unavailable |
| local working tree | unavailable |
| staged state | unavailable |
| untracked state | unavailable |
| `origin/core` | inspected through GitHub |
| `origin/master` | inspected through GitHub |

The previous Phase A temporary directory and local prototype were not available
and were not reconstructed from guesses.

## 5. Recovered files and commits

The remote branch contained two commits after the earlier C1.5 closeout point:

1. `cd8e0eb96d6a89508a74890d57adac4fd109080a` — reopened Cards product
   acceptance in documentation and created a preliminary Phase A report and
   display-identity draft;
2. `b3055ac4992c1658101d6d837a9aa74ab1274d9a` — added two intentionally red
   tests without production implementation.

The second commit was outside the C1.5R.0 delivery boundary. The two tests were
removed from `origin/core` by restoring their parent blobs before the
Markdown-only baseline commit. Their scenarios remain recorded below for
C1.5R.1/C1.5R.3.

The preliminary Phase A report remains at:

```text
reports/core/c1-5r-cards-profiles-ux-remediation.md
```

It is supporting forensic history, not the C1.5R closeout report.

## 6. Unavailable or lost state

The following state could not be recovered in this chat:

- any uncommitted Phase A Markdown edits from a previous local checkout;
- any uncommitted exact red-test diff beyond the two tests already pushed;
- the previous local prototype source and temporary screenshots;
- the raw owner-profile export or private Anki profile;
- the legacy `cards.zip` archive as a file in the current environment.

No private owner profile was imported, opened, or read.

## 7. Evidence inventory

| Source | Availability | Actually opened in this stage | Role | Freshness | Limitations |
| --- | --- | --- | --- | --- | --- |
| accepted C1.5 E2E artifact, run `29649071545`, artifact `8430943370` | available and downloaded | yes | historical technical evidence for the accepted implementation SHA | exact run from C1.5 | proves the rejected implementation worked; does not prove product acceptance |
| 28 screenshots inside the accepted artifact | available | yes, inventory opened; representative Cards images visually inspected | runtime/layout evidence for synthetic/APKG Cards and Inspection Profiles | same exact run | synthetic/APKG evidence, not owner-profile acceptance |
| owner-provided Cards screenshot with `Cards = 0` | referenced by recovery prompt/Phase A | no raw file in this chat | product defect evidence | post-C1.5 owner review | separate from accepted artifact; not present among its 28 screenshots |
| owner-provided Inspection Profiles screenshots | referenced by recovery prompt and Phase A report | no raw file in this chat | product evidence that the normal path is too technical and long | post-C1.5 owner review | current stage relies on the recorded Phase A observation, not a new visual review |
| legacy `cards.zip` | referenced by Phase A | no | historical comparison only | older than accepted C1.5 artifact | distinct evidence set; must not be treated as the accepted C1.5 artifact |
| earlier front/back screenshots | referenced by Phase A | no raw files in this chat | expected answer-side semantic evidence | historical | supports direction, not a new runtime verification |
| previous Phase A messages/report | available in prompt and repository | yes | recovered forensic findings and decisions | current remediation context | not a substitute for unavailable local diffs |
| current `origin/core` docs/code/tests | available | yes | authoritative current remote state | current branch state | no local worktree visibility |

The accepted artifact contained exactly 84 ZIP entries and 28 image files. The
Cards/Profiles subset included five Cards screenshots and four Inspection
Profiles screenshots. The Inspection Profiles `dirty-suggestion` and
`validated-preview` full-page captures were approximately 6068 px and 6576 px
high, respectively, which is consistent with the Phase A report's concern about
the normal workflow's length.

The accepted artifact and legacy `cards.zip` are not interchangeable. The
separate owner screenshot reporting `Cards = 0` was not found in the accepted
artifact inventory.

## 8. Confirmed defects

Read-only inspection of current production code confirmed:

1. Search card identity uses the note sort field and then arbitrary non-empty
   fields. A media-heavy card can therefore fall back to an unrelated field.
2. Triage resolves card rows through the same Search projector and repeats the
   same incorrect compact text in Cards.
3. Search card rows, Triage items, the Cards queue, and the Cards Inspector do
   not share a dedicated canonical compact card-identity projection.
4. The Inspector and expanded preview currently render the same front side;
   the expanded surface does not default to answer/back.
5. The Cards hook hides a fixed seven-day learning period in implementation.
6. Automatic content candidates reuse the period-bound revlog candidate set;
   zero recent reviews can therefore suppress current content failures.
7. An unconfigured Inspection Profile does not receive the suggestion as a ready
   unsaved draft until the user invokes `Use suggestion`.
8. The normal Inspection Profiles path exposes runtime-level role slugs, check
   kinds, modes, IDs, template ordinals, and repeated fieldsets.
9. The C1.5 table/split layout is product-rejected, especially around the 1024 px
   desktop contour.

## 9. Accepted design decisions

The following decisions are fixed for remediation planning and are not reopened
in C1.5R.0:

- wide desktop: **Variant A — identity-led dense inbox list** plus persistent
  Inspector;
- approximately 1024 px: full-width queue plus a non-modal detail drawer;
- the drawer does not use `inert`, a focus trap, or modal semantics;
- row activation does not steal focus;
- the drawer has an explicit return-to-queue action;
- compact identity is shared across Search card row/Inspector, Triage, Cards
  queue, and Cards Inspector heading;
- Inspector( isplays rendered front;
- expanded preview defaults to rendered answer/back;
- current-content candidates are independent of the selected learning period;
- Inspection Profiles use a guided Basic workflow, with the strict runtime
  editor behind Advanced;
- suggestions become ready unsaved drafts without an extra adoption step;
- no formatter is silently added to strict Inspection Profile v1;
- C1.6 remains blocked until C1.5R and separate owner product acceptance are
  complete.

## 10. C1.5 historical technical evidence

Historical evidence is retained without reclassifying successful runs as
failures:

```text
accepted implementation SHA: 0460afe472cd87029368924bdf5640e90271c03c
Fast CI: 29648956309 — PASS
real-Anki standard/cards E2E: 29649071545 — PASS
artifact: 8430943370
closeout SHA: 101103585149aa0a30d411ad538fbcc06641a05b
```

These runs prove the old implementation's technical execution and artifact
production. They do not prove the current product contract or owner acceptance.

## 11. Withdrawn product acceptance

The corrected status is:

```text
C1.4 runtime/API foundation — accepted
C1.4 configuration UX — remediation required

C1.5 technical architecture — historical verified evidence
C1.5 product acceptance — withdrawn

C1.5R — In progress
C1.6 — Blocked and not started
Core C1 — In progress
```

The old C1.5 report is retained as historical evidence and explicitly amended.
Its former visual/product-acceptance statements are superseded.

## 12. C1.5R decomposition

```text
C1.5R.0 Recovery and corrective baseline — Complete
C1.5R.1 Canonical card display identity — Next, not started
C1.5R.2 Declarative compact formatter runtime — Not started
C1.5R.3 Front/back preview semantics — Not started
C1.5R.4 Independent triage candidate sources — Not started
C1.5R.5 Cards attention inbox redesign — Not started
C1.5R.6 Guided Inspection Profiles UX — Not started
C1.5R.7 Integrated acceptance and owner review package — Not started
```

The decomposition orders shared identity before formatter configuration and UI
redesign, and keeps owner acceptance as a distinct final gate.

## 13. Red-test inventory and future scenarios

Two premature red tests had been pushed and were removed from the R0 remote
baseline without running them:

```text
tests/test_search_service.py
  test_card_identity_uses_rendered_front_not_unrelated_sort_field

tests/test_note_intelligence.py
  test_full_preview_uses_reviewer_render_not_browser_appearance
```

Required future scenarios:

### C1.5R.1

- media-heavy card does not fall back to an unrelated part-of-speech field;
- Search/Triage/Cards compact-display parity;
- Browser Appearance present, absent, and empty;
- exact default Japanese compact display;
- strict unknown-field rejection during a schema-version transition.

### C1.5R.3

- Inspector uses front;
- expanded modal uses back/answer;
- answer-only marker semantics;
- narrow preview clipping;
- modal focus trap and focus restoration for the expanded preview.

### C1.5R.4

- zero period reviews plus a current content failure;
- content remains when the learning period changes;
- Programming profile does not receive a false audio issue;
- bounded partial/truncated content scan.

### C1.5R.6

- automatic unsaved suggested draft;
- Japanese audio default;
- Programming no-audio default;
- Basic confirmation without opening Advanced;
- compact formatter preview.

R0 does not implement or execute these tests.

## 14. Files changed

The corrective baseline changes only Markdown, after a separate corrective
commit removed the premature test additions:

```text
docs/ai-handoff.md
docs/card-display-identity.md
docs/inspection-profiles-ui.md
roadmap/README.md
roadmap/core/README.md
reports/core/c1-5-cards-workspace.md
reports/core/c1-5r-0-recovery-baseline.md
```

Existing C1.5R status banners in `docs/cards-v2-product-contract.md` and
`docs/cards-v2-workspace-ui.md` remain in force.

## 15. Verification

Performed for the exact generated Markdown set:

- manual path/link review for changed internal links;
- trailing-whitespace scan;
- Markdown file inventory check;
- a temporary staged-tree `git diff --check` against the generated files;
- post-write GitHub commit inspection and changed-file boundary review.

Not run:

- Python tests;
- frontend tests;
- TypeScript typecheck;
- frontend/add-on build;
- package validation/build;
- Fast CI;
- Docker or real-Anki E2E.

## 16. Git boundary

```text
branch: origin/core
PR: no
merge: no
rebase: no
force-push: no
release: no
deployment: no
AnkiWeb publication: no
production code changed: no
production schemas changed: no
```

## 17. Status

```text
C1.5R.0 — Complete
C1.5R.1 — Next, not started
C1.6 — Blocked
Core C1 — In progress
```

## 18. Next step

```text
C1.5R.1 — Canonical card display identity
```
