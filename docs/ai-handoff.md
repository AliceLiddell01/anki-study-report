# Передача актуального контекста ИИ

**Снимок:** 2026-07-29

Этот файл — короткая точка входа. Он не заменяет production code, профильные contracts, roadmap или closeout reports.

## Порядок чтения

1. [`../AGENTS.md`](../AGENTS.md);
2. [`../README.md`](../README.md);
3. этот файл;
4. профильный roadmap;
5. профильный contract в `docs/`;
6. production/research code и tests;
7. свежий closeout только когда он нужен задаче.

При противоречиях:

```text
current branch production/research code и tests
→ current branch docs/
→ PR/base branch contracts
→ roadmap/
→ reports/artifacts
→ старые планы и сообщения
→ предположения
```

`master` является релизной веткой, а `core` — integration branch обязательного production Core-трека. Feature/remediation branch или открытый PR может содержать более свежее состояние своего scope, чем base branch. Перед выводами всегда определить current branch/PR, base/head SHA и merge state.

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
C2 base implementation/integration — завершены и влиты в core
PR #130 Stage 1: latest-Core sync + rejected-overlay cleanup — COMPLETE
PR #130 Stage 2: Cards 1:1 composition + native CSS + AV/media repair — COMPLETE
Cards final exact-card real-Anki evidence — PASS
Cards owner verdict — ACCEPT CARDS 1:1
Cards status — ACCEPTED / COMPLETE / FROZEN
Cards technical blockers — NONE
Cards accessibility blockers — NONE
Inspection Profiles corrected screenshot-first audit — COMPLETE
WP1 Settings shell — STRUCTURAL FOUNDATION DELIVERED
WP1 Settings owner visual assessment — 6/10 (исторический verdict владельца)
WP1 Settings visual language — PROVISIONAL
WP2 original Inspection Profiles frame candidate — REQUEST CHANGES
WP2 bounded corrective pass — IMPLEMENTATION CANDIDATE DELIVERED
WP2 bounded corrective pass external visual review — 7.8/10 (историческая внешняя оценка)
WP2 owner acceptance — NOT GRANTED
Owner progression decision — WP3 START AUTHORIZED WITHOUT WP2 ACCEPTANCE
WP3 Inspection Profiles Basic correction — COMPLETE
WP4 Inspection Profiles Advanced — COMPLETE
WP5 states/validation/accessibility — COMPLETE
WP6 final visual/system evidence — COMPLETE
Inspection Profiles — COMPLETE FOR C2 CLOSEOUT
PR #130 — MERGED INTO CORE
merged core SHA — 57eeca039247ab0522555b1292fc1f25c66976fd
Fast CI — 30408497011 / PASS ON MERGED CORE
real-Anki standard/full + restart — 30408746188 / PASS ON MERGED CORE
C3 — NOT STARTED
release/master — NOT TOUCHED
```

Точный scope: [`../roadmap/core/README.md`](../roadmap/core/README.md).

## Gamification

Canonical branch:

```text
gamification
```

### Current repository state

```text
G0 — COMPLETE

G1 — COMPLETE
G1 final outcome — RECOMMEND_RESEARCH_CANDIDATE
recommended Review XP research candidate — P-TAPER-ZERO-30D
P-STEP-ZERO — CONFIRMATORY_ELIGIBLE; not selected; not falsified
P-TAPER-ZERO-30D — CONFIRMATORY_ELIGIBLE; selected research winner; not falsified

G2 — COMPLETE
G2 final outcome — RECOMMEND_LEARN_XP_RESEARCH_MODEL
recommended Learn XP research candidate — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
selected candidate evidence status — CONFIRMATORY_INCONCLUSIVE
decision basis — MINIMIZE_UNVALIDATED_REWARD_STATE_SURFACE

G3 — DEFERRED / POST-MVP / NOT STARTED
G3 critical path — NO
G3 blocks G4/G5/G6 — NO

