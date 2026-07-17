# C1.0 Core branch baseline

**Checked on:** 2026-07-18  
**Verification source:** connected GitHub repository metadata and file reads; uploaded C1.0 task specification  
**Repository:** `AliceLiddell01/anki-study-report`

## Repository and branch baseline

| Item | Verified value |
| --- | --- |
| Default/base branch | `master` |
| Verified base SHA | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Base commit message | `test: make changelog release fixtures version-agnostic` |
| Core branch | `core` |
| Core branch origin | created directly from the verified base SHA |
| Core HEAD after applying C1.0 | the documentation commit containing this report |
| Open pull requests at audit time | none |
| Other explicitly Core-oriented branches found | none |

The base SHA was re-checked instead of being accepted only from the task specification. The latest changes after the roadmap restructure include the documentation realignment, the 1.2.0 release/changelog sequence and the final version-agnostic changelog fixture correction.

## Long-lived branch and delivery policy

`core` is an independent long-lived branch for sequential C1 and C2 work.

- Do not create a pull request to `master`, merge, tag, publish a GitHub Release, publish `.ankiaddon`, deploy or publish to AnkiWeb until the owner separately approves a stable Core build.
- Do not close the global Core track after one C1 increment.
- Synchronize from `master` only for a named reason and verify every transferred change.
- Do not automatically merge or rebase unrelated work.
- Do not force-push without separate owner approval.
- Commit messages must describe the actual change.
- Pushes for this track go only to `core` until the delivery policy is explicitly changed.

## Current session capability matrix

| Capability | Status | Evidence / limitation |
| --- | --- | --- |
| GitHub repository read | available and used | repository metadata, source files and tests read through the connected GitHub tool |
| GitHub branch listing | available and used | `core`, `c1`, `cards` and `triage` searches performed |
| GitHub branch creation | available and used | `core` created from the verified base SHA |
| GitHub file writes | available | used only for the documentation files listed below |
| Git commit creation | available | one documentation commit prepared for `core` |
| Local repository checkout | unavailable | no repository working tree was attached to this ChatGPT execution path |
| Shell / terminal | unavailable for repository verification | no Git CLI command was claimed as executed |
| Python runtime | available only as a disconnected scratch runtime | not evidence for repository checks |
| Node / PowerShell | unavailable for repository verification | no project command was executed |
| Uploaded `cards.zip` | unavailable | only the C1.0 task file was available; Cards screenshots were not reviewed |
| GitHub Actions definitions/metadata | available and read | canonical workflow files were inspected |
| Start a new GitHub Actions dispatch | unavailable through the connected action set | workflows remain manually dispatchable in GitHub UI |
| Docker | unavailable | no Docker or real-Anki run was executed |

An unavailable operation did not stop the read-only audit or the documentation baseline.

## Sources read

### Repository and current contracts

1. `README.md`
2. `docs/ai-handoff.md`
3. `roadmap/README.md`
4. `roadmap/core/README.md`
5. `docs/project-overview.md`
6. `docs/architecture.md`
7. `docs/frontend-map.md`
8. `docs/dashboard-api.md`
9. `docs/search-v1-and-safe-actions.md`
10. `docs/signals-foundation.md`
11. `docs/notification-center.md`
12. `docs/security-and-safety.md`
13. `docs/test-matrix.md`
14. `docs/verification-run-policy.md`

### Workflows and implementation inventory

15. `.github/workflows/ci-fast.yml`
16. `.github/workflows/ci-e2e.yml`
17. `web-dashboard/src/pages/CardsPage.tsx`
18. `web-dashboard/src/lib/cardAttention.ts`
19. `anki_study_report/metrics.py`
20. `anki_study_report/note_intelligence.py`
21. `anki_study_report/signal_detection.py`
22. `anki_study_report/entity_actions.py`
23. `web-dashboard/src/hooks/useSearchWorkspace.ts`
24. `web-dashboard/src/lib/notificationHandoff.ts`
25. `web-dashboard/src/types/report.ts`
26. `web-dashboard/src/pages/CardsPage.test.tsx`

Related contract/test locations were also identified from the documentation and repository search, including Search, entity-action, Signals, Notification and attention-card tests.

## Sources not read or unavailable

- `cards.zip` and its APKG/synthetic light/dark screenshots were not available in the current chat.
- No local working tree, uncommitted files, local Git configuration or Docker state was available.
- No GitHub Actions run was started, so no new run logs or artifacts were produced.
- The complete bodies of every related test file were not required for this baseline; canonical contracts, representative tests and the production paths above were inspected.

## Existing C1 dependency inventory

### Cards

