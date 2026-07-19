# Card display formatter v1

## Status

**Stage:** `C1.5R.2 — Complete`

**Branch:** `core`

**Schema:** [`schemas/card-display-formatter-v1.schema.json`](../schemas/card-display-formatter-v1.schema.json)

**Runtime:**

```text
anki_study_report/card_display_formatter_store.py
anki_study_report/card_display_formatter_service.py
anki_study_report/card_display_formatter_runtime.py
```

Card display formatter v1 is an independent local configuration contract for
changing the compact identity of one exact Anki note type/template. It does not
extend Inspection Profile v1, alter full Inspector/expanded preview, modify the
collection, or execute user code.

## Exact purpose

Without configuration, the canonical R1 identity remains:

```text
【に】（する）
```

For a configured Japanese note type whose rendered reviewer front contains:

```html
【<b>に</b>】<img src="感.gif"><img src="謝.gif">（<b>する</b>）
```

an enabled `imageMode: stem` formatter can produce:

```text
【に】感謝（する）
```

Programming and every other note type without an exact ID-bound formatter keep
their existing canonical identity.

## Independent storage

The document is stored per active Anki profile:

```text
<profile>/addon_data/<addon-id>/card_display_formatters.json
```

It is separate from:

```text
inspection_profiles.json
config.json
meta.json
collection
note types/templates
```

The store uses deterministic UTF-8 JSON, a same-directory temporary file,
`flush`, `os.fsync`, and `os.replace`. Every successful save/delete increments a
monotonic `revision`; callers supply `expectedRevision`.

Recovery states:

| State | Behavior |
| --- | --- |
| missing | empty revision 0 |
| corrupt/invalid v1 | quarantine rename and canonical display fallback |
| future schema | preserve bytes, reject writes, canonical display fallback |
| inaccessible | unavailable, canonical display fallback |

No path or document content is included in API errors or normal logs.

## Document and bounds

Canonical empty document:

```json
{
  "schemaVersion": 1,
  "revision": 0,
  "formatters": []
}
```

Formatter entry:

```json
{
  "noteTypeId": "123",
  "noteTypeName": "Japanese Vocabulary",
  "templateOrdinal": null,
  "templateName": null,
  "storedState": "enabled",
  "inputSource": "reviewer_front",
  "textMode": "preserve",
  "imageMode": "stem",
  "audioMode": "omit",
  "maxLines": 1,
  "lineSeparator": " ",
  "maxCharacters": 240,
  "updatedAt": "2026-07-19T00:00:00Z"
}
```

Hard bounds:

```text
document                         1 MiB
formatters                       1000
entries per note type            33
noteTypeName/templateName        160 Unicode characters
templateOrdinal                  null | 0..31
lineSeparator                    0..8 characters, no controls/CR/LF
maxLines                         1..4
maxCharacters                    1..240
noteTypeId                       positive signed-64 decimal string
```

Root and nested objects reject unknown keys. Booleans are not integers.
Duplicate `(noteTypeId, templateOrdinal)` keys, incoherent nullable template
fields, invalid timestamps and future-schema writes fail closed.

## Identity and resolution

Binding key:

```text
(noteTypeId, templateOrdinal)
```

Names are bounded display/diagnostic snapshots only. There is no binding by
name, deck, field value or fuzzy similarity.

Resolution:

```text
exact enabled  → apply exact formatter
exact disabled → suppress default inheritance and use canonical R1 fallback
exact absent + note-type default enabled  → apply default
exact absent + default disabled/absent    → canonical R1 fallback
```

The store is read once per Search/Triage request. One immutable resolver map is
then reused for all projected cards. There are no per-card file reads, HTTP
calls, collection scans, or mutable module-global formatter cache.

## Declarative policies

Enums:

```text
storedState: enabled | disabled
inputSource: browser_question | reviewer_front
textMode: preserve | omit
imageMode: omit | filename | stem | marker
audioMode: omit | filename | stem | marker
```

Fixed markers:

```text
image: 🖼
audio: 🔊
```

Marker text is not configurable in v1.

The schema/API contains no JavaScript, Python, SQL, shell, regex, selector,
expression, callback, import, module, path, URL, field value, template HTML/CSS,
or remote endpoint capability. Runtime uses no `eval`, `exec`, dynamic import,
plugin callback, or subprocess.

