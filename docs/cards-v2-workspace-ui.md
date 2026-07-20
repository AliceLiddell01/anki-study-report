# Cards v2 workspace UI — historical C1.5 contract

## Status

This document is retained only as historical evidence for the rejected C1.5
native-table Design Gate. It is not a current implementation contract.

The current `#/cards` presentation contract is:

- [`cards-attention-inbox.md`](cards-attention-inbox.md) — C1.5R.5 identity-led
  semantic inbox, wide Inspector and 1024 px non-modal drawer;
- [`card-preview-semantics.md`](card-preview-semantics.md) — Inspector front and
  expanded answer/back;
- [`triage-candidate-sources-v4.md`](triage-candidate-sources-v4.md) — independent
  learning/current-content sources and manual cursor continuation.

## Historical decision

C1.5 selected a compact native table plus persistent Inspector. Later owner
screenshot and real-profile review withdrew product acceptance. C1.5R.5 removes
that table instead of retaining it behind a responsive alias, hidden mode,
feature flag or fallback.

Historical green CI/E2E runs still prove that the old implementation executed;
they do not prove current product correctness.

## Current boundary

C1.5R.5 remains read-only. It does not add selection, mutation, Safe Actions,
manual resolution, recheck lifecycle, editor functionality, an ARIA grid, a
listbox, or a second preview renderer. Those capabilities remain outside R5.
