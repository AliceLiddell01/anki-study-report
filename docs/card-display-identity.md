# Card display identity

## Status

**Canonical baseline:** `C1.5R.1 — Complete`

**Optional formatter layer:** `C1.5R.2 — Complete`

**Branch:** `core`

**Implementations:**

```text
anki_study_report/card_display_identity.py
anki_study_report/card_display_formatter_store.py
anki_study_report/card_display_formatter_service.py
anki_study_report/card_display_formatter_runtime.py
```

**Public contracts:** Search schema v2, Triage schema v3 — unchanged by R2.

C1.5R.1 established one backend-owned exact-card identity across Search, Triage,
and current Cards surfaces. C1.5R.2 adds an optional bounded declarative formatter
above that projector. Missing, disabled, corrupt, unsupported, unavailable, or
empty formatter output always returns to the completed R1 semantics.

Contracts:

- [`card-display-formatter-v1.md`](card-display-formatter-v1.md)
- [`../reports/core/c1-5r-1-canonical-card-display-identity.md`](../reports/core/c1-5r-1-canonical-card-display-identity.md)
- [`../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md`](../reports/core/c1-5r-2-declarative-compact-formatter-runtime.md)

## Shared exact-card identity

The same compact identity is consumed by:

- Search card result row;
- Search card Inspector heading;
- canonical Triage item;
- Cards queue item;
- Cards Inspector heading.

Note-mode Search remains a note projection and keeps `primaryText`. Card rows,
card details, and Triage items have no card `primaryText` alias.

## Authoritative projector

`project_card_display_identity(card, formatter=None)` owns one exact card.
Without an active formatter it uses:

1. native Browser question: `card.question(reload=True, browser=True)`;
2. native reviewer front: `card.question(reload=True, browser=False)`;
3. explicit `media_only` or `unavailable` state.

With an active formatter, only its declared `inputSource` is attempted first.
A request-local resolver selects by exact `(noteTypeId, templateOrdinal)` with
note-type default inheritance and exact disabled opt-out. Names, decks, fields,
and fuzzy similarity never participate in binding.

A configured failure reuses already-rendered values and returns to the sequence
above. Each source is rendered at most once per card projection. The projector
never renders `card.answer()`.

## Ordered compact tokenization

The parser emits only:

```text
text
line_break
image
audio
```

Text and media token order is retained. Inline nodes concatenate without an
invented separator; `<br>` and block boundaries create lines; entities are
decoded; whitespace is collapsed only inside final lines. Script/style/iframe,
object/embed, SVG/MathML, template/form and unsafe media container contents are
dropped. Malformed blocked nesting fails closed.

Canonical R1 projection omits media tokens and selects the first meaningful line.
The exact media-heavy Japanese fixture therefore remains:

```text
【に】（する）
```

An enabled reviewer-front formatter with `imageMode: stem` may produce:

```text
【に】感謝（する）
```

Safe media handling, policy enums, line selection and exact truncation are
specified in [`card-display-formatter-v1.md`](card-display-formatter-v1.md).
No media file is opened or checked for existence.

## Wire contract

Card identity remains the same flat exact fragment:

```json
{
  "displayText": "【に】感謝（する）",
  "displaySource": "reviewer_front",
  "displayStatus": "available",
  "displayTruncated": false
}
```

`displaySource`:

```text
browser_question | reviewer_front | none
```

`displayStatus`:

```text
available | media_only | unavailable
```

Coherence rules:

- `available`: non-empty bounded text and a rendered Browser/reviewer source;
- `media_only`: empty text, no truncation, rendered source retained;
- `unavailable`: empty text, source `none`, no truncation.

Formatter state and configuration are not copied into Search/Triage wire data.
There is no public `formatterApplied`, `formatterId`, alias, HTML, or filename
metadata field.

## Search and Triage schemas

Search query and inspect remain exact schema v2. Search metadata remains its
independent schema v1 variant. Triage remains exact schema v3.

`project_card_row()` serves normal Search, Search inspect, and exact-card
resolution reused by Triage. Therefore one resolver and one backend identity path
serve all card surfaces; Triage has no second formatter implementation.

Strict TypeScript parsers continue to reject old schemas, unknown keys, card
aliases, malformed IDs, overlong text, and incoherent display state/source/text.

## UI behavior

Backend text is displayed unchanged for `available`. The frontend localizes only
explicit fallback states:

| State | RU | EN |
| --- | --- | --- |
| `media_only` | Карточка только с медиа | Card with media only |
| `unavailable` | Текст карточки недоступен | Card text unavailable |

R2 adds no formatter route, page, hook, Settings navigation, form, live preview,
or Cards redesign. Guided configuration belongs to C1.5R.6; preview semantics
belong to C1.5R.3.

## Security and privacy

The dashboard remains loopback-only and token-protected. Frontend never reads
the collection. Compact identity and formatter configuration stay local and are
not copied to telemetry or normal logs. Runtime executes no JavaScript, Python,
SQL, shell, regex, selector, expression, callback, dynamic import, or subprocess.

No raw HTML, note field values, media contents, absolute paths, renderer
exceptions, formatter filenames, generated `displayText`, or tokens are logged.

## Verification state

C1.5R.1 remains complete at its recorded tested implementation HEAD. C1.5R.2
owner-checkout verification is complete for the tree committed and pushed as
`edad09e8ffae443b94e192b266084abb66c37adf`:

```text
focused backend: 142 passed
focused frontend: 49 passed
TypeScript typecheck: PASS
package build and validation: PASS
canonical run_full_check.ps1 -SkipDocker: PASS
Git hygiene and origin/core synchronization: PASS
```

R3 is now Next, not started. C1.6 remains blocked until the complete C1.5R
remediation and separate owner product acceptance are finished.
