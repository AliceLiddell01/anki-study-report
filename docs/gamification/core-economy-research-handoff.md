# Core economy research handoff после G4

## Передаваемое состояние

```text
G4: COMPLETE
final outcome: REJECT
accepted evidence version: v4
recommended integrated bundle: NONE
production integration: PROHIBITED
```

Каноническое решение и полный dimension ledger находятся в [G4.4 bounded screening](core-economy-bounded-screening.md). Machine results находятся в [`research/gamification-sim/results`](../../research/gamification-sim/results/).

## Зафиксированные research inputs

```text
Review winner/default: P-TAPER-ZERO-30D
Review alternative: P-STEP-ZERO
Review averaging: PROHIBITED
Learn winner/input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
Learn limitation: DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
Create domain: EXCLUDED
```

## Почему нет implementation handoff в production

Обе recommendation-eligible uncertainty policies провалили `HG-FALSE-POSITIVE-CONTEXT-HARM-BOUNDED`; high daily policy также провалила `HG-EXTREME-VOLUME-BOUNDED`. Поэтому G4 не передаёт формулу, payload contract, persistence model или UI contract в G5/G6.

## Допустимый следующий research шаг

Новый эксперимент возможен только как отдельная prospective protocol version с заранее опубликованными uncertainty candidates, gates, expected outcomes и matrix. Нельзя:

- менять v4 thresholds или expected outcomes;
- собирать passing bundle из isolated candidates задним числом;
- трактовать G1/G2 winner как production approval;
- использовать реальные пользовательские данные;
- автоматически начинать G5/G6.
