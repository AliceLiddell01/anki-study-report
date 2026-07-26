# G1.5 — Confirmatory 90/365, robustness and safety evidence

## Статус

```text
G1.5: COMPLETE
G1: IN PROGRESS
G1.6: NOT STARTED
ranking performed: NO
final candidate selected: NO
production approved: NO
```

G1.5 выполнил prospectively frozen confirmatory protocol для двух survivors G1.4:

```text
P-STEP-ZERO
P-TAPER-ZERO-30D
```

Оба survivor получили `CONFIRMATORY_ELIGIBLE`. Этап не ранжирует STEP и TAPER, не выбирает финального кандидата Review XP и не разрешает production integration.

## Scope и источники

Authoritative artifacts:

- [human protocol](../../docs/gamification/review-xp-confirmatory-protocol.md);
- [machine protocol](../../research/gamification-sim/contracts/review-xp-confirmatory-protocol-v1.json);
- [strict Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-confirmatory-protocol-v1.schema.json);
- [G1.4 closeout](g1-bounded-screening.md);
- published research source и tests на implementation SHA ниже;
- внешний canonical evidence bundle, идентифицированный SHA-256.

PR closeout: `#153`, base `gamification`.

## Publication barrier

До просмотра результатов были committed и pushed:

- human и machine protocol;
- strict schema;
- exact 840-unit manifest;
- executable harness и evidence validator;
- CLI;
- focused tests.

```text
pre-results base SHA:
646be9379518977381ae04a37da3a6027c4ec6ec

published implementation SHA:
7ae7a26cf0591dfc7f004f3b378eb3bff8b7d2c8

local/remote equality:
PASS

result files in implementation commit:
NO
```

Protocol validation перед canonical run:

```text
VALID review-xp-confirmatory-manifest-v1
840 unique units
eea4e2ed6da087f7ac45eb56d9390b23e44ce52837b5f1d015afb3276049c728
```

После публикации protocol, axes, seeds, thresholds, outcomes и boundaries не менялись.

## Exact matrix

```text
core longitudinal:
576

persona safety:
192

invariant / abuse probes:
72

total:
840
```

Core matrix:

```text
3 variants
× 4 matched policy pairs
× 2 horizons
× 2 replicas
× 2 fresh seeds
× 2 replay identities
× 3 model conditions
= 576
```

Persona safety:

```text
3 variants
× 16 committed personas
× 2 fresh seeds
× 2 replay identities
= 192
```

Invariant и abuse probes:

```text
3 variants
× 12 probes
× 2 replay identities
= 72
```

Accounting:

```text
expected / actual / actual unique:
840 / 840 / 840

missing / extra / duplicates:
0 / 0 / 0

CORE_LONGITUDINAL:
576

PERSONA_SAFETY:
192

INVARIANT_ABUSE_PROBE:
72
```

## Provenance и evidence identities

```text
implementation SHA:
7ae7a26cf0591dfc7f004f3b378eb3bff8b7d2c8

base SHA:
646be9379518977381ae04a37da3a6027c4ec6ec

branch:
chatgpt/g1-5-confirmatory-evidence

Python:
3.11.15

fsrs:
6.3.1

jsonschema:
4.26.0

manifest digest:
eea4e2ed6da087f7ac45eb56d9390b23e44ce52837b5f1d015afb3276049c728

evidence digest:
9b4d6aa41bf2392aac273784b45b28ff88210e05ea04533bf440d6522ad75afa

evidence.json SHA-256:
e19854893b6b0b035b4ed34a8888ab8b8b331faaf8623b4a5f658aaaeb9fe6b4

external evidence bundle SHA-256:
90b2132cbe46edeb2a28e6f9ae81de311807353dd5e0826cbe8d3a6af41a85fb
```

Внешний bundle содержит:

```text
FILES.sha256
canonical-run.log
confirmatory/9b4d6aa41bf2/evidence.json
confirmatory/9b4d6aa41bf2/manifest.json
confirmatory/9b4d6aa41bf2/run-metadata.json
confirmatory/9b4d6aa41bf2/summary.md
validation.txt
```

