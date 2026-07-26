# Review XP bounded screening — техническая справка G1.4

**Stage:** `G1.4 — Bounded screening`  
**Status:** `COMPLETE`  
**Research package:** `research/gamification-sim/`  
**Production integration:** `PROHIBITED`  
**Next stage:** `G1.5`, готов, но не начат

Этот документ описывает реализованный screening harness G1.4 и его операционный контракт. Он не заменяет frozen protocol G1.3 и не выбирает финального кандидата Review XP.

## Иерархия источников

При противоречиях используется следующий порядок:

1. актуальный research source code и tests;
2. [machine-readable candidate protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json);
3. [строгая Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json);
4. frozen [человекочитаемое объяснение protocol](review-xp-candidate-protocol.md);
5. [closeout-отчёт G1.4](../../roadmap/gamification/g1-bounded-screening.md).

Human protocol — зафиксированный pre-screening design document G1.3. Его исторический текст о readiness нельзя трактовать как актуальный статус репозитория. Текущее состояние выполнения и результаты записаны в closeout G1.4 и track README.

## Назначение

G1.4 отвечает на один ограниченный вопрос:

> Какие заранее определённые post-transition MemoryGain parameterization остаются eligible для последующей confirmatory работы при frozen matrix G1.3 и non-compensable hard gates?

G1.4 не:

- настраивает coefficients после просмотра результатов;
- выполняет поиск вне четырёх registered parameterization;
- выбирает финального кандидата между семействами;
- доказывает human learning effectiveness или motivation;
- разрешает production reward behavior;
- меняет FSRS, due dates, scheduling или Anki runtime behavior.

## Реализованные компоненты

### Registry candidate mechanisms

`src/gamification_sim/review_candidate_mechanisms.py` определяет:

- `FrozenReviewCandidate` — immutable typed identity parameterization;
- `RewardExecutionContext` — simulation day и structural retention-transition days;
- `FROZEN_REVIEW_CANDIDATES` — ровно четыре registered parameterization;
- `memory_gain_multiplier()` — единственное mechanism-specific вычисление multiplier;
- semantic validation относительно frozen machine protocol.

Registry содержит ровно:

| Family | Parameterization | Endpoint | Shape |
|---|---|---:|---|
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-ZERO` | `0.0` | immediate step |
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-NEUTRAL-RATIO` | `0.8333333333333334` | immediate step |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-ZERO-30D` | `0.0` | linear 30-day taper |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-NEUTRAL-RATIO-30D` | `0.8333333333333334` | linear 30-day taper |

`R-CURRENT` является regression reference. Он не candidate и не может получить survivor или promotion status.

### Подключение reward path

Candidate path проходит через:

- `episode_reward.py`;
- `day_aggregation.py`;
- `longitudinal_runner.py`.

Масштабируется только contribution MemoryGain. Attempt credit, outcome credit, support credit, completion credit, volume credit и всё scheduling behavior остаются неизменными.

Когда candidate parameterization не передана, runner вызывает исходный default path. Clean-HEAD parity доказал, что `R-CURRENT` создаёт одинаковые trajectory, final-cohort, report и full-payload digests с wiring G1.4 и без него.

### Screening harness

`src/gamification_sim/bounded_screening.py` предоставляет:

- загрузку и semantic validation protocol/schema;
- typed identities `ScreeningExecutionUnit`;
- deterministic построение manifest из 160 units;
- per-unit выполнение matched policies;
- извлечение compact evidence;
- evaluation защищённых invariants;
- 16 non-compensable hard gates на candidate;
- result validation и canonical digest evidence;
- запись external reports.

### CLI surface

Research CLI предоставляет две команды G1.4:

```text
validate-bounded-screening
run-bounded-screening
```

## Семантика day и transition

Авторитетным источником является machine protocol.

### Семейство STEP

```text
day < 60  → multiplier 1.0
day >= 60 → registered endpoint multiplier
```

### Семейство TAPER

```text
day <= 60     → multiplier 1.0
60 < day < 90 → linear interpolation from 1.0 to endpoint
day >= 90     → registered endpoint multiplier
```

Последний transition обязан структурно происходить на day `60`. Если переданный retention timeline не заканчивается на зарегистрированном start day candidate, multiplier остаётся `1.0`.

Механизм использует simulation day и policy retention timeline. Он никогда не определяет применимость через:

- session boundaries;
- wall-clock time;
- UI state;
- response duration;
- Anki profile data.

Boundary tests покрывают days `59`, `60`, `61`, `89`, `90` и `91`.

