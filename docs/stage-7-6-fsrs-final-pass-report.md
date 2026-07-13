# FSRS final UX/visual pass

Status: COMPLETE

## Scope

This pass closes the two confirmed shared-shell visual regressions left after the
FSRS visual delivery work. It does not add analytics, change FSRS formulas,
modify the typed payload, alter cache identity, or weaken read-only semantics.

The existing successful Stage 7.5 full run `29238747588` on functional SHA
`2c2ee56` was used as the visual baseline. No duplicate baseline run was
started.

Functional acceptance SHA: `5103ad66ea59358b811b04e22bd976277f2ec57b`.

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

The baseline and accepted artifacts cover:

- FSRS Overview: default and mixed-configuration presentation;
- Memory State: snapshot presentation;
- Model Accuracy: idle and sparse-ready presentation;
- Learning Steps: insufficient-sample presentation;
- Simulator: idle form and ready comparison;
- all five neighbouring Statistics routes;
- light and dark themes;
- desktop widths `989` and `1265`;
- 100% and 125% E2E zoom profiles.

No additional user-visible English/debug copy requiring a product-code change
was found in the reviewed rendered states. Existing terminology, units and
read-only wording were preserved rather than cosmetically rewritten.

## Regression coverage

`FsrsVisualContract.test.tsx` verifies that:

- every FSRS subroute renders the shared Statistics sidebar and header surface;
- the sidebar correction uses an internal inset and explicit icon reset;
- the correction does not rely on `overflow: hidden`;
- the FSRS-only pseudo-element is disabled;
- no replacement radial/blob styling is introduced in the correction layer.

The real-Anki `fsrs-visual-contract.mjs` browser gate checks 80 combinations:
10 Statistics/FSRS routes, two themes, widths `989` and `1265`, and 100%/125%
profiles. The accepted full artifact recorded:

- `80/80` successful geometry checks;
- `40/40` FSRS checks with `content: none`, `display: none`, and no pseudo-element
  background image;
- minimum icon-to-sidebar inset of `23.5 px`;
- preserved rounded sidebar and shared header surface;
- zero contract console, page, and request errors.

The canonical browser smoke retained all existing routes and states and
produced 86 unique screenshots:

- 40 light/dark page captures;
- 22 state captures;
- 10 125% captures;
- 12 Cards captures;
- 2 navigation captures.

No screenshot path was missing or duplicated.

## Intentionally unchanged

- backend FSRS formulas and native Anki calculation source;
- `StudyReport.statisticsHub.fsrs` and `/api/statistics/fsrs/query` contracts;
- manual execution of heavy calibration and simulator operations;
- configuration grouping and the rule against averaging incompatible presets;
- lazy route boundaries and the 500 kB production chunk guard;
- token/security model and Anki configuration;
- established screenshot routes, states and browser error aggregation.

The accepted packaged FSRS lazy chunk was `48,890` bytes, below the 500 kB
guard.

## Cloud verification

| Gate | SHA | Result |
| --- | --- | --- |
| Existing Stage 7.5 baseline | `2c2ee56` | PASS — run `29238747588`, 86 unique screenshots |
| Fast CI after visual implementation | `438d68d3` | PASS — run `29255190266` |
| Initial targeted `standard/stats` | `438d68d3` | PASS — run `29255538234`; artifact review identified the missing explicit browser geometry gate |
| Fast CI with browser geometry gate | `5103ad66` | PASS — run `29256612779` |
| Accepted targeted `standard/stats` | `5103ad66` | PASS — run `29256992831`, job `86840316129` |
| Accepted final `standard/full` | `5103ad66` | PASS — run `29257634244`, job `86842098050` |

The final full run used Anki `26.05`, scope `full`, three screenshot workers,
resource telemetry, and restart verification. It completed successfully in
262 seconds. The browser report contained zero console errors, page errors, or
actionable request failures, and both initial and restart API smokes passed.

Earlier Fast CI attempts failed while the new CSS contract test was being wired
into the browser-only TypeScript project. Those failures were test-harness
issues rather than product regressions. The accepted implementation keeps Node
access local to the test and preserves frontend type checking without
`skipLibCheck`, test exclusion, or global Node types in production code.

No local Docker run was performed because the cloud real-Anki contour is the
acceptance gate and duplicating a successful exact-SHA run would add no evidence.

## Remaining limitations

- The acceptance matrix is intentionally desktop-focused; mobile and very narrow
  responsive layouts are outside this stage.
- The 125% profile is the canonical E2E scaling contour, not an exhaustive sweep
  of operating-system display scaling combinations.
- The closure report is a docs-only commit after the accepted functional SHA;
  it does not require another Docker E2E run.