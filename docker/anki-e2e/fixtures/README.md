# Docker E2E fixture provenance

**Contract snapshot:** 2026-07-23

Docker/real-Anki E2E no longer uses a generated synthetic collection or the old
`asr-e2e-render-fixtures.apkg` regression package.

The only collection-content fixtures are the three owner-provided working decks
under:

```text
real-decks/words-n1.apkg
real-decks/grammar-n5.apkg
real-decks/java-core.apkg
```

Their provenance, public-storage authorization, byte sizes, SHA-256 values,
replacement procedure and runtime mutation boundary are documented in:

```text
real-decks/README.md
real-decks/manifest.json
```

The harness imports these packages into a disposable profile through Anki's
public package API. It may mutate only scheduling/revlog/suspended/buried state
of existing imported cards. It must not create or clone notes/cards, alter
fields/templates/media, accept an external APKG override, or fall back to
synthetic content.

Runtime collections, media directories, logs, screenshots, reports, tokens and
`.ankiaddon` outputs belong under ignored `e2e-artifacts/`; they are not source
fixtures and must not be committed.
