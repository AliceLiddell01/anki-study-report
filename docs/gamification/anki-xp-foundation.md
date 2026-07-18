# Anki XP domain status foundation

## Purpose

This document records the status and boundaries of Anki-related XP domains
after selective recovery. It intentionally contains no new reward formula,
coefficient, threshold, cap, level curve, streak or Momentum rule.

## Frozen provenance

Historical source: `48298d02c6871df0ffa112d862d9b2af629c523f:docs/gamification/anki-xp-foundation.md`.

The historical foundation was not promoted verbatim because it mixed a
developed Review candidate with Learn/Create domains that were not started and
with cross-domain economy concepts deferred to G4.

## Domain status

| Domain | Status | Canonical detail |
| --- | --- | --- |
| Review XP | `RECOVERED_UNVERIFIED` research candidate | [Event taxonomy](anki-review-event-taxonomy.md), [reward model](anki-review-reward-model.md), [abuse model](anki-review-abuse-model.md), [session/day aggregation](anki-review-session-and-day.md), [simulation specification](anki-review-simulation-spec.md) |
| Learn XP | `NOT_STARTED` | G2, after Review evidence gates |
| Create XP | `NOT_STARTED` | G3, after Learn methodology |
| Global conversion/economy | `DEFERRED_TO_G4` | Requires accepted Review/Learn/Create candidates |

## Review XP — recovered candidate

Review event classification and reward semantics are defined only in the
linked detailed Review documents. This foundation does not duplicate or alter
their formulas. Historical numerical results were not reproduced in G0.4.

## Learn XP — not started

No Learn XP taxonomy, formula, simulation candidate or evidence baseline is
accepted by this document.

## Create XP — not started

No Create XP taxonomy, formula, simulation candidate or evidence baseline is
accepted by this document.

## Global conversion and economy — deferred to G4

Level progression, cross-domain conversion, productive-day scale, streak,
Momentum, planned rest, Streak Guard and recovery behavior remain outside the
Review-only G0.4 recovery. The historical `progression-foundation.md` was not
imported.

## Evidence status

`NOT_REPRODUCED`

Recovery verifies source provenance and target placement only. G0.5–G0.7 must
establish environment, functional behavior and reproduced evidence.

## Production boundary

No XP domain is approved for production storage, API, migrations, UI,
telemetry or package integration.

## Source precedence

Detailed Review specifications and later reproduced evidence override broad
historical foundation wording. Historical reports remain archive material.
