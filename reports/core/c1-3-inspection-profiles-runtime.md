# C1.3 — Inspection Profiles: contract and runtime

## Status

**Current:** Implemented; candidate exact-SHA Fast CI passed. Targeted real-Anki
`standard/cards` verification remains pending after two diagnosed harness
failures; the second fix has local evidence only.
**C1.4:** Blocked; no UI work started.

## Baseline and scope

- branch: `core`;
- base: `master` at `359c26f82a9ee78c8e27603f9ded5ca9bef2c71e`;
- initial HEAD/origin-core: `e4292d090a79b857b81a987c8e0853656f178e0e`;
- initial divergence `origin/master...HEAD`: `0 6`;
- initial worktree: clean;
- open PR from `core`: none;
- C1.2 exact-initial-HEAD Fast CI: run `29637745360`, PASS;
- PR, merge, release, deployment and AnkiWeb publication: prohibited and not performed.

In scope is the backend/store/API/TypeScript foundation and triage content
source. C1.4 Settings UI, CardsPage migration, Inspector, import/export,
arbitrary rules, media existence and collection mutations remain out of scope.

## Sources reviewed

Repository sources included README/roadmap/handoff, product and triage
contracts, C1.2 report, architecture/frontend/security/test/verification
documents, current attention/note-intelligence/Search/QueryOp/server/store
implementations, frontend triage parser/tests and the real-Anki E2E harness.

Primary external sources:

- [Anki Manual — Getting Started](https://docs.ankiweb.net/getting-started.html): note types, fields, cards;
- [Card Templates](https://docs.ankiweb.net/templates/intro.html), [Field Replacements](https://docs.ankiweb.net/templates/fields.html) and [Template Errors](https://docs.ankiweb.net/templates/errors.html): template/field identity and change behavior;
- [Add-on Configuration / User Files](https://addon-docs.ankiweb.net/addon-config.html): add-on local data boundaries;
- [Background Operations](https://addon-docs.ankiweb.net/background-ops.html): serialized `QueryOp` read boundary;
- [JSON Schema Core 2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html) and [Validation 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation.html): portable schema dialect.

No secondary source overrode code/current-contract evidence.

## Architecture and decisions

```text
Anki models/cards via QueryOp
→ bounded structure/candidate readers
→ InspectionProfileStore + InspectionProfileService
→ allowlisted evaluation
→ profileChecks adapter
→ canonical triage v2
```

1. One strict JSON document v1 is stored per active Anki profile at
   `<profile>/addon_data/<addon-id>/inspection_profiles.json`; no collection or
   global-config storage is used.
2. Store ownership is limited to validation, revision, atomic persistence and
   recovery. Writes use same-directory temp + flush + fsync + replace.
3. Missing is revision-0 empty; corrupt input is quarantined; a future schema
   is preserved and rejects writes; optimistic revision conflicts are typed.
4. The Draft 2020-12 artifact and native validator reject unknown fields. The
   native layer additionally enforces cross-object uniqueness, exact mappings,
   signed-64-bit IDs and check-to-role relationships.
5. Fingerprint is SHA-256 over canonical noteTypeId, ordered exact fields,
   ordered template identities/front-back field refs and standard/cloze kind.
   CSS/static text/sample values/deck assignment do not affect it.
6. Suggestions reuse local deterministic note intelligence and are never
   authoritative or auto-confirmed.
7. Only `confirmed` plus current fingerprint/exact refs is authoritative;
   suggested/disabled/not-configured/needs-review/unavailable fail closed while
   learning reasons remain.
8. Check runtime is a strict discriminated allowlist: non-empty, audio marker,
   image ref, min text length, one-of roles and all roles. No regex/code/query/
   network/filesystem/media existence capability exists.
9. Preview is exact-ID batched and capped at 20. Evidence contains identities,
   safe lengths/marker result/revision/fingerprint/sibling count, never values,
   HTML, filenames, paths, token or template source.
10. Three POST JSON endpoints reuse the loopback token boundary. Current model
    and card reads run in `QueryOp`; only the profile-local file is written.
11. Triage is explicitly schema v2. Stable reason identity includes profile
    and check ID; content scope is note; Search first-selected and automatic
    smallest-card representative rules prevent sibling duplication.
12. Automatic triage uses one 100+sentinel bounded revlog/card/note candidate
    query shared by learning/content projection. Legacy `attentionCards` and
    its heuristic `missing_*` output remain unchanged and non-authoritative.

## Contracts and bounds

- document 1 MiB; profiles 500;
- mappings/checks per profile 32/32;
- refs per mapping/check 16/16;
- structure fields/templates 64/32;
- query catalog IDs 200, catalog result 500;
- preview cards 20;
- automatic candidates 100 plus one truncation sentinel;
- Search workset 200;
- profile API request body 64 KiB; triage request body remains 8 KiB.

Full schema/lifecycle/check/API/evidence behavior is in
[`docs/inspection-profiles-v1.md`](../../docs/inspection-profiles-v1.md).
Canonical reason/source/item behavior is in
[`docs/cards-v2-triage-read-api.md`](../../docs/cards-v2-triage-read-api.md).

## Implementation and compatibility

Production modules added:

- `inspection_profile_store.py`;
- `inspection_profile_service.py`;
- `inspection_profile_runtime.py`.

Existing runtime changes wire the per-profile store, API handlers, bounded
candidate collector and triage v2 profile source. Frontend adds strict
`types/inspectionProfiles.ts`, `inspectionProfilesApi.ts` and tests, and bumps
the unused triage foundation to v2. No route, component, form or generated
dashboard asset was added/edited.

Compatibility retained:

- legacy report `attentionCards` and current CardsPage;
- Search query/inspect and Safe Actions;
- Signals/Notification Center;
- sanitized Shadow DOM previews/media endpoint;
- loopback/token and 8 KiB limits for existing endpoints;
- no remote telemetry taxonomy or payload change.

## Tests and local evidence

Focused results before canonical closeout:

- profile/store/service/runtime focused slice: 16 PASS;
- profile/triage/runtime/dashboard integration slice: 42 PASS;
- frontend profile + triage Vitest: 10 PASS;
- frontend TypeScript `tsc --noEmit`: PASS;
- final E2E/attention helper slice after diagnosed fixes: 35 PASS;
- final full Python suite with JSON Schema parity: 706 PASS, 4 expected
  platform SKIP, 25.74 s;
- `node scripts/run_python.mjs -m compileall -q anki_study_report`: PASS;
- `git diff --check`: PASS at the local closeout checkpoint.

Two Python invocations encountered one hygiene-only failure apiece because an
earlier explicit compilation/test run had created
`anki_study_report/__pycache__`. In each case the exact generated directory was
verified inside the workspace and removed; each immediate full rerun passed.

Canonical `run_full_check.ps1 -SkipDocker`: final PASS in 51.9 s (frontend
276 PASS; Python 706 PASS/4 expected platform SKIP; package 66 entries).
Candidate exact-SHA Fast CI: PASS; final post-evidence Fast CI is reported in
the handoff response.
Targeted real-Anki: pending.

## Targeted real-Anki plan

The actual model/field/profile-local persistence risk requires one
`Full Docker / Anki E2E` dispatch on `core` after exact-SHA Fast CI:

```text
mode=standard
scope=cards
verify_restart=true
fast_ci_run_id=<exact successful Fast CI run>
```

The cards harness now creates `E2E Japanese Vocabulary` and `E2E Programming`
note types, confirms both profiles through supported API, asserts exactly one
Japanese missing-audio reason, no Programming audio requirement, independent
learning reason and value-safe evidence. During the controlled restart fixture
only, Anki is stopped and a Japanese front-template field reference is added.
The restart assertion requires persisted revision/profile identity, Japanese
`needs_review` with content fail-closed, Programming still confirmed and the
learning reason still present. Product runtime performs no collection mutation.

No screenshots are required because C1.3 changes no UI. Full/strict-APKG/
Perf100 are not part of this risk-matched proof unless the verification planner
escalates based on the final diff.

## Security and privacy

- no arbitrary regex/code/SQL/shell/import/callback/network rule;
- no media-file existence or filesystem scan;
- no user-controlled store path;
- no note/profile/check telemetry;
- no raw values, media filenames, paths, token or exceptions in evidence/API
  failures/log metadata;
- future/corrupt/unavailable/stale states fail closed;
- runtime profile JSON, databases, logs, tokens, screenshots, build outputs and
  E2E artifacts are excluded from commits.

## Commits and cloud evidence

Implementation commits:

- `d82c0ca` — `feat: add confirmed inspection profile runtime`;
- `d549ed4` — `test: cover inspection profile lifecycle and restart`;
- `1d20ac2` — `docs: document inspection profile runtime boundaries`;
- `b8f584f` — `fix: select exact media fixture in cards E2E`;
- `4d9d693` — `fix: separate cards E2E inspection fixture risk`.

Candidate Fast CI evidence:

- run `29640555184`: PASS on `1d20ac2aeaa92a69886628314368954d500863c7`;
  exact package and `ci-fast` diagnostics artifacts present with SHA-256
  digests;
- run `29640792565`: PASS on `b8f584feb121e228b89cd3c35b24ab08dfd8f5c6`;
  exact package and diagnostics artifacts present with SHA-256 digests.

Targeted Docker evidence:

- run `29640654092`, `standard/cards`, `verify_restart=true`, source Fast CI
  `29640555184`: FAIL before restart because the API smoke helper selected the
  new missing-audio Japanese card as the rich media preview fixture. The
  profile proof had already passed: revision 2, Japanese/Programming confirmed,
  exactly one Japanese audio reason, zero Programming audio reasons, learning
  reason preserved and no value leak. Fixed in `b8f584f` with a regression
  test;
- run `29640871856`, same inputs with source Fast CI `29640792565`: API smoke
  PASS with the same profile proof, then FAIL before restart because legacy
  CardsPage selected the higher-risk missing-audio fixture for the independent
  synthetic visual contract. The fixture review groups were separated in
  `4d9d693`; focused and canonical local gates pass. Per the bounded retry
  policy, no third E2E was dispatched.

Therefore persistence through restart, post-mutation Japanese `needs_review`
and Programming-still-confirmed assertions are not yet accepted in cloud.
Exact rerun required after a new successful Fast CI:

```text
mode=standard
scope=cards
verify_restart=true
fast_ci_run_id=<exact successful Fast CI for final HEAD>
```

Docs status commit/final Fast CI: reported in the final handoff response.

## Limitations and C1.4 prerequisites

- C1.3 exposes no configuration UI, import/export or CardsPage consumption;
- one profile per noteTypeId in v1;
- template field references are structurally parsed, not full template render;
- automatic profile evaluation is capped to the same explicit period/deck
  candidate surface and is not a full-collection audit;
- content reason lists remain bounded by canonical per-item reason limits;
- C1.4 must consume strict API/types without weakening confirmation,
  fingerprint, revision, privacy or arbitrary-code boundaries.

## Delivery boundary

Push target is only `origin/core`. No PR, merge, release, deployment,
`.ankiaddon` publication or AnkiWeb update is part of C1.3.
