# Card payload alias audit

Снимок: 2026-07-06.

Этот документ фиксирует, где используются canonical `attentionCards`, оставшиеся
legacy fallback aliases `cards` / `cardIssues`, и удаленный в Stage 9 alias
`problemCards`. Это не removal plan и не изменение runtime behavior.

## Current contract

- Backend canonical output: `attentionCards`, `attentionCardsStatus`,
  `noteTypeCatalog`.
- Frontend priority after Stage 9:

```text
attentionCards > cards > cardIssues
```

- `attentionCards: []` is explicit canonical empty result and does not fall back
  to legacy aliases.
- `cards` and `cardIssues` remain compatibility fallback.
- Top-level `problemCards` payload alias was removed in Stage 9. Derived
  `summary.problemCards` UI counts are not payload alias support.

## Audit summary

| Alias/key | Current role | Producers found | Consumers found | Fixtures/tests | Docs mentions | Removal readiness |
| --- | --- | --- | --- | --- | --- | --- |
| `attentionCards` | Canonical card-level payload key | Yes: `dashboard_payload.py` emits it from internal `attention_cards`; default dashboard overlay and `metrics.py` produce internal `attention_cards`. | Yes: `cardAttention.ts`, `CardsPage`, `mockReport`, Docker browser/API smokes. | Backend contract tests, frontend normalizer/UI tests, mockReport canonical data, Docker API smoke helper tests. | Public API/docs, architecture, frontend map, troubleshooting, payload examples, legacy inventory. | Keep. |
| `cards` | Legacy fallback alias; also a very noisy normal word | No backend producer for top-level `cards` found. | Yes: `cardAttention.ts`; Docker browser/API smokes keep it as fallback after `attentionCards`. | Compatibility tests in `cardAttention.test.ts`; Docker API smoke helper tests; no JSON dashboard fixtures. | Public compatibility docs and inventory. | Not first; highest ambiguity and possible old payload risk. |
| `cardIssues` | Legacy fallback alias | No backend producer found. | Yes: `cardAttention.ts`; Docker API helper keeps it as fallback after `attentionCards` and `cards`. | Compatibility tests in `cardAttention.test.ts`; Docker API smoke helper tests; backend tests assert it is absent from generated payload. | Public compatibility docs and inventory. | Next runtime removal candidate. |
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
`problemCards` was found in `anki_study_report/` or backend tests. Stage 4
backend tests also assert `cardIssues` and `problemCards` are absent from
backend-generated payload; `cards` is absent in the same canonical-output test.

### Frontend consumers

`web-dashboard/src/lib/cardAttention.ts` is the intentional compatibility
consumer. It reads the first array among:

```text
attentionCards
cards
cardIssues
```

This means `attentionCards: []` is a real selected source and prevents fallback
to legacy arrays.

`web-dashboard/src/types/report.ts` keeps optional legacy alias fields for
`cards` and `cardIssues` in `StudyReport` and comments that `attentionCards` is
canonical. The optional top-level `problemCards` field was removed in Stage 9.

`web-dashboard/src/pages/CardsPage.tsx` consumes normalized rows from
`buildCardAttentionRows(report)`; its `summary.problemCards` is a derived UI KPI
name, not the top-level legacy payload alias.

### Tests and fixtures

Current coverage:

- `web-dashboard/src/lib/cardAttention.test.ts` covers canonical-only,
  remaining legacy-only aliases, mixed canonical-first priority, legacy fallback
  order, negative `problemCards` coverage, snake_case row normalization, and
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
cardIssues
```

For API smoke, `attentionCards: []` is an explicit canonical empty result and
does not fall back to legacy aliases. Stage 9 removed `problemCards` from the
API smoke fallback list. The Docker smoke helpers are compatibility QA helpers,
not backend producers.

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
| `cardIssues` | No. | Still supported by `cardAttention.ts`, TS type, compatibility tests, Docker API fallback, public docs. | Remove from `cardAttention.ts`, remove from `StudyReport`, remove or rewrite `cardIssues` test cases, drop Docker API fallback, update `dashboard-api`, `frontend-map`, inventory/audit. Keep canonical and `cards` fallback tests. | Next. |
| `cards` | No. | Most ambiguous name; may exist in old manual payload samples or external scripts, and broad search has heavy unrelated noise. | Keep until last; add a deprecation note first, drop QA helper fallback at its removal stage, and run broad UI/API smoke after removal. | Last. |

## Recommended next steps

1. Keep all aliases through at least one canonical-first release.
2. Remove `cardIssues` next if cleanup continues.
3. Keep `cards` until the final explicit removal stage because it is the most
   ambiguous alias.
4. Preserve tests for `attentionCards`, empty canonical `attentionCards: []`,
   and at least one remaining legacy fallback until all aliases are removed.
5. After the last alias is removed, update `StudyReport`, `dashboard-api`,
   `frontend-map`, `troubleshooting`, `legacy-cleanup-inventory`, and this
   audit together.
