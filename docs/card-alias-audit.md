# Card payload alias audit

Снимок: 2026-07-06.

Этот документ фиксирует, где используются canonical `attentionCards`, оставшийся
legacy fallback alias `cards`, удаленный в Stage 10 alias `cardIssues`, и
удаленный в Stage 9 alias `problemCards`. Это не removal plan и не изменение
runtime behavior.

## Current contract

- Backend canonical output: `attentionCards`, `attentionCardsStatus`,
  `noteTypeCatalog`.
- Frontend priority after Stage 10:

```text
attentionCards > cards
```

- `attentionCards: []` is explicit canonical empty result and does not fall back
  to legacy aliases.
- `cards` remains the only compatibility fallback.
- Top-level `cardIssues` payload alias was removed in Stage 10.
- Top-level `problemCards` payload alias was removed in Stage 9. Derived
  `summary.problemCards` UI counts are not payload alias support.

## Audit summary

| Alias/key | Current role | Producers found | Consumers found | Fixtures/tests | Docs mentions | Removal readiness |
| --- | --- | --- | --- | --- | --- | --- |
| `attentionCards` | Canonical card-level payload key | Yes: `dashboard_payload.py` emits it from internal `attention_cards`; default dashboard overlay and `metrics.py` produce internal `attention_cards`. | Yes: `cardAttention.ts`, `CardsPage`, `mockReport`, Docker browser/API smokes. | Backend contract tests, frontend normalizer/UI tests, mockReport canonical data, Docker API smoke helper tests. | Public API/docs, architecture, frontend map, troubleshooting, payload examples, legacy inventory. | Keep. |
| `cards` | Legacy fallback alias; also a very noisy normal word | No backend producer for top-level `cards` found. | Yes: `cardAttention.ts`; Docker browser/API smokes keep it as fallback after `attentionCards`. | Compatibility tests in `cardAttention.test.ts`; Docker API smoke helper tests; no JSON dashboard fixtures. | Public compatibility docs and inventory. | Not first; highest ambiguity and possible old payload risk. |
| `cardIssues` | Removed legacy top-level payload alias | No backend producer found. | No current top-level payload alias consumer after Stage 10. | Negative frontend/smoke helper tests assert it is ignored; backend tests assert it is absent from generated payload. | Historical/removal notes only. | Removed in Stage 10. |
| `problemCards` | Removed legacy top-level payload alias; also a derived UI KPI name in normalized summary | No backend producer for top-level `problemCards` found. | No current top-level payload alias consumer after Stage 9. `summary.problemCards` remains a derived UI count, not a payload input. | Negative frontend/smoke helper tests assert it is ignored; backend tests assert it is absent from generated payload. | Historical/removal notes only. | Removed in Stage 9. |

## Findings by area

### Backend producers

Backend source currently produces canonical data through internal snake_case
fields and then exports camelCase:

- `anki_study_report/metrics.py` returns internal `attention_cards`,
  `attention_cards_status`, and `note_type_catalog`.
- `anki_study_report/__init__.py` overlays fresh default dashboard rows into
  internal `attention_cards` / `attention_cards_status`.
- `anki_study_report/dashboard_payload.py` emits public `attentionCards`,
  `attentionCardsStatus`, and `noteTypeCatalog`.

No backend producer for top-level public `cards`, `cardIssues`, or
`problemCards` was found in `anki_study_report/` or backend tests. Backend tests
also assert `cardIssues` and `problemCards` are absent from
backend-generated payload; `cards` is absent in the same canonical-output test.

### Frontend consumers

`web-dashboard/src/lib/cardAttention.ts` is the intentional compatibility
consumer. It reads the first array among:

```text
attentionCards
cards
```

This means `attentionCards: []` is a real selected source and prevents fallback
to legacy arrays.

`web-dashboard/src/types/report.ts` keeps optional legacy alias field `cards`
in `StudyReport` and comments that `attentionCards` is canonical. The optional
top-level `problemCards` and `cardIssues` fields were removed in Stage 9 and
Stage 10.

`web-dashboard/src/pages/CardsPage.tsx` consumes normalized rows from
`buildCardAttentionRows(report)`; its `summary.problemCards` is a derived UI KPI
name, not the top-level legacy payload alias.

### Tests and fixtures