G4 — COMPLETE
G4.1 — COMPLETE
G4.2 — COMPLETE
G4.3 — COMPLETE
G4.3 v1 — SUPERSEDED_PRE_EXECUTION
G4.3 v1 results — NOT_AVAILABLE
G4.3 v2 — SUPERSEDED_PRE_EXECUTION
G4.3 v3 — INVALIDATED_AFTER_SCREENING
G4.3 v4 — FROZEN_AND_EXECUTED
G4.4 — COMPLETE
results — AVAILABLE
screening — COMPLETE
final G4 outcome — REJECT
recommended integrated bundle — NONE
production integration — PROHIBITED
```

### Frozen source inputs

Review:

```text
axis — REVIEW_MODEL_AXIS_V1
members — P-STEP-ZERO; P-TAPER-ZERO-30D
selection — P-TAPER-ZERO-30D
default — P-TAPER-ZERO-30D
evaluation — PARALLEL_SEPARATE
averaging — PROHIBITED
winner — P-TAPER-ZERO-30D
```

Raw G1 bundles are not declared freshly revalidated.

Learn:

```text
candidate — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
status — CONFIRMATORY_INCONCLUSIVE
limitation — DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
achievement subject — NOTE_SIBLING
allocation — CONFIRMATION_ONLY_NO_PROVISIONAL_STATE
source unit — LRU
frozen source total — 1.0
common economy XP — false
```

G1/G2 selections are bounded research governance. They do not mean scientific superiority, confirmatory eligibility, human benefit or production approval.

Create:

```text
CREATE_DOMAIN — EXCLUDED FROM INITIAL CORE ECONOMY
G3 activation — POST-MVP ONLY
```

Activation requires all three:

```text
FIRST_STABLE_GAMIFICATION_RELEASE
AND SEPARATE_OWNER_DECISION
AND CONCRETE_EVIDENCE_BACKED_PRODUCT_TRIGGER
```

### G4.1 — problem contract

Canonical artifacts:

- [human problem contract](gamification/core-economy-problem-contract.md)
- [machine contract](../research/gamification-sim/contracts/core-economy-problem-contract-v1.json)
- [strict schema](../research/gamification-sim/schemas/core-economy-problem-contract-v1.schema.json)
- [G4.1 closeout](../roadmap/gamification/g4-core-economy-problem-contract.md)

```text
status — FROZEN_PRE_NORMALIZATION_ANALYSIS
initial domains — REVIEW_DOMAIN; LEARN_DOMAIN
Create XP — EXCLUDED
Review winner — NONE
Learn status — CONFIRMATORY_INCONCLUSIVE
production integration — PROHIBITED
```

### G4.2 — input normalization and uncertainty model

Canonical artifacts:

- [human model](gamification/core-economy-input-normalization-model.md)
- [machine contract](../research/gamification-sim/contracts/core-economy-input-normalization-v1.json)
- [strict schema](../research/gamification-sim/schemas/core-economy-input-normalization-v1.schema.json)
- [G4.2 closeout](../roadmap/gamification/g4-core-economy-input-normalization.md)

```text
status — FROZEN_PRE_CANDIDATE_FAMILY_DESIGN
domain input types — REVIEW_DOMAIN_INPUT; LEARN_DOMAIN_INPUT
common records — NORMALIZATION_INPUT; DOMAIN_CONTRIBUTION_RECORD; DAILY_AGGREGATION_INPUT; DAILY_AGGREGATION_RESULT_PLACEHOLDER
axes — SESSION; ANKI_DAY; CALENDAR_DAY
dispositions / fail-closed reasons — 7 / 18
personas / fixture requirements — 9 / 15
threats / invariants — 14 / 28
numeric policy — NOT SELECTED
```

G4.2 shapes, validation, provenance, decomposition and fail-closed boundaries remain frozen. It did not create candidate families, exact traces, a matrix or results.

G4.2 provenance correction performed during G4.3 changed only the stale identity ledger in its closeout:

```text
pre-final stale human blob — b8fd53917eab9a1433d301383c76617de5ebb85f
current final merged human blob — 72478cb841a93fe678e290c7e5ce54502b7420b2
current final merged human SHA-256 — 996bce4c2f3e9fadb1d8546f93ef533384769ce568749a9b7de022ca7dd447f9
human document changed — NO
semantics changed — NO
contract/schema changed — NO
```

### G4.3 — candidate economy protocol and hypothesis design (historical v1)

Canonical artifacts:

- [human candidate protocol](gamification/core-economy-candidate-protocol.md)
- [machine candidate protocol](../research/gamification-sim/contracts/core-economy-candidate-protocol-v1.json)
- [candidate schema](../research/gamification-sim/schemas/core-economy-candidate-protocol-v1.schema.json)
- [deterministic scenarios](../research/gamification-sim/fixtures/core-economy-candidate-scenarios-v1.json)
- [scenario schema](../research/gamification-sim/schemas/core-economy-candidate-scenarios-v1.schema.json)
- [dry screening matrix](../research/gamification-sim/matrices/core-economy-screening-matrix-v1.json)
- [matrix schema](../research/gamification-sim/schemas/core-economy-screening-matrix-v1.schema.json)
- [G4.3 canonical closeout](../roadmap/gamification/g4-core-economy-candidate-protocol.md)
- [G4.3 post-merge report](../reports/research/g4-3-candidate-economy-protocol-closeout-2026-07-28.md)

Frozen protocol:

```text
owner principle — GRACEFUL_DEGRADATION_OVER_ABRUPT_CUTOFF
preferred research direction — TAPER / RECOVERY
abrupt uncertainty policy — RETAINED AS CONTROL
design — CURATED_BOUNDED_FACTORIAL_DESIGN
full primitive Cartesian product — PROHIBITED
primitive policies — 20
curated candidate bundles — 24
hypotheses — 24
non-compensable hard gates — 23
metrics — 19
deterministic scenarios — 40
matrix expected / unique — 762 / 762
matrix duplicates / missing / extra — 0 / 0 / 0
scenario digest — 9f53c8e6af181a0106a74f0bb52d1695a00e158a6ad15cb656c91bf6670881a3
matrix digest — 9f0ad95f8e99b3e25d19d859f88afa13a0b5b3b9efc99427facde336e146241c
```

Publication identities:

```text
starting gamification HEAD — a46e920cea0bbe97f2d0c785965febf0a52ed9e7
protocol publication HEAD — 801a0112fa1af9334b0992725056da4292bc5d94
final PR head — 8b22851abbd71f661957fefcbde84548fdcd38f4
PR — #166
merge SHA — 0d42e7bbee80b99de7e3369071c9a2dcdc6ba6bb
remote task branch — DELETED
owner local task branch — DELETED
```

Validation recorded by the bounded owner runner:

```text
strict duplicate-key-safe parse — PASS
Draft 2020-12 schema self-check — PASS
artifact-schema validation — PASS
semantic reference integrity — PASS
G4.2 exact dependency identity — PASS
candidate/scenario/matrix uniqueness — PASS
Review-axis coverage — PASS
Learn limitation propagation — PASS
results-not-run enforcement — PASS
negative samples — 34 / 34 rejected
changed-path allowlist — exact 9 paths
workflow checks — 0
```

`workflow checks — 0` is a fact, not `CI PASS`. Fast CI, frontend build, Docker real-Anki E2E, package validation and production implementation were not run because G4.3 changed only research contracts, schemas, synthetic fixtures, a dry matrix and documentation.

No-results proof:

```text
historical v1 results — NOT_AVAILABLE
all matrix rows — NOT_RUN
screening executed — NO
simulation — NOT_STARTED
historical v1 winner — NONE
production approved — NO
historical v1 next stage — G4.4 / NOT STARTED
```

### G4.4 final state

Accepted artifacts:

- [technical G4.4 evidence](gamification/core-economy-bounded-screening.md);
- [canonical G4.4 closeout](../roadmap/gamification/g4-core-economy-bounded-screening.md);
- [research handoff](gamification/core-economy-research-handoff.md);
- [v4 result manifest](../research/gamification-sim/results/core-economy-screening-manifest-v4.json);
- [v4 row results](../research/gamification-sim/results/core-economy-screening-results-v4.json).

```text
v4 publication SHA — 78ce71d82d72577f8283707a85b8e6b226330c94
v4 evaluator SHA — 6174c5deae40b339b7e738ae08c1060b3f0158fa
rows expected / actual / unique — 1275 / 1275 / 1275
missing / extra / duplicates — 0 / 0 / 0
gate results / metric results — 3952 / 3710
unexpected failures — 33
result artifact digest — ad000099135574d285561d8e9bcc624ff430d25c42dd5b2d89a35476f3fad5db
result-set digest — bbbacf3880378409a740c26d85dbc589178ec2480f471107639e4c7ed8198d90
byte-identical reproduction — PASS
```

Every recommendation-eligible integrated bundle failed at least one non-compensable gate. The final G4 outcome is `REJECT`; isolated passing candidates are not combined post hoc.

```text
Review winner — P-TAPER-ZERO-30D
Learn winner — C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
Learn status — CONFIRMATORY_INCONCLUSIVE
Learn limitation — DISPOSABLE_ANKI_IDENTITY_PROBE_UNAVAILABLE
G5 — PLANNED / NOT STARTED
G6 — CONDITIONAL / NOT STARTED
```

### Exact Gamification sources

- [`../roadmap/gamification/README.md`](../roadmap/gamification/README.md)
- [Gamification docs index](gamification/README.md)
- [G1.6 decision](../roadmap/gamification/g1-review-xp-decision.md)
- [G2.6 decision](../roadmap/gamification/g2-learn-xp-decision.md)
- [G4.1 problem contract](gamification/core-economy-problem-contract.md)
- [G4.1 closeout](../roadmap/gamification/g4-core-economy-problem-contract.md)
- [G4.2 input model](gamification/core-economy-input-normalization-model.md)
- [G4.2 closeout](../roadmap/gamification/g4-core-economy-input-normalization.md)
- [G4.3 candidate protocol](gamification/core-economy-candidate-protocol.md)
- [G4.3 closeout](../roadmap/gamification/g4-core-economy-candidate-protocol.md)
- [G4.3 post-merge report](../reports/research/g4-3-candidate-economy-protocol-closeout-2026-07-28.md)
- [G4.4 bounded screening](gamification/core-economy-bounded-screening.md)
- [G4 final closeout](../roadmap/gamification/g4-core-economy-bounded-screening.md)

`gamification → master`, production integration, package inclusion and release remain prohibited without a separate owner decision.

## Current accepted Cards evidence

```text
PR: #130 — MERGED INTO CORE
frozen PR base / merge-base: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f

