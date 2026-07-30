# G5.2 Study Rhythm contract freeze evidence

**Date:** 2026-07-30
**Mode:** Codex local checkout / Windows PowerShell 7
**Repository:** local Windows checkout `<workspace>/anki-study-report`
**Target branch:** `chatGPT/G5`
**Base:** `origin/gamification`
**Contract candidate commit:** `7d8c834904ea8f12f2432c8373f4839e3ccc9da2`

## Outcome

```text
G5: IN PROGRESS / NOT COMPLETE
G5.0: COMPLETE
G5.1: COMPLETE
G5.1 owner visual acceptance: GRANTED
G5.1 merge: PR #182 / 4c16753fdbd0367b16c9fc9992602f3f86f65c5f
G5.2: CONTRACT CANDIDATE / REVIEW PENDING
G5.2 merge: NOT PERFORMED
G5.3: NOT STARTED
G6/G7/G8: NOT STARTED
```

G5.2 freezes the minimal Study Rhythm v1 contract as documentation, strict
schemas, canonical fixtures and executable contract tests. It does not
implement the store, service, endpoint handlers, report integration, frontend
route or UI.

## Preflight and topology

Initial local task state:

```text
branch: chatGPT/G5
initial HEAD: ad54dc73d144e843afb7dbb2e4e1634ad9a69d20
initial tree: clean
```

Verified remote state:

```text
G5.1 PR: #182
G5.1 PR state: MERGED
G5.1 base/head: gamification <- chatGPT/G5
G5.1 merge commit: 4c16753fdbd0367b16c9fc9992602f3f86f65c5f
open PR from chatGPT/G5 to gamification: none
origin/gamification: 4c16753fdbd0367b16c9fc9992602f3f86f65c5f
```

The only commit between the initial local HEAD and `origin/gamification` was
the verified G5.1 merge commit; its second parent contained the same content.
The existing branch was advanced with:

```text
git merge --ff-only origin/gamification
```

No branch, worktree, clone, rebase, reset or force operation was used.

## Sources reviewed

The contract was reconciled against:

- repository agent rules, README, AI handoff and local Codex environment rules;
- Gamification index, G5–G8 roadmap and G5.1 contract/evidence;
- architecture, dashboard API, frontend map, profile, navigation, test matrix
  and verification policy documentation;
- current `activity_service.py`, `profile_service.py`, `dashboard_server.py`
  and report refresh integration in `anki_study_report/__init__.py`;
- current ActivityHub, Profile and dashboard server tests;
- existing strict JSON Schema/store-test conventions;
- add-on package manifest logic and Fast CI workflow boundaries.

Confirmed source compatibility:

- ActivityHub v1 distinguishes `active`, `inactive` and `unavailable`;
- ActivityHub exposes `scope.kind` as `all` or `selected`;
- ProfileModel provides current and best existing streak context;
- report refresh derives Profile and ActivityHub from the same cache snapshot;
- the local dashboard API remains loopback/token protected;
- no Gamification handler or route exists;
- new root schemas, fixtures and docs are not add-on package inputs.

The prompt named `tests/test_activity_service.py`; that file does not exist in
the current checkout. The authoritative current ActivityHub coverage is
`tests/test_activity_feed.py`.

## Frozen contract

The candidate fixes:

- schema versions `1` and calculation version `study-rhythm-v1`;
- UTC `Z` timestamps, ISO dates/weekdays and Monday–Sunday weeks;
- ActivityHub v1 all-collection scope as the only activity source;
- disabled defaults, safe revisions, feasibility and ascending stored/public
  rest weekdays;
- missing/corrupt/future-schema store behavior;
- strict optimistic-concurrency `replace` and `reset` mutations;
- public availability, coverage, today, seven-day week, progress,
  opportunities and completion-state rules;
- up to four factual fully covered completed weeks;
- existing Profile streak as explicitly non-rest-aware context;
- bounded explanation, limitation and error allowlists;
- no post-MVP reward/economy fields.

The normative human contract is
[`study-rhythm-mvp-contract-v1.md`](../../docs/gamification/study-rhythm-mvp-contract-v1.md).

## Artifact inventory

Primary artifacts:

| SHA-256 | Path |
| --- | --- |
| `0f4494658a9c6439213efd954952f08db52407fdefb2ef542ed6f6d43ce2a3fd` | `docs/gamification/study-rhythm-mvp-contract-v1.md` |
| `e718d2ac7a2858eeed972ea1ac7a077c2379b2f071597703f453d66b999e83c0` | `schemas/gamification-settings-v1.schema.json` |
| `d566bcd00aac11fb097f20dc7e447bf6a6676c6cdc4ba0edb46332aa23340dd6` | `schemas/gamification-settings-request-v1.schema.json` |
| `afa2e2c07fa05829fbda6eb5cb6cb41a63e2d00ba312651a2b2dc80586fab430` | `schemas/gamification-model-v1.schema.json` |
| `c5c61dc2999def824ef6c9aaba893fce67396418d7ebcb7619acdb2d56e13a5e` | `schemas/gamification-error-v1.schema.json` |
| `da0fe37e94d0438aad158edc702b1611f2c4e64eaae66a1c2fc234bbd80bcd52` | `tests/test_gamification_contract_v1.py` |