Current coverage:

- `web-dashboard/src/lib/cardAttention.test.ts` covers canonical-only,
  the remaining `cards` legacy alias, mixed canonical-first priority, negative
  `problemCards` and `cardIssues` coverage, snake_case row normalization, and
  empty canonical behavior.
- `tests/test_dashboard_payload.py` covers canonical backend output and asserts
  legacy aliases are not emitted.
- `tests/test_attention_cards.py` covers backend collection of internal
  `attention_cards` rows and status.
- `tests/test_default_dashboard_attention_overlay.py` covers default dashboard
  overlay into canonical public payload.
- `tests/test_stats_cache.py` preserves live-only `attentionCards` fields when
  cache parts are merged.

Dashboard JSON fixtures under `tests/fixtures/dashboard/` do not contain
`attentionCards` or legacy aliases. `web-dashboard/src/data/mockReport.ts` uses
canonical `attentionCards` and `attentionCardsStatus`.

### QA and E2E helpers

The old Tampermonkey manual QA helper was removed in Stage 7.

After Stage 8, Docker browser/API smoke follows canonical-first card payload
lookup. Smoke helpers prefer `attentionCards` and keep legacy aliases only as
compatibility fallback while aliases still exist.

`docker/anki-e2e/smoke-browser.mjs` is canonical-first for APKG checks: it reads
`attentionCards` first and only then `cards`.

`docker/anki-e2e/smoke-api.py` accepts card rows in this order:

```text
attentionCards
cards
```

For API smoke, `attentionCards: []` is an explicit canonical empty result and
does not fall back to legacy aliases. Stage 9 removed `problemCards` from the
API smoke fallback list; Stage 10 removed `cardIssues`. The Docker smoke helpers
are compatibility QA helpers, not backend producers.

### Docs

Current docs that mention aliases:

- `docs/dashboard-api.md`: public contract and compatibility fallback note.
- `docs/frontend-map.md`: frontend map for canonical plus fallback aliases.
- `docs/troubleshooting.md`: debugging note for normalizer order.
- `docs/legacy-cleanup-inventory.md`: cleanup inventory and Stage 4/5 coverage.
- `docs/payload-examples.md`: canonical `attentionCards` examples only.
- `docs/architecture.md`: canonical top-level payload shape.
- `docs/fixtures-and-test-data.md`: fixture guidance; no alias-specific fixture.

No stale docs wording was found that still describes the old Stage 4
legacy-first order as current behavior.

### Ambiguous / unrelated `cards` hits

Most `cards` hits are not the legacy top-level alias. Examples:

- Anki collection cards, revlog card ids, deck/card counts.
- `newCards`, `cardsTotal`, `candidateCards`, `fieldScanCards`.
- CSS classes and UI labels such as Cards page, card tiles, card KPI counts.
- `summary.problemCards` from `summarizeCardAttentionRows`, which is a UI metric
  field rather than top-level payload input.

Treat `cards` as legacy only when it is a top-level report key, a normalizer
source key, a test payload key, or an explicit compatibility-doc mention.

## Removal readiness

| Candidate | Can remove now? | Blockers | Required tests/docs before removal | Suggested stage |
| --- | --- | --- | --- | --- |
| `problemCards` | Removed. | None for top-level payload input after Stage 9. | Keep negative frontend/smoke tests and backend absence assertions while nearby aliases remain. | Done in Stage 9. |
| `cardIssues` | Removed. | None for top-level payload input after Stage 10. | Keep negative frontend/smoke tests and backend absence assertions while `cards` remains. | Done in Stage 10. |
| `cards` | No. | Final remaining alias; most ambiguous name; may exist in old manual payload samples or external scripts, and broad search has heavy unrelated noise. | Keep until last; add a deprecation note first, drop QA helper fallback at its removal stage, and run broad UI/API smoke after removal. | Last. |

## Recommended next steps

1. Keep `cards` until the final explicit removal stage because it is the most
   ambiguous alias.
2. Preserve tests for `attentionCards`, empty canonical `attentionCards: []`,
   the remaining `cards` fallback, and removed-alias negative coverage.
3. After the last alias is removed, update `StudyReport`, `dashboard-api`,
   `frontend-map`, `troubleshooting`, `legacy-cleanup-inventory`, and this
   audit together.
