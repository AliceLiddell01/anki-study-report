# Inspection Profiles v1

## Status and purpose

**Contract version:** 1
**Runtime stage:** C1.3
**UI:** deferred to C1.4

An Inspection Profile is a local, declarative set of content requirements for
one exact Anki note type. It answers questions such as “Japanese Vocabulary
requires meaning and audio” without applying that rule to Programming cards.
It never executes user code and never modifies a collection, note, card,
template or media file.

Anki note types own ordered fields and card templates; one note may generate
multiple cards. This contract follows those native boundaries rather than
assuming a universal card shape. See Anki’s [Getting
Started](https://docs.ankiweb.net/getting-started.html), [Card
Templates](https://docs.ankiweb.net/templates/intro.html) and
[Field Replacements](https://docs.ankiweb.net/templates/fields.html).

## Lifecycle

```text
not_configured → suggested → confirmed
                         ↘ needs_review
suggested|confirmed → disabled
```

Persisted state is `suggested | confirmed | disabled`. `not_configured` and
`needs_review` are computed. Only a `confirmed` profile whose fingerprint and
exact references still match the current note type is authoritative.

| Effective state | Authoritative content reasons |
| --- | --- |
| `not_configured` | no |
| `suggested` | no |
| `confirmed` | yes |
| `needs_review` | no; fail closed |
| `disabled` | no |

Learning reasons do not depend on profiles and continue in every state.
Suggestions cannot confirm, modify or fuzzy-rebind a profile.

## Storage and recovery

The document is stored inside the active Anki profile:

```text
<profile>/addon_data/<addon-id>/inspection_profiles.json
```

It is not stored in the collection, add-on global config, note types or
templates. This follows Anki’s add-on [Configuration and User
Files](https://addon-docs.ankiweb.net/addon-config.html) boundaries while
keeping runtime state isolated per Anki profile.

The store is thread-safe and uses UTF-8 deterministic JSON. Writes use a temp
file in the same directory, `flush`, `fsync` and `os.replace`. Every successful
write increments a monotonic `revision`; writers must supply the current
`expectedRevision`. A stale revision returns a conflict without overwriting
newer state.

- missing file: valid empty store, revision 0;
- corrupt/invalid v1: original is atomically renamed with a bounded
  `.corrupt-<UTC>` suffix and the source fails closed;
- future `schemaVersion`: file remains byte-for-byte untouched and writes are
  rejected;
- inaccessible store: safe `unavailable` status, no exception/path leak.

No user-supplied path is accepted. Document size is capped at 1 MiB.

## Schema v1

The portable Draft 2020-12 schema is
[`schemas/inspection-profile-v1.schema.json`](../schemas/inspection-profile-v1.schema.json).
The production Python validator independently enforces the same shapes plus
cross-field uniqueness, signed-64-bit IDs and mapping/check relationships.
Draft behavior follows [JSON Schema Core
2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html) and
[Validation 2020-12](https://json-schema.org/draft/2020-12/json-schema-validation.html).

```json
{
  "schemaVersion": 1,
  "revision": 1,
  "profiles": [
    {
      "profileId": "note-type-123",
      "noteTypeId": "123",
      "noteTypeName": "Japanese Vocabulary",
      "storedState": "confirmed",
      "displayName": "Japanese vocabulary",
      "expectedFingerprint": {"algorithm": "sha256", "value": "<64 lowercase hex>"},
      "appliesTo": {"templateOrdinals": []},
      "fieldMappings": [
        {"role": "meaning", "fields": [{"ordinal": 2, "name": "Meaning"}]}
      ],
      "checks": [
        {
          "checkId": "meaning-required",
          "kind": "non_empty",
          "roles": ["meaning"],
          "mode": "any",
          "priority": "high"
        }
      ],
      "confirmedAt": "2026-07-18T00:00:00Z",
      "updatedAt": "2026-07-18T00:00:00Z"
    }
  ]
}
```

V1 permits one profile per `noteTypeId`; IDs are positive signed-64-bit
decimal strings. Unknown fields are rejected. Profile/check IDs, roles,
timestamps, arrays and numeric parameters are bounded. Documents contain no
field values, template HTML/CSS, deck binding, path, code or query.

## Structures and fingerprints

The bounded catalog reads current Anki model metadata inside a serialized
`QueryOp`, following Anki’s [Background
Operations](https://addon-docs.ankiweb.net/background-ops.html). A public
structure contains only:

- note type ID, name and `standard | cloze` kind;
- ordered field ordinal and exact name;
- ordered template ordinal/name and referenced field names on front/back;
- SHA-256 fingerprint.

The fingerprint is SHA-256 of canonical JSON containing noteTypeId, ordered
fields, template identities/references and kind. Field add/remove/rename/
reorder and relevant template reference changes invalidate it. CSS, static
template text, mod time, sample values and deck assignment do not.

Confirmation checks both ordinal and exact field-name snapshot. A stale
profile is never fuzzy-matched to renamed fields or another noteTypeId.
Bounded reason codes are `field_added`, `field_removed`, `field_changed`,
`template_field_usage_changed`, `note_type_missing`, `fingerprint_mismatch`
and `unsupported_profile`.

## Roles and suggestions

Standard roles are:

```text
term reading meaning example audio image part_of_speech pitch
question answer explanation code
```

A bounded custom role may match `[a-z][a-z0-9_]{0,39}`. Each mapped field is
an exact `{ordinal,name}` reference. Roles and field references cannot be
duplicated, and every role targeted by a check must be mapped.

Suggestions reuse deterministic local note-intelligence heuristics. They may
return detected kind, per-mapping confidence, proposed checks, warnings and
unresolved fields. They use no network, LLM or telemetry and persist no note
samples. Ambiguity remains unresolved; suggestion is never authority.

## Allowlisted checks

| Kind | Semantics |
| --- | --- |
| `non_empty` | normalized meaningful text exists in `any`/`all` mapped refs; media-only fields are empty text |
| `contains_audio` | safe `[sound:filename]` marker exists in declared refs; file existence is not checked |
| `contains_image` | safe `<img … src=…>` reference exists in declared refs; media is not read |
| `min_text_length` | normalized plain-text Unicode length meets `1..10000` in `any`/`all` mode |
| `one_of_roles_non_empty` | at least one target role has meaningful text |
| `all_roles_non_empty` | every target role has meaningful text |

Plain text uses the existing safe extraction: tags, invisible markup, media
markers, NBSP and repeated whitespace cannot create false text. Checks use
only confirmed exact mappings and optional template ordinal scope. No full
card render or template JavaScript is executed.

Rejected rule capabilities include arbitrary regex/substring languages, CSS
selectors, Python, JavaScript, SQL, shell, imports/callbacks, filesystem/media
existence, network rules, cross-note aggregates and review-history conditions.

## Evaluation and safe evidence

Failed checks produce typed internal results with profile/note-type/check
identity, check kind, note scope, priority, roles, exact mapped field
identities, profile revision, fingerprint, sibling count and template scope.
Evidence may include expected condition, actual/expected text length or
`markerPresent: false`.

Evidence never includes raw note content, HTML, audio/image filename, local
path, token, template source or exception text. Preview accepts at most 20
explicit card IDs and returns only safe failure evidence.

## Runtime API

All endpoints are loopback-only, require the current dashboard token, accept
`POST application/json`, use IDs/documents in the body, cap the body at 64 KiB
and return generic machine errors:

```text
POST /api/inspection-profiles/query
POST /api/inspection-profiles/validate
POST /api/inspection-profiles/update
```

- `query`: `schemaVersion`, `noteTypeIds` (0..200), `limit` (1..500); returns
  structures, effective states, stored profile, suggestions and store revision;
- `validate`: strict draft plus 0..20 exact card IDs; does not persist;
- `update/save`: `expectedRevision`, explicit `targetState`, strict profile and
  current fingerprint/reference validation;
- `update/disable`: preserves configuration but suppresses authority;
- `update/delete`: removes only that profile.

Current model reads and preview card reads run through serialized `QueryOp`.
The only write is the profile-local JSON file; it is not an Anki `CollectionOp`
and does not mutate collection state.

## Canonical triage v2

Triage schema v2 adds `sourceStatus.profileChecks`, aggregate
`contentChecks`, stable `reasonId` and `profile_check` evidence. Content codes:

```text
content.required_text_missing
content.audio_missing
content.image_missing
content.text_too_short
content.required_group_missing
```

Identity is `profile:<profileId>:check:<checkId>`, so two same-kind checks stay
distinct. Content scope is `note`. One failing note appears once on a
deterministic representative card; evidence reports only the affected sibling
count. Automatic data chooses the smallest candidate card ID. Search worksets
choose the first explicitly selected applicable sibling, preserve requested
order and never invent unselected rows. Independent card-level learning
reasons on sibling cards remain separate.

Automatic evaluation uses one bounded shared revlog/card/note candidate query
(100 plus a truncation sentinel), including candidates with no learning issue.
Search worksets load at most 200 exact IDs in one batch. Raw fields never leave
the backend. Legacy `attentionCards`, including its heuristic missing-field
labels, is unchanged; heuristics do not become canonical content reasons.

Content status distinguishes `available`, `no_confirmed_profiles`,
`profiles_need_review`, `disabled`, `partial` and `unavailable`. Missing
profiles are not an error. Store/model unavailability never means resolved.

## Examples

Japanese Vocabulary maps `meaning → Meaning`, `audio → Audio`, `example →
Example` and may confirm `non_empty`/`contains_audio` checks. A missing audio
marker creates `content.audio_missing` only after explicit confirmation.

Programming maps `question → Question` and `answer → Answer`; it confirms two
`non_empty` checks and has no audio requirement. The Japanese rule cannot
apply to it because profiles are keyed to exact noteTypeId and fingerprint.

## Bounds, privacy and compatibility

| Resource | Bound |
| --- | ---: |
| document | 1 MiB |
| profiles | 500 |
| mappings/checks per profile | 32 / 32 |
| refs per mapping/check | 16 / 16 |
| fields/templates in structure | 64 / 32 |
| preview cards | 20 |
| automatic candidates | 100 |
| Search workset | 200 |

Profile contents, field mappings and checks are never sent through telemetry.
Logs contain only operation/error codes and exception types, not profile data,
note values, paths or tokens. Search, Safe Actions, Signals, Notifications,
preview isolation, existing CardsPage and legacy report payload remain intact.

C1.4 may add user configuration UI and separately designed import/export. C1.3
adds no route, form, editor, navigation placeholder or collection mutation.