Fallback `STEP from day 61` не является авторитетной семантикой и не применяется.

## Зафиксированная execution matrix

`ScreeningExecutionUnit` — tuple:

```text
(candidate_or_reference,
 policy_pair,
 control_condition,
 horizon,
 replica,
 seed,
 population_variant)
```

Оси:

| Axis | Values | Count |
|---|---|---:|
| candidate/reference | `R-CURRENT` + четыре registered parameterization | 5 |
| policy pair | четыре frozen cases | 4 |
| control condition | `MATCHED_CONTROL_FROM_CASE` | 1 |
| horizon | `90`, `365` | 2 |
| replica | `0`, `1` | 2 |
| seed | `20260716`, `20260717` | 2 |
| population | `CANONICAL_SYNTHETIC_COHORT` | 1 |

```text
5 × 4 × 1 × 2 × 2 × 2 × 1 = 160 units
```

`candidate_or_reference` — самостоятельная axis variants.

Поле `parameterization` не является дополнительной axis и не отражает потерю dimension. Оно детерминированно выводится в payload:

```text
R-CURRENT → parameterization: null
candidate → parameterization: <variant ID>
```

Это normalization representation.

`required_invariant_checks` — metadata, проверяемая по evidence, а не execution axis.

Каждый unit получает canonical digest-based `unit_id`. Manifest fail closed, если в нём не ровно 160 units, 160 unique IDs и нулевые missing, extra и duplicate units.

## Policy cases

Четыре protocol cases сопоставляются актуальным matched-analysis policy pairs:

| Protocol case | Matched pair |
|---|---|
| `CASE-RETENTION-HIGH` | `retention-high-cycle` |
| `CASE-RETENTION-LOW` | `retention-low-cycle` |
| `CASE-INTENTIONAL-BACKLOG` | `intentional-backlog` |
| `CASE-HONEST-BACKLOG-RETURN` | `honest-backlog-return` |

В каждом unit left и right policy execution обязаны иметь одинаковые initial cohort digest и latent stream ID. Несовпадение прерывает evidence generation.

## Validation command

Из `research/gamification-sim/` при доступном `src`:

```bash
python -m gamification_sim   --research-root .   validate-bounded-screening
```

Валидный результат:

```text
VALID review-xp-bounded-screening-manifest-v1 160 unique units <manifest-digest>
```

Команда валидирует semantics protocol/schema и пересчитывает точный manifest. Simulations она не запускает.

## Screening command

Canonical G1.4 run использовал published implementation commit до просмотра результатов:

```bash
python -m gamification_sim   --research-root .   run-bounded-screening   --implementation-sha a8857f111849e2e98744adda8e06fe1910bdf805   --base-sha 54dd47cc2817b9c07fad81da29fa666a0423c4e7   --output-dir <external-output-root>
```

Runner требует:

- оба SHA в lowercase 40-character hexadecimal form;
- текущий `HEAD` равный `--implementation-sha`;
- `--base-sha`, являющийся ancestor implementation;
- валидные frozen protocol, schema, config и candidate registry;
- ровно 160 manifest units.

Canonical result нельзя регенерировать с post-merge `gamification` HEAD: screened identity — published implementation commit, а не более поздний merge commit. Для review используются записанные evidence identities. Любая будущая reproduction должна выполняться в isolated checkout screened implementation и не должна смешиваться с новым G1.5 experiment.

## Evidence output

Writer создаёт:

```text
<output-root>/bounded-screening/<evidence-digest-prefix>/
  evidence.json
  manifest.json
  summary.md
  run-metadata.json
```

### `evidence.json`

Содержит:

- provenance implementation/base/branch и environment;
- полный manifest;
- все 160 compact unit results;
- per-candidate gate evidence;
- canonical `evidence_digest`.

### `manifest.json`

Содержит identities protocol/schema/config, frozen axes, exact accounting и все unit definitions.

### `summary.md`

Содержит человекочитаемую таблицу PASS/REJECT. Это projection evidence, а не normative artifact.

### `run-metadata.json`

Содержит write-time metadata и identity evidence. Timestamp не входит в scientific result digest.

Generated screening output остаётся вне Git. Repository documentation хранит immutable digests и bounded summaries, а не raw payload.

Политика external evidence:

- original bundle хранится вне Git и не изменяется;
- repository хранит identities и semantic summary;
- unit-level audit требует raw bundle;
- bundle сохраняется минимум до завершения G1.5/G1.6 либо отдельного archive decision.

Точные identities:

```text
G1.4 historical merge SHA:
d855baf7355bba3f4014370cafba3fdc6d0c0e3c

current gamification HEAD at G1.5 task start:
f595a47ecaaaf93cf345978de052cf4f4747b8ef

manifest digest:
40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c

evidence digest:
836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694

external evidence bundle SHA-256:
bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be

evidence.json SHA-256:
976e728df07fdf46c8e6037f79a5b81fd5ee3b0293d70f6ab03e4a0259483b5c
```

Перед G1.5 external bundle повторно прошёл read-only validation:

```text
expected / actual unique:
160 / 160

missing / extra / duplicates:
0 / 0 / 0

validator:
PASS
```

## Hard gates

Каждый candidate обязан независимо пройти все 16 gates:

1. `GATE-ENDPOINT-CAP`;
2. `GATE-NO-CYCLING-GROWTH`;
3. `GATE-BASELINE-PRESERVED`;
4. `GATE-ZERO-SUPPRESSION`;
5. `GATE-HONEST-BACKLOG-FAIRNESS`;
6. `GATE-NO-BACKLOG-GAIN`;
7. `GATE-ORDINARY-UNIT`;
8. `GATE-AGAIN-CREDIT`;
9. `GATE-BUTTON-NEUTRAL`;
10. `GATE-SESSION-INVARIANT`;
11. `GATE-NO-RESPONSE-TIME-REWARD`;
12. `GATE-RESPONSE-VALIDITY`;
13. `GATE-DETERMINISTIC-REPLAY`;
14. `GATE-SECONDARY-SEED`;
15. `GATE-EVIDENCE-COMPLETE`;
16. `GATE-RESEARCH-ONLY`.

Aggregate score, weighted compensation, Pareto rescue и least-bad promotion отсутствуют. Один failed hard gate даёт `REJECT`.

## Интерпретация результата

G1.4 дал по одному survivor в каждом семействе:

```text
F-POST-TRANSITION-MG-STEP
→ P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER
→ P-TAPER-ZERO-30D
```

Neutral-ratio variants были отклонены только по `GATE-NO-CYCLING-GROWTH`. Их остальные safety, baseline, fairness и evidence gates прошли, но исходная cross-horizon growth problem сохранилась в required cells.

Survivor G1.4 означает только:

- parameterization прошла frozen bounded screening gates;
- она eligible для отдельно разрешённой confirmatory работы G1.5;
- в её семействе сохранилась не более чем одна parameterization.

Survivor не означает:

- выбор финального candidate;
- превосходство STEP или TAPER;
- production readiness;
- benefit для человеческого обучения или motivation;
- разрешение менять reward economy add-on.

## Reproducibility identities и источник acceptance

```text
base SHA:
54dd47cc2817b9c07fad81da29fa666a0423c4e7

screened implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

G1.4 historical merge SHA:
d855baf7355bba3f4014370cafba3fdc6d0c0e3c

current gamification HEAD at G1.5 task start:
f595a47ecaaaf93cf345978de052cf4f4747b8ef

manifest digest:
40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c

evidence digest:
836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694

external evidence bundle SHA-256:
bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be
```

G1.4 local research verification прошла согласно closeout ledger и являлась источником acceptance. GitHub combined status checks не были источником acceptance. Их отсутствие не требует rerun.

## Testing boundary

Реализация была проверена через:

- clean-HEAD parity `R-CURRENT`;
- boundary и registry tests;
- focused reward/aggregation/runner tests;
- tests manifest и gate evaluator;
- полный research pytest suite после последнего изменения code;
- независимую validation evidence и unit digests.

Fast CI, Docker/real-Anki E2E и `.ankiaddon` packaging намеренно не запускались, потому что изменения изолированы в research/docs и не затрагивают production/package surfaces.

## Production и security boundary

Implementation G1.4 не имеет пути в:

- add-on runtime;
- dashboard payloads или API;
- Anki collection access;
- local server/token handling;
- sanitizer или preview behavior;
- package/release workflows;
- telemetry или remote services.

Simulator потребляет deterministic synthetic inputs. В него запрещено передавать real profile exports, collection data, tokens или user-identifying records.

## Передача в G1.5

G1.5 остаётся отдельным этапом и должен запускаться явно. Он может использовать только двух зарегистрированных survivors и frozen confirmatory boundary.

G1.5 не должен молча:

- возвращать rejected neutral-ratio variants;
- менять thresholds G1.4 после просмотра results;
- считать два семейства уже ранжированными;
- называть любой survivor production-ready;
- вливать `gamification` в `master`.
