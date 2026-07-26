# Learn XP candidate protocol — G2.3

**Protocol ID:** `learn-xp-candidate-protocol`  
**Version:** `1`  
**Status:** `FROZEN_PRE_SCREENING_IMPLEMENTATION`  
**G2.4:** `NEXT / NOT STARTED`  
**Production integration:** `PROHIBITED`

Нормативный источник — [machine-readable protocol](../../research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json), проверяемый [Draft 2020-12 schema](../../research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json). Документ не содержит результатов screening.

## 1. G2.2 fixes

Первый commit G2.3 — `4d9b05f0347df85cb34ad85c1a935892ea7b4e4d`.

- локальный digest helper удалён;
- evaluator использует shared `canonical_json.canonical_digest`;
- legacy/shared parity доказана на 31 frozen lifecycle case;
- states, ledgers, reason codes и result digests не изменились;
- fixture manifest digest остался `4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93`;
- direct event input теперь требует exact types и registered enums без `str/int/bool` coercion.

## 2. Reward domain

`1.0 LRU` (`Learn Reward Unit`) — максимальная суммарная comparative allocation для одного confirmed initial-learning achievement.

LRU не является Review Unit, production XP, level curve или spendable economy. Negative allocation и total выше `1.0` запрещены.

## 3. Frozen families

Ровно две:

1. `F-CONFIRMATION-ONLY`: pending `0.0`, confirmation settlement `1.0`.
2. `F-PENDING-CONFIRMED-SPLIT`: pending `0.25`, confirmation settlement `0.75`.

Split ratio выбран как один binary-exact, легко проверяемый minority share. Он не считается оптимальным или production-ready.

## 4. Delay policies

- `D1`: минимум 1440 synthetic minutes и `anki_day_delta >= 1`; expiry 10080 minutes / 7 Anki days.
- `D2`: минимум 4320 synthetic minutes и `anki_day_delta >= 3`; expiry 20160 minutes / 14 Anki days.

Обе policies требуют source-event linkage, исключают same-chain, не используют displayed interval и не считают scheduler state `Review` достаточным.

Эти delays — prospective bounded contrasts. Исследования поддерживают delayed/spaced retrieval, но не единственный универсальный оптимум.

## 5. Subject strategies

- `S-CARD` — granular card subject.
- `S-NOTE-SIBLING` — note-derived sibling group.

`NOTE` и `SIBLING_GROUP` классифицированы как `OPERATIONALLY_EQUIVALENT`: в доступной non-private Anki identity boundary siblings — cards, созданные из одной note, поэтому дополнительного безопасного synthetic key нет. `CARD` сохраняется как отдельная granular comparison strategy.

## 6. Candidate registry

Четыре parameterizations × две subject strategies = **8 candidates**:

```text
C-CONFIRMATION-ONLY-D1-CARD
C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
C-CONFIRMATION-ONLY-D2-CARD
C-CONFIRMATION-ONLY-D2-NOTE-SIBLING
C-PENDING-SPLIT-D1-CARD
C-PENDING-SPLIT-D1-NOTE-SIBLING
C-PENDING-SPLIT-D2-CARD
C-PENDING-SPLIT-D2-NOTE-SIBLING
```

Reference `L-NO-LEARN-XP` имеет две subject-aware variants и всегда выделяет `0.0 LRU`. Reference не candidate и не survivor.

## 7. Terminal disposition

- `CONFIRMED`: pending settles, а не складывается поверх total; итог `1.0 LRU`.
- `EXPIRED`, `CANCELLED`, `INVALIDATED`: provisional allocation становится `VOID`; итог `0.0 LRU`; fresh eligibility отсутствует.
- historical audit event может сохраняться отдельно от value.

## 8. Hypotheses and hard gates

Заморожены пять hypotheses и 23 non-compensable hard gates. Missing evidence fails closed. Weighted aggregate score запрещён.

Hard gates покрывают G2.1/G2.2 continuity, digest parity, strict event types, step/Again/Hard/reset/reimport/object/sibling/session/config farming, independent confirmation, pending idempotency/non-spendability, total cap, terminal disposition, deterministic replay, evidence completeness, research-only, privacy и отсутствие production approval.

## 9. Survivor and ties

Максимум один survivor на family.

После прохождения всех hard gates применяется frozen lexicographic order только по safety/accounting metrics. Если несколько parameterizations полностью равны по frozen criteria, family получает `FAMILY_INCONCLUSIVE`. Имя, registry order, один seed, эстетика и post-hoc score запрещены.

## 10. Exact G2.4 dry matrix

```text
candidates: 8
subject-aware references: 2
scenario registry: 30
scenario conditions per identity: 34
replicas: [0]
seed axis: ABSENT
expected units: 340
expected unique unit IDs: 340
adaptive units: 0
```

Frozen 23 lifecycle fixtures обязательны. Семь дополнительных scenarios ограничены allocation, confirmation settlement, expiry/cancel/invalidation, subject collision и zero-reference parity.

Unit ID — `U-` + canonical SHA-256 полного typed identity. Execution order и filesystem path в identity не входят.

## 11. Amendments

Typo/link correction может сохранить version при неизменной semantics.

Изменение family, ratio, delay, subject strategy, gate, metric, matrix axis, unit identity, survivor rule, status или missing-data behavior требует новой version, field-level diff, rationale, results-viewed disclosure, invalidation prior run, required rerun и roadmap note.

## 12. Claims boundary

Допустимо утверждать только прохождение frozen synthetic gates, устойчивость к перечисленным synthetic traces и сохранение research-only boundaries.

Запрещено утверждать mastery, реальное улучшение retention/motivation, предотвращение всего gaming, production readiness или объективную истинность rating.

## 13. External basis

- Anki card states and notes/cards: https://docs.ankiweb.net/getting-started.html
- learning/relearning steps: https://docs.ankiweb.net/deck-options.html
- answer buttons and siblings: https://docs.ankiweb.net/studying.html
- templates: https://docs.ankiweb.net/templates/intro.html
- filtered decks: https://docs.ankiweb.net/filtered-decks.html
- prospective discipline: https://www.cos.io/initiatives/prereg
- registered reports: https://www.cos.io/initiatives/registered-reports
- retrieval/spacing methodology: PMID 21574747, 21707204, 24744260, 19076480

## 14. Boundary

G2.4 implementation, screening, outcomes, survivors, final model and production integration не начаты.
