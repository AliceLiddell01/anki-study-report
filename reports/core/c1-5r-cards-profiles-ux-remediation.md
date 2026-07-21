# C1.5R — Cards and Inspection Profiles UX remediation

**Current status:** `C1.5R.0–R.7 Complete`; owner accepted; `C1.6 Next`; `C1.6B Conditional`

**Product gate:** owner product acceptance is accepted for C1.5R.7; the complete C1.5R.0–R.7 line remains closed.

## Initial baseline

- branch: `core`;
- initial HEAD: `101103585149aa0a30d411ad538fbcc06641a05b`;
- initial divergence: `0 behind / 24 ahead` of `origin/master`;
- `origin/core...HEAD`: `0 behind / 0 ahead`;
- initial worktree: clean;
- open pull requests from `core`: none;
- C1.6 production work after the reference HEAD: not found.

The old C1.5 implementation and runs remain historical technical evidence.
Owner product acceptance was withdrawn after screenshot and real-profile review,
so they do not establish the correctness of the user model being remediated.

## Sources actually read so far

Current production/tests and the C1.1–C1.5 contract/report line were inspected,
including Search, triage, rendered preview, Cards workspace, Inspection Profiles,
strict frontend parsers, E2E fixtures/workflows, roadmap and handoff sources named
in the C1.5R contract. The final inventory will list every source used by the
implementation and verification slices.

Official sources read:

- Anki Manual: Card Templates, Styling & HTML / Browser Appearance, Field
  Replacements / FrontSide, Browsing and Searching;
- Writing Anki Add-ons: the `anki` module, Background Operations and Reviewer
  JavaScript;
- W3C WAI: Forms, Grouping Controls, Multi-page Forms, Disclosure and Modal
  Dialog patterns;
- official Anki `26.05` source at
  `e64c6b1aee3e8d668fb8bbe084beada8e070d985`.

## User evidence inventory

Located evidence is intentionally kept outside git:

- accepted C1.5 E2E ZIP
  `ci-e2e-standard-29649071545-1.zip`;
- two owner screenshots, `photo_2026-07-18_19-24-30.jpg` and
  `photo_2026-07-18_19-24-43.jpg`;
- historical baseline `artifacts/screenshots/cards.zip`;
- earlier E2E ZIPs retained only for historical comparison.

Both owner JPGs were visually opened. They show the same normal Inspection
Profiles path as an extremely long technical page: repeated mapping/check
fieldsets dominate the page and the action area appears only after a roughly
6000 px scroll. The accepted C1.5 ZIP is being inventoried image-by-image; the
completed filename/surface/theme/viewport/fixture/state/observation table will
be recorded before technical acceptance.

## Defect reproduction before production changes

1. `search_service._primary_text()` starts with the note sort field and then
   scans arbitrary non-empty fields. Search card rows use it directly and
   triage inherits it, allowing a media-heavy front to become the unrelated
   `「Существительное」` field.
2. `note_intelligence._call_native_render_output()` requests
   `browser=True`; the same result supplies the full preview even though Anki
   Browser Appearance is a compact Browser surface, not reviewer front/back.
3. Cards renders `side="front"` in both the Inspector and expanded modal even
   though Search inspect already carries `backHtml`.
4. `useCardsTriageWorkspace` hardcodes a seven-day interval with no visible
   period control.
5. automatic profile candidates are the same period-bound revlog candidates
   used for learning issues; zero recent reviews therefore produces zero
   current-content candidates.
6. an unconfigured Inspection Profile keeps `draft=null` until an explicit
   suggestion-apply action.
7. the normal profile editor exposes role slugs, check IDs/kinds/modes,
   template ordinals, repeated mapping/check fieldsets and equal-weight actions.
8. the C1.5 native table is product-rejected. At 1024 it remains a narrow split
   and the preview's fit constraints weaken readability.

Focused red tests recorded before the fix:

