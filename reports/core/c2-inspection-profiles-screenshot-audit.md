# C2 Inspection Profiles — corrected screenshot-first audit

**Date:** 2026-07-27
**PR:** `#130`
**Branch:** `c2-manual-acceptance-remediation`
**Production capture SHA:** `ce45194e659aeba43f05a2b13cbf6f0583e601aa`
**Scope:** evidence correction and owner-target audit only; no Profiles implementation

## Purpose

The previous evidence package used several same-state labels for captures that had different identities or different interaction models. This audit rebuilds the matrix before any Inspection Profiles production work.

## Direct comparison contract

A pair is classified as direct only when these values match:

```text
note-type identity
editor mode
validation/draft state
viewport
locale
color scheme
```

The controlled committed-fixture identities are `Слова` and `Java`. They are evidence identities, not a claim about the owner's private collection.

## Direct pairs

| Identity | Mode/state | Theme/viewport | Result |
| --- | --- | --- | --- |
| Слова | Basic ready | light, 1440×900 | comparable; production composition materially differs |
| Слова | Basic ready | dark, 1440×900 | comparable; production composition materially differs |
| Java | Basic ready | light/dark, 1440×900 | comparable |
| Java | Advanced ready | light/dark, 1440×900 | comparable; production editor is substantially more vertical |
| Слова | Basic validation error | dark, 1440×900 | same identity and error intent; layout differs |
| Java | Basic tabs focus | dark, 1440×900 | comparable focus contour |
| Java | Advanced | light, 2560×1440 | comparable; production underuses available width |

## Intentional differences

These captures are explicitly not used as literal 1:1 proof:

- dirty state: Prototype inline messaging versus production confirmation modal;
- `1024` navigation: Prototype overflow menu versus production persistent sidebar;
- route target: Prototype inline demonstration versus real production navigation;
- production language selector: production-only control, not a Settings-navigation equivalent.

## Findings

Confirmed from valid direct pairs:

- the prior `Копия Основная ↔ Java` identity mismatch is removed;
- production Basic and Advanced are functional but remain a different composition from Prototype;
- production uses a wider Settings sidebar and a long vertical editor instead of the compact three-column target;
- QHD space utilization remains substantially lower than Prototype;
- validation and dirty-state semantics require an explicit owner decision before implementation;
- `1024` navigation is an IA difference rather than a same-state visual drift.

## Verdict

```text
Inspection Profiles screenshot-first coverage: COMPLETE
Evidence identity/state validity: PASS after correction
Prototype ↔ production visual parity: REVISE / OWNER TARGET DECISION REQUIRED
Inspection Profiles implementation: NOT STARTED
Inspection Profiles owner acceptance: NOT READY
```

No Profiles source code, API, payload, validation behavior or shared Settings shell was modified by this audit.

## Evidence

```text
cards-visual-parity-and-profiles-audit-evidence.zip
SHA-256: e2c1d35bb12088ad0d285371514789637be60025050f5a8ded6307048c6dd2da
files: 121
manifest content files: 119
SHA256SUMS entries: 120
self-verification: PASS
page errors: 0
console errors: 0
```

## Next owner decision

The next action is not implementation by default. The owner must decide whether Prototype's compact three-column composition, inline draft model and overflow navigation remain the exact target, or which production differences are intentionally retained.
