# G0.2 Core compatibility snapshot

## Status

`COMPLETE`

Immediate decision: `NO_IMPORT_REQUIRED`.

The active Core line is the long-lived `core` branch. It is based on the same
current `master` commit as the canonical `gamification` branch. Core changes are
not required for G0.3 and were not imported, merged, rebased or cherry-picked.

## Recorded refs

| Field | Value |
| --- | --- |
| Repository | `AliceLiddell01/anki-study-report` |
| Recorded at | `2026-07-18` |
| Current master SHA | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Gamification snapshot input SHA | `c09f9cedef731c2201ee24df8edcde1b0e1e4669` |
| G0.1 master baseline SHA | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Selected Core branch | `core` |
| Core tip SHA | `e4292d090a79b857b81a987c8e0853656f178e0e` |
| Core merge-base SHA | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Historical Gamification source | `chatgpt/gamification-concept-foundation` |
| Historical source SHA | `48298d02c6871df0ffa112d862d9b2af629c523f` |

`master` did not advance after the G0.1 baseline. The Gamification input SHA is
the branch tip before the G0.2 documentation commits; final branch-tip
verification is recorded in the task closeout because a commit cannot contain
its own resulting SHA.

## Core branch discovery

The discovery pass used branch-name searches for `core`, `c1`, `cards`,
`triage` and `problem`, recent and historical pull requests, repository commit
searches, current roadmap/handoff documents, and direct ref resolution.

| Candidate | Tip SHA | Activity | Scope match | Status | Decision |
| --- | --- | --- | --- | --- | --- |
| `core` | `e4292d090a79b857b81a987c8e0853656f178e0e` | six commits after current `master`; C1.0–C1.2 records and implementation | exact match for C1 Cards v2 / Problem Triage | active long-lived branch | selected |
| former Search/Cards-related PR branches | merged or historical heads | completed Stage 8/Search work | prerequisites, not current C1 | historical | excluded |
| CI, release, telemetry and dispatcher branches | unrelated or historical | non-Core scopes | no C1 match | excluded | excluded |

The connector's generic branch search did not enumerate `core`, but direct
resolution of the exact lowercase ref succeeded. The branch identifies itself
as the active long-lived Core line in `docs/ai-handoff.md`,
`roadmap/core/README.md` and the C1 reports. No competing active Core branch or
Core pull request was found.

The six Core commits are:

```text
2b99b3468de0a46b00ce5be71e7c95da0930fb12  docs: establish the long-lived core branch baseline
22c6820bee44d25c3d10b871eb008a91cd56da31  docs: define the Cards v2 product contract
ae27a9f3f8bb295b09ae9305f825eb4d615ae6e3  docs: clarify the Cards display-mode contract
13b1a20ec704ebc8e6cd05ee6d243ac6576b6f56  feat: add the bounded canonical triage read API
e7c4eded97886dc902499a0f4bdb44e842599bde  docs: document the canonical triage read contract
e4292d090a79b857b81a987c8e0853656f178e0e  docs: close the canonical triage read milestone
```

C1.2's implementation/report candidate `e7c4eded97886dc902499a0f4bdb44e842599bde`
passed Fast CI run `29637594843`. No workflow run or combined status was exposed
for the final documentation-only tip `e4292d090a79b857b81a987c8e0853656f178e0e`;
this does not change the compatibility decision, but it means the final closeout
tip's exact-SHA gate was not independently confirmed in G0.2.

## Pairwise comparisons

### master ↔ gamification

| Item | Value |
| --- | --- |
| Status | `gamification` ahead |
| Ahead / behind | `2 / 0` before G0.2 documentation writes |
| Merge base | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Changed paths | `roadmap/gamification/README.md`; `roadmap/gamification/g0-branch-baseline.md` |

The pre-G0.2 Gamification branch still contained only the two G0.1 Markdown
changes. It contained no research package, Core implementation or production
change.

### master ↔ Core

| Item | Value |
| --- | --- |
| Status | `core` ahead |
| Ahead / behind | `6 / 0` |
| Merge base | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Changed paths | 26 |
| Current increment | `C1.2` Complete; `C1.3` Next |

Logical change groups:

- C1.0 long-lived branch baseline and delivery policy;
- C1.1 Cards v2 product/IA contract;
- C1.2 additive bounded triage read API and deterministic projection;
- backend wiring through the existing dashboard server and serialized `QueryOp`;
- reuse of attention-card, Search projection and active card-Signal sources;
- strict TypeScript types, parser/client and focused backend/frontend tests;
- Core documentation, contracts, roadmap and evidence reports.

