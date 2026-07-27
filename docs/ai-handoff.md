# Передача актуального контекста ИИ

**Снимок:** 2026-07-28

Этот файл — короткая точка входа. Он не заменяет production code, профильные contracts, roadmap или closeout reports.

## Порядок чтения

1. [`../README.md`](../README.md)
2. этот файл;
3. профильный roadmap;
4. профильный contract в `docs/`;
5. production/research code и tests нужного scope;
6. свежий closeout только когда он нужен задаче.

При противоречиях:

```text
production/research code и tests
→ docs/
→ roadmap/
→ reports/artifacts
→ старые планы и сообщения
→ предположения
```

## Проект и границы

Anki Study Report — локальный add-on для Anki 26.05+ с Python runtime и React/TypeScript dashboard.

- dashboard работает только через loopback и защищён access token;
- frontend получает bounded API projections и не читает collection напрямую;
- preview использует sanitizer и Shadow DOM без JavaScript execution surface;
- учебные и профильные данные остаются локальными;
- payload/public behavior меняются синхронно между слоями, tests и docs;
- Gamification research остаётся изолированным от add-on package, Fast CI и production runtime до отдельного решения.

Подробности: [architecture.md](architecture.md), [dashboard-api.md](dashboard-api.md), [security-and-safety.md](security-and-safety.md).

## Core

```text
C1 — завершён и принят
C2 implementation/integration — завершены и влиты в core
C2 owner acceptance — открыта bounded remediation
C3 → C4 → C5 → C6 — обязательный путь к Core 1.0
release — не начат
```

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

## Gamification

Canonical branch:

```text
gamification
```

Текущий repository state:

```text
G0 — COMPLETE

G1 — COMPLETE
G1 final outcome — DEFER_REVIEW_MODEL
recommended Review XP research candidate — NONE
P-STEP-ZERO — CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D — CONFIRMATORY_ELIGIBLE; not selected; not falsified

G2 — COMPLETE
G2 final outcome — RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended Learn XP research candidate — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
selected candidate G2.5 status — CONFIRMATORY_INCONCLUSIVE
selected candidate reason — DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
production integration — PROHIBITED

G3 — DEFERRED / POST-MVP / NOT STARTED
G3 critical path — NO
G3 blocks G4/G5/G6 — NO
G3 production integration — PROHIBITED

G4 — IN PROGRESS
G4.1 — COMPLETE
core economy contract — FROZEN_PRE_NORMALIZATION_ANALYSIS
core economy domains — REVIEW_DOMAIN; LEARN_DOMAIN
Create XP — EXCLUDED / DEFERRED WITH G3
Review winner — NONE
G4.2 — NEXT / NOT STARTED
production integration — PROHIBITED
```

### G1 Review input

G1.6 закрыл Review XP outcome `DEFER_REVIEW_MODEL`. `P-STEP-ZERO` и `P-TAPER-ZERO-30D` остаются `CONFIRMATORY_ELIGIBLE`, не выбраны и не фальсифицированы. G4 обязана сохранять оба candidates как explicit `REVIEW_UNCERTAINTY_AXIS` и не использовать один как hidden default.

### G2 Learn input

G2.6 закрыл G2 outcome `RECOMMEND_LEARN_XP_RESEARCH_MODEL` и рекомендует `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` как bounded research model. Его G2.5 outcome остаётся `CONFIRMATORY_INCONCLUSIVE`; отсутствующий disposable Anki identity probe не позволяет называть candidate confirmatory-eligible или production-ready. Frozen `1.0 LRU` не является автоматически common economy XP.

### G3 owner decision

G3/Create XP не отменён, но исключён из первого Gamification MVP и initial G4 core economy. Возвращение возможно только при выполнении всех условий:

