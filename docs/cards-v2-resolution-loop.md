# Cards canonical single-card resolution loop

## Status

**Stage:** C1.6

**Delivery:** Implemented / verification complete; owner acceptance pending

**Scope:** one active automatic-queue card at a time

The Cards Inspector and 1024 px drawer share one lifecycle:

```text
issue
→ existing Safe Action or Open in Anki
→ action result
→ Awaiting recheck
→ exact-card canonical bounded recheck
→ Still active | Partially resolved | Resolved | Recheck failed | Evidence stale
```

Action success, including `action.no_changes`, is never resolution evidence.
The queue cap and disappearance from the first 100 rows are never resolution
evidence either.

## Action paths

- Learning items expose only applicable existing single-card Safe Actions:
  suspend/unsuspend and bury/unbury.
- Content-only items keep Open in Anki as the primary editing path and link to
  Inspection Profiles when configuration is relevant.
- Open in Anki is a handoff, not a mutation claim. After a successful handoff
  the item remains active until the user explicitly rechecks it.
- Only one mutation may be in flight. Mutation requests are not aborted.
- Reads use latest-wins cancellation/sequence guards so an older open, inspect
  or recheck response cannot replace newer active-card state.

No bulk selection, checkbox, manual Done/Resolve/Hide/Archive/Snooze control or
persistent completion store is part of C1.6. C1.6B remains Conditional.

## Canonical exact-card recheck

`POST /api/triage/recheck` schema v1 accepts one card ID, its expected note ID,
the current stable reason IDs and the current Cards scope. It is token-protected,
JSON-only, capped at 8 KiB and serialized through the existing `QueryOp` bridge.

The service evaluates only the requested card and delegates to the same
canonical components used by Triage v4:

- bounded learning detectors over the requested period/deck scope;
- active local Signal projection;
- Search-owned exact card identity;
- current confirmed Inspection Profiles.

There is no second detector stack, client-side resolution inference, automatic
cursor loop or collection-wide scan.

The response reports `entityStatus`, typed source status, content-check status
and the current canonical item. `partial`, `unavailable` or `error` coverage
fails closed: existing reasons stay active/stale and the UI cannot show
Resolved. A prior profile reason also fails closed if its profile authority is
no longer current.

## Reason reconciliation

Stable `reasonId` is the comparison key:

- remaining reasons keep the item and refresh priority, primary reason,
  evidence, state and recommended step in place;
- removed plus remaining reasons produce Partially resolved;
- new reasons are shown explicitly and keep the item active;
- zero current reasons remove the item only after a fully available recheck;
- missing, changed or outside-scope identity has a distinct non-success state.

After removal, focus moves to the next item at the same queue position, then the
previous item, or the queue heading when empty. Filters, loaded pages and queue
order remain intact.

## Accessibility and localization

Resolution state uses a polite live status region and busy state during action
or recheck. Conflicting controls are disabled while required, keyboard
activation remains native, and post-removal focus is deterministic. All new
labels and states have RU/EN parity.

## Verification boundary

Required evidence is recorded in
[`../reports/core/c1-6-canonical-single-card-resolution-loop.md`](../reports/core/c1-6-canonical-single-card-resolution-loop.md).
Owner product acceptance and merge remain separate pending gates.
