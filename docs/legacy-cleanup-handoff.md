# Legacy cleanup handoff

## Closure status

```text
Legacy cleanup: complete
Date: 2026-07-10
Final branch: master (fast-forward from codex/stage-15-product-and-helper-cleanup)
Final commits: Stage 1–15 cleanup line plus docs: finalize legacy cleanup handoff
```

## What was completed

- Removed legacy card payload aliases in favour of canonical `attentionCards` and
  `attentionCardsStatus`.
- Added stale dashboard-asset/full-check protection and hardened static fallback
  diagnostics.
- Characterized the cache/report bridge as a transitional adapter without
  changing its public contract.
- Removed misleading Stats, FSRS and Browse placeholder routes; kept
  Integrations as real read-only diagnostics.
- Removed five verified definition-only helpers.
- Completed cumulative non-Docker and Docker verification of the cleanup line.

## Current route set

```text
#/home
#/profile
#/decks
#/cards
#/calendar
#/actions
#/integrations
#/logs
#/settings
#/settings/server
```

Stats, FSRS and Browse were removed because they were placeholders. Returning
them is product development, not cleanup. Unknown or removed hashes resolve to
Home.

## Contracts and protected boundaries

- `attentionCards` is the canonical card-level payload; use it with
  `attentionCardsStatus`.
- `report_from_cache.py` remains a transitional cache/report adapter.
- Markdown/HTML report remains a user-facing surface.
- Dashboard static fallback remains diagnostic.
- Token validation, media safety, action allowlists, sanitizer and Shadow DOM
  Cards preview remain protected runtime boundaries.
- Generated outputs stay outside Git, including E2E artifacts, dashboard build
  directories, runtime data and `.ankiaddon` archives.

## Intentionally retained helpers

`_rendered_preview_fallback` and `_append_av_media_html` remain untouched.
They need Cards/media-specific runtime proof before any change and are not
cleanup candidates without new evidence.

## Verification summary

| Check | Result |
| --- | --- |
| Stage 15 targeted frontend/Python tests and modified-file py_compile | PASS |
| `./scripts/run_full_check.ps1 -SkipDocker` | PASS — 88 Python tests, 47 frontend tests, build/copy and package validation |
| `./scripts/run_full_check.ps1 -CleanDocker` | PASS — local checks, package/install layout, Anki import/readiness, API smoke, browser smoke and restart |

No token-bearing artifact is committed.

## Next product sequence

```text
Navigation / IA
→ Settings Hub
→ Profile MVP
→ Calendar + Activity Feed
→ Decks v2
→ Statistics v1
→ FSRS inside Stats
→ Browse/Search
→ Signals
→ Cards v2
```

The next chat starts only with **Navigation / IA**. Do not start Settings Hub
or another product area until the information architecture is agreed.

## Suggested new-chat starter

```text
Legacy cleanup Anki Study Report завершён и влит в master.
Хочу начать отдельный этап Navigation / Information Architecture.
Сначала проанализируй текущие routes, sidebar и продуктовую иерархию,
не переходя к Settings Hub или другим функциям до фиксации IA.
```
