# C1.6 — Canonical single-card resolution loop

**Date:** 2026-07-22

**Target branch:** `core`

**Draft PR:** [#125](https://github.com/AliceLiddell01/anki-study-report/pull/125)

**Base SHA:** `f5a7bf663e6721714a3f883e3e1f2451c84df532`

**Verified runtime candidate:** `edaf9030dbba355593e52cf8922d4c7985ce4b75`

**Owner decision:** Pending

## Result

C1.6 is implemented and mandatory verification is complete. The existing Cards
Inspector and narrow drawer now expose one-card Safe Action/Open in Anki paths,
separate action results from resolution, require explicit canonical exact-card
recheck and reconcile stable reasons before updating or removing an item.

Owner product acceptance and merge remain pending. Core C1 is not declared
complete. C1.6B remains Conditional and was not started.

## Architecture

- `POST /api/triage/recheck` schema v1 is strict, token-protected, JSON-only,
  8 KiB bounded and serialized through the existing `QueryOp` runtime.
- The service reads one exact card and delegates to the canonical period
  learning detector, active Signal projection, Search-owned identity and
  current confirmed Inspection Profile evaluator.
- The request carries the current stable reason IDs so loss of prior profile
  authority fails closed instead of producing a false resolution.
- The frontend compares old/current reasons by `reasonId`. Remaining/new
  reasons refresh the item in place; zero reasons remove it only after fully
  available evidence; missing/changed/partial/unavailable states never resolve.
- Safe Actions reuse the existing one-card action endpoint. Mutations are
  serialized and never aborted; inspect/open/recheck reads are latest-wins.
- Full resolution selects the next queue item predictably and restores focus
  without resetting filters, loaded pages or ordering.
- No bulk controls, manual resolve/archive/snooze, persistent completion state,
  new detector stack, automatic cursor loop or client-side resolution inference
  was added.

## Verification

| Gate | Result |
| --- | --- |
| focused backend + E2E helpers | PASS — 81 tests |
| focused Cards/API/frontend | PASS — 37 tests; later full frontend superseded it |
| frontend typecheck | PASS |
| full frontend | PASS — 324 tests |
| production bundle guard | PASS — 20 JS chunks; entry 429,516 bytes |
| focused harness after selector correction | PASS — `node --check`; 30 tests |
| Python 3.11 compileall | PASS — `python -m compileall -q anki_study_report` |
| canonical non-Docker | PASS — 324 frontend; 802 Python passed, 5 platform skips |
| package build/check | PASS — 77 entries |
| Fast CI exact runtime SHA | PASS — run `29862254960` |
| exact Fast package | PASS — artifact `8507861970`; SHA `edaf9030dbba355593e52cf8922d4c7985ce4b75` |
| targeted real-Anki | PASS — run `29862551442`, `standard/cards`, restart enabled, artifact `8507958104` |
| final full real-Anki | PASS — run `29862800106`, `standard/full`, restart enabled, artifact `8508096629` |
| repository diff hygiene | PASS — `git diff --check` |

Fast CI and both E2E runs used the exact prebuilt package handoff. The E2E image
was the immutable GHCR digest selected by the workflow. Uploaded artifacts are
the workflow's redacted public artifacts; no raw token-bearing artifact is
published or committed.

## Failures resolved during execution

- Runs `29861530303` and `29861909109` stopped before Anki because GitHub
  dynamically attached pull-request identity to a manual Fast CI source run,
  which the exact handoff validator correctly rejects. The same draft PR was
  temporarily closed while producing and consuming the valid workflow-dispatch
  handoff; no second PR was created.
- Run `29862014838` reached real Anki: API smoke passed, then the new browser
  assertion matched identical outcome text in two live regions. The harness was
  corrected to scope the assertion to `cards-resolution-state` in `edaf9030`.
  Its artifact export also rejected the failure log because it contained a
  private absolute container path; no unsafe artifact was published.
- The corrected targeted and full runs both passed, including redacted artifact
  preparation and cleanup.

## Product review boundary

Owner review should confirm the clarity of applicable actions, the visible
action-versus-resolution distinction, reason-level removed/remaining/new
feedback, stale/error states and focus behavior after full resolution.

## Explicit exclusions

- owner product acceptance: pending;
- merge to `core` or `master`: not performed;
- release, tag, GitHub Release, deployment or AnkiWeb publication: not performed;
- C1.6B bulk actions: not started;
- C2: not started;
- private owner Anki profile: not read or modified.