Stage 1 verified production candidate:
a746172f8746eac82ff628d36a7a6328d9332acf

Cards production package source:
a162dde223b1bc40b6b0f566ae1fb5d665089359

Cards final evidence harness:
5487bb32d43b11bbe618ec45e1b0e1e365fabb39

exact package SHA-256:
e01b9dd3e3277d9ff0cafb9ac3a298a1459118056f07834a171662c91ae79357

final evidence:
cards-final-av-media-fidelity-evidence.zip

final evidence size:
56 358 736 bytes

final evidence SHA-256:
539cf5f08c5f804fa6de3b87c87f0792e6d60777f0b40a9c413a0b912516dfc3

exact card:
1649481469689 / 影

standard browser smoke:
19/19 PASS / 18 screenshots

exact browser:
6/6 scenarios PASS / 32 screenshots

replay reset:
PASS

visible keyboard focus light/dark:
PASS

accessible-name localization:
PASS

live GIF:
cross-scenario frame difference PASS

deterministic GIF:
frameCount=154

network/security:
external=0 / Inspection Profiles requests=0 / page errors=0 / console errors=0 / failed requests=0

evidence self-verification:
PASS / missing=0 / unexpected=0 / mismatches=0

owner visual assessment:
average≈9.3/10 / minimum mandatory aspect=8.7/10
```

Актуальные Cards contracts:

- [Cards workspace по Prototype v3.2.3](cards-v323-production-workspace.md);
- [Cards exact AV/audio/media E2E](cards-exact-av-media-e2e.md).

### Cards frozen boundary

Cards production заморожен. Без новой доказанной регрессии запрещено менять Cards component composition, queue, rail, drawer, expanded answer, native preview, AV/audio/GIF path, Shadow DOM или Cards styles ради Settings. Успешный exact Cards real-Anki gate повторно не запускается без нового риска.

После shared Settings changes допустим только короткий Cards regression smoke, если изменение действительно затронуло shared shell/styles.

### Visual coverage checkpoint

`ACCEPT CARDS 1:1` относится только к route `#/cards`. PR #130 позднее прошёл
отдельный Profiles closeout, exact merged Fast CI/E2E и был влит в `core`;
это не активирует C3 и не означает release.

