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
G1.1 и correction — Complete
G1.2 и G1.2a correction — Complete
G1.3 — Complete
G1.4 — Complete
G1.4 survivors — P-STEP-ZERO; P-TAPER-ZERO-30D
G1.5 — Complete
G1.5 outcomes — both CONFIRMATORY_ELIGIBLE
G1.6 — Complete
G1 final outcome — DEFER_REVIEW_MODEL
recommended research candidate — NONE
P-STEP-ZERO — not selected; not falsified
P-TAPER-ZERO-30D — not selected; not falsified
production integration — PROHIBITED
G2 — PLANNED / NOT STARTED
```

G1.2a оставляет root cause частично локализованным с `MEDIUM` confidence: `memory_main` — крупнейший component, `post_transition` — dominant timing window, Challenge не direction-consistent, уникальная corrective formula не доказана.

G1.4 завершён на опубликованной implementation `a8857f111849e2e98744adda8e06fe1910bdf805`. Exact matrix дала `160/160` unique units, `0/0/0` missing/extra/duplicates и evidence digest `836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694`.

G1.5 выполнил prospectively frozen 840-unit matrix на published implementation `7ae7a26cf0591dfc7f004f3b378eb3bff8b7d2c8`: `840/840` unique units, `0/0/0` missing/extra/duplicates, evidence digest `9b4d6aa41bf2392aac273784b45b28ff88210e05ea04533bf440d6522ad75afa`. `P-STEP-ZERO` и `P-TAPER-ZERO-30D` получили `CONFIRMATORY_ELIGIBLE`.

G1.6 применил frozen decision policy и закрыл G1 outcome `DEFER_REVIEW_MODEL`. Raw bundles G1.4/G1.5 не были доступны для обязательной read-only continuity revalidation, а принятые агрегаты не дают неарбитрарного основания предпочесть STEP или TAPER. Оба candidates остаются eligible, не выбраны и не falsified. Новые simulations, ranking и production integration не выполнялись.

Точные источники:

- [`../roadmap/gamification/README.md`](../roadmap/gamification/README.md)
- [human candidate protocol](gamification/review-xp-candidate-protocol.md)
- [`../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json`](../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json)
- [`../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json`](../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json)
- [G1.4 bounded screening closeout](../roadmap/gamification/g1-bounded-screening.md)
- [G1.5 confirmatory protocol](gamification/review-xp-confirmatory-protocol.md)
- [G1.5 confirmatory closeout](../roadmap/gamification/g1-confirmatory-evidence.md)
- [G1.6 decision and G1 closeout](../roadmap/gamification/g1-review-xp-decision.md)

`gamification → master`, production integration, package inclusion и release запрещены без отдельного owner decision. G2 не начат.

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
- Docs-only sync не требует повторного Fast CI или Docker E2E.
- Для Gamification target и PR base — `gamification`, даже если общие environment docs приводят Core-примеры.

## Режим работы

- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [Codex agent rules](codex-agent-rules.md)
- [Codex local environment](codex-local-environment.md)

ChatGPT mode может использовать GitHub connector и консоль владельца WSL/PowerShell. Скачиваемые scripts выдаются отдельными файлами и предваряются `Unblock-File`.

Codex mode работает непосредственно в локальном task worktree; созданные там scripts не требуют download/unblock ritual.

Не начинать следующий roadmap stage автоматически только потому, что предыдущая техническая работа завершена.
