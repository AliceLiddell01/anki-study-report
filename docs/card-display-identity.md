# Canonical card display identity

## Status and scope

**Contract:** C1.5R corrective architecture, version 1

**Status:** In progress; owner product acceptance pending
**Surfaces:** Search card rows, Cards inbox, Cards Inspector, safe front preview,
expanded answer preview, and Inspection Profiles display configuration

This contract separates compact card identity from full card rendering. A
compact label helps the user recognize one generated card in a list. It does
not replace the card's native question or answer and does not alter Anki note
types, templates, fields, scheduling, or collection data.

## Canonical surfaces

| Surface | Canonical value | Rendering side |
| --- | --- | --- |
| Search card row | backend `displayText` | compact identity |
| Cards inbox item | same backend `displayText` | compact identity |
| Cards Inspector heading | same backend `displayText` | compact identity |
| Cards Inspector preview | sanitized native reviewer question | front |
| Expanded preview | sanitized native reviewer answer | back/answer |

Search `mode=notes` may retain note-level sort identity. Card rows must never
derive a second frontend label or fall back to an unrelated note field.

## Source precedence

The shared backend projector resolves one exact `noteTypeId` and
`templateOrdinal` in this order:

1. enabled, current user formatter for the exact template;
2. enabled, current user formatter for the note type;
3. Anki Browser Appearance Question rendered through the public browser mode;
4. native reviewer question/front rendered through the public native mode;
5. media-aware neutral fallback;
6. localized no-visible-text label.

An empty Browser Appearance template naturally falls back to the native
question through Anki's renderer. An empty compact result never authorizes the
old `sort field -> next non-empty field` behavior.

## Verified Anki 26.05 behavior

The official `26.05` source at tag commit
`e64c6b1aee3e8d668fb8bbe084beada8e070d985` provides:

- `Card.question(reload=False, browser=False)`;
- `Card.render_output(reload=False, browser=False)`;
- `Card.answer()` from the current native render output;
- `browser=True` selection of Browser Appearance question/answer formats;
- template keys `bqfmt`/`bafmt`, falling back to `qfmt`/`afmt` when empty.

The implementation must request browser and reviewer renders independently.
It must not reuse a `Card.render_output()` cache created for a different mode.
Full previews always use reviewer/native mode. Browser mode is only one source
for compact identity.

## Ordered display token model

Rendered HTML is converted to a bounded ordered token stream before compact
plain-text projection. Version 1 tokens are:

```text
text
line_break
image
audio
```

An image/audio token contains only a validated basename and bounded safe stem;
it never contains a directory, URL, local path, field value, or raw HTML.

Parsing rules:

- preserve DOM/media order and meaningful line boundaries;
- decode safe entities and normalize Unicode whitespace;
- extract `[sound:...]` and allowlisted image references in place;
- ignore scripts, styles, iframes, objects, embeds, SVG and MathML;
- reuse sanitizer/media filename rules;
- cap source HTML, token count, token name, line count, and output length;
- malformed input fails closed to a neutral fallback;
- no media file is opened for compact identity.

## Default compact projection

Without a user formatter, visible text from Browser Question or native front is
preserved in source order. Image and audio tokens are omitted, the first
meaningful line is selected, whitespace is collapsed, and output is truncated
to the documented bound.

For the supplied media-heavy Japanese front, the default is:

```text
【に】（する）
```

It must not become `「Существительное」` or any other unrelated note field. If
no visible text survives, a localized media summary such as “Card with audio
and images” is allowed. If no semantic/media token survives, use the localized
no-visible-text label.

## Declarative formatter v1

The formatter changes compact identity only. It binds to an exact
`noteTypeId`, with an optional exact `templateOrdinal` override. Resolution is
exact-template, then note-type default, then the default pipeline.

Version 1 permits only:

- source: `browser_question | front`;
- text: preserve, whitespace collapse, first `N` meaningful lines, bounded
  maximum characters;
- image: `hide | icon | filename | stem`;
- audio: `hide | icon | filename | stem`;
- adjacent media separator: empty, space, or middle dot;
- source token order preservation.

It does not permit JavaScript, Python, SQL, shell, imports, expressions,
callbacks, regular expressions, arbitrary HTML, filesystem reads, network
requests, or template JavaScript execution.

For the supplied token sequence, `front + image stem + audio hide + one line +
empty adjacent separator` must produce exactly:

```text
【に】感謝（する）
```

## Storage and lifecycle

Formatter configuration is profile-local, durable, strict, versioned, atomic,
and optimistic-concurrency aware. It is independent from Inspection Profile
authority: disabling or invalidating content checks must not erase a valid
display formatter.

The least disruptive storage boundary is a dedicated
`card_display_profiles.json` document under the existing profile-local add-on
data directory, using the same atomic-write/revision/future-schema fail-closed
patterns as Inspection Profiles. It is not stored in localStorage, the Anki
collection, note types/templates, global add-on config, logs, or telemetry.

A binding stores an exact note-type structure fingerprint. A mismatch preserves
configuration, marks it `needs_review`, and falls back safely; it never fuzzy
rebinds. Unknown fields and future schema versions fail closed.

## Typed projection contract

Card Search and canonical triage expose the same bounded projection:

```text
displayText
displaySource      formatter | browser_question | native_front | media_fallback | no_text
displayStatus      available | fallback | needs_review | unavailable
displayTruncated
displayHasImages
displayHasAudio
```

Formatter identity/version may be returned as bounded diagnostics, but raw
rules, filenames, HTML, field values, paths, and template source are excluded
from queue payloads and evidence. Public shape changes require synchronized
Python/TypeScript/schema/parser/tests/docs updates; strict clients reject
unknown versions and fields.

## Search/Cards parity

For the same card and active display-store revision:

```text
Search card row displayText
== triage item displayText
== Cards inbox label
== Cards Inspector heading
```

The frontend renders this value and never reconstructs identity from fields,
reason evidence, note type, or preview HTML.

## Preview contract

Inspector renders `frontHtml` with `frontPlainText` fallback. Expanded preview
opens on `backHtml` with `backPlainText` fallback and naturally preserves
Anki-produced `FrontSide`. Both sides retain sanitized CSS and validated media
inside the existing Shadow DOM host; scripts never execute.

If back is unavailable, the modal explicitly names the fallback before showing
front. It never opens blank. Fit-width plus vertical scrolling is preferred to
scaling a long answer until it is unreadable. The accessible modal remains a
portal outside the inert application shell and traps/restores focus.

## Performance and boundedness

- Search and triage batch-project card identities inside serialized QueryOp;
- at most the request/result bounds are rendered;
- no HTTP inspect call or media read occurs per queue row;
- note-type/template/formatter lookups use a request-local bounded cache;
- cache keys include exact note type, template ordinal, formatter/store
  revision, and structure fingerprint;
- tokens and output have strict structural budgets;
- only the active card receives full front/back preview;
- no persistent rendered-content cache can outlive its invalidation inputs.

## Privacy and security

Compact display and full card content are local presentation data. They are not
added to telemetry, remote diagnostics, logs, triage evidence, or screenshot
manifest metadata. Synthetic E2E fixtures may appear in redacted screenshot
binaries. Owner collection content is not read or exported without an explicit
manual checkpoint.

The dashboard remains loopback-only and token-protected. Frontend collection
access, arbitrary code, iframe rendering, raw template execution, unsafe media
paths, and collection mutation remain prohibited.