- Canonical payload keys are `attentionCards`, `attentionCardsStatus` and `noteTypeCatalog`.
- The live collector is read-only, bounded to 100 returned cards and publishes diagnostics for period, deck filtering, note profiles and issue counts.
- Current issue families include learning issues (`leech`, `repeated_again`, `slow_answer`, `low_pass_rate`) and heuristic content issues (`missing_audio`, `missing_example`, `missing_image`, `missing_meaning`, `missing_part_of_speech`).
- Current sorting is primarily an opaque numeric `riskScore`.
- Cards v1 owns filters, Browser handoff and three display modes but does not own a full editor.

### Search

- Existing `POST /api/search/query` and `/api/search/inspect` are token-protected, bounded, strict and read-only.
- Native Anki search grammar and structured filters are used without adding arbitrary SQL or a second Search API.
- `useSearchWorkspace` already owns latest-wins cancellation, pagination, explicit selection up to 200, inspector state and refresh/reconciliation after actions.
- C1 must reuse this workspace and its inspect path rather than duplicate query state.

### Safe Actions

- Card actions are limited to suspend/unsuspend, set/clear flag, bury/unbury and move to a normal deck.
- Note actions are limited to add/remove tags.
- Requests use exact fields, positive decimal string IDs, a batch cap of 200 and full preflight before mutation.
- Stale entities reject the whole batch. No-op results are typed and non-undoable; mutations use the existing official Anki operation bridge and one undo step.
- C1 may compose only these existing actions until a separately reviewed contract expands the allowlist.

### Signals

- Signals are local, bounded and read-only with respect to the collection.
- The current detector registry contains workload pressure, recent retention drop, deck health decline and repeated Again.
- `card.repeated_again` is based on one grouped seven-day revlog query, returns no card content and is capped at 50 cards.
- Resolution is detector-driven and requires two successful evaluations without the candidate; read state is independent from signal resolution.
- C1 must reuse the signal lifecycle instead of adding manual hidden/resolved state.

### Notification handoff

- Notification Center is local per profile and is not an account inbox.
- Card/deck context uses a strict session-only handoff with exact fields, decimal entity IDs, a 10-minute maximum age and consume-once behavior.
- Entity IDs are not placed in the hash, persistent local storage or remote telemetry.
- C1 can consume this handoff but must not create another notification navigation contract.

### Preview isolation

- Preview HTML/CSS/media are sanitized on the backend.
- `table` and `tiles` use front-only Shadow DOM previews.
- `ankiPreview` uses a single answer-only Shadow DOM host from sanitized `renderedPreview.backHtml`.
- No iframe or template JavaScript execution is permitted.
- Media remains token-protected and filename-validated.

## Known Cards v1 product findings

These are accepted baseline findings, not C1.1 implementation.

1. `risk` and `check` both return all currently filtered rows; `check` only adds the requirement to select a deck.
2. `gaps` filters missing-content issues.
3. `patterns` filters `repeated_again`, `slow_answer` and `low_pass_rate`.
4. The labels “Risk”, “Problems/Patterns” and “Check” do not form distinct user workflows and partially overlap.
5. `table`, `tiles` and `ankiPreview` expose substantially the same queue with different density and can create very long pages.
6. The preliminary C1 direction is one “Requires attention” queue, filters instead of workflow-like tabs, a compact queue plus Inspector, and explicit reason/evidence instead of an opaque score.
7. Full editing remains in Anki Browser.
8. Content-quality checks require a confirmed profile for each note type. The current implementation infers roles and kinds heuristically; C1.1 must define an explicit confirmation/fail-closed contract before treating missing content as authoritative.
9. Universal learning issues remain independent of an Inspection Profile.

## Security boundaries

- Frontend never accesses the Anki collection directly.
- The server remains bound to `127.0.0.1` and all sensitive API calls require the dashboard token.
- Token validation, redaction and token-bearing artifact restrictions must not be weakened.
- No duplicate Search API, action stack or signal lifecycle.
- No arbitrary SQL, RPC, JavaScript, Python execution or iframe.
- Sanitizer, media filename validation and Shadow DOM preview isolation remain mandatory.
- Runtime data, logs, screenshots, caches, profile data, tokens, generated assets, `.ankiaddon` and E2E outputs remain outside Git.
- Signal evidence/entity IDs remain local and outside the remote telemetry taxonomy.

## Verification paths

### C1.0 documentation-only path

The applicable minimum is repository metadata verification, branch/head verification, changed-file inspection and Markdown link/path review. Fast CI and Docker E2E are not required because C1.0 changes only documentation.

### Fast CI

Workflow: **Fast CI** (`.github/workflows/ci-fast.yml`).