- reviewer-preview mode: FAIL because native preview called
  `render_output(reload=True, browser=True)` instead of `browser=False`;
- media-heavy compact identity: FAIL because the Search card row had no
  canonical `displayText` and still exposed unrelated-field identity.

## Corrective architecture decisions

1. One backend projector owns Search-card, triage, Cards-list and Inspector
   compact identity.
2. Browser Appearance is an identity source; reviewer/native front and answer
   remain the full preview sources.
3. Ordered bounded text/line/image/audio tokens precede compact collapse.
4. The old arbitrary note-field fallback is removed for cards.
5. Formatter v1 is declarative only and is stored in an independent strict,
   profile-local, optimistic-concurrency document.
6. Exact template override precedes a note-type default; mismatches fail closed
   without fuzzy rebinding.
7. Search/triage public shape changes are explicitly versioned and parsed
   strictly in Python and TypeScript.
8. Learning candidates remain period-bound; current-content candidates are a
   separate bounded collection scan with explicit partial/truncated status.
9. Cards becomes a dense structured inbox list plus persistent Inspector; the
   rejected spreadsheet-like table is not retained as a hidden mode.
10. Inspection Profiles defaults to a guided Basic workflow; the full runtime
    editor remains behind Advanced disclosure.
11. Inspector renders front; the expanded modal opens on answer/back.
12. Only the active card receives a full preview; compact rows never read media.

The detailed display contract is
[`docs/card-display-identity.md`](../../docs/card-display-identity.md).

## Verification ledger

| Gate | Result |
| --- | --- |
| focused red tests before implementation | expected FAIL, recorded above |
| R1–R4 focused and canonical gates | PASS; see increment reports |
| R5 focused frontend/backend | PASS — 25 Vitest / 92 pytest |
| R5 TypeScript/build/bundle/package | PASS — run `29740393142` |
| R5 isolated visual matrix | PASS — run `29738841012`, artifact `8459497217` |
| R5 canonical `run_full_check.ps1 -SkipDocker` | PASS — exact `a30f4db66e73f3f836e69ba90cfc06974ce3df47` |
| R6 guided Inspection Profiles closeout | PASS — implementation `8d07bc6a3ab7d1e4f2395ebc52b01895aab96d94`, merged `d2ee9703a2b841c0438fc07a43db3b701835a958` |
| R7 focused harness regression | PASS — 30 tests on `df633563490f80346617871ec5640adf99154956` |
| R7 canonical non-Docker | PASS — 318 frontend tests, 796 Python tests, package verified |
| R7 clean full real-Anki E2E | PASS — Anki 26.05, restart, 50 pages, 2 navigation, 4 synthetic Cards, 1 APKG Cards screenshot |
| owner product decision | Accepted |

## Delivery boundary

- implementation PR: #50 merged into `core` as
  `d2ee9703a2b841c0438fc07a43db3b701835a958`;
- merge to `master`: no;
- release/tag: no;
- deployment: no;
- `.ankiaddon`/AnkiWeb publication: no;
- owner private profile read/export: no;
- C1.6 implementation: planned only after accepted R7; not started;
- C1.6B bounded bulk actions: Conditional; not started.

## R6 remediation outcome

C1.5R.6 replaced the rejected machine-first normal path with an immediate generated
draft, guided Basic field/requirement/scope workflow, lifecycle-aware actions,
friendly bounded validation and collapsed Advanced/Profile tools. The strict v1
runtime, confirmed-only authority, fail-closed lifecycle, conflict protection and
security boundary remain unchanged. Final implementation
`8d07bc6a3ab7d1e4f2395ebc52b01895aab96d94` and merged `core`
`d2ee9703a2b841c0438fc07a43db3b701835a958` passed the required non-Docker and
Chromium closeout gates. R7 integrated acceptance passed on `df633563490f80346617871ec5640adf99154956` and owner product acceptance is accepted. C1.5R is complete. C1.6 is Next and not started; C1.6B remains Conditional.
