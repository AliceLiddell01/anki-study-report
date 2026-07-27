# G2.4 — Итоговый отчёт bounded screening Learn XP

## Статус и режим

```text
Mode: ChatGPT
G2.4: COMPLETE
G2: IN PROGRESS
G2.5: NEXT / NOT STARTED
final Learn XP model selected: NO
production approved: NO
production integration: PROHIBITED
```

G2.4 реализовал frozen Learn XP screening protocol, соблюл publication barrier, выполнил полный replacement run из `340` deterministic units и оставил по одному survivor внутри каждой из двух family.

```text
F-CONFIRMATION-ONLY
→ C-CONFIRMATION-ONLY-D1-NOTE-SIBLING

F-PENDING-CONFIRMED-SPLIT
→ C-PENDING-SPLIT-D1-NOTE-SIBLING
```

Эти outcomes являются family-local synthetic research results. G2.4 не сравнивает winners разных families, не выбирает final Learn XP model и не разрешает production integration.

## Repository / branch / PR

```text
repository: AliceLiddell01/anki-study-report
target branch: gamification
task branch: g2-4-learn-xp-bounded-screening
PR: #159
starting HEAD: 933325f8d2647d52cbc0d6859ff44ded0b6686c4
initial pre-results implementation: e89a2309c7a84a477db9e7cd9557f9f1085f15d2
command-provenance correction: ef7c638a70b7bbb7883f512309a1e248118a9203
screened implementation publication SHA: 548b27de6283b32fb27541db02ce6c8b65c29756
final merge SHA: PENDING_UNTIL_VERIFIED_MERGE
```

`final merge SHA` нельзя знать внутри pre-merge closeout commit без нарушения normal-merge workflow. Авторитетная exact identity фиксируется в итоговом ChatGPT-отчёте и PR после verified merge.

## Protocol и continuity

```text
protocol publication SHA: 41313c9369c76d331d489a9aa4b44da2497b3132
human protocol blob: e738514a08f5f25a006914dbf5fe257518f1ed95
machine protocol blob: f2fda31abcc9a9990229a3193d589214222de241
protocol schema blob: 110ce870ee1aaa92f2703237deda59ce8dab4f93
dry generator blob: e5a096985bc544545334edc58f4a55b5f4ef5bcd
fixture manifest blob: f8e60cc8b0ebd3ff20fd66f602543f9aa75c2167
fixture manifest digest: 4e39fa6eb8d95de00765ae65b9efe54c542794f2f541735086707319717d0c93
G2.1 continuity: PASS
G2.2 continuity: PASS
G2.3 continuity: PASS
frozen lifecycle cases: 31
fixtures: 23
screening design changed after results: NO
```

Frozen families, ratios, delays, subject strategies, scenarios, unit IDs, gates, metrics, ordering, status policy, tie policy и missing-data behavior не менялись.

## Реализация

Research-only implementation включает:

- deterministic reward allocation для `confirmation-only` и `pending/confirmed split`;
- D1/D2 confirmation delay policies;
- operational subject strategies `S-CARD` и `S-NOTE-SIBLING`;
- exact manifest, unit execution и canonical digests;
- 23 hard gates и 14 metrics;
- family-local lexicographic selection;
- strict Draft 2020-12 evidence schema;
- detached recomputation;
- installed CLI;
- deterministic external bundle writer;
- focused regression tests.

Production add-on, dashboard, payload/API, scheduler, FSRS, database, package, workflow, release и telemetry surfaces не изменялись.

## Проверки до результатов

Последний pre-results code state был опубликован remote до replacement result access.

```text
regular install: PASS
editable install: false
collection: 1004 tests
full research suite: 1002 passed / 2 skipped / exit 0
full-suite log SHA-256: 405e952644cdb00f91c50fa9b71598ca9a1ba629a653e4e8b75d4704f8a4f21d
source state unchanged: YES
inventory unchanged: YES
local / remote implementation SHA equality: PASS
force push: NO
```

Cargo-dependent tests дали два штатных skip markers, поскольку task-only environment не содержал Cargo. Других failures или errors не было.

## Accounting и evidence identities

```text
expected units: 340
actual units: 340
unique unit IDs: 340
missing units: 0
extra units: 0
duplicate units: 0
replica: 0
seed: null
candidates: 8
reference variants: 2
families: 2
scenarios: 30
hard gates per candidate: 23
metrics per candidate: 14
manifest digest: fafff6ac14b00e268d25a9a7b3553aad94b0e6594b64b40722fd44eba4a91e1a
evidence digest: 5144665ad75110cfd5817b6d76c9791274bf206ee25d01d34ed05e72f45d3da6
evidence.json SHA-256: d0d79802f8512fa40730aac5c377d75021ff39100330483a784c43ce20b09462
external bundle SHA-256: a2578fd2f7540cff10fdde0adc389afeaf8267dbf34185d2378467e6552ffa78
external validation.json SHA-256: 364d46f091eb1e61f85d21dc788ea622bcdcd2673c475093431715a43260a0c0
replacement-run output SHA-256: 2c007ac5b9d8795b4b82088b0a7fc16cc586f5ff1cd99232056155f19990a1a3
```

