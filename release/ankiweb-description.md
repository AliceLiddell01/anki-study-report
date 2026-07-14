Anki Study Report turns your Anki review data into a practical local study dashboard. It helps you understand daily progress, answer quality, deck health, difficult cards, upcoming workload, and FSRS-related signals without exposing your collection to a remote service.

## New: Search your Anki collection

The dashboard now includes a dedicated Search workspace for both cards and notes. It uses native Anki query syntax and adds structured filters, sorting, bounded pagination, explicit selection, and a compact inspector without loading or executing card-template HTML.

Search results can be opened directly in Anki Browser. A small allowlist of safe actions is also available for common maintenance tasks: suspend or unsuspend cards, set or clear flags, add or remove note tags, bury or unbury cards, and move ordinary cards to a normal deck. Confirmed changes use Anki's native undo system.

## Support the author

If you find Anki Study Report useful, you can support the continued development of my free Anki decks and the Anki Study Report add-on on Boosty.

Your support helps fund new cards, corrections, deck maintenance, testing, documentation, and further development of free Anki tools.

All decks and the core features of Anki Study Report will remain free.

<a href="https://boosty.to/ankistudyreport">
  <img src="https://upload.wikimedia.org/wikipedia/commons/9/92/Boosty_logo.svg" alt="Support the author on Boosty" width="220">
</a>

## Main features

- Opens from the Anki Tools menu and includes both a report window and a bundled local dashboard.
- Covers Today, Activity, Statistics, Decks, Search, Cards, profile settings, diagnostics, and maintenance tools.
- Creates compact, normal, or full reports for common periods and selected deck scopes.
- Copies or saves reports as Markdown.
- Shows workload forecasts, study trends, deck comparisons, card attention signals, and read-only FSRS analytics.
- Searches cards and notes with native Anki syntax, structured filters, sorting, bounded pagination, and compact inspection.
- Opens explicit result selections in Anki Browser and provides a limited set of undoable maintenance actions.
- Provides table, tile, and answer-side card previews with isolated HTML/CSS rendering.
- Supports complete bundled Russian and English interfaces with persistent language and theme choices.
- Uses an optional local aggregate cache for faster long-period views.

## Privacy and safety

The dashboard runs only on `127.0.0.1` through a temporary token-protected address. It does not upload your collection and does not require an external service account.

Analytics, forecasts, FSRS views, and card previews remain read-only. Search actions are explicit, allowlisted, batch-validated, and undoable through Anki. The dashboard does not delete cards or notes, reschedule reviews, edit fields or templates, change note types, alter review history, or modify FSRS parameters. Moves involving filtered decks are rejected when their scheduling semantics would be unsafe.

Card previews are sanitized, JavaScript from card templates is not executed, and unsafe URLs, local file paths, and dangerous HTML/CSS patterns are blocked. Raw Search queries and the temporary dashboard token are not placed in the URL, page title, normal logs, or public diagnostic artifacts.

## Compatibility and limitations

- Designed for Desktop Anki 26.05 and newer.
- Forecasts and recommendations are guidance only and never reschedule cards.
- Search is intentionally bounded and does not include saved searches, arbitrary columns, inline editing, or rich card preview execution.
- Heavily scripted card templates can look different because preview JavaScript is intentionally disabled.
- The dashboard is optimized for ordinary desktop and laptop window sizes.

## Links and contact

- [Source code and documentation](https://github.com/AliceLiddell01/anki-study-report)
- [Contact the author](https://t.me/Alice_ha_doko?direct)