- `workflow_dispatch` is enabled and has no custom inputs.
- Automatic push/PR triggers target `master`, so a push to `core` does not automatically run it.
- In GitHub Actions UI, select the `core` branch in **Run workflow**.
- A manually dispatched non-default branch is compared with `origin/master` by the verification planner.

### Real-Anki Docker E2E

Workflow: **Full Docker / Anki E2E** (`.github/workflows/ci-e2e.yml`).

Manual inputs:

- `mode`: `standard`, `strict-apkg`, `perf100`;
- `scope`: `full`, `global`, `stats`, `decks`, `activity`, `cards`, `settings`, `notifications`;
- `screenshot_workers`: `auto`, `1`, `2`, `3`, `4`;
- `resource_telemetry`: boolean;
- `verify_restart`: `auto`, `true`, `false`;
- `fast_ci_run_id`: exact successful Fast CI run ID.

The workflow can be dispatched with `core` selected as its ref. Cloud E2E rejects a source-build fallback, so a normal Core branch run must use the exact successful Fast CI package via `fast_ci_run_id`. C1.0 does not require this run. Future Cards rendering/media changes require the targeted Cards browser scope and any final escalation required by the verification matrix.

## Checks actually performed in C1.0

- repository identity and permissions verified;
- default branch verified as `master`;
- current base commit SHA and message verified;
- absence of `core` and other obvious C1/Cards/triage branches verified before creation;
- absence of open pull requests verified;
- `core` created directly from the verified base SHA;
- mandatory current docs, contract files, workflows and representative production/tests inspected;
- changed scope constrained to documentation/report files;
- branch and changed files re-read after commit;
- comparison against `master` used to confirm documentation-only divergence.

## Checks not performed

- local `git status --short --branch`;
- local `git rev-parse HEAD`;
- local `git branch --show-current`;
- local `git log -1 --oneline`;
- local `git diff --check`;
- project scripts, Python tests, frontend tests, typecheck or package validation;
- Fast CI;
- Docker / real-Anki E2E;
- Cards screenshot review from `cards.zip`.

No unexecuted command is reported as passing.

## Manual verification fallback

No manual check is required to accept this documentation-only C1.0 baseline.

For a future C1.1 runtime/UI change:

1. Open GitHub **Actions → Fast CI → Run workflow**.
2. Select branch `core` and run it.
3. Record the successful run ID for the exact Core commit.
4. If the verification matrix requires real Anki, open **Actions → Full Docker / Anki E2E → Run workflow**.
5. Select branch `core`, choose the risk-matched mode/scope and provide the successful `fast_ci_run_id`.
6. Inspect the run summary and redacted artifacts before claiming PASS.

## Long-lived Core branch risks

| Risk | Required control |
| --- | --- |
| Divergence from `master` | periodically audit commits; transfer only named fixes with explicit verification |
| Fixes landing only in `master` | evaluate each fix for Core relevance; cherry-pick or merge deliberately, never automatically |
| Core fixes needed by `master` | do not merge the whole branch; extract only separately approved, verified changes |
| Stale contracts during a long C1/C2 cycle | update baseline/handoff when a public contract or branch policy changes |
| Heuristic content checks | require confirmed note-type profiles and fail-closed behavior before authoritative triage |
| Missing screenshot evidence | review APKG/synthetic light/dark fixtures when `cards.zip` or equivalent evidence becomes available |
| No local working-tree verification in this session | rely only on GitHub object/compare evidence and run local checks when a checkout is available |
| Heavy verification overuse | follow the test matrix and run Docker only for a risk that unit/metadata checks cannot cover |

## Exact prerequisites for C1.1

1. Continue on `core`; do not create a PR, merge or release.
2. Treat this report and current production contracts as the baseline.
3. Define the Product contract for one canonical triage queue: item identity, source, reason, severity, evidence, status and deterministic ordering.
4. Define how `attentionCards`, active card Signals and explicit Search/Notification handoffs map into that queue without duplicate storage or APIs.
5. Define the Inspection Profile confirmation lifecycle and fail-closed behavior for content-quality checks.
6. Keep universal learning issues independent of note-type profiles.
7. Reuse Search inspect, Safe Actions, Notification handoff and isolated preview.
8. Specify backend/frontend/types/tests/docs changes together before implementation.
9. Select focused, Fast CI and real-Anki verification from the actual future diff.

## C1.0 closure

- Pull request created: **no**
- Merge performed: **no**
- Tag or release created: **no**
- Deployment or AnkiWeb publication performed: **no**
- Production code changed: **no**
- Workflow/build script changed: **no**
- Next step implemented: **no**

Next step only:

```text
C1.1 — Product contract
```