Проверки bundle:

```text
FILES.sha256: PASS
gzip mtime/name metadata: PASS
tar member mode / mtime / uid / gid / owner names: PASS
archive inventory/order: PASS
detached validation: PASS
reverse-order deterministic replay: PASS
byte-identical reproduction: PASS
old/new evidence mixed: NO
```

Raw `evidence.json`, manifest и archive не коммитятся. Original canonical bundle хранится владельцем вне repository до G2.5/G2.6 или отдельного archive decision.

## Candidate outcomes

| Candidate | Status | First failing gate | Survivor |
| --- | --- | --- | --- |
| `C-CONFIRMATION-ONLY-D1-CARD` | `SCREENING_ELIGIBLE` | — | нет |
| `C-CONFIRMATION-ONLY-D1-NOTE-SIBLING` | `SCREENING_ELIGIBLE` | — | да |
| `C-CONFIRMATION-ONLY-D2-CARD` | `SCREENING_ELIGIBLE` | — | нет |
| `C-CONFIRMATION-ONLY-D2-NOTE-SIBLING` | `SCREENING_ELIGIBLE` | — | нет |
| `C-PENDING-SPLIT-D1-CARD` | `SCREENING_ELIGIBLE` | — | нет |
| `C-PENDING-SPLIT-D1-NOTE-SIBLING` | `SCREENING_ELIGIBLE` | — | да |
| `C-PENDING-SPLIT-D2-CARD` | `SCREENING_ELIGIBLE` | — | нет |
| `C-PENDING-SPLIT-D2-NOTE-SIBLING` | `SCREENING_ELIGIBLE` | — | нет |

References:

```text
R-NO-LEARN-XP-CARD: REFERENCE_ONLY
R-NO-LEARN-XP-NOTE-SIBLING: REFERENCE_ONLY
```

## 23-gate summary

Все `23/23` gates прошли у каждого из восьми candidates; missing evidence отсутствует, first failing gate отсутствует.

```text
GATE-G2-1-CONTINUITY
GATE-G2-2-CONTINUITY
GATE-LIFECYCLE-DIGEST-PARITY
GATE-STRICT-EVENT-TYPES
GATE-NO-STEP-COUNT-GAIN
GATE-NO-AGAIN-FARMING
GATE-NO-HARD-MISREPORT-ADVANTAGE
GATE-NO-RESET-FARMING
GATE-NO-REIMPORT-FARMING
GATE-NO-DUPLICATE-OBJECT-GAIN
GATE-NO-SIBLING-TEMPLATE-GAIN
GATE-SESSION-TIME-INVARIANCE
GATE-CONFIGURATION-INVARIANCE
GATE-INDEPENDENT-CONFIRMATION
GATE-PENDING-IDEMPOTENT
GATE-PENDING-NON-SPENDABLE
GATE-TOTAL-REWARD-CAP
GATE-TERMINAL-DISPOSITION
GATE-DETERMINISTIC-REPLAY
GATE-EVIDENCE-COMPLETENESS
GATE-RESEARCH-ONLY
GATE-NO-REAL-USER-DATA
GATE-NO-PRODUCTION-APPROVAL
```

## 14-metric summary

| Metric | Результат / роль в frozen selection |
| --- | --- |
| `M-PROVISIONAL-ALLOCATION` | `0` confirmation-only; `10.25 LRU` pending-split; descriptive |
| `M-CONFIRMED-ALLOCATION` | `2 LRU` у всех candidates; descriptive |
| `M-UNCONFIRMED-PROVISIONAL-EXPOSURE` | `0`; `3561.75` для pending D1; `7521.75` для pending D2 |
| `M-CONFIRMATION-RATE` | `0.043478260869565216` у всех candidates; descriptive |
| `M-TERMINAL-RATE` | `0.391304347826087` у всех candidates; descriptive |
| `M-TIME-TO-CONFIRMATION` | `1440` synthetic minutes для D1; `4320` для D2 |
| `M-DUPLICATE-GAIN` | `0` у всех candidates |
| `M-STEP-COUNT-GAIN` | `0` у всех candidates |
| `M-RESET-REIMPORT-GAIN` | `0` у всех candidates |
| `M-SESSION-CONFIG-GAIN` | `0` у всех candidates |
| `M-SUBJECT-COLLISION-FRAGMENTATION` | `2` для `S-CARD`; `0` для `S-NOTE-SIBLING` |
| `M-ACTIVE-PENDING-PEAK` | `0` confirmation-only; `1` pending-split |
| `M-INVALID-TERMINAL-RETAINED-LRU` | `0` у всех candidates |
| `M-EXPLANATION-COMPLEXITY-FIELDS` | confirmation `4/5`; pending `6/7` для card / note-sibling |