```text
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

G3.1, Create lifecycle, candidates, units, formulas и simulation не определены.

### G4.1 core economy contract

Canonical artifacts:

- [human contract](gamification/core-economy-problem-contract.md)
- [machine contract](../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [strict schema](../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](../roadmap/gamification/g4-core-economy-problem-contract.md)

Frozen inventory:

```text
contract_id — core-economy-problem-contract
version — 1
status — FROZEN_PRE_NORMALIZATION_ANALYSIS
terminology — 30
personas — 9
threat families — 14
protected invariants — 28
allowed final G4 outcomes — 3
G4.2 requirements — 14
```

G4.1 фиксирует problem, Review/Learn inputs, productive-day/level/streak/rest/Momentum/recovery boundaries, personas, threats, invariants, privacy/claims и G4.2 entry contract. Он не выбирает Review winner, conversion ratio, normalized XP, cap, threshold, level curve, streak/Momentum/recovery formula, candidate family, matrix или seed.

Allowed final G4 outcomes:

```text
RECOMMEND_CORE_ECONOMY_RESEARCH_MODEL
DEFER_CORE_ECONOMY_MODEL
REJECT_CORE_ECONOMY_MODEL
```

G4.1 не выбирает outcome.

Точные источники:

- [`../roadmap/gamification/README.md`](../roadmap/gamification/README.md)
- [Gamification docs index](gamification/README.md)
- [G1.6 Review decision](../roadmap/gamification/g1-review-xp-decision.md)
- [G2.6 Learn decision](../roadmap/gamification/g2-learn-xp-decision.md)
- [Core economy problem contract](gamification/core-economy-problem-contract.md)
- [G4.1 closeout](../roadmap/gamification/g4-core-economy-problem-contract.md)

`gamification → master`, production integration, package inclusion и release запрещены без отдельного owner decision.

## Platform / CI

```text
real-deck E2E foundation — COMPLETE / merged
E2E-I1–I6 — COMPLETE / merged
E2E-I6 bounded corrective fix — COMPLETE / merged через PR #144
следующий Platform/CI stage — не активирован
```

Последний Core sync baseline:

```text
core HEAD: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
E2E-I6 corrective implementation: afe650adbf3ba55cb6b59068a1127022b651fbf3
PR #144 merge SHA: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
Fast CI: 30169763775 — PASS
standard/full: 30169890912 — PASS
```

E2E-I6 corrective fix не является новым этапом и не активирует CI 7–12. Любая оптимизация требует отдельного измеренного trigger и owner decision.

## Рабочие правила

- Сначала определить track, target branch и точный scope.
- Desktop/laptop — основной target; mobile не приоритет без отдельной задачи.
- Не добавлять placeholder routes, speculative APIs или future extension surfaces заранее.
- Не возвращать legacy aliases без доказанной compatibility необходимости.
- Не дробить существующий roadmap stage на новые буквенные или цифровые лестницы.
- Successful unchanged exact-SHA gates не повторять.
- Harness failure не объявлять production failure без подтверждения.
- Docs/contracts-only sync не требует повторного Fast CI или Docker E2E.
- Для Gamification target и PR base — `gamification`, даже если общие environment docs приводят Core-примеры.
- Не начинать G4.2 автоматически после G4.1.

## Режим работы

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [Codex agent rules](codex-agent-rules.md)
- [Codex local environment](codex-local-environment.md)

ChatGPT mode может использовать GitHub connector и консоль владельца WSL/PowerShell. Скачиваемые scripts выдаются отдельными файлами и предваряются `Unblock-File`.

Codex mode работает непосредственно в локальном task worktree; созданные там scripts не требуют download/unblock ritual.

Не начинать следующий roadmap stage автоматически только потому, что предыдущая техническая работа завершена.

### G4.1 closeout

```text
G3: DEFERRED / POST-MVP / NOT STARTED
G4: IN PROGRESS
G4.1: COMPLETE
contract: FROZEN_PRE_NORMALIZATION_ANALYSIS
Review inputs: P-STEP-ZERO; P-TAPER-ZERO-30D
Review winner: NONE
Learn input: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status: CONFIRMATORY_INCONCLUSIVE
G4.2: NEXT / NOT STARTED
production approved: NO
production integration: PROHIBITED
```
