# Передача актуального контекста ИИ

**Снимок:** 2026-07-27

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
G2.2 — COMPLETE
Learn XP lifecycle model — FROZEN_PRE_CANDIDATE_DESIGN
identity architecture — FACTORIZED; LearningEpisode<AchievementSubject>
lifecycle states / events / transitions — 7 / 20 / 12
fixtures / threat families / invariants — 23 / 6 / 19
fixture manifest digest — 4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
G2.3 — COMPLETE
Learn XP candidate protocol — FROZEN_PRE_SCREENING_IMPLEMENTATION
protocol publication SHA — 41313c9369c76d331d489a9aa4b44da2497b3132
families / candidates / reference variants — 2 / 8 / 2
subject strategies — S-CARD; S-NOTE-SIBLING
NOTE/SIBLING_GROUP relation — OPERATIONALLY_EQUIVALENT
delay policies — D1; D2
pending split — 0.25 provisional / 0.75 settlement
hypotheses / hard gates / metrics — 5 / 23 / 14
G2.4 matrix budget — 340 deterministic units
G2.4 — COMPLETE
screened implementation SHA — 548b27de6283b32fb27541db02ce6c8b65c29756
replacement matrix — 340 / 340 unique; 0 / 0 / 0 missing / extra / duplicates
manifest / evidence / bundle — fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a / 5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6 / a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78
F-CONFIRMATION-ONLY survivor — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
F-PENDING-CONFIRMED-SPLIT survivor — C-PENDING-SPLIT-D1-NOTE-SIBLING
G2.5 — COMPLETE — CONFIRMATORY INCONCLUSIVE
G2.5 variants / reference — 2 / 1
G2.5 conditions — 16 core / 12 identity / 8 explainability
G2.5 replay / expected units — FORWARD+REVERSE / 216
G2.5 identity evidence mode — SYNTHETIC_CONTRACT_ONLY
G2.5 results accessed — YES — AFTER PROTOCOL PUBLICATION
final G2 decision stage — NOT STARTED
production integration — PROHIBITED
```

G1.6 закрыл Review XP outcome `DEFER_REVIEW_MODEL`; production approval отсутствует.

G2.1 заморозил отдельный Learn XP problem contract. Он отделяет официальные Anki states `New/Learning/Review/Relearn` от Learn XP research lifecycle, фиксирует четыре identity candidates, pending/confirmation minimum requirements, шесть anti-farming threat families, 19 protected invariants, privacy/claims boundary и entry contract G2.2.

G2.2 определил семь typed lifecycle states, 20 events и 12 deterministic transitions. Identity architecture factorized как `LearningEpisode<AchievementSubject>`: `LEARNING_EPISODE` является container, а `CARD`, `NOTE`, `SIBLING_GROUP` остаются невыбранными subject candidates.

G2.2 опубликовал research-only evaluator и 23 synthetic fixtures, покрывающие шесть threat families и все 19 invariants. Model status — `FROZEN_PRE_CANDIDATE_DESIGN`.

G2.3 устранил duplicate canonical digest helper, запретил direct-input coercion и доказал отсутствие drift на 31 frozen lifecycle case. Затем prospectively заморозил две Learn XP families, две delay policies, две operational subject strategies, восемь candidates, две reference variants и exact deterministic G2.4 budget `340/340`.

Protocol publication SHA — `41313c9369c76d331d489a9aa4b44da2497b3132`; G2.3 full research suite — `982 passed`. Первый canonical G2.4 attempt на `ef7c638a…` был изолирован как `INVALID` после failure byte-identical archive reproduction. Packaging-only `HARNESS` correction (`TarInfo.mode → 0644`) опубликована как `548b27de6283b32fb27541db02ce6c8b65c29756` без изменения screening design. Полный replacement run завершён `340/340`, detached validation и deterministic reproduction прошли. Внутри `F-CONFIRMATION-ONLY` выбран `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING`, внутри `F-PENDING-CONFIRMED-SPLIT` — `C-PENDING-SPLIT-D1-NOTE-SIBLING`. Cross-family ranking, final model selection и production approval в G2.4 не выполнялись. G2.5 был активирован отдельно и завершён на prospectively frozen matrix из двух survivors, одной reference, 36 conditions и двух replay identities: `216/216/216`, `0/0/0`, detached validation и byte-identical reproduction прошли. Оба survivors получили `CONFIRMATORY_INCONCLUSIVE` из-за `DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE`; reference осталась `REFERENCE_ONLY`. Ranking, winner, recommendation, final model selection и production approval не выполнялись.

Точные источники:

- [`../roadmap/gamification/README.md`](../roadmap/gamification/README.md)
- [Gamification docs index](gamification/README.md)
- [Learn XP human problem contract](gamification/learn-xp-problem-contract.md)
- [Learn XP machine problem contract](../research/gamification-sim/contracts/learn-xp-problem-contract-v1.json)
- [Learn XP problem schema](../research/gamification-sim/schemas/learn-xp-problem-contract-v1.schema.json)
- [Learn XP human lifecycle model](gamification/learn-xp-lifecycle-model.md)
- [Learn XP machine lifecycle model](../research/gamification-sim/contracts/learn-xp-lifecycle-model-v1.json)
- [Learn XP lifecycle schemas](../research/gamification-sim/schemas/learn-xp-lifecycle-model-v1.schema.json)
- [Learn XP human candidate protocol](gamification/learn-xp-candidate-protocol.md)
- [Learn XP machine candidate protocol](../research/gamification-sim/contracts/learn-xp-candidate-protocol-v1.json)
- [Learn XP candidate protocol schema](../research/gamification-sim/schemas/learn-xp-candidate-protocol-v1.schema.json)
- [Learn XP bounded screening technical reference](gamification/learn-xp-bounded-screening.md)
- [G2.1 closeout](../roadmap/gamification/g2-learn-xp-problem-contract.md)
- [G2.2 closeout](../roadmap/gamification/g2-learn-xp-lifecycle.md)
- [G2.3 closeout](../roadmap/gamification/g2-learn-xp-candidate-protocol.md)
- [G2.4 closeout](../roadmap/gamification/g2-learn-xp-bounded-screening.md)
- [Learn XP confirmatory protocol](gamification/learn-xp-confirmatory-protocol.md)
- [G2.5 confirmatory closeout](../roadmap/gamification/g2-learn-xp-confirmatory-evidence.md)
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

### G2.5 closeout

Canonical confirmatory evidence completed on publication SHA `903604245aaa540674f650b998d32f497b018f49`:
`216/216/216`, `0/0/0`, detached validation PASS and byte-identical
reproduction PASS. Both G2.4 survivors are `CONFIRMATORY_INCONCLUSIVE` because
the frozen identity mode was `SYNTHETIC_CONTRACT_ONLY` and the disposable Anki
identity probe was unavailable. The zero-reward reference remains
`REFERENCE_ONLY`. No ranking, winner, recommendation, final model selection or
production approval was produced.