No workflow, release, package-layout or generated-asset path differs from
`master`.

### gamification ↔ Core

| Item | Value |
| --- | --- |
| Status | diverged |
| Core commits ahead of common base | `6` |
| Gamification commits ahead of common base | `2` before G0.2 writes |
| Merge base | `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e` |
| Same-path edits | none |
| Structural dependency | none for G0.3–G0.7 reconciliation work |
| Semantic dependency | future G3 provenance and G5/G6 production architecture must revisit stable Core contracts |

The G0.1 changes are confined to `roadmap/gamification/`. Core changes are in
runtime, tests, `web-dashboard/src/lib` and `src/types`, Core contracts/reports,
and `roadmap/core/README.md`. There is no current textual conflict or competing
edit to the same file.

## Changed-area analysis

### Core product/runtime

C1.2 adds `triage_service.py`, `triage_runtime.py`, route/add-on wiring and small
adapters in existing attention, Search and NotificationStore paths. It is an
additive read projection, not the complete Cards v2 workspace. The current
Cards page remains on legacy `attentionCards`.

Impact: no dependency for G0.3–G0.7 research reconciliation. Future production
Gamification must consume stable public contracts after Core integration rather
than copy this unfinished branch directly.

### Frontend and dashboard contracts

Core adds strict triage types and a fail-closed API client/parser. It does not
wire CardsPage, add the Inspector UI or create Gamification UI.

Impact: no current research dependency. Future G6 UI integration must align
with the final App Shell, Cards and handoff contracts after C1/C2 stabilization.

### Backend/API/payload

`POST /api/triage/query` is token-protected, loopback-only, bounded and additive.
Legacy report payload, Search routes, Safe Actions and `attentionCards` remain
unchanged. The schema is explicitly pre-1.0 until C2 contract freeze.

Impact: importing the pre-freeze endpoint into Gamification would create an
unnecessary dependency. Wait for acceptance through `master`.

### Persistence and migrations

C1.2 adds no triage persistence or migration. C1.3 Inspection Profiles and C2
migration/recovery policy remain future Core work.

Impact: no current action. Inspection Profile persistence and C2 schema policy
must be watched before G5 designs a Gamification ledger, migrations or profile
reconciliation.

### Cards/Search/Actions/Signals integrations

Core deliberately reuses the existing attention collector, exact Search row
projection, active card Signals, Safe Actions boundaries, Notification handoff
and isolated preview. It creates no duplicate query/action/signal stack.

Impact: these reuse boundaries are relevant design constraints for later G3,
G5 and G6, but they do not block historical asset inventory or simulation
reconciliation.

### Tests and E2E fixtures

Core adds focused Python and TypeScript tests. The implementation/report
candidate passed focused checks, canonical non-Docker verification and exact-SHA
Fast CI. No E2E fixture or workflow path changed, and real-Anki E2E was
intentionally not run for C1.2.

Impact: Core-specific evidence; no import into Gamification research.

### CI/release/platform

No Core delta exists in `.github/workflows/`, release files, packaging scripts
or Docker E2E infrastructure.

Impact: irrelevant to G0.3.

### Documentation and roadmap

Core adds its own contracts/reports and updates Core-oriented current docs.
Gamification edits different paths. `docs/ai-handoff.md` will eventually need a
normal compatibility refresh when stable Core work reaches `master`, not a
cherry-pick from the active branch.

Impact: no same-path conflict now; wait for `master`.

### Repository/tooling

No repository tooling change is present.

Impact: irrelevant to Gamification.

### Security/privacy boundaries

Core preserves loopback binding, token validation, serialized collection access,
sanitizer/media/Shadow DOM isolation, action allowlists and local-only Signal
evidence. It introduces no telemetry taxonomy expansion.

Impact: compatible with Gamification's local-first direction. Revalidate these
boundaries in G5 rather than importing implementation now.

### Generated assets

No generated dashboard asset, runtime artifact, screenshot, profile data,
token, `.ankiaddon` or E2E output is part of the Core delta.

Impact: irrelevant to Gamification.

## Compatibility decision matrix

