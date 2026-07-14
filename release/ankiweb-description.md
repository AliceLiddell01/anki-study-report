Anki Study Report turns your Anki review data into a practical local study dashboard. It helps you understand daily progress, answer quality, deck health, difficult cards, upcoming workload, and FSRS-related signals without exposing your collection to a remote service.

## Main features

- Opens from the Anki Tools menu and includes both a report window and a bundled local dashboard.
- Covers Today, Activity, Statistics, Decks, Cards, profile settings, diagnostics, and maintenance tools.
- Creates compact, normal, or full reports for common periods and selected deck scopes.
- Copies or saves reports as Markdown.
- Shows workload forecasts, study trends, deck comparisons, card attention signals, and read-only FSRS analytics.
- Provides table, tile, and answer-side card previews with isolated HTML/CSS rendering.
- Opens safe filtered searches in Anki Browser when a card needs manual attention.
- Supports complete bundled Russian and English interfaces with persistent language and theme choices.
- Uses an optional local aggregate cache for faster long-period views.

## Privacy and safety

The dashboard runs only on `127.0.0.1` through a temporary token-protected address. It does not upload your collection and does not require an external service account.

Anki Study Report is a read-only analysis tool. It does not edit cards, notes, decks, tags, scheduling data, review history, or FSRS parameters. Card previews are sanitized, JavaScript from card templates is not executed, and unsafe URLs, local file paths, and dangerous HTML/CSS patterns are blocked.

## Compatibility and limitations

- Designed for Desktop Anki 26.05 and newer.
- Forecasts and recommendations are guidance only and never reschedule cards.
- Heavily scripted card templates can look different because preview JavaScript is intentionally disabled.
- The dashboard is optimized for ordinary desktop and laptop window sizes.

## Support

- [Source code and documentation](https://github.com/AliceLiddell01/anki-study-report)
- [Contact the author](https://t.me/Alice_ha_doko?direct)
- [Support development on Boosty](https://boosty.to/ankistudyreport)

All core features remain free.
