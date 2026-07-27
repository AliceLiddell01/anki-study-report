# Learn XP confirmatory protocol — G2.5

**Stage:** `G2.5 — Confirmatory evidence`
**Protocol ID:** `learn-xp-confirmatory-protocol`
**Version:** `1`
**Status:** `FROZEN_PRE_RESULTS`
**Results accessed:** `NO`
**Production integration:** `PROHIBITED`

## Цель

G2.5 независимо проверяет каждого из двух family-local survivors G2.4 на fresh confirmatory conditions. Этап не повторяет screening, не возвращает отклонённые варианты, не ищет новые ratios/delays/subject strategies и не выбирает winner между families.

Допустимые outcomes каждого survivor:

```text
CONFIRMATORY_ELIGIBLE
CONFIRMATORY_NOT_ELIGIBLE
CONFIRMATORY_INCONCLUSIVE
```

Reference получает только `REFERENCE_ONLY`.

## Evidence continuity G2.4

Canonical run разрешён только после независимой проверки exact raw bundles:

```text
valid implementation: 548b27de6283b32fb27541db02ce6c8b65c29756
valid bundle SHA-256: a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78
evidence.json SHA-256: d0d79802f8512fa40730aac5c377d75021ff39100330483a784c43ce20b09462
manifest digest: fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a
evidence digest: 5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6

invalid implementation: ef7c638a70b7bbb7883f512309a1e248118a9203
invalid bundle SHA-256: 58989ea862be86e2edb0c71b19aec520214af7bb0abe08791d7f72396d66b2c3
invalid evidence digest: 51ef8d8caa55a2579795a72f5af1576da69da224a5023190d5fde6c145aac726
classification: HARNESS
```

Fail-closed classification for a missing, damaged, mixed or non-reproducible source bundle is `EVIDENCE_CONTINUITY`; canonical G2.5 outcomes are then not assigned.

## Frozen variants and reference

```text
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
C-PENDING-SPLIT-D1-NOTE-SIBLING
R-NO-LEARN-XP-NOTE-SIBLING
```

No D2, `S-CARD`, alternative ratio, delay, subject strategy or rescue candidate is present.

## Exact fresh matrix

```text
identities: 3
condition groups per identity: 36
CORE_ROBUSTNESS: 16
IDENTITY_COMPATIBILITY: 12
EXPLAINABILITY_OBSERVABILITY: 8
replay identities: FORWARD, REVERSE
replica: 0
seed: null
expected / unique units: 216 / 216
adaptive units: 0
```

Unit identity is canonical SHA-256 over protocol version, candidate/reference ID, condition group and ID, identity evidence mode, replay identity, replica, null seed and source G2.4 evidence digest. Absolute paths and execution order are excluded.

## Core robustness

The frozen registry covers:

- D1 minimum `1439/1440` and Anki-day `0/1` boundaries;
- expiry `10079/10080` and day `6/7` boundaries;
- failed retrieval and later independent success;
- Again/retry loops and same-chain Good/Easy;
- reset before/after confirmation;
- undo/cancel/invalidate terminal void;
- empty, one-step, multi-step and interday route equivalence;
- filtered deck, session split and Anki-day routing;
- reverse/cloze/template sibling proliferation.

Displayed intervals, scheduler states and answer buttons are not interpreted as a direct XP timer or button price.

## Identity evidence

Frozen mode:

```text
SYNTHETIC_CONTRACT_ONLY
```

A disposable Anki runtime probe is unavailable in the current bounded execution environment. The twelve typed synthetic identity conditions still verify deterministic grouping, distinct-note separation, stable non-content operations and fail-closed ambiguity. They do not constitute runtime-compatible Anki identity evidence.

Therefore `GATE-NOTE-SIBLING-IDENTITY-CONTINUITY` has required evidence missing for both survivors and must produce `CONFIRMATORY_INCONCLUSIVE` unless a prospectively frozen disposable Anki probe is actually available before result access. It must never be represented as `PASS` from contract-only evidence.

No real collection, note fields, card text, media, profile path or raw revlog may be accessed.

## Explainability contract

Every unit records:

```text
state_code
allocation_code
provisional_lru
confirmed_lru
settled_total_lru
window_code
reason_codes
subject_strategy
identity_continuity_code
claim_boundary_code
```

Forbidden claims include `learned`, `mastered`, `retention improved`, `motivation improved`, `optimal` and `production-ready`.

## Hypotheses and hard gates

The machine protocol freezes five hypotheses:

```text
H-CONFIRMATION-ONLY-ROBUSTNESS
H-PENDING-SPLIT-ROBUSTNESS
H-NOTE-SIBLING-IDENTITY-CONTINUITY
H-EXPLANATION-BOUNDARY
H-G2-4-EVIDENCE-CONTINUITY
```

Thirty non-compensable gates cover G2.1–G2.4 continuity, exact manifest/fresh conditions/reference zero, D1 boundaries, confirmation/pending/terminal invariants, configuration/session/identity/privacy/explanation boundaries, deterministic replay, evidence completeness, bundle reproduction and research/production boundaries.

Outcome semantics:

```text
complete evidence + all required gates pass -> CONFIRMATORY_ELIGIBLE
complete evidence + any required gate fails -> CONFIRMATORY_NOT_ELIGIBLE
missing required evidence -> CONFIRMATORY_INCONCLUSIVE
reference -> REFERENCE_ONLY
```

No aggregate score exists.

## Metrics and contrast boundary

Fourteen metrics are descriptive only. A cross-family contrast ledger may report provisional exposure, active pending state, confirmation settlement, terminal behavior, explanation field count, identity mode, gate outcome and evidence completeness.

The ledger has no winner, weighted score, ranking, lexicographic selection or recommendation.

## Publication and amendment policy

Before result access, the remote publication commit must contain this document, the machine protocol and schemas, exact manifest generator, harness, detached validator, CLI and focused tests. Canonical execution is prohibited until focused checks and one full research suite pass on that source state and local/remote publication SHA equality is confirmed.

After result access, a substantive defect requires disclosed invalidation, a new publication as applicable, complete rerun of all 216 units and old/new evidence isolation. Typographical or status-only documentation corrections do not change machine semantics.

## Claims and production boundary

`CONFIRMATORY_ELIGIBLE` would mean only that a survivor passed the prospectively frozen synthetic, identity and explanation gates and may be considered by a separate final G2 decision stage.

G2.5 performs no ranking, selects no final Learn XP model, approves no production amount and changes no add-on, dashboard, API, scheduler, FSRS, database, workflow, package or release surface.
