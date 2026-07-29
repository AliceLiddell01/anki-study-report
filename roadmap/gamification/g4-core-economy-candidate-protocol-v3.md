# G4.3 v3 — pre-screening republication

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
G4.3 v3: FROZEN_PRE_SCREENING
G4.4: ACTIVATED_AFTER_PUBLICATION_CHECKPOINT
screening: NOT STARTED
results: NOT_AVAILABLE
production integration: PROHIBITED
```

## Назначение

v3 исправляет подтверждённые дефекты v2 до любого доступа к comparative results:

- исполняемая uncertainty state machine;
- exact G1 member-specific Review source transitions;
- candidate × scenario × Review member × replay × gate expected outcomes;
- cumulative false-positive metric и non-compensable gate;
- математически bounded daily candidate;
- отдельная linkage Review/Learn marginal metrics;
- exact set coverage всех registries;
- immutable v1/v2 identities.

Machine и human contract: [core-economy-candidate-protocol-v3.md](../../docs/gamification/core-economy-candidate-protocol-v3.md).

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
protocol: 2c95e263f8df7884914630aade4ae641cbc12de58dfdc5b3099fe5a23729eeba
pipeline: 1f8d3cfe8d60b1ac7e2a8f0dd27808b8c28d448f90ab02fe947d9c3c68720001
scenarios: 28eabe85b9de45ed4f3b1673fe2e1db7209243bbc5616c83351f2e7a1b575c62
matrix: 9a0a762a9c81adedb536a8b82f97ef33c271271ba1183a425f0fa0dba99a22da
validator: core-economy-protocol-v3-validator-1
generator: core-economy-protocol-v3-generator-1
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
