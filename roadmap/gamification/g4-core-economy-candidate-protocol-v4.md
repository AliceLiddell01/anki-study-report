# G4.3 v4 — replacement pre-screening republication

## Статус

```text
G4: IN PROGRESS
G4.1: COMPLETE
G4.2: COMPLETE
G4.3: COMPLETE
G4.3 v1: SUPERSEDED_PRE_EXECUTION
G4.3 v1 results: NOT_AVAILABLE
G4.3 v2: SUPERSEDED_PRE_EXECUTION
G4.3 v2 results: NOT_AVAILABLE
G4.3 v3: INVALIDATED_AFTER_SUBSTANTIVE_DEFECT
G4.3 v3 results: INVALIDATED_NOT_DECISION_EVIDENCE
G4.3 v4: FROZEN_PRE_SCREENING
G4.4: ACTIVATED_AFTER_PUBLICATION_CHECKPOINT
screening: NOT STARTED
results: NOT_AVAILABLE
production integration: PROHIBITED
```

## Назначение

v4 заменяет invalidated v3 после первого result access:

- row-local linkage каждого gate со всеми required metrics;
- exact abrupt-control expected outcomes по фактическим uncertainty-bearing events;
- marginal probes ниже combined boundary, если scenario сам не насыщает control;
- immutable v1/v2/v3 identities и явный invalidation ledger.

Machine и human contract: [core-economy-candidate-protocol-v4.md](../../docs/gamification/core-economy-candidate-protocol-v4.md).

## Frozen inventory

```text
candidates: 19
bundles: 21
hypotheses: 20
hard gates: 30
metrics: 22
pipeline steps: 17
scenarios: 52
matrix rows: 1275
negative samples: 18
personas / threats / invariants: 9 / 14 / 28
```

## Frozen digests

```text
protocol: a6f8faf819e7d4a7c3d5ffd73ad82775642020faa019584b823e20ad3f2b18cd
pipeline: f49169b3e91e04e781819bea33b5c86778b981e17a27c954b0ed7295b387af62
scenarios: fabd2cb9934953987cf6b64a6e34d070c3c1d26ef2d4f21641cfe5649cf6443d
matrix: 6c640a17643ac83c09fe56276072930152baa07f46147ab76c36b7f2b8160f67
validator: core-economy-protocol-v4-validator-1
generator: core-economy-protocol-v4-generator-1
```

## Evidence firewall

Publication commit должен быть создан после focused pre-screening checks. До него:

```text
candidate result rows: PROHIBITED
screening execution: PROHIBITED
winner analysis: PROHIBITED
threshold changes from results: PROHIBITED
```

После publication commit owner prompt активирует G4.4 без дополнительного вопроса. Каждый result artifact обязан ссылаться на exact publication SHA и digests выше. Substantive protocol mutation после result access требует новой versioned republication.

## Production boundary

Production runtime, dashboard, API, scheduler, FSRS, due dates, collection, package, workflow, release и deployment не входят в scope. G5 и G6 не начаты.