| Core change group | Current stability | Interaction with G | Decision | Rationale |
| --- | --- | --- | --- | --- |
| C1.1 Cards v2 product contract | accepted inside active Core, not in `master` | no dependency for G0.3–G0.7; later G6 UX boundary | `WAIT_FOR_MASTER` | product contract belongs to Core and may still evolve through C1 |
| C1.2 triage runtime and read API | additive candidate verified; schema pre-1.0 | possible later input/context surface, not a research prerequisite | `WAIT_FOR_MASTER` | direct import would bind G to an unfinished Core API |
| Search/Signals/attention reuse rules | explicit and security-aligned | informs G3 provenance and G5/G6 integration | `COMPATIBILITY_WATCH` | retain as a design constraint; no code transfer required |
| C1.3 Inspection Profiles | future, not implemented | may affect Create/content XP provenance and profile-local persistence | `COMPATIBILITY_WATCH` | revisit after the contract/runtime exists |
| C2 migration/versioning/recovery policy | future | direct dependency for production ledger/migrations in G5 | `COMPATIBILITY_WATCH` | G5 already waits for sufficiently stable C2 contracts |
| Core tests and evidence reports | Core-specific | no research or production dependency | `IRRELEVANT_TO_G` | do not copy another track's verification package |
| CI/release/platform | no Core delta | none | `IRRELEVANT_TO_G` | no changed area to reconcile |
| Core roadmap/current-doc updates | active-branch documentation | eventual handoff refresh after integration | `WAIT_FOR_MASTER` | stable updates should arrive through accepted `master` history |

No group qualifies for `IMPORT_NOW`, `ADAPT_MANUALLY` or `BLOCKS_G0`.

## Immediate decision

`NO_IMPORT_REQUIRED`

G0.3 can begin from the current canonical `gamification` branch without Core
code, contracts or commits. The normal path remains:

```text
accepted Core work → master → named future compatibility checkpoint → gamification
```

The active `core` branch must not be merged, rebased or cherry-picked into
`gamification` during G0.2.

## Watchlist for later G stages

### G0.3–G0.7

- inventory historical assets against the current repository structure;
- do not rewrite research artifacts around the pre-1.0 triage API;
- record references to Cards/Search/Signals only as external current contracts;
- no Core import is needed to reproduce or classify historical research.

### G3

- revisit action provenance, duplicate/reset/import farming boundaries and the
  final Cards/Search/Safe Actions contracts before Create XP is frozen;
- Inspection Profiles may become relevant to evidence that a content fix is
  useful, but must not become an unreviewed reward oracle.

### G5

- wait for stable C2 migration, versioning, profile-isolation and recovery
  contracts before finalizing the production Gamification ledger;
- preserve separation from triage/notification persistence;
- align reconciliation and public API versioning with accepted Core policy.

### G6

- reuse stable App Shell, Cards handoff, Search, Safe Actions, Signals and
  Notification surfaces;
- do not create a second collection query/action stack or send study evidence to
  telemetry;
- run a new compatibility checkpoint before product integration.

### Integration gate

Before any production merge decision, compare the then-current `master`,
`gamification` and accepted Core state again. A branch name or current C1.2
snapshot is not a permanent compatibility guarantee.

## Verification

Tools and evidence used:

- GitHub repository metadata and exact ref resolution;
- branch-keyword searches and recent/historical PR inspection;
- commit searches and direct commit resolution;
- branch-scoped file reads from `gamification` and `core`;
- `master...gamification`, `master...core` and `gamification...core`
  comparisons;
- Core exact candidate Fast CI evidence recorded in current Core docs;
- final G0.2 documentation diff verification after writes.

Paths inspected include the mandatory G0.2 documents, current Core roadmap and
handoff, C1.0–C1.2 reports, Cards v2 product/read contracts, and the complete
per-file compare inventory.

Tests intentionally not run:

```text
Fast CI: not required for G0.2 documentation
Docker E2E: not required
real-Anki E2E: not required
Python/Node/Rust tests: not required
```

G0.2 changes only Markdown documentation and executes no production or research
code.

## Environment limitations

- no local repository checkout or project shell was available;
- `git diff --check` and an automated relative-link checker were not run;
- generic connector branch search returned no enumeration, so exact refs,
  comparisons, PR metadata and branch-owned documents were used;
- `AGENTS.md` and `agents.md` do not exist on the inspected `gamification` ref;
- no new GitHub Actions workflow was dispatched;
- the connector exposed no workflow run or combined status for the final Core
  documentation tip.

## Recorded guarantees

- `master` was not changed;
- `core` was read only and was not changed;
- the historical Gamification branch was read only;
- G0.1 baseline was not rewritten;
- no Core or research asset was imported;
- no merge, rebase, cherry-pick, force update or branch synchronization occurred;
- no production, frontend, backend, test, workflow, package or generated file
  was changed by G0.2;
- no pull request, tag, release, deployment or publication was created.

## Next step

`G0.3 — Historical asset inventory`

G0.3 was not started in this task.