## Ordered token stream

The compact parser produces only:

```text
text
line_break
image
audio
```

Source order is retained. Adjacent inline text/media tokens receive no invented
separator. HTML entities are decoded, `<br>` and block boundaries emit line
breaks, whitespace is normalized inside final lines, and blocked embedded
content fails closed when malformed.

Audio recognition includes safe `[sound:filename]`, unnamed `[anki:play:...]`
and safe rendered audio/source references. Unnamed audio emits only the fixed
marker when `audioMode: marker`.

## Safe media filename rules

A media token may carry only a normalized flat local filename or `null`.
Accepted names are bounded and contain no scheme, absolute path, slash,
backslash, traversal or control character. Validation occurs after HTML entity
decoding.

Rejected references include:

```text
../x.png
folder/x.png
folder\x.png
C:x.png
http://...
https://...
data:...
file:...
```

Rejected/unnamed media may still emit a fixed marker. Raw unsafe text is never
returned. Formatter processing never opens a media file, checks existence,
resolves a filesystem path, or loads a remote resource.

## Line and truncation semantics

Processing order:

```text
tokenize
→ apply text/media modes
→ build lines
→ discard empty lines
→ select first maxLines meaningful lines
→ normalize whitespace per line
→ join with lineSeparator
→ apply maxCharacters
```

Truncation adds one terminal ellipsis, never exceeds `maxCharacters`, and sets
`displayTruncated` exactly.

A valid non-empty configured result uses:

```text
displayStatus = available
displaySource = configured inputSource
displayText = configured output
displayTruncated = formatter truncation
```

Search stays schema v2 and Triage stays schema v3. No public
`formatterApplied`, formatter ID, alias, or formatter configuration is added to
Search/Triage payloads.

## Canonical fallback and render reuse

Without an active formatter:

```text
Browser question → reviewer front → media_only/unavailable
```

With an active formatter, only its selected source is attempted. Render
unavailable, invalid token stream, empty output, or policy-omitted-only output
returns to the unchanged canonical R1 fallback.

Within one card projection each source is rendered at most once. A failed
configured attempt is cached and reused by fallback. `card.answer()` is never
called.

## Local dashboard API

Token-protected POST-only JSON endpoints:

```text
/api/card-display-formatters/query
/api/card-display-formatters/validate
/api/card-display-formatters/update
```

All use schema v1, exact keys and the existing 64 KiB body cap.

Query request:

```json
{"schemaVersion":1}
```

Query response contains:

```text
schemaVersion
status: empty | available | corrupt | future_schema | unavailable
revision
formatters
errorCode
quarantined
```

Validate accepts one strict formatter, performs no persistence and no collection
read, and returns its normalized value or bounded field errors.

Update actions:

```text
save   expectedRevision + formatter
delete expectedRevision + exact noteTypeId/templateOrdinal key
```

Delete cannot remove all formatters for a note type accidentally. Revision
conflict returns current revision. Errors expose generic machine codes only.

## Frontend contract

Strict types/parser/client live in:

```text
web-dashboard/src/types/cardDisplayFormatters.ts
web-dashboard/src/lib/cardDisplayFormattersApi.ts
```

They reject old/future schemas, unknown keys, malformed IDs/timestamps, invalid
enums/limits, duplicate keys, incoherent nullable template fields and malformed
error envelopes.

R2 adds no route, page, hook, Settings navigation or form. Guided formatter UX
belongs to C1.5R.6.

## Security and privacy

Preserved boundaries:

```text
loopback-only server
dashboard token
frontend has no collection access
no iframe/template JavaScript execution
no arbitrary code or query language
no media file reads or remote loads
no raw HTML/note fields in formatter store
no local paths or token-bearing URLs
no formatter filename/displayText telemetry or normal logs
```

Configured `displayText` is returned only to the local dashboard as the explicit
product output.

## Deferred work

Not part of formatter v1:

```text
Settings/guided UI
automatic suggestions
live formatter preview API
front/back preview semantics
candidate-source redesign
Cards inbox redesign
C1.6 actions/recheck/resolution
```
