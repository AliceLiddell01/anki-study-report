# Real working deck fixtures

**Contract snapshot:** 2026-07-23

This directory is the only source of Anki collection content for Docker/real-Anki E2E.

The three packages are owner-provided working decks. The owner has confirmed that they are public/non-confidential and may be stored in the public repository for local and CI verification. No AnkiWeb identifier is recorded here because an exact package-to-publication mapping was not present in the supplied materials.

## Packages

| Purpose | Repository file | Original supplied name | Size | SHA-256 | Added |
| --- | --- | --- | ---: | --- | --- |
| Words | `words-n1.apkg` | `Words__N1(2).apkg` | 24,979,986 bytes | `78dfab9424fcdb1f5da4005f7e5a2789a04c13414c5477bc647069a06ad10a9b` | 2026-07-23 |
| Grammar | `grammar-n5.apkg` | `文法__N5(2).apkg` | 116,622 bytes | `72f0d9707604dff2c7b51fbde4ace51f104f07a5671f608eb987c2067443c19d` | 2026-07-23 |
| Java | `java-core.apkg` | `Java(2).apkg` | 74,610 bytes | `3c7ee2fe3435d57c5ac5ff8fb8eb913d9406d9461f11975114d6e6ac52b041d3` | 2026-07-23 |

Total repository payload is 25,171,218 bytes. Each file is below GitHub's 50 MiB warning threshold and 100 MiB hard limit, so these fixtures use ordinary Git rather than Git LFS.

## Runtime boundary

The package bytes are immutable source fixtures. E2E imports them into a disposable Docker profile through Anki's public package API:

```text
Collection.import_anki_package(ImportAnkiPackageRequest)
```

Allowed mutations apply only to the disposable imported collection:

- scheduling and due-state fields;
- revlog rows;
- suspended or buried state;
- bounded state required by action/recheck scenarios.

The harness must not edit these `.apkg` files, create new notes/cards/templates/media, clone notes/cards for performance, or fall back to synthetic collection content.

## Manifest and anchors

`manifest.json` pins package paths, byte sizes, SHA-256 values, expected inventory and stable anchors. Concrete note GUIDs, note type names, field names and profile mappings belong only in the manifest. Generic importer, API smoke, media checks and browser smoke consume resolved inventory/anchor reports and must not duplicate those fixture-specific values.

The note-type structure fingerprint algorithm is:

```text
asr-note-type-structure-v1
```

It hashes canonical JSON containing only schema version, note-type name, ordered field names/ordinals and ordered template names/ordinals. It deliberately does not hash mutable note content or package-local numeric IDs.

Preferred anchor order is:

```text
note GUID + template ordinal
→ unique tag
→ deck + note type + field fingerprint
```

The current contract uses the first form. Imported card IDs are runtime results and are never stable source selectors.

## Required runtime evidence

A successful run writes:

```text
real-deck-manifest-report.json
real-deck-import-report.json
collection-inventory.json
anchor-resolution-report.json
scenario-application-report.json
```

The inventory must state `contentSource = committed-real-apkg-only` with zero synthetic notes/cards/media. The scenario report must show zero content creation and, for `perf100`, exactly 100 distinct existing imported cards.

## Replacing one deck

1. Export the intended working deck from Anki as `.apkg`, including media required by the scenarios.
2. Replace only the corresponding repository file.
3. Record its exact byte size and SHA-256.
4. Inspect decks, note types, fields, templates, notes/cards, scheduling data and media inventory.
5. Update the package entry and any affected anchors/fingerprints in `manifest.json`.
6. Run focused manifest/checksum/anchor tests before Docker.
7. Run exact-head Fast CI.
8. Run one policy-required real-deck Docker gate for the final exact tree; do not repeat a successful exact-tree gate.

PowerShell checksum command:

```powershell
Get-FileHash .\docker\anki-e2e\fixtures\real-decks\words-n1.apkg -Algorithm SHA256
```

Linux/WSL checksum command:

```bash
sha256sum docker/anki-e2e/fixtures/real-decks/words-n1.apkg
```

A missing file, checksum mismatch, duplicate package ID/path, failed official import, unresolved anchor or ambiguous anchor is a hard failure. There is no local-only or synthetic fallback.
