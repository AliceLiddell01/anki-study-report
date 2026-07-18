# C1.2 canonical triage model and read API report

**Date:** 2026-07-18

**Repository:** `AliceLiddell01/anki-study-report`

**Branch:** `core`

**Status at report commit:** Implemented — Fast CI pending

## Branch and preflight

| Item | Value |
| --- | --- |
| Base branch | `origin/master` |
| Verified base SHA | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Initial Core HEAD | `22c6820bee44d25c3d10b871eb008a91cd56da31` |
| Initial divergence | 0 behind / 2 ahead |
| Candidate divergence after this report commit | 0 behind / 5 ahead |
| Initial worktree | clean |
| Merge/rebase from master | not performed |

The required `git status`, branch, HEAD, log, fetch, divergence and diff-stat
preflight ran before changes. The task stayed on the long-lived `core` branch.

## Sources read

All mandatory current sources from the C1.2 specification were inspected:

- README, AI handoff, roadmap Core context, C1.0/C1.1 reports and product contract;
- architecture, frontend map, dashboard/Search/Signals/Notifications/security/test/verification contracts;
- attention collector and note intelligence;
- Search service/runtime/types/client/workspace;
- NotificationStore and Signal detector/reconciliation;
- dashboard server, QueryOp bridge and add-on handler wiring;
- legacy CardsPage/CardAttention/preview and notification handoff;
- related backend/frontend tests and fixtures.

The supplied `cards.zip` contains the expected 12 original APKG/synthetic ×
table/tiles/Anki-preview × light/dark PNGs. C1.2 did not repeat the C1.1 visual
audit because the specification explicitly says a new screenshot analysis is
not required and this diff does not change Cards UI.

## Architecture decision

The implementation is a narrow read projection, not a new subsystem:

```text
existing bounded attention collector (without renderedPreview)
+ NotificationStore active card Signals
+ exact Search card row projector
→ triage_service deterministic projection
→ triage_runtime serialized QueryOp
→ POST /api/triage/query
→ TypeScript types + fail-closed parser/client
```

`triage_service.py` owns no persistence, Signal lifecycle, Search grammar,
actions, localization, preview rendering or issue resolution. HTTP handlers do
not read SQLite files directly. Collection work stays in the existing Anki
operation path.

## Exact contract

