# Card payload alias audit

Снимок: 2026-07-06.

Этот документ фиксирует, где используются canonical `attentionCards` и legacy
fallback aliases `cards`, `cardIssues`, `problemCards`. Это не removal plan и не
изменение runtime behavior.

## Current contract

- Backend canonical output: `attentionCards`, `attentionCardsStatus`,
  `noteTypeCatalog`.
- Frontend priority after Stage 5:

```text
attentionCards > cards > cardIssues > problemCards
```

- `attentionCards: []` is explicit canonical empty result and does not fall back
  to legacy aliases.
- Legacy aliases remain compatibility fallback.

## Audit summary

| Alias/key | Current role | Producers found | Consumers found | Fixtures/tests | Docs mentions | Removal readiness |
| --- | --- | --- | --- | --- | --- | --- |
| `attentionCards` | Canonical card-level payload key | Yes: `dashboard_payload.py` emits it from internal `attention_cards`; default dashboard overlay and `metrics.py` produce internal `attention_cards`. | Yes: `cardAttention.ts`, `CardsPage`, `mockReport`, Docker browser/API smokes. | Backend contract tests, frontend normalizer/UI tests, mockReport canonical data. | Public API/docs, architecture, frontend map, troubleshooting, payload examples, legacy inventory. | Keep. |
| `cards` | Legacy fallback alias; also a very noisy normal word | No backend producer for top-level `cards` found. | Yes: `cardAttention.ts`, Docker API helper; Docker browser helper checks `attentionCards` then `cards`. | Compatibility tests in `cardAttention.test.ts`; no JSON dashboard fixtures. | Public compatibility docs and inventory. | Not first; highest ambiguity and possible old payload risk. |
| `cardIssues` | Legacy fallback alias | No backend producer found. | Yes: `cardAttention.ts`, Docker API helper. | Compatibility tests in `cardAttention.test.ts`; backend tests assert it is absent from generated payload. | Public compatibility docs and inventory. | Candidate after `problemCards`. |
| `problemCards` | Legacy fallback alias; also UI KPI name in normalized summary | No backend producer for top-level `problemCards` found. | Yes: `cardAttention.ts`, Docker API helper. | Compatibility tests in `cardAttention.test.ts`; backend tests assert it is absent from generated payload. | Public compatibility docs and inventory. | Best first removal candidate, after deprecation docs/tests update. |

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
problemCards
```

This means `attentionCards: []` is a real selected source and prevents fallback
to legacy arrays.

`web-dashboard/src/types/report.ts` keeps optional legacy alias fields in
`StudyReport` and comments that `attentionCards` is canonical.

`web-dashboard/src/pages/CardsPage.tsx` consumes normalized rows from
`buildCardAttentionRows(report)`; its `summary.problemCards` is a derived UI KPI
name, not the top-level legacy payload alias.

### Tests and fixtures

Current coverage:

- `web-dashboard/src/lib/cardAttention.test.ts` covers canonical-only,
  legacy-only aliases, mixed canonical-first priority, legacy fallback order,
  snake_case row normalization, and empty canonical behavior.
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

The old Tampermonkey manual QA helper was removed in Stage 7 because Docker
E2E/browser/API smoke is now the supported QA path.

`docker/anki-e2e/smoke-browser.mjs` is mostly canonical-first for APKG checks:
it reads `attentionCards` first and only then `cards`.

`docker/anki-e2e/smoke-api.py` still accepts all aliases in this order:

```text
cards
attentionCards
cardIssues
problemCards
```

The Docker smoke helpers are compatibility QA helpers, not backend producers.
Before removing any alias, update these helper checks or intentionally keep them
as external-old-payload probes.

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
| `problemCards` | No. | Still supported by `cardAttention.ts`, TS type, compatibility tests, Docker API helper, public docs. | Remove or rewrite `problemCards` test cases, update `StudyReport`, `dashboard-api`, `frontend-map`, inventory/audit, QA helpers. Keep canonical and other legacy alias tests. | First staged removal candidate. |
| `cardIssues` | No. | Same as `problemCards`, but semantically closer to issue rows and may be more plausible in old payload samples. | Same as above, after `problemCards` is gone and a release has carried the deprecation. | Second. |
| `cards` | No. | Most ambiguous name; may exist in old manual payload samples or external scripts, and broad search has heavy unrelated noise. | Keep until last; add a deprecation note first, update QA helpers, and run broad UI/API smoke after removal. | Last. |

## Recommended next steps

1. Keep all aliases through at least one canonical-first release.
2. If cleanup continues, deprecate `problemCards` first in docs and QA helpers
   before deleting runtime support.
3. Update `docker/anki-e2e/smoke-api.py` to canonical-first before any removal
   stage, or document that it intentionally tests old external payloads.
4. Preserve tests for `attentionCards`, empty canonical `attentionCards: []`,
   and at least one remaining legacy fallback until all aliases are removed.
5. After the last alias is removed, update `StudyReport`, `dashboard-api`,
   `frontend-map`, `troubleshooting`, `legacy-cleanup-inventory`, and this
   audit together.