| Route / area | Текущее подтверждение | Статус |
| --- | --- | --- |
| `#/cards` wide | exact same-card production captures + native CSS + AV/media evidence | OWNER ACCEPTED / FROZEN |
| `#/cards` drawer | exact 1024 light/dark capture и GIF crop | OWNER ACCEPTED / FROZEN |
| `#/cards` expanded | exact answer light/dark, GIF+PNG и geometry | OWNER ACCEPTED / FROZEN |
| replay/audio | два playback, reset к нулю, local MP3 HTTP 200 | PASS |
| animated GIF | exact SHA, 160×120, live light/dark frame difference, decoder 154 frames | PASS |
| `#/settings/inspection-profiles` original frame candidate | исходный WP2 evidence; сохранён как исторический baseline | REQUEST CHANGES |
| `#/settings/inspection-profiles` corrective frame | historical WP2 candidate и external review сохранены как baseline | HISTORICAL / SUPERSEDED BY FINAL C2 CLOSEOUT |
| `#/settings/inspection-profiles` Basic | two-column 1024/QHD composition, strict routing, focus и unmasked comparisons | COMPLETE FOR C2 CLOSEOUT |
| `#/settings/inspection-profiles` Advanced | authored strict mappings/checks/templates editor; three QHD columns; missing references remain visible | COMPLETE FOR C2 CLOSEOUT |
| Settings shared shell | структурная foundation; прежняя owner visual assessment 6/10 | STRUCTURAL FOUNDATION DELIVERED / VISUAL LANGUAGE PROVISIONAL |
| Other Settings routes | shared shell regression only; business behavior preserved | VERIFIED IN WP1 SCOPE |