Selection использовал только exact frozen lexicographic order. Weighted score, Pareto ranking, rescue sweep и post-hoc criterion не добавлялись.

В обеих families `S-NOTE-SIBLING` устраняет synthetic collision/fragmentation count `2 → 0`. Среди равных subject strategies D1 имеет более короткий confirmation delay и, для pending family, меньшую provisional exposure. Эти эффекты объясняют family-local survivors только внутри frozen metric order; они не доказывают human-learning benefit или optimal delay.

## Family outcomes

### `F-CONFIRMATION-ONLY`

```text
outcome: SURVIVOR_SELECTED
survivor: C-CONFIRMATION-ONLY-D1-NOTE-SIBLING
tie: false
```

### `F-PENDING-CONFIRMED-SPLIT`

```text
outcome: SURVIVOR_SELECTED
survivor: C-PENDING-SPLIT-D1-NOTE-SIBLING
tie: false
```

Cross-family ranking не выполнялся.

## Amendments и deviations

### Pre-results command-provenance correction

До canonical result access обнаружено, что `python -m` переносит private launcher path в `sys.argv[0]`. CLI provenance нормализован до публичного `gamification-sim` и опубликован отдельным non-force commit до screening.

### Disclosed post-results harness correction

Первый canonical attempt на `ef7c638a70b7bbb7883f512309a1e248118a9203` открыл results, но признан `INVALID`.

```text
classification: HARNESS
independent root cause: TAR_MEMBER_MODE_INHERITED_FROM_OUTPUT_FILESYSTEM
prior evidence digest: 51ef8d8caa55a2579795a72f5af1576da69da224a5023190d5fde6c145aac726
prior archive SHA-256: 58989ea862be86e2edb0c71b19aec520214af7bb0abe08791d7f72396d66b2c3
results viewed: true
required rerun: FULL_340_UNIT_MATRIX
screening design changed: false
old/new evidence mixed: false
```

Correction меняет только tar member mode с filesystem-derived значения на `0644`. После нового implementation commit был выполнен полный replacement run; selective rerun не использовался.

Substantive protocol amendments отсутствуют.

## Known limitations и G2.5 handoff

Передаются только:

- все восемь candidate statuses;
- два family outcomes и два survivors;
- exact evidence identities;
- disclosed invalid-attempt history;
- synthetic-only claims boundary;
- unresolved confirmatory needs.

Краткие unresolved confirmatory needs:

- устойчивость обоих survivors за пределами текущих frozen synthetic scenarios;
- различимость confirmation-only и pending-split без post-hoc cross-family criterion;
- подтверждение operational `S-NOTE-SIBLING` mapping на реальных Anki identities без чтения private card content;
- human-facing explainability и observability delay/pending behavior;
- отсутствие human learning, motivation и gaming claims до отдельного evidence stage.

G2.5 matrix внутри G2.4 не проектировалась и не запускалась.

## Changed paths

Финальный PR scope:

```text
docs/README.md
docs/ai-handoff.md
docs/gamification/README.md
docs/gamification/learn-xp-bounded-screening.md
research/gamification-sim/README.md
research/gamification-sim/schemas/learn-xp-bounded-screening-evidence-v1.schema.json
research/gamification-sim/src/gamification_sim/cli.py
research/gamification-sim/src/gamification_sim/learn_bounded_screening.py
research/gamification-sim/src/gamification_sim/learn_reward_allocation.py
research/gamification-sim/tests/test_cli.py
research/gamification-sim/tests/test_learn_bounded_screening.py
roadmap/README.md
roadmap/gamification/README.md
roadmap/gamification/g2-learn-xp-bounded-screening.md
```

## Не запускалось

```text
Fast CI
Docker real-Anki E2E
frontend tests
.ankiaddon / package build
master merge
release
deployment
production integration
G2.5
```

Причина: diff ограничен isolated research package и documentation; production/package surfaces не изменялись.

## Production boundary

```text
final Learn XP model selected: NO
production approved: NO
production integration: PROHIBITED
add-on runtime changed: NO
dashboard / API / payload changed: NO
scheduler / FSRS changed: NO
package / release changed: NO
```

Survivors являются research candidates, а не production models.

## Cleanup

До merge:

```text
canonical external replacement bundle: сохранён
prior invalid bundle: quarantined / сохранён
task worktree / branch: ещё существуют
temporary task environments / scripts / logs: ещё существуют
```

После verified merge удалить только linked G2.4 worktree, local/remote task branch, stale tracking ref, temporary scripts/logs, temporary extracted evidence и ненужную task-only environment. Canonical replacement bundle и frozen G2.1–G2.3 sources не удалять.

## Итог

```text
G2.4: COMPLETE
G2.5: NEXT / NOT STARTED
family survivors: 2
cross-family ranking: NO
final model selected: NO
production approved: NO
production integration: PROHIBITED
```
