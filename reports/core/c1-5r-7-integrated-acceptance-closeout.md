# C1.5R.7 — Integrated acceptance closeout

**Date:** 2026-07-21
**Target branch:** `core`
**PR:** #55
**Accepted candidate:** `df633563490f80346617871ec5640adf99154956`
**Core base included:** `4e71de18d7a370a1ebc182290894e0b5c4975502`
**Owner decision:** Accepted

## Result

C1.5R.7 is complete. The integrated R1–R6 product contour passed the required
focused, canonical non-Docker and clean full real-Anki acceptance gates. Owner
product acceptance is recorded as accepted.

C1.6 and C1.6B were not implemented. C1.6 is Next and not started. C1.6B
remains Conditional.

## Corrections closed during acceptance

Two E2E harness scope mismatches were corrected without changing production
behavior or public payloads:

1. `smoke-api.py` now runs the Inspection Profiles contract for both `cards`
   and `full`.
2. `restart-anki.sh` now performs the deterministic Inspection Profiles
   structure mutation for both `cards` and `full`.

Regression coverage was added in `tests/test_docker_smoke_helpers.py`.

## Verification

| Gate | Result |
| --- | --- |
| focused Docker smoke helpers | PASS — 30 tests |
| canonical non-Docker | PASS — 318 frontend tests; 796 Python tests |
| TypeScript / production bundle | PASS |
| package build and validation | PASS — 74 archive entries |
| clean full real-Anki E2E | PASS — Anki 26.05 |
| first API smoke | PASS |
| browser smoke | PASS |
| FSRS visual contract | PASS — 80 route/theme/profile combinations |
| restart API smoke | PASS |
| structured artifact manifest | PASS — 50 page, 2 navigation, 4 synthetic Cards, 1 APKG Cards screenshots |
| repository worktree after verification | clean |
| candidate push | PASS |

The local WSL Docker bridge could not reach package repositories during image
build. The image was therefore built once with BuildKit host networking; the
actual real-Anki E2E ran through the canonical Compose runtime network. This was
an environment workaround only and did not alter repository code or runtime
test scope.

## Retained historical evidence

The earlier cloud acceptance run remains historical evidence:

- run `29828336280`;
- package artifact `8494243010`;
- provenance artifact `8494242618`;
- targeted Cards artifact `8494293447`;
- full artifact `8494328398`.

That run exposed the full-scope Inspection Profiles harness defect. The final
accepted candidate is the later local verified SHA above.

## Cleanup boundary

PR #55 removes the temporary R7 workflows and package/acceptance helper scripts.
Disposable `c1-5r-7-*` remote branches are deleted only after PR #55 merges into
`core`, using an explicit SHA-checked allowlist.

## Explicit exclusions

- no merge to `master`;
- no release, tag, deployment, GitHub Release or AnkiWeb publication;
- no C1.6 implementation;
- no C1.6B activation;
- no committed E2E artifacts, logs, screenshots, profiles or `.ankiaddon`.
