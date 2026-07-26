# Передача актуального контекста ИИ

**Снимок:** 2026-07-26

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
G0 — Complete
G1 — Complete
G1 final outcome — DEFER_REVIEW_MODEL
recommended Review XP research candidate — NONE
P-STEP-ZERO — CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D — CONFIRMATORY_ELIGIBLE; not selected; not falsified
G2 — IN PROGRESS
G2.1 — COMPLETE
Learn XP contract — FROZEN_PRE_LIFECYCLE_ANALYSIS
identity candidates — CARD; NOTE; SIBLING_GROUP; LEARNING_EPISODE
identity winner — NONE
reward amount / pending ratio / confirmation delay — NONE
G2.2 — NEXT / NOT STARTED
production integration — PROHIBITED
```

G1.6 закрыл Review XP outcome `DEFER_REVIEW_MODEL`; production approval отсутствует.

G2.1 заморозил отдельный Learn XP problem contract. Он отделяет официальные Anki states `New/Learning/Review/Relearn` от Learn XP research lifecycle, фиксирует четыре identity candidates, pending/confirmation minimum requirements, шесть anti-farming threat families, 19 protected invariants, privacy/claims boundary и entry contract G2.2.

G2.1 не выбрал identity winner, lifecycle, XP amount, pending ratio, confirmation delay, candidate family или simulation matrix. Simulation не запускалась. G2.2 не начата.

Точные источники:

- [`../roadmap/gamification/README.md`](../roadmap/gamification/README.md)
- [Gamification docs index](gamification/README.md)
- [Learn XP human contract](gamification/learn-xp-problem-contract.md)
- [Learn XP machine contract](../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json)
- [Learn XP strict schema](../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json)
- [G2.1 closeout](../roadmap/gamification/g2-learn-xp-problem-contract.md)
- [G1.6 decision and G1 closeout](../roadmap/gamification/g1-review-xp-decision.md)

`gamification → master`, production integration, package inclusion и release запрещены без отдельного owner decision.

## Platform / CI

```text
real-deck E2E foundation — COMPLETE / merged
E2E-I1–E2E-I6 — COMPLETE / merged
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

## Режим работы

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [Codex agent rules](codex-agent-rules.md)
- [Codex local environment](codex-local-environment.md)

ChatGPT mode может использовать GitHub connector и консоль владельца WSL/PowerShell. Скачиваемые scripts выдаются отдельными файлами и предваряются `Unblock-File`.

Codex mode работает непосредственно в локальном task worktree; созданные там scripts не требуют download/unblock ritual.

Не начинать следующий roadmap stage автоматически только потому, что предыдущая техническая работа завершена.
