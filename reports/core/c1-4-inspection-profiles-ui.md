# C1.4 — Inspection Profiles: user configuration

**Status:** `C1.4 — Implemented, verification pending`

**Initial HEAD:** `d66b899ab36ce9cc0e60a0b352b268b124aa0d18`

**Initial divergence:** `0 behind / 13 ahead` of `origin/master`

## Delivered capabilities

- lazy `#/settings/inspection-profiles` route and Data-group Settings item;
- localized searchable/status-filtered note-type catalog, compact counters,
  deterministic lifecycle-first sorting, empty/partial/store failure states;
- explicit `not_configured`, `suggested`, `confirmed`, `needs_review`, and
  `disabled` editor states;
- isolated server snapshot/draft/dirty/validation/revision state with
  latest-wins reads, serialized mutations, no autosave, unsaved navigation
  protection, and explicit conflict reconciliation;
- non-authoritative suggestion application, exact field mappings, template
  scope, allowlisted checks, modes, priorities, and stable IDs;
- backend-authoritative validation plus bounded deterministic sample preview;
- explicit draft, confirm/reconfirm, enable, disable, and local-only delete;
- strict one-profile 1 MiB import and client-side deterministic export;
- accessible labels, fieldsets/legends, linked instructions/errors, live
  status, focus-trapped confirmations, textual state, and RU/EN parity;
- light/dark responsive desktop styling and real-Anki screenshot assertions.

CardsPage, legacy `attentionCards`, Search, Safe Actions, Signals,
Notification Center, preview isolation, and Anki collection state are not
changed.

## Sources read

Project sources included README/handoff/roadmap, Cards v2 product and triage
contracts, Inspection Profile v1/runtime report, project/frontend/navigation/
localization/security/API/test/verification docs, current router/Settings
pages/components/styles/locales/tests, strict profile types/client/parser,
Python service/store/runtime/dashboard endpoints/tests/schema, and Docker/Fast
CI/E2E fixtures and screenshot harness.

Official sources applied:

- Anki Manual: [Getting Started](https://docs.ankiweb.net/getting-started.html),
  [Adding/Editing](https://docs.ankiweb.net/editing.html),
  [Card Templates](https://docs.ankiweb.net/templates/intro.html),
  [Field Replacements](https://docs.ankiweb.net/templates/fields.html), and
  [Checks and Errors](https://docs.ankiweb.net/templates/errors.html);
- Anki add-on docs: [Background Operations](https://addon-docs.ankiweb.net/background-ops.html);
- W3C WAI Forms Tutorial: [Labeling Controls](https://www.w3.org/WAI/tutorials/forms/labels/),
  [Grouping Controls](https://www.w3.org/WAI/tutorials/forms/grouping/),
  [Form Instructions](https://www.w3.org/WAI/tutorials/forms/instructions/),
  [Validating Input](https://www.w3.org/WAI/tutorials/forms/validation/), and
  [User Notification](https://www.w3.org/WAI/tutorials/forms/notifications/).

These sources support exact note-type identity, multiple card templates per
note, meaningful field names/ordinals, explicit review after structural
changes, background collection reads, visible labels, grouped controls,
associated instructions, server-side validation, field-specific correction,
announced feedback, and confirmation for destructive changes.

## Architecture and product decisions

1. The route is in the existing Settings Data group after Data and does not
   enter primary navigation.
2. The page is a route-level dynamic chunk; i18next/react-i18next are isolated
   in an existing-style runtime chunk so the 500 kB guard remains intact.
3. Normal buttons represent note-type selection because rows expose structured
   state and must not become a nested-control listbox.
4. The UI edits a detached draft and never mutates API snapshots.
5. Suggestion use is always dirty/local and never automatically persisted.
6. Empty template ordinals retain the v1 meaning “all templates”.
7. Only runtime-allowlisted check shapes are constructible.
8. The backend remains validation authority for every confirm transition.
9. Validate v1 stays compatible; additive validate v2 supplies a bounded
   deterministic exact-note-type sample for standalone Settings.
10. Import requires current exact fingerprint/references and becomes a
    non-authoritative local draft; revision has no imported authority.
11. Revision conflicts preserve dirty work and prohibit auto-retry.
12. Cards v2 queue/Inspector is explicitly deferred to C1.5.

## API extension

Validate request v2 is `{schemaVersion:2, profile, preview:{mode:"sample",
limit:1..20}}`. It rejects unknown fields, selects ordered card IDs only for
`profile.noteTypeId`, reads at most `limit+1` rows in serialized QueryOp,
reports truncation, and emits the existing value-safe preview shape with
`schemaVersion:2`. Validate v1 exact `cardIds` is unchanged. Python, TypeScript,
strict parser, tests, API docs, and E2E smoke are synchronized.

## Verification evidence

Focused checks completed before the canonical gate:

- `python -m pytest -q tests/test_inspection_profile_service.py tests/test_inspection_profile_runtime.py tests/test_dashboard_server.py -k inspection`: PASS, 14 passed;
- `pnpm exec vitest run src/pages/InspectionProfilesSettingsPage.test.tsx src/lib/inspectionProfilesApi.test.ts src/app/router.test.tsx src/i18n/resources.test.ts`: PASS, 14 passed;
- `python -m pytest -q tests/test_e2e_screenshot_contract.py tests/test_docker_smoke_helpers.py tests/test_fast_ci_e2e_handoff.py`: PASS, 51 passed / 1 environment skip;
- `pnpm run typecheck`: PASS;
- `pnpm run build`: PASS; 18 JS chunks, entry/largest 459,733 bytes;
- `python -m compileall -q anki_study_report docker/anki-e2e`: PASS.
- first `.\scripts\run_full_check.ps1 -SkipDocker`: FAIL after frontend PASS
  and 706 Python PASS because the earlier direct `compileall` left
  `anki_study_report/__pycache__`; the generated cache directories were
  removed explicitly inside the workspace;
- repeated `.\scripts\run_full_check.ps1 -SkipDocker`: PASS in 54.7 s — 51
  frontend files / 280 tests, 707 Python tests with 5 documented platform/
  artifact skips, split production bundle, copied asset graph, package build
  and package verification.

The exact-SHA Fast CI, targeted real-Anki run, artifact
inventory, screenshot inventory, implementation commits, final HEAD/
divergence, and documentation closeout are intentionally PENDING here until
those gates actually complete.

## Security, privacy, compatibility, and limitations

- no arbitrary code, expressions, regex, SQL, query language, network rules,
  template execution, filesystem/media scan, or collection mutation;
- no raw values, HTML, media filenames, paths, tokens, or template source in
  validation responses, exports, logs, or remote telemetry;
- loopback token, strict body/unknown-field parsing, exact fingerprint/refs,
  optimistic revision, QueryOp, action allowlists, sanitizer/media/Shadow DOM
  boundaries remain intact;
- no PR, merge, release, deployment, `.ankiaddon` publication, or AnkiWeb
  update is part of C1.4;
- automation verifies semantics and screenshot production but does not claim
  complete WCAG conformance; accepted real-Anki visual evidence remains a
  required completion gate;
- C1.5 must consume the confirmed/current profile state and canonical triage
  model without reimplementing this editor or profile runtime.
