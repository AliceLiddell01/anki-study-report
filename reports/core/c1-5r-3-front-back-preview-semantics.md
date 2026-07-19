# C1.5R.3 — Front/back preview semantics

## Git and source decision

- initial core HEAD: `3fc5bd3c19f61bfd4812c19fc4e1df862f9e9c45`
- strategy: isolated task branch and disposable GitHub runner; no PR
- workflow run: \
- evidence artifact: \
- tested implementation HEAD: `3b1b363a675d2b182d0a4ce04e482b1742333368`
- documentation closeout HEAD: this Markdown-only commit
- exact Anki source inspected: tag `26.05`, `pylib/anki/cards.py` and `pylib/anki/template.py`

## Implemented semantics

- full preview: `Card.render_output(reload=True, browser=False)`
- explicit fallback: reviewer `question(reload=True, browser=False)` plus `answer()`
- Inspector: sanitized front; expanded dialog: sanitized answer/back
- compact identity and queue rows: unchanged; no full preview reads
- Anki-rendered `FrontSide` remains intact; frontend does not concatenate sides
- question and answer AV markers are resolved; media refs are a deduplicated union
- bounded Inspector width/scroll, natural expanded-answer vertical scroll, shared accessible modal

## Verification

| Contour | Exit | Duration seconds |
| --- | ---: | ---: |
| `apply_backend` | 0 | 0 |
| `apply_layout` | 0 | 0 |
| `apply_cards` | 0 | 0 |
| `apply_tests` | 0 | 0 |
| `apply_docs` | 0 | 0 |
| `apply_diff_check` | 0 | 0 |
| `install_python` | 0 | 3 |
| `install_frontend` | 0 | 2 |
| `bootstrap_assets` | 0 | 22 |
| `focused_python` | 0 | 11 |
| `focused_frontend` | 0 | 3 |
| `typecheck` | 0 | 12 |
| `production_build` | 0 | 21 |
| `playwright_install` | 0 | 11 |
| `browser_smoke` | 0 | 8 |
| `canonical_non_docker` | 0 | 76 |
| `git_diff_check` | 0 | 0 |

The clean runner bootstrapped copied dashboard assets before focused Python because generated assets are intentionally absent from Git. Production build and canonical non-Docker were then run normally.

## Visual evidence

- `r3-inspector-front-1440-light.png`
- `r3-expanded-answer-1440-light.png`
- `r3-inspector-front-1024-light.png`
- `r3-expanded-long-answer-1024-light.png`
- `r3-expanded-answer-1440-dark.png`

Screenshots were uploaded as a workflow artifact and were not committed. The smoke asserted horizontal fit, explicit front metadata and answer-only content.

## Changed files

- `anki_study_report/note_intelligence.py`
- `docs/README.md`
- `docs/ai-handoff.md`
- `docs/architecture.md`
- `docs/card-display-identity.md`
- `docs/card-preview-semantics.md`
- `docs/cards-v2-product-contract.md`
- `docs/cards-v2-workspace-ui.md`
- `docs/dashboard-api.md`
- `docs/frontend-map.md`
- `docs/localization.md`
- `docs/search-query-foundation.md`
- `docs/security-and-safety.md`
- `reports/core/c1-5r-3-front-back-preview-semantics.md`
- `roadmap/README.md`
- `roadmap/core/README.md`
- `tests/test_note_intelligence.py`
- `web-dashboard/src/components/AccessibleModal.tsx`
- `web-dashboard/src/components/AnkiCardShadowPreview.test.tsx`
- `web-dashboard/src/components/AnkiCardShadowPreview.tsx`
- `web-dashboard/src/i18n/locales/en.ts`
- `web-dashboard/src/i18n/locales/ru.ts`
- `web-dashboard/src/pages/CardsPage.test.tsx`
- `web-dashboard/src/pages/CardsPage.tsx`
- `web-dashboard/src/styles.css`

## Failures and fixes

- Initial transformation diagnostics found two identical native-render test fakes; the staging transform was made exact for both.
- A clean runner lacked copied dashboard assets, causing two unchanged static-fallback tests to return the built-in page; assets were bootstrapped before focused Python without changing server code.
- The first closeout attempted to stage a nonexistent generated-assets path; generated assets remain uncommitted by contract, and the verified implementation transfer was repeated with strict Git error handling.

## Security and boundaries

No Browser Appearance for full preview, card JavaScript, iframe, remote loads, raw paths or token disclosure. Sanitizer, media validation and Shadow DOM remain in place.

## Not verified

Fast CI, Docker, real-Anki E2E, the owner private profile and final owner product acceptance were not run. No PR, master merge, release, deployment, AnkiWeb publication, R4 or C1.6 work was performed.

## Status

C1.5R.3 — Complete
C1.5R.4 — Next, not started
C1.6 — Blocked
