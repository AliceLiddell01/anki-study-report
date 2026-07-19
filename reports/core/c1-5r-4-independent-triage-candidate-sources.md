# C1.5R.4 — Independent triage candidate sources

## Confirmed state

- initial `core` HEAD: `8a91a69f147e78133673924d20bee296a15f562f`
- tested implementation HEAD: `31b3b795e055f6be963c129b3edc1afdfc9dcd57`
- tested implementation tree: `2aa017edbd992402e11b97967adccd33c56f7a02`
- final verification run: `29701478622` — PASS
- post-transfer run: `29701642665` — PASS
- transfer: exact fast-forward to `core`, no conflict and no force
- PR / merge to `master` / release / deployment: none

## Reconstruction

The durable implementation was reconstructed from the latest temporary R4
candidate onto exact `core`. The clean implementation history contains one
logical commit and 25 durable files. Apply/verify scripts, temporary workflow
YAML, triggers, status files, logs, generated dashboard assets and package
output were excluded from the implementation tree.

The backend now owns independent bounded loaders:

- `learningCandidates`: review-history source bounded by the requested period;
- `contentCandidates`: current-content source independent of review history;
- authoritative confirmed Inspection Profiles are resolved before note scanning;
- current content uses a 500-note `note.id > contentCursor` keyset window and one
  batched card/note read;
- one note is evaluated once and anchored to a deterministic applicable card;
- Search identity resolution runs only for cards carrying merged reasons.

Triage request/response schema is strict v4. Search remains schema v2. R1 compact
identity and R3 preview semantics are unchanged. R5 layout work was not started.

## Verification

| Contour | Exit | Duration seconds |
| --- | ---: | ---: |
| Materialization and diff checks | 0 | 0.3 |
| Python dependency install | 0 | 3.1 |
| Frontend dependency install | 0 | 1.3 |
| Bootstrap `pnpm run build:addon` | 0 | 18.7 |
| Focused backend | 0 | 11.8 |
| Focused frontend | 0 | 2.6 |
| TypeScript typecheck | 0 | 10.2 |
| Production build | 0 | 17.8 |
| Package build and validation | 0 | 0.2 |
| Package `--check-only` | 0 | 0.1 |
| API smoke | 0 | 1.5 |
| Canonical `run_full_check.ps1 -SkipDocker` | 0 | 63.9 |
| Git hygiene / denylist | 0 | 0.0 |

Focused backend: `104 passed`.

Focused frontend: 3 files / `21 passed`.

Canonical non-Docker gate: `788 Python tests passed`; frontend suite, build,
bundle guard, package build/validation and ZIP integrity passed. Package had 73
entries and `ZipFile.testzip() = None`.

Post-transfer checks ran on exact detached `core` SHA
`31b3b795e055f6be963c129b3edc1afdfc9dcd57`:

| Contour | Exit | Duration seconds |
| --- | ---: | ---: |
| Focused backend | 0 | 12 |
| Focused frontend | 0 | 3 |
| Typecheck | 0 | 10 |
| API smoke | 0 | 1 |
| Git hygiene | 0 | 0 |

## Acceptance scenarios

- zero reviews + confirmed Japanese audio requirement → `content.audio_missing`;
- Programming profile without audio requirement → no audio false positive;
- period changes do not alter current-content candidates;
- deck scope and profile template scope are applied before representative-card
  selection;
- continuation uses a strictly increasing note-ID cursor, bounded to 500 notes,
  with no duplicate/automatic loop;
- no confirmed profiles → no content SQL scan;
- source failures are represented independently instead of collapsing the other
  source;
- current-content collection uses two bounded DB reads and no N+1 profile/check
  queries;
- candidate scan performs no preview rendering and no media file reads.

## Failure classification

Temporary verification attempts exposed only reconstruction/test-contract defects:

- stale v3 backend assertions and old shared-collector monkeypatches;
- incomplete strict-v4 frontend fixtures;
- a test regex that incorrectly placed `contentCursor` in a response fixture.

Production behavior was not changed to satisfy obsolete tests. Every fix was
followed by the full focused contour, and the final implementation passed the
canonical gate.

## Workflow and artifact evidence

- final isolated verification: run `29701478622`, exact trigger
  `2d14e9eb8eed37791f80ded4b358de4254c67c14`, PASS;
- post-transfer verification: run `29701642665`, exact trigger
  `39859c3529fe8eb47382ca192c3743f5ed25adb0`, PASS;