Canonical contract: [`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md).

Key decisions:

1. strict `schemaVersion: 1` and exact nested request fields;
2. `automatic` cap 100; exact-ID `search_workset` cap 200;
3. decimal signed-64-bit string IDs; duplicate workset IDs normalize first-seen;
4. explicit period required; no raw query/SQL/sort/content input;
5. four canonical learning reasons; heuristic content reasons suppressed;
6. fixed High/Medium/Low mapping; no `riskScore` in the new contract;
7. `code + scope` reason identity and card-ID item identity;
8. overlapping repeated Again merges attention + Signal provenance/evidence;
9. automatic canonical order; workset preserves explicit selection order;
10. `available | partial | unavailable` plus typed per-source status;
11. missing/deleted exact cards remain typed `availability: missing` items;
12. CardsPage/report/legacy preview/actions/Signals/Notifications remain compatible.

## Source integration and precedence

- attention owns learning issue identity and period evidence;
- Signals are read directly from the canonical store, active/card-only/bounded;
- only `card.repeated_again` is mapped; unknown card codes fail closed;
- Signal severity/freshness/evidence wins on overlap, while attention provenance
  and non-duplicate evidence remain;
- Search `project_card_row()` owns compact identity/text/state; attention is a
  bounded fallback when an entity no longer resolves;
- notification history is not scraped and no duplicate storage is created.

## Priority mapping

| Reason | Mapping |
| --- | --- |
| leech | High |
| attention repeated Again | Medium |
| Signal repeated Again warning / critical | Medium / High |
| low pass rate | Medium |
| slow answer | Low |

The projection never sorts by or returns legacy numerical risk.

## Changed areas

Backend:

- `triage_service.py`, `triage_runtime.py`;
- dashboard route/manager/add-on wiring;
- bounded active-card Signal store read;
- exact Search card row resolver;
- attention collector option to skip full rendered preview.

Frontend:

- `types/triage.ts`;
- `triageApi.ts` and focused parser/client tests;
- no CardsPage/hook/layout changes.

Documentation:

- C1.1 display-mode clarification;
- technical contract, dashboard API, architecture, frontend map, roadmap and handoff.

## Commits

```text
ae27a9f — docs: clarify the Cards display-mode contract
13b1a20 — feat: add the bounded canonical triage read API
<this report commit> — docs: document the canonical triage read contract
```

## Focused verification

| Command | Result | Evidence |
| --- | --- | --- |
| `python -B -m py_compile` on changed Python modules through `node scripts/run_python.mjs` | PASS | Python compilation completed; generated `anki_study_report/__pycache__` was removed before hygiene/package checks |
| focused triage/attention/store/server pytest | PASS | 53 passed |
| focused triage/Search/CardAttention Vitest | PASS | 63 passed |
| frontend `pnpm run typecheck` | PASS | no TypeScript errors |
| focused cross-source regression pytest | PASS | 146 passed |

An initial attempted focused command named nonexistent
`tests/test_notification_integration.py`; pytest returned file-not-found before
collection. The actual test tree was inspected, and existing Signal store,
notification fixture and handoff tests were used in the successful 146-test
regression run.

## Canonical local verification

Command:

```powershell
.\scripts\run_full_check.ps1 -SkipDocker
```

First completed attempt: **FAIL**, 83.7 s. Frontend typecheck, 271 frontend
tests and build/bundle passed; Python reached 682 passed/4 skipped, but
`test_addon_directory_has_no_generated_junk` found the `__pycache__` created by
the earlier compile check. The exact generated cache was verified and removed.

Second attempt: **PASS**, 52.5 s.

- frontend typecheck: PASS;
- frontend Vitest: 271 passed;
- Vite production build and bundle guard: PASS;
- Python: 683 passed, 4 environment skips;
- package build/validation: PASS, 63 entries;
- `ZipFile.testzip()`: `None`;
- missing/forbidden/unreferenced/unsafe assets: none.

The four skips are existing Windows/symlink/Bash-environment limitations and
not C1.2 failures.

## Bounds and performance evidence

- request/body/result/reason/evidence/text caps are constant and tested;
- shuffled source tests prove deterministic aggregation/order;
- duplicates and malformed evidence remain bounded;
- attention adapter test proves full rendered preview is not invoked;
- Search resolution is exact and bounded to 200 IDs;
- one QueryOp owns collection access per request;
- no wall-clock threshold was added.

## Security review

- [x] loopback server unchanged;
- [x] current constant-time dashboard token validation reused;
- [x] POST JSON/body-size/method contracts tested;
- [x] card IDs stay out of URL and normal logs;
- [x] no raw query/SQL/action/RPC surface;
- [x] no exception/token/path returned to client;
- [x] no full preview/media/revlog/card fields in response;
- [x] frontend has no direct collection/store access;
- [x] Signal evidence remains local and telemetry taxonomy unchanged;
- [x] sanitizer/media/Shadow DOM/action allowlists unchanged;
- [x] no runtime artifact, screenshot, profile DB or token added to Git.

## Compatibility

The change is additive. Legacy report payload, `attentionCards`, CardsPage,
Search, entity actions, Signals, Notification Center, notification handoff,
preview isolation and media routes remain in place. No frontend state machine
or hidden feature flag was added.

## Fast CI

Status at this report commit: **PENDING**. The final candidate must be pushed
to `origin/core`, manually dispatched through **Actions → Fast CI → Run
workflow → Branch: core**, and verified against its exact SHA. C1.2 must not be
marked Complete until that run passes.

## Docker decision

Docker / real-Anki E2E: **not run**. The diff adds a read API and uses the
already-established QueryOp path, but does not change Cards UI, rendering,
media, startup, E2E harness or package layout. Focused runtime tests, full
server tests, canonical local build/package and exact Fast CI are the
proportionate gates specified for C1.2. A targeted real-Anki run is reserved
for evidence of a collection-integration gap.

## Unverified / prerequisites

- exact-SHA Fast CI on the final `core` commit remains pending;
- no real Anki profile was used; no runtime/UI behavior was changed that would
  justify automatic Docker escalation;
- C1.3 implementation must not start until the cloud gate closes.

## Delivery confirmation

- push target: `origin/core` only;
- pull request: no;
- merge to `master`: no;
- force-push: no;
- release/tag/deployment/AnkiWeb publication: no;
- C1 declared complete: no.

Next step only after C1.2 closure:

```text
C1.3 — Inspection Profiles: contract and runtime
```
