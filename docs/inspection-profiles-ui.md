# Inspection Profiles settings UI

**Route:** `#/settings/inspection-profiles`

**Settings labels:** `Проверка карточек` / `Card checks`

**Page titles:** `Профили проверки` / `Inspection Profiles`

This route is the local user-facing editor for the versioned
[Inspection Profile v1](inspection-profiles-v1.md) contract. It configures
requirements for exact Anki note types. It does not inspect or mutate notes,
cards, templates, or scheduling, and it does not replace the future Cards v2
queue/Inspector.

## Workspace and lifecycle

The desktop workspace uses a compact summary followed by a searchable,
state-filtered note-type catalog and a profile editor. Wide layouts use a
`280–340 px` catalog plus a fluid editor; narrower desktop layouts stack the
two regions. The deterministic order is `needs_review`, `confirmed`,
`suggested`, `not_configured`, `disabled`, then locale-aware note-type name.

The editor presents all runtime states without converting machine codes into
the primary language of the UI:

- `not_configured`: current structure, non-authoritative suggestion, Start
  empty, Import JSON;
- `suggested`: stored non-authoritative draft, validation, confirm, delete;
- `confirmed`: enabled badge, edit-as-draft, reconfirm, save-as-draft warning,
  disable, export, delete;
- `needs_review`: reason, exact current structure, fail-closed warning,
  remap/revalidate/reconfirm actions, no fuzzy rebinding;
- `disabled`: preserved configuration with validated enable-and-confirm.

Suggestions always produce a browser-only dirty draft. They never save or
confirm automatically and cannot replace dirty edits without a confirmation
dialog.

## Draft and concurrency model

`useInspectionProfilesWorkspace` keeps separate server catalog/snapshot,
selected `noteTypeId`, baseline profile, editable profile draft, dirty flag,
validation result, field errors, mutation state, and revision conflict. Reads
use `AbortController` plus a monotonically increasing sequence. Mutations are
serialized by the busy state and always carry the store revision observed at
load.

There is no autosave. Browser navigation is guarded with `beforeunload` and
note-type changes use an accessible confirmation dialog. A revision conflict
preserves the dirty draft, refreshes the catalog separately, and offers either
server review or an explicit reload/discard. No conflict is retried or
overwritten automatically.

## Mappings, checks, and templates

Field mappings connect one semantic role to one or more exact `{ordinal,
name}` references. Roles use bounded slug identifiers and remain unique.
Controls show Anki field names and ordinals, and a field cannot be silently
claimed by another mapping.

The check editor exposes only the runtime allowlist:

```text
non_empty
contains_audio
contains_image
min_text_length
one_of_roles_non_empty
all_roles_non_empty
```

Each check has a stable ID, mapped roles, categorical priority, and only the
parameters supported by its discriminated kind. Priority changes triage
ordering; it does not determine whether a check runs. There is no code,
JavaScript, Python, SQL, regular-expression, query, filesystem, or network
editor.

Template scope is either all templates (an empty ordinal list) or explicit
exact ordinals. This reflects that one Anki note type may create multiple
sibling card types. Renames, field order changes, template-reference changes,
and other semantic fingerprint changes require review.

## Validation and preview

Client checks provide early field guidance, but the backend is authoritative.
Check, confirm, reconfirm, and enable call the strict validate endpoint.
Standalone Settings uses validate request v2:

```json
{
  "schemaVersion": 2,
  "profile": {},
  "preview": {"mode": "sample", "limit": 10}
}
```

The QueryOp selects the smallest card IDs for the exact profile `noteTypeId`,
reads at most `limit + 1`, evaluates no more than 20 cards, and returns only
safe IDs, counts, field identities, expected conditions, lengths, marker
presence, sibling counts, and truncation. Raw note values, HTML, template
source, media filenames, paths, and tokens remain in the backend. Structural
validation may succeed when no cards exist; the UI then explains that content
preview is unavailable. Draft saving remains possible.

## Save, disable, delete, import, and export

- Save draft writes `targetState=suggested`, warns when a confirmed profile
  will become non-authoritative, and refetches after success.
- Confirm/reconfirm/enable validates first, uses the current exact fingerprint,
  then writes `targetState=confirmed` with `expectedRevision`.
- Disable preserves configuration and affects no Anki object.
- Delete requires a named confirmation and removes only the local profile.
- Export creates one client-side Inspection Profile v1 document with
  `revision: 0`; it performs no server/filesystem write.
- Import accepts one strict JSON document up to 1 MiB, requires exactly one
  locally existing note type and current exact fingerprint/references, ignores
  imported revision, and loads only a non-authoritative browser draft.

Editable raw JSON is deliberately rejected. Imported JSON is data and is never
executed.

## Accessibility and localization

Every input has a visible programmatic label. Mappings, checks, roles, and
template choices use `fieldset`/`legend`; instructions are adjacent or linked
with `aria-describedby`. Selection is a normal button state, not a nested
`listbox`. Dynamic results use status/alert regions, error summaries identify
the relevant section and move focus to a related control, and destructive or
draft-discarding actions use the existing focus-trapped `AccessibleModal`.
State is expressed in text as well as color. Light/dark themes and visible
focus use existing project tokens.

All visible workflow strings exist in exact RU/EN resource parity. Unknown
suggestion, lifecycle, and backend codes receive bounded localized fallback
copy instead of becoming the main UI label.

## Security and deferred integration

The page calls only token-protected loopback endpoints and never receives
direct collection access. Profile contents, note values, and entity IDs are
not added to remote telemetry. Existing Search, Safe Actions, signals,
notifications, CardsPage, legacy `attentionCards`, sanitizer, media boundary,
and Shadow DOM preview are unchanged.

Cards v2 queue/Inspector, Search handoff, actions/recheck/resolution, remote
sync, marketplace, and mobile-first redesign remain deferred to later stages.
