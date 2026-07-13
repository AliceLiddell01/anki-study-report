# FSRS final UX/visual pass

Status: implementation complete; cloud acceptance pending.

## Scope

This pass closes the two confirmed shared-shell visual regressions left after the
FSRS visual delivery work. It does not add analytics, change FSRS formulas,
modify the typed payload, alter cache identity, or weaken read-only semantics.

The existing successful Stage 7.5 full run `29238747588` on functional SHA
`2c2ee56` was used as the visual baseline. No duplicate baseline run was
started.

## Confirmed defects and root causes

### Statistics sidebar icon geometry

The sidebar card had a narrow content inset while its heading used a separate
padding rule. The icon itself had no explicit reset protecting it from offsets
and box-model changes. In the captured Statistics/FSRS surfaces this made the
icon appear too close to, and at some widths visually beyond, the rounded card
boundary.

The correction is shared by all Statistics routes:

- a named internal content inset is defined on `.statistics-sidebar`;
- `.statistics-sidebar-heading` uses that inset;
- heading text is allowed to shrink without pushing the icon;
- the icon uses border-box sizing with zero margin and no transform;
- the sidebar is not hidden with global overflow clipping, so focus outlines
  remain available.

### FSRS header decoration

The large translucent spot was produced by the FSRS-only
`.fsrs-hero::after` pseudo-element. It was not part of the shared Statistics
header language and appeared on all five FSRS routes.

The pseudo-element is disabled and the hero returns to the shared
`.statistics-page-surface` background. No decoration was added to neighbouring
Statistics pages, and no empty clipping layer remains.

## Routes and states reviewed

The baseline artifacts and current implementation were checked for:

- FSRS Overview: normal, mixed configuration and sparse presentation;
- Memory State: snapshot, distributions and table alternatives;
- Model Accuracy: idle, loading and sparse ready presentation;
- Learning Steps: insufficient sample and expanded preset wording;
- Simulator: idle form and ready comparison;
- light and dark themes;
- the existing desktop and 125% capture contour.

No additional user-visible English/debug copy requiring a product-code change
was found in the reviewed rendered states. Existing terminology, units and
read-only wording were therefore preserved rather than cosmetically rewritten.

## Regression coverage

`FsrsVisualContract.test.tsx` now verifies that:

- every FSRS subroute renders the shared Statistics sidebar and header surface;
- the sidebar correction uses an internal inset and explicit icon reset;
- the correction does not rely on `overflow: hidden`;
- the FSRS-only pseudo-element is disabled;
- no replacement radial/blob styling is introduced in the correction layer.

The real-Anki E2E contour continues to capture all five FSRS routes, light/dark
state screenshots, 125% screenshots, horizontal-overflow diagnostics and
browser console/page/request failures. The final targeted and full runs must
confirm the corrected pixels and preserve at least the existing 86-entry full
screenshot manifest.

## Intentionally unchanged

- backend FSRS formulas and native Anki calculation source;
- `StudyReport.statisticsHub.fsrs` and `/api/statistics/fsrs/query` contracts;
- manual execution of heavy calibration and simulator operations;
- configuration grouping and the rule against averaging incompatible presets;
- lazy route boundaries and the 500 kB production chunk guard;
- token/security model and Anki configuration;
- screenshot routes, states and browser error aggregation.

## Verification

| Gate | Result |
| --- | --- |
| Existing Stage 7.5 baseline | PASS — run `29238747588`, 86 unique screenshots, no missing/duplicates |
| Targeted frontend tests/build | pending Fast CI |
| Fast CI exact SHA | pending |
| `standard/stats` | pending manual dispatch after Fast CI |
| `standard/full` | pending manual dispatch after targeted PASS |

No local Docker run is planned because the cloud real-Anki contour is the
acceptance gate and duplicate Docker work is outside the verification budget.

## Remaining limitations

Final screenshot evidence, browser error totals, run IDs and durations remain
pending until the exact functional SHA passes Fast CI, targeted `standard/stats`
and one final `standard/full` run. These results must be added without rerunning
a successful exact-SHA gate.
