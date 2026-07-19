# C1.5R.3 — Front/back preview semantics

## Git and source decision

- initial `core` HEAD: `3fc5bd3c19f61bfd4812c19fc4e1df862f9e9c45`
- strategy: isolated task branch and disposable GitHub Actions runner; no PR
- tested implementation HEAD: `3b1b363a675d2b182d0a4ce04e482b1742333368`
- documentation closeout HEAD: this Markdown-only commit
- final `core` HEAD: this Markdown-only commit
- transfer: fast-forward to `core` completed without force-push
- final synchronization: `origin/core...c1-5r-3-preview-semantics = 0/0`
- open PR from `core`: none
- evidence: GitHub Actions artifact retained outside Git; screenshots are not repository files
- exact Anki source inspected: tag `26.05`, `pylib/anki/cards.py` and `pylib/anki/template.py`

## Sources actually read

Repository entrypoints and contracts included `README.md`, `docs/ai-handoff.md`, both roadmap indexes, R0–R2 and remediation reports, card identity/Cards/Search/API/architecture/frontend/security/localization/test contracts, relevant package scripts, backend preview generation, Cards/Search consumers, shared Shadow DOM/modal components, locale files, styles and focused Python/frontend tests.

The exact implementation inventory included:

- `anki_study_report/note_intelligence.py`
- `anki_study_report/search_service.py`
- `anki_study_report/search_runtime.py`
- `anki_study_report/dashboard_server.py`
- `web-dashboard/src/pages/CardsPage.tsx`
- `web-dashboard/src/components/AnkiCardShadowPreview.tsx`
- `web-dashboard/src/components/AccessibleModal.tsx`
- relevant Search types/consumers, locales, styles and tests

## Reproduced defect and renderer decision

The old full-preview adapter preferred `browser=True`, so the payload represented Browser Appearance rather than reviewer question/answer semantics. Cards then rendered `frontHtml` in both Inspector and expanded modal. Preview layout also enforced a minimum scale that could exceed width fit.

Anki 26.05 confirms the reviewer path as `Card.render_output(reload=True, browser=False)`. The explicit compatibility fallback is reviewer `question(reload=True, browser=False)` plus argument-free `answer()`. Browser Appearance remains part of compact display identity only.

## Implemented semantics

- full preview uses one native reviewer render for the active inspected card
- front and answer/back remain distinct sanitized payload sides
- Inspector renders front
- expanded dialog opens on answer/back
- Anki-rendered `{{FrontSide}}` remains intact; frontend does not concatenate sides
- front replaces question AV markers
- back resolves both question and answer AV markers
- media references are a deduplicated union of both sides
- native failures fall safely into the existing sanitized template renderer
- explicit front/back availability helpers prevent presenting front as answer
- queue rows and compact identity remain unchanged; opening the answer reuses the active inspect payload
- Inspector scaling is width-driven with bounded internal vertical scrolling
- expanded answers fit width and use natural dialog vertical scrolling
- image/font/resize remeasurement remains active
- the shared accessible modal remains portal-based, inerting the app shell, trapping focus, closing on Escape and restoring focus when possible
- RU/EN labels distinguish Front and Answer

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

Focused Python passed `79/79`. Focused frontend passed `18/18`. The clean runner bootstrapped copied dashboard assets before focused Python because generated assets are intentionally absent from Git. Production build and canonical non-Docker were then run normally.

## Visual evidence

- `r3-inspector-front-1440-light.png`
- `r3-expanded-answer-1440-light.png`
- `r3-inspector-front-1024-light.png`
- `r3-expanded-long-answer-1024-light.png`
- `r3-expanded-answer-1440-dark.png`

The screenshots were uploaded as a workflow artifact and were not committed. The smoke asserted horizontal fit, explicit front metadata and answer-only content in the back preview.

## Changed files

- `anki_study_report/note_intelligence.py`
- `tests/test_note_intelligence.py`
- `web-dashboard/src/components/AccessibleModal.tsx`
- `web-dashboard/src/components/AnkiCardShadowPreview.tsx`
- `web-dashboard/src/components/AnkiCardShadowPreview.test.tsx`
- `web-dashboard/src/pages/CardsPage.tsx`
- `web-dashboard/src/pages/CardsPage.test.tsx`
- `web-dashboard/src/i18n/locales/en.ts`
- `web-dashboard/src/i18n/locales/ru.ts`
- `web-dashboard/src/styles.css`
- `docs/card-preview-semantics.md`
- related current contracts, roadmap indexes, AI handoff and this closeout report

Generated dashboard assets, screenshots, logs, caches and runner helpers are not committed.

## Failures and fixes

- Initial transformation diagnostics found two identical native-render test fakes; the staging transform was made exact for both.
- A clean runner lacked copied dashboard assets, causing two unchanged static-fallback tests to return the built-in page; assets were bootstrapped before focused Python without changing server code.
- The first layout test exposed that long Inspector content was still height-fitted below the correct width scale; the algorithm was corrected to use width fit plus vertical scrolling.
- A temporary transform quoting error was corrected before verification.
- The first closeout attempted to stage a nonexistent generated-assets path; generated assets remain uncommitted by contract, and the verified implementation transfer was repeated with strict Git error handling.

## Security and privacy

No Browser Appearance is used for full preview. Card JavaScript is not executed. No iframe, object/embed, remote loads, raw local paths or dashboard-token disclosure were introduced. Sanitizer allowlists, media validation, URL redaction and Shadow DOM isolation remain in place.

## Not verified

Fast CI, Docker, real-Anki E2E, the owner's private Anki profile and final owner product acceptance were not run. No PR, merge into `master`, release, deployment, AnkiWeb publication, R4 or C1.6 work was performed.

## Status

```text
C1.5R.0 — Complete
C1.5R.1 — Complete
C1.5R.2 — Complete
C1.5R.3 — Complete
C1.5R.4 — Next, not started
C1.5R.5–R.7 — Not started
C1.6 — Blocked
Core C1 — In progress
```
