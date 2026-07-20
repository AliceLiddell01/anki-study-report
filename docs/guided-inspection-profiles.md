# Guided Inspection Profiles

This document is the current product and interaction contract for
`#/settings/inspection-profiles` after C1.5R.6.

## Product purpose

Inspection Profiles answer five normal-user questions:

1. What content should be present in cards from this exact note type?
2. Which exact Anki fields represent those purposes?
3. Which bounded declarative checks will run?
4. Can the proposed setup be safely enabled?
5. Why did a previously enabled profile become non-authoritative?

The page is a local settings surface. It never edits the collection and never
executes arbitrary code, queries, regular expressions, JavaScript, Python or SQL.

## Generated draft

Selecting a `not_configured` note type immediately materializes the backend's
deterministic suggestion as a browser-only strict v1 profile draft.

```text
select exact note type
-> generated draft appears
-> no save request
-> no confirmation
-> no authoritative inspection
```

There is no normal-path `Use suggestion` step.

Generated draft and user work are distinct states:

```text
origin: generated
userEdited: false
dirty: false
```

A clean generated draft may be discarded on note-type switch or rebuilt after a
fresh catalog query. The first Basic or Advanced profile edit changes ownership to
user work. Imported and start-empty drafts are user-owned immediately. Only real
user work arms the selection guard and `beforeunload` protection.

Stored `suggested`, `confirmed`, `needs_review` and `disabled` profiles load as
clean stored baselines. No state is auto-saved or auto-confirmed.

## Normal information architecture

The selected workspace is ordered as follows:

```text
exact note-type header
lifecycle guidance
Suggested setup
Fields used
Requirements
Card scope
validation/sample result
state-aware primary actions
Advanced settings disclosure
Profile tools disclosure
```

Basic is open by default. Advanced and Profile tools are collapsed by default.
There is one strict profile draft; Basic is a friendly projection over it rather
than a second persisted model.

## Friendly roles

Known roles use localized human labels and short purposes, for example Word,
Meaning, Example, Part of speech, Pitch accent, Audio, Image, Question, Answer,
Code and Explanation. Exact field names come from the selected note type.
Ordinals and role slugs do not appear in Basic.

A field already claimed by another single-field role is disabled in the relevant
selector. The page never silently duplicates a conflicting field claim. Unknown
roles use a safe humanized custom-role fallback and retain their exact strict
mapping.

## Friendly requirements

Basic projects every Inspection Profile v1 check kind:

- `non_empty` -> selected field is required;
- `contains_audio` -> audio marker is required;
- `contains_image` -> image marker is required;
- `min_text_length` -> bounded minimum character count;
- `one_of_roles_non_empty` -> at least one selected role is filled;
- `all_roles_non_empty` -> every selected role is filled.

The user can change friendly priority, role selection and minimum length; add a
supported hard-coded requirement kind; and remove a requirement. Check IDs remain
stable internal identifiers and are not regenerated during ordinary edits.

## Japanese and Programming expectations

The frontend uses `suggestion.detectedKind` and the exact backend suggestion. It
does not infer study kind from the note-type display name.

A Japanese vocabulary suggestion with a mapped Audio role visibly contains an
Audio requirement in Basic. A Programming suggestion visibly contains Question
and Answer requirements and does not invent an Audio requirement. The safe
Add-requirement selector may still offer the supported Audio check kind; this does
not mean Audio is configured by default.

## Card scope

Empty `templateOrdinals` means all card templates. Basic displays template names,
never ordinal-first copy. A one-template note type uses a compact read-only summary.
A missing selected template is a blocking review error and is never silently reset.

## Lifecycle actions

| Effective state | Normal primary behavior |
| --- | --- |
| `not_configured` | Confirm and enable; generated draft may also be saved as draft |
| `suggested` | Confirm and enable; dirty changes may be saved |
| `confirmed`, unchanged | Enabled status; no redundant confirmation |
| `confirmed`, edited | Validate and confirm changes |
| `needs_review` | Review and confirm again |
| `disabled` | Review and enable |

Saving an edited confirmed profile as `suggested` requires confirmation because it
removes authority. Disable and delete remain explicit confirmed tools.

## Validation and sample

`Check setup` sends validate request schema v2 with a bounded sample limit of 10.
Confirmation validates before update schema v1 and sends no mutation after an
invalid result. The result groups failures by friendly requirement, not check ID.

The UI may show counts, exact mapped field names, marker presence, bounded text
length and sibling impact. It never shows raw note values, card HTML, template
source, media filenames, filesystem paths or tokens.

A structurally valid profile with no available cards is reported honestly as a
structurally valid setup without a content sample.

## Advanced and hidden errors

Advanced preserves display name, exact template scope, role slugs, exact field
references, check kinds, priorities, modes, minimum lengths and stable IDs.
Basic and Advanced edit the same strict document.

Validation errors associated with collapsed Advanced controls are represented by
an error count in the disclosure summary and by the page error summary. An explicit
failed Check/Confirm action focuses the summary; activating its link opens Advanced
before focusing the exact control.

## Conflict and reload

Reads remain AbortController/latest-wins. Mutations remain serialized. A revision
conflict preserves the user draft, refreshes server catalog state separately and
exposes explicit review-server or discard-and-reload choices. The client never
retries a conflicting mutation or overwrites the latest server revision silently.

## Accessibility

The page has one `h1`; native catalog buttons; visible labels; fieldset/legend
groups; native selects and checkboxes; keyboard-operable native disclosures;
programmatic open state; status/alert semantics; and focus movement only after an
explicit failed action or modal interaction. State and priority are expressed in
text rather than color alone. RU and EN use the same strict data model.

## Security and privacy

The frontend has no collection access. It uses only token-protected loopback APIs.
Basic compiles exclusively to the existing hard-coded v1 union. Import remains
strict data (maximum 1 MiB), exact-note-type/fingerprint/reference bound, dirty and
non-authoritative until explicit confirmation. Export contains only the stored
local profile document.

## Stage boundary

C1.5R.6 verifies the guided page on deterministic fixtures and Chromium. It does not
claim owner product acceptance and does not run Docker/real-Anki integration. The
integrated package and owner review belong to C1.5R.7. C1.6 remains blocked.
