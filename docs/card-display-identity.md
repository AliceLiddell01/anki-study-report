# Card display identity

## Status

**Status:** corrective design contract baseline

**Implementation:** C1.5R.1 and C1.5R.2

**Branch:** `core`

This document defines the product and architecture boundary for one compact card
identity across Search, Triage, and Cards. It is not a final API signature,
storage schema, or production implementation specification.

Recovery context: [`../reports/core/c1-5r-0-recovery-baseline.md`](../reports/core/c1-5r-0-recovery-baseline.md).

## Affected surfaces

The same compact identity must be used by:

- Search card result row;
- Search card Inspector identity;
- canonical Triage item;
- Cards attention queue item;
- Cards Inspector heading.

Note-mode Search remains a note projection and is not silently converted into a
card identity.

## Current defect

The current card row projector starts with the note sort field and then scans
other non-empty note fields. This is a note-centric fallback, not card identity.
It can choose an unrelated field when the rendered card front is media-heavy or
contains little plain text. Triage and Cards inherit the same incorrect value.

The corrective implementation must not infer card identity by scanning arbitrary
note fields.

## Compact identity and full preview are different products

Compact identity is a bounded, stable scan label. It must be cheap enough for
Search result lists and Cards queues and must not require media loading for each
row.

Full preview is the sanitized rendered card surface for one active card. It may
include card CSS and validated local media through the existing token-protected
preview boundary.

Compact identity must not be produced by shrinking a full preview, and a full
preview must not be replaced by compact text.

## Required source precedence

The implementation in C1.5R.1/C1.5R.2 must preserve this conceptual precedence:

1. an exact, valid declarative compact formatter configuration for the current
   card template, when such a configuration exists;
2. a safe compact projection derived from the card's native Browser Appearance,
   when it provides meaningful bounded identity;
3. a safe compact projection derived from the rendered native front;
4. a bounded explicit fallback that communicates unavailable or media-only
   identity without scanning unrelated note fields.

Exact template configuration takes precedence over a note-type default.
Structure mismatch fails closed; no fuzzy rebinding is allowed.

This precedence is a design requirement. The exact payload field names, request
shape, persistence document, and migration mechanism remain C1.5R.1/R2 work.

## No unrelated-field fallback

Card identity may use only sources belonging to the exact card/template display
contract. It must not fall through to:

- the note sort field merely because it is non-empty;
- the first non-empty field;
- a part-of-speech field unrelated to the displayed card;
- tags, deck names, or evidence text as a substitute for card identity.

When no meaningful compact identity can be produced, the UI must show a bounded
explicit unavailable/media-only state rather than inventing text.

## Search and Cards parity

One backend-owned card-identity projector must be authoritative for Search card
rows and exact-card resolution used by Triage. Cards must consume that projected
identity rather than reimplementing extraction in React.

The following values must agree for the same exact card and contract version:

```text
Search card row
Search card Inspector identity
Triage item
Cards queue item
Cards Inspector heading
```

Frontend parsers remain strict. A public shape change requires synchronized
Python projection, TypeScript types/validators, focused tests, and documentation.
No silent alias is introduced across a semantic version change.

## Inspector and expanded preview semantics

The compact heading and the full card preview remain separate:

- Cards Inspector: rendered native front;
- expanded preview: rendered native answer/back by default;
- Search/card detail may expose both sanitized sides through the existing bounded
  inspect path;
- only the active card starts a full preview read;
- queue rows never load full HTML or media.

The answer/back surface must preserve Anki's answer semantics, including the
front-side contribution where Anki provides it. An answer-only marker may be
shown as presentation metadata, but the implementation must not fabricate a
second renderer.

## Exact Japanese example

For a media-heavy Japanese card whose unrelated note sort field contains
`「Существительное」`:

```text
Default compact:
【に】（する）

Configured compact:
【に】感謝（する）

Inspector:
full front

Expanded preview:
full back/answer
```

`「Существительное」` is not a valid fallback identity for this card.

## Declarative formatter boundary

The optional compact formatter belongs to C1.5R.2 and must be:

- local and profile-scoped;
- declarative and bounded;
- tied to exact note-type/template identity and structure versioning;
- previewable before confirmation;
- independent from Inspection Profile v1 unless a separately versioned contract
  explicitly composes them;
- fail-closed on unknown or future schema versions.

Inspection Profile v1 must not silently gain formatter fields. A version
transition must reject unknown fields under the old schema and define an explicit
migration/compatibility boundary.

## No arbitrary executable code

The formatter cannot accept or execute:

- Python, JavaScript, SQL, shell, or callbacks;
- arbitrary regular-expression or query languages;
- template JavaScript;
- filesystem or network rules;
- arbitrary HTML execution;
- direct collection access from the frontend.

The existing sanitizer, media validation, action allowlists, Shadow DOM preview,
loopback server, and dashboard-token boundaries remain unchanged.

## Privacy and security

Compact identity and formatter configuration remain local. They are not added to
remote telemetry. Normal logs and public E2E artifacts must not include tokens,
absolute paths, raw note dumps, private profile documents, or unbounded card
content.

The backend remains responsible for collection reads and sanitization. The
frontend receives only the bounded versioned projection needed by the current
surface.

## Schema and versioning requirement

C1.5R.1/R2 must explicitly decide and document:

- which public schema owns compact card identity;
- whether an additive field is sufficient or a new schema version is required;
- strict unknown-field behavior during transition;
- exact default/configured/unavailable states;
- structure fingerprinting and migration rules for formatter configuration;
- Search/Triage parser parity;
- rollback and future-schema preservation.

No final field name or storage filename is approved by this baseline alone.

## Deferred implementation details

The following remain for C1.5R.1/R2 and must not be inferred as already accepted:

- final Python type and function names;
- final Search/Triage request and response signatures;
- final formatter storage path and JSON schema;
- exact tokenization/collapse algorithm and length limits;
- detailed Browser Appearance fallback rules;
- configuration UI controls;
- migration from any experimental local file;
- final E2E screenshot assertions.

C1.5R.0 stops at this contract baseline.