Ранее заданный владельцем целевой порог для будущего Inspection Profiles
acceptance, а не оценка текущего candidate:

```text
minimum acceptable result: 8.5/10
preferred target: 9.0/10 or higher
```

Reports:

- [Stage 1 — C2 manual acceptance remediation](../reports/core/c2-manual-acceptance-remediation-closeout.md);
- [Stage 2 — Cards Prototype v3.2.3 production integration](../reports/core/c2-cards-v323-production-integration.md);
- [Cards final AV/audio/media evidence closeout](../reports/core/c2-cards-final-av-media-evidence-closeout.md);
- [Inspection Profiles — corrected screenshot-first audit](../reports/core/c2-inspection-profiles-screenshot-audit.md);
- [WP1 Settings shell implementation](../reports/core/c2-settings-shell-wp1-implementation.md);
- [WP2 Inspection Profiles original workspace frame](../reports/core/c2-inspection-profiles-wp2-frame-implementation.md);
- [WP2 Inspection Profiles bounded corrective pass](../reports/core/c2-inspection-profiles-wp2-corrective-pass.md);
- [WP3 Inspection Profiles Basic implementation](../reports/core/c2-inspection-profiles-wp3-basic-implementation.md);
- [PR #130 final integration closeout](../reports/core/c2-pr130-final-integration-closeout.md).

## Platform / CI

```text
real-deck E2E foundation — COMPLETE / merged
E2E-I1–E2E-I6 — COMPLETE / merged
E2E-I6 bounded corrective fix — COMPLETE / merged через PR #144
следующий Platform/CI stage — не активирован
```

Последний documented Core sync baseline:

```text
core HEAD: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
E2E-I6 corrective implementation: afe650adbf3ba55cb6b59068a1127022b651fbf3
PR #144 merge SHA: 62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f
Fast CI: 30169763775 — PASS
standard/full: 30169890912 — PASS
```

E2E-I6 corrective fix does not activate CI 7–12. Any optimization requires a separate measured trigger and owner decision.

## Рабочие правила

- Сначала определить track, target branch и точный scope.
- Desktop/laptop — основной target; mobile не приоритет без отдельной задачи.
- Не добавлять placeholder routes, speculative APIs или future extension surfaces заранее.
- Не возвращать legacy aliases без доказанной compatibility необходимости.
- Real-Anki Docker E2E выбирать по [test matrix](test-matrix.md) и [verification policy](verification-run-policy.md).
- Для exact Cards AV/media использовать [специализированный runbook](cards-exact-av-media-e2e.md).
- Successful unchanged exact-SHA gates не повторять.
- Не создавать вложенную лестницу этапов вместо одной цельной задачи.
- Docs-only post-merge sync не требует повторного Fast CI или Docker E2E.
- Для нетривиальной реализации использовать локальный `.agents/task-contract.toml` и `node scripts/run_python.mjs scripts/check_task_scope.py` из PowerShell 7.
- Harness failure не объявлять production failure без подтверждения.
- Для Gamification target и PR base — `gamification`.
- Не трактовать historical dry matrix, preferred direction или отсутствие workflow checks как новый screening result, winner либо CI PASS.

## Режим работы

- [Корневой auto-loaded entrypoint](../AGENTS.md)
- [Компактный AI context bootstrap](ai-context-bootstrap.md)
- [Режимы ChatGPT и Codex](ai-work-modes.md)
- [ChatGPT work mode](chatgpt-work-mode.md)
- [ChatGPT manual operations](chatgpt-manual-operations.md)
- [Codex agent rules](codex-agent-rules.md)
- [Codex local environment](codex-local-environment.md)
- [Task contract template](templates/task-contract.toml)

Сначала определите фактическую branch/PR, трек и точный scope. Не начинайте следующий roadmap stage автоматически только потому, что предыдущий завершён.
