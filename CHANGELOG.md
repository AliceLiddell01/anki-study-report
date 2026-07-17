# Changelog

All notable user-facing changes to Anki Study Report are documented here.

## [Unreleased]

## [1.2.0] - 2026-07-18

### Added

- Added per-profile product notices, an accessible What's New dialog, and bundled bilingual release history.
- Added Privacy settings with separate opt-in controls for reliability diagnostics and feature-usage statistics.
- Added local study signals, a Notification Center, notification bell, filters, and per-profile in-app notification preferences.

### Changed

- Consent, release-history, signal, and notification state is now stored separately for each Anki profile.

### Fixed

- Improved consent and release-history themes and localization, active-profile background task binding, and handling of temporary connection failures.

### Safety

- Optional diagnostic data sharing is disabled by default, while study signals and notification preferences remain local.

## [1.1.0] - 2026-07-15

### Added

- Added a dedicated Search workspace for cards and notes using native Anki query syntax.
- Added structured deck, note type, tag, state, and flag filters with sorting, bounded pagination, compact inspection, explicit selection, and handoff to Anki Browser.
- Added safe undoable actions for suspending and unsuspending cards, setting or clearing flags, adding or removing note tags, burying or unburying cards, and moving ordinary cards to normal decks.

### Changed

- Added Search to the primary navigation between Decks and Cards.
- Kept Search query state session-local without placing raw queries in the URL, page title, normal logs, or public diagnostic artifacts.
- Refreshes Search results, selection, pagination, and the active inspector after a confirmed action.
- Reduced duplicate Fast CI runs for pull requests and strengthened real-Anki verification around Search, actions, restart behavior, telemetry, and screenshot contracts.

### Safety

- All modifying operations use explicit card or note allowlists, validate the full batch before changing the collection, and create at most one native Anki undo step.
- Filtered-deck destinations and moves from filtered-deck source cards are rejected instead of silently altering scheduling or FSRS state.
- Search does not provide deletion, rescheduling, field editing, template execution, note type changes, review history changes, or FSRS parameter changes.

## [1.0.0] - 2026-07-14

### Added

- Added a local study dashboard for Today, Activity, Statistics, Decks, Cards, profile settings, diagnostics, and maintenance tools.
- Added Markdown reports, workload forecasts, deck health, card diagnostics, safe card previews, and read-only FSRS analytics.
- Added complete bundled Russian and English dashboard interfaces with persistent language and theme controls.

### Changed

- Made long-period analytics faster with an optional local aggregate cache and bounded query contracts.
- Made dashboard delivery safer with token-protected local access, sanitized previews, and validated lazy-loaded assets.

### Fixed

- Improved localization consistency, card preview compatibility, package validation, and real-Anki startup diagnostics.