Fixture inventory:

| SHA-256 | Fixture |
| --- | --- |
| `2572b3ca3183c06d7303f350910d59f2d9ca7194b3925c5196f021988bb66899` | `error-revision-conflict.json` |
| `f8f5263243a58be3c06a162ae3725e6140bab4dd202b093ef102d5b245cf7007` | `error-store-unavailable.json` |
| `7988c2211516ba9ebb5b2bd1b28aa408988e2b5e1269c709790bb0c62c5290fb` | `model-active-on-rest-day.json` |
| `1375c5f3aed2a4a91622ae6d4e1c658d579a6b4d5eea3aad4ae6ecb05384075e` | `model-completed-week.json` |
| `96484a9e15d03a4e21135722527dfe55d2ab5eb2e7ceda5a01bfae6922c3787d` | `model-disabled.json` |
| `f0e4d9e1374570e08f37a2b1807544fc0ef4ce824d04a4a1f283f843d859e093` | `model-enabled-in-progress.json` |
| `eeb8b366e64f9157e696b887ef5082c946f8494920ed92f4972feaaee6286a5c` | `model-partial-coverage.json` |
| `1c0e2a0be7a4213b55112dc196dbdac32aa51e32893249607d311ed029c7f705` | `model-planned-rest-today.json` |
| `c3c8726f1d2bcb7c6f8f3dbd971179a240e5f9648c87f426e280bace5715e14a` | `model-unavailable-source.json` |
| `416dd0240dde57510734cd0ce0b623fe6dd11e492187c36cc831b54a921fb2e2` | `settings-default-disabled.json` |
| `2e94eb947eaeebf6078444868106954bed4e052a317c0d0e2fc789fe60598fa9` | `settings-replace-enabled.json` |
| `018632d4ace0c2050ac21d58598bccbfdbb1ac0cb218f7832236dffad7aa9004` | `settings-reset-request.json` |

## Validation

Checks executed on exact contract candidate
`7d8c834904ea8f12f2432c8373f4839e3ccc9da2`:

| Check | Result | Evidence |
| --- | --- | --- |
| `node scripts/run_python.mjs -m pytest tests/test_gamification_contract_v1.py -q` | PASS | `17 passed in 0.55s` |
| `node scripts/run_python.mjs -m compileall -q tests/test_gamification_contract_v1.py` | PASS | exit `0` |
| `node scripts/run_python.mjs scripts/check_task_scope.py` | PASS | `Changed paths: 21`, `task-scope: PASS` |
| `git diff --check origin/gamification..HEAD` | PASS | exit `0` |
| clean candidate tree | PASS | no dirty or untracked files |
| duplicate-key JSON parsing | PASS | exercised by focused pytest |
| Draft 2020-12 schema self-validation | PASS | exercised by focused pytest |
| valid fixture schema + semantic validation | PASS | all 12 canonical fixtures |
| mandatory invalid cases | PASS | all 12 cases rejected |
| human JSON example parity | PASS | all 5 named examples equal fixtures |
| forbidden post-MVP machine fields | PASS | exercised by focused pytest |
| runtime/frontend/package/CI path audit | PASS | no prohibited changed paths |
| secret and absolute-path audit | PASS | no findings |

After adding this evidence report, the final 22-path candidate was checked
again:

| Check | Result |
| --- | --- |
| focused contract pytest | PASS — `17 passed in 0.54s` |
| Python compile | PASS |
| task scope guard | PASS — `Changed paths: 22` |
| Git diff hygiene | PASS |
| Markdown local links and code fences | PASS |
| sensitive-data audit | PASS |

## Not run

- Full non-Docker suite: **NOT RUN** — no production/shared runtime change.
- Frontend lint/typecheck/build: **NOT RUN** — no frontend source change.
- Add-on package validation/build: **NOT RUN** — no package input changed.
- Fast CI: **NOT RUN / NOT TRIGGERED** — workflow does not run for this
  contract-only branch/base and no package-impacting change exists.
- Docker or real-Anki E2E: **NOT RUN** — no runtime, API, route or UI exists to
  exercise.
- Owner visual acceptance: **NOT APPLICABLE** — G5.2 has no UI.

These omissions are intentional under `docs/test-matrix.md` and
`docs/verification-run-policy.md`; they are not substitutes for later G5.3+
runtime verification.

## Scope and risk review

```text
runtime changed: NO
public live payload/API changed: NO
persistence implementation changed: NO
frontend/route/UI changed: NO
package contents changed: NO
Docker/real-Anki behavior changed: NO
documentation changed: YES
machine contract changed: YES
fixtures/tests changed: YES
release/publication/master changed: NO
```

Residual risk is limited to design review: a reviewer may request a contract
change before G5.3. Any such change must update the human contract, affected
schemas, fixtures and executable tests together. G5.2 must not be marked
complete or merged by this report.

## Next gate

Create one new Draft PR from `chatGPT/G5` to `gamification`, keep it unmerged,
and request contract review. G5.3 remains blocked until G5.2 is reviewed and
merged by the owner.