- narrow fixture inspection: run `29701445382`, completed;
- earlier temporary failed attempts retained as historical evidence:
  `29699284419`, `29699354074`, `29699584092`, `29699696383`,
  `29699845625`, `29701073993`, `29701152231`, `29701316740`;
- final and post-transfer runs published no Actions artifacts;
- the connector exposes no workflow-run/artifact deletion action, so completed
  run records remain immutable; no R4 temporary run remains active.

## Cleanup

All surviving temporary refs were fast-forwarded to commits whose tree is exactly
the clean implementation tree. This preserves historical evidence in ancestry
while removing every workflow, apply/verify script, trigger, log and status file
from current ref tips. The connector has no delete-ref operation, so neutralized
refs remain as clean, non-runnable pointers. Canonical workflows were not changed.

```json
{
  "canonicalWorkflowsTouched": false,
  "coreR4MarkerFiles": [],
  "coreTemporaryScripts": [],
  "coreTemporaryWorkflowFiles": [],
  "localTaskBranch": "not_created",
  "localWorktree": "not_created",
  "temporaryActionsRuns": "completed; deletion API unavailable",
  "temporaryArtifacts": [],
  "temporaryRemoteRefs": {
    "c1-5r-4-candidate-sources": "neutralized",
    "c1-5r-4-final-run": "neutralized",
    "c1-5r-4-final-status": "neutralized",
    "c1-5r-4-verify-run": "neutralized",
    "c1-5r-4v-closeout-exec-20260720": "neutralized_after_closeout",
    "c1-5r-4v-closeout-status-20260720": "neutralized_after_closeout",
    "c1-5r-4v-exec-20260720": "neutralized",
    "c1-5r-4v-post-status-20260720": "neutralized",
    "c1-5r-4v-posttransfer-20260720": "neutralized",
    "c1-5r-4v-status-20260720": "neutralized"
  }
}
```

## Security and privacy

- raw note values remain internal and are absent from response/log contracts;
- no media file reads or preview renders occur in candidate collection;
- SQL is internal, read-only and parameterized; no arbitrary SQL input exists;
- loopback/token/content-type/body-size boundaries are unchanged;
- no token-bearing URL, private path, owner profile data or runtime logs entered
  the durable Git history.

## Changed files

- `anki_study_report/triage_candidates.py`
- `anki_study_report/triage_service.py`
- `docker/anki-e2e/README.md`
- `docs/README.md`
- `docs/architecture.md`
- `docs/cards-v2-product-contract.md`
- `docs/cards-v2-triage-read-api.md`
- `docs/dashboard-api.md`
- `docs/frontend-map.md`
- `docs/security-and-safety.md`
- `docs/test-matrix.md`
- `docs/triage-candidate-sources-v4.md`
- `tests/test_dashboard_server.py`
- `tests/test_package_build.py`
- `tests/test_triage_candidates.py`
- `tests/test_triage_runtime.py`
- `tests/test_triage_service.py`
- `web-dashboard/src/hooks/useCardsTriageWorkspace.test.tsx`
- `web-dashboard/src/hooks/useCardsTriageWorkspace.ts`
- `web-dashboard/src/i18n/locales/en.ts`
- `web-dashboard/src/i18n/locales/ru.ts`
- `web-dashboard/src/lib/triageApi.test.ts`
- `web-dashboard/src/lib/triageApi.ts`
- `web-dashboard/src/pages/CardsPage.test.tsx`
- `web-dashboard/src/types/triage.ts`
- `roadmap/core/README.md`
- `roadmap/README.md`
- `docs/ai-handoff.md`
- `reports/core/c1-5r-4-independent-triage-candidate-sources.md`

## Not verified

- Fast CI;
- Docker / real-Anki E2E;
- owner private Anki profile;
- owner product acceptance;
- C1.5R.5 UI acceptance.

## Git boundary

```text
pushed to origin/core: yes
PR: no
merge into master: no
force-push: no
release: no
deployment: no
AnkiWeb publication: no
```

## Status

```text
C1.5R.0 — Complete
C1.5R.1 — Complete
C1.5R.2 — Complete
C1.5R.3 — Complete
C1.5R.4 — Complete
C1.5R.5 — Next, not started
C1.5R.6–R.7 — Not started
C1.6 — Blocked
Core C1 — In progress
```
