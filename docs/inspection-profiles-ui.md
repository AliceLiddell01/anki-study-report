# Inspection Profiles settings UI

> [!IMPORTANT]
> **Corrective status:** the C1.4 runtime/API foundation remains accepted, but
> the normal configuration UX is under C1.5R remediation. The current Advanced
> runtime editor is historical technical evidence, not the accepted normal user
> path. C1.5R.6 will provide a guided Basic workflow and keep strict controls
> behind Advanced. See the
> [C1.5R.0 recovery report](../reports/core/c1-5r-0-recovery-baseline.md) and
> [card display identity baseline](card-display-identity.md).

**Route:** `#/settings/inspection-profiles`

**Settings labels:** `Проверка карточек` / `Card checks`

**Page titles:** `Профили проверки` / `Inspection Profiles`

This route is the local user-facing configuration surface for the versioned
[Inspection Profile v1](inspection-profiles-v1.md) runtime. It configures
requirements for exact Anki note types. It does not inspect or mutate notes,
cards, templates, or scheduling.

## Current production behavior

The C1.4 implementation currently presents a compact catalog plus a full strict
profile editor. Wide layouts use a `280–340 px` catalog and a fluid editor;
narrower desktop layouts stack them. Deterministic catalog order is
`needs_review`, `confirmed`, `suggested`, `not_configured`, `disabled`, then
locale-aware note-type name.

The production editor exposes all runtime states:

- `not_configured`: current structure, suggestion panel, Start empty, Import;
- `suggested`: stored non-authoritative draft, validation, confirm, delete;
- `confirmed`: enabled state, edit/reconfirm, save-as-draft warning, disable,
  export, delete;
- `needs_review`: exact reason/current structure, fail-closed warning,
  remap/revalidate/reconfirm;
- `disabled`: preserved configuration with validated enable-and-confirm.

This implementation is technically functional but product-remediated because
machine-level mappings/checks dominate the normal path and an unconfigured note
type requires an extra `Use suggestion` action before a draft exists.

## Corrective normal-path contract

C1.5R.6 must provide a guided Basic workflow that:

1. selects a note type;
2. immediately prepares the deterministic suggestion as a browser-only unsaved
   draft when no stored profile exists;
3. explains user-facing requirements such as meaning, audio, image, question,
   answer, or code without leading with role slugs/check IDs;
4. allows a normal user to review and confirm a safe default without opening
   Advanced;
5. explains Japanese audio expectations and Programming no-audio defaults;
6. keeps ambiguity, unavailable previews, and structural mismatch explicit;
7. preserves the current strict runtime editor behind an Advanced disclosure;
8. never saves or confirms automatically.

A suggestion may replace a clean generated draft deterministically. It may not
silently overwrite user edits; dirty draft replacement still requires explicit
confirmation.

## Draft and concurrency model

`useInspectionProfilesWorkspace` keeps separate server catalog/snapshot,
selected `noteTypeId`, baseline profile, editable browser draft, dirty flag,
validation result, field errors, mutation state, and revision conflict.

Reads use `AbortController` plus a monotonically increasing sequence. Mutations
are serialized and carry the store revision observed at load.

There is no autosave. Browser navigation is guarded with `beforeunload`; note-
type changes with a dirty draft require an accessible confirmation. A revision
conflict preserves the dirty draft, refreshes server state separately, and
offers explicit reconciliation. No conflict is silently retried or overwritten.

The C1.5R.6 UI may simplify presentation but must not weaken these semantics.

## Strict Advanced editor

Advanced preserves the v1 runtime's exact capabilities:

- exact field mappings from one semantic role to one or more `{ordinal,name}`
  references;
- unique bounded role slugs;
- all-template or exact template-ordinal scope;
- stable check IDs;
- categorical priority;
- only the hard-coded check union:

```text
non_empty
contains_audio
contains_image
min_text_length
one_of_roles_non_empty
all_roles_non_empty
```

No field may be silently claimed by another mapping. Renames, field-order
changes, template-reference changes, and other semantic fingerprint changes
require review.

There is no code, JavaScript, Python, SQL, regular-expression language, query,
filesystem, or network editor.

## Validation and preview

Client checks provide early guidance; the backend remains authoritative.
Confirm, reconfirm, and enable use strict validation.

Standalone Settings uses validate request v2:

```json
{
  "schemaVersion": 2,
  "profile": {},
  "preview": {"mode": "sample", "limit": 10}
}
```

The serialized collection read selects bounded cards for the exact
`noteTypeId`, reads at most `limit + 1`, evaluates no more than 20 cards, and
returns only safe IDs/counts/field identities/conditions/marker presence/sibling
counts/truncation. Raw note values, HTML, template source, media filenames,
paths, and tokens remain in the backend.

Structural validation may succeed when no cards exist; the UI explains that
content preview is unavailable. A draft may still be saved.

The future compact formatter preview is not silently stored inside Inspection
Profile v1. Formatter integration requires a separately versioned contract.

## Save, confirm, disable, delete, import, and export

- Save draft writes `targetState=suggested` and warns when a confirmed profile
  becomes non-authoritative.
- Confirm/reconfirm/enable validates first, uses the current exact fingerprint,
  and writes `targetState=confirmed` with `expectedRevision`.
- Disable preserves configuration and changes no Anki object.
- Delete requires named confirmation and removes only the local profile.
- Export creates one client-side v1 document with `revision: 0`.
- Import accepts one strict JSON document up to 1 MiB, requires one locally
  existing note type and exact current fingerprint/references, ignores imported
  revision, and loads a non-authoritative browser draft.

Editable raw JSON is deliberately rejected. Imported JSON is data and is never
executed.

## Accessibility and localization

Every input has a visible programmatic label. Grouped controls use
`fieldset`/`legend`; instructions and errors are associated. Selection remains a
normal button state rather than a nested-control listbox. Dynamic results use
status/alert regions. Error summaries identify the relevant section and move
focus only when the user requests an action.

Destructive and draft-discarding confirmations reuse the focus-trapped portal
modal. State is expressed in text as well as color. Light/dark themes, visible
focus, and exact RU/EN resource parity remain required.

Basic/Advanced disclosure must be keyboard- and screen-reader-operable and must
not hide an error or required action solely by collapsing Advanced.

## Security and deferred integration

The page calls only token-protected loopback endpoints and never receives direct
collection access. Profile contents, note values, and entity IDs are not added
to remote telemetry. Existing Search, Safe Actions, Signals, notifications,
sanitzer, media validation, and Shadow DOM preview boundaries remain intact.

Cards handoff/action/recheck/resolution, remote sync, marketplace, and mobile-
first redesign remain outside C1.5R.6. C1.6 remains blocked until C1.5R and
separate owner product acceptance are complete.