Bundle остаётся вне Git и сохраняется как canonical raw evidence для unit-level audit. Репозиторий хранит identities и bounded semantic summary, а не дублирует 840-unit payload.

## Verification

### До результатов

```text
focused confirmatory tests:
5 passed

full research pytest suite:
PASS

configured optional skips:
2
```

Точный pass count полного quiet suite не выдумывается: лог зафиксировал успешное завершение и два skips.

### После canonical run

```text
strict detached validator:
PASS

independent validation:
PASS

embedded / detached manifest equality:
PASS

canonical evidence digest recomputation:
PASS

canonical manifest digest recomputation:
PASS

840 unit result-digest recomputations:
PASS

420 same-input replay groups:
PASS; 0 mismatches

FILES.sha256 inventory:
PASS
```

Repository `HEAD`, worktree и published remote branch не изменились во время run.

## Outcomes

| Family | Parameterization | Outcome |
|---|---|---|
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-ZERO` | `CONFIRMATORY_ELIGIBLE` |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-ZERO-30D` | `CONFIRMATORY_ELIGIBLE` |

Все 19 required gates прошли у обоих survivors.

### STEP

```text
365-day endpoint unexplained-advantage range:
-0.04534237224396034 to -0.01545876751445053

90→365 cycling-growth range:
-0.05436197195043082 to -0.008160610762557667

maximum absolute baseline delta vs R-CURRENT:
0.0

suppression events:
0

honest-backlog differential range:
0.0 to 0.0

intentional-backlog advantage delta range:
0.0 to 0.0
```

### TAPER

```text
365-day endpoint unexplained-advantage range:
-0.03589059030574444 to -0.014261856317041764

90→365 cycling-growth range:
-0.06013775306156703 to -0.008898854267061052

maximum absolute baseline delta vs R-CURRENT:
0.0

suppression events:
0

honest-backlog differential range:
0.0 to 0.0

intentional-backlog advantage delta range:
0.0 to 0.0
```

### Общие safety results

```text
ordinary successful review:
1.00 RU

Again AttemptCredit:
0.25 RU

direct-button neutrality:
PASS

session invariance:
PASS

response-time positive reward:
ABSENT

response-validity proportionality:
PASS

model-condition sensitivity:
PASS; 32 primary cells per condition per survivor

persona safety:
PASS; no failures

abuse probes:
PASS

research-only boundary:
PASS
```

## Интерпретация

Поддерживается только следующий ограниченный вывод:

> В frozen synthetic confirmatory design оба zero-endpoint survivor воспроизводимо закрыли required 90→365 cycling-growth и endpoint gates на fresh seeds, exact replay, трёх committed cohort conditions, полном synthetic persona catalog и candidate-aware safety probes.

`CONFIRMATORY_ELIGIBLE` означает eligibility для отдельного решения G1.6. Он не означает:

- что STEP лучше TAPER или наоборот;
- что уже выбран финальный research candidate;
- что механизм подтверждён на реальных пользователях;
- что reward formula разрешена в add-on;
- что G1 закрыт;
- что production integration разрешена.

Attribution остаётся synthetic, а root cause — partially localized. Два eligible outcomes оставляют реальную decision boundary для G1.6.

## Production и security boundary

Не изменены:

```text
add-on runtime
dashboard
API/payload
Anki collection access
local server/token behavior
sanitizer/preview
package contents
release workflows
telemetry/remote services
```

Real profile, collection, token и identifiable learning data не использовались.

## Намеренно не выполнялось

```text
Fast CI:
not run — research/docs-only scope

Docker / real-Anki E2E:
not run — production/integration surfaces unchanged

.ankiaddon build:
not run — package contents unchanged

candidate ranking:
prohibited and not performed

final candidate selection:
not performed

production integration:
not performed

G1.6:
not started
```

## Handoff

```text
G1.5: COMPLETE
P-STEP-ZERO: CONFIRMATORY_ELIGIBLE
P-TAPER-ZERO-30D: CONFIRMATORY_ELIGIBLE
ranking: NO
final candidate: NOT SELECTED
production: PROHIBITED
G1.6: NEXT / NOT STARTED
```

G1.6 должен быть активирован отдельной задачей. Этот closeout не принимает решение между STEP и TAPER.
