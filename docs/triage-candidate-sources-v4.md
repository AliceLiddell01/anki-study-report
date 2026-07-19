# Triage candidate sources v4

Triage v4 separates period-bound learning history from period-independent current
collection content.

## Source semantics

- `learningCandidates` reads bounded review history for the requested period.
- `contentCandidates` scans current notes/cards independently of the review period.
- `signals` remains an existing independent source.
- `search_workset` remains exact-card mode and does not run either automatic loader.

## Authoritative profile boundary

Only profiles whose stored state is `confirmed`, whose fingerprint matches the
current note-type structure, and which contain at least one check can drive an
automatic content scan. Suggested, disabled and needs-review profiles are reported
but do not inspect note values.

## Bounds and continuation

The current-content loader scans at most 500 note IDs per request using:

```text
note.id > contentCursor
order by note.id asc
limit 501
```

It then performs one batched card/note read. There is no offset pagination, no
automatic continuation loop and no global total-count query. `nextCursor` is
present exactly when the source is truncated.

## Scope and representative card

Empty `deckIds` means all decks. Selected parent decks include descendants through
the existing deck-expansion semantics. Suspended and buried cards remain eligible
because content quality is independent of scheduling state. A note is evaluated
once and anchored to the lowest applicable in-scope card ID. Sibling count covers
all current cards for the note.

## Merge and payload

Learning, signal and content reasons merge by card. Only cards with reasons are
resolved through canonical Search display identity. Raw fields, HTML, media names,
SQL, paths and exception text are not exposed.

## R5 boundary

R4 types and validates continuation state but does not add a visible load-more
control or redesign the Cards inbox. That product work belongs to C1.5R.5.
