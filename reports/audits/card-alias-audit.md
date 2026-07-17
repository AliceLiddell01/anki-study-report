# Card payload alias audit

Снимок: 2026-07-06.

Этот документ фиксирует, где используется canonical `attentionCards`, а также
историю удаления legacy aliases `cards`, `cardIssues` и `problemCards`. Это не
removal plan и не изменение runtime behavior.

## Current contract

- Backend canonical output: `attentionCards`, `attentionCardsStatus`,
  `noteTypeCatalog`.
- Frontend input after Stage 11:

```text
attentionCards
```

- `attentionCards: []` is explicit canonical empty result and does not fall back
  to legacy aliases.
- No legacy top-level card payload aliases remain.
- Top-level `cards` payload alias was removed in Stage 11.
- Top-level `cardIssues` payload alias was removed in Stage 10.
- Top-level `problemCards` payload alias was removed in Stage 9. Derived
  `summary.problemCards` UI counts are not payload alias support.

## Audit summary

| Alias/key | Current role | Producers found | Consumers found | Fixtures/tests | Docs mentions | Removal readiness |
| --- | --- | --- | --- | --- | --- | --- |
| `attentionCards` | Canonical card-level payload key | Yes: `dashboard_payload.py` emits it from internal `attention_cards`; default dashboard overlay and `metrics.py` produce internal `attention_cards`. | Yes: `cardAttention.ts`, `CardsPage`, `mockReport`, Docker browser/API smokes. | Backend contract tests, frontend normalizer/UI tests, mockReport canonical data, Docker API smoke helper tests. | Public API/docs, architecture, frontend map, troubleshooting, payload examples, legacy inventory. | Keep. |
| `cards` | Removed legacy top-level payload alias; also a very noisy normal word | No backend producer for top-level `cards` found. | No current top-level payload alias consumer after Stage 11. | Negative frontend/smoke helper tests assert it is ignored; backend tests assert it is absent from generated payload. No JSON dashboard fixtures. | Historical/removal notes only. | Removed in Stage 11. |
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

`web-dashboard/src/lib/cardAttention.ts` reads the canonical array:

```text
attentionCards
```

This means `attentionCards: []` is a real selected source. If `attentionCards`
is absent, the frontend returns its stable no-source/empty behavior and does not
fall back to removed aliases.

`web-dashboard/src/types/report.ts` keeps only canonical `attentionCards` for
card-level rows. The optional top-level `problemCards`, `cardIssues`, and
`cards` fields were removed in Stage 9, Stage 10, and Stage 11.

`web-dashboard/src/pages/CardsPage.tsx` consumes normalized rows from
`buildCardAttentionRows(report)`; its `summary.problemCards` is a derived UI KPI
name, not the top-level legacy payload alias.

### Tests and fixtures

Current coverage:

- `web-dashboard/src/lib/cardAttention.test.ts` covers canonical-only,
  mixed canonical-plus-removed-alias priority, negative `cards`, `problemCards`,
  and `cardIssues` coverage, snake_case row normalization, and empty canonical
  behavior.
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

After Stage 11, Docker browser/API smoke uses canonical `attentionCards` only.

`docker/anki-e2e/smoke-browser.mjs` reads `attentionCards` for APKG checks.

`docker/anki-e2e/smoke-api.py` accepts card rows in this order:

```text
attentionCards
```

For API smoke, `attentionCards: []` is an explicit canonical empty result and
does not fall back to legacy aliases. Stage 9 removed `problemCards` from the
API smoke fallback list; Stage 10 removed `cardIssues`; Stage 11 removed
`cards`. The Docker smoke helpers are QA helpers, not backend producers.

### Docs

Current docs that mention aliases:

- `docs/dashboard-api.md`: public canonical card-level contract.
- `docs/frontend-map.md`: frontend map for canonical `attentionCards`.
- `docs/troubleshooting.md`: debugging note for canonical normalizer input.
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
| `cardIssues` | Removed. | None for top-level payload input after Stage 10. | Keep negative frontend/smoke tests and backend absence assertions while nearby code evolves. | Done in Stage 10. |
| `cards` | Removed. | None for top-level payload input after Stage 11. The word remains common in non-alias contexts. | Keep negative frontend/smoke tests and backend absence assertions until the cleanup line settles. | Done in Stage 11. |

## Recommended next steps

1. No legacy card payload aliases remain.
2. Preserve tests for `attentionCards`, empty canonical `attentionCards: []`,
   and removed-alias negative coverage for a while.
3. Future legacy cleanup should focus on cache/report/fallback/dashboard layers,
   not card payload aliases.
