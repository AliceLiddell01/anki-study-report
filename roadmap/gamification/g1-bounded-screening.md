# G1.4 — Полный отчёт bounded screening

## Итоговая сводка

G1.4 завершён.

Этап восстановил и интегрировал ранее незавершённый механизм кандидатов Review XP, доказал неизменность поведения `R-CURRENT` по умолчанию, опубликовал реализацию до просмотра результатов screening, выполнил ровно зафиксированную матрицу из 160 units и зарегистрировал по одному survivor в каждом семействе кандидатов.

```text
G1.4: COMPLETE
G1.5: NEXT / READY; NOT STARTED
final candidate selected: NO
production integration: PROHIBITED
```

Survivors на уровне семейств:

```text
F-POST-TRANSITION-MG-STEP
→ P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER
→ P-TAPER-ZERO-30D
```

Обе parameterization с neutral-ratio были отклонены только по `GATE-NO-CYCLING-GROWTH`. Все остальные hard gates и защищённые invariants у них прошли.

G1.4 не ранжирует STEP относительно TAPER, не выбирает финального кандидата Review XP и не разрешает production integration.

Реализованный command surface и операционный контракт описаны в [технической справке G1.4](../../docs/gamification/review-xp-bounded-screening.md).

## Финальное состояние репозитория и доставки

```text
canonical branch:
gamification

pre-G1.4 base SHA:
54dd47cc2817b9c07fad81da29fa666a0423c4e7

screened implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

closeout commit SHA:
678ca6a229218a2a7c301aab3d38d4e0105b24cb

PR:
#146

G1.4 historical merge SHA:
d855baf7355bba3f4014370cafba3fdc6d0c0e3c

current gamification HEAD at G1.5 task start:
f595a47ecaaaf93cf345978de052cf4f4747b8ef
```

`d855baf7355bba3f4014370cafba3fdc6d0c0e3c` — исторический merge SHA этапа G1.4. Он не является текущим `gamification` HEAD: к началу задачи G1.5 каноническая ветка уже находилась на `f595a47ecaaaf93cf345978de052cf4f4747b8ef`.

PR #146 был влит обычным двухродительским merge commit. После проверки канонического merge удалённая task-ветка, локальная task-ветка, remote-tracking ref и linked task worktree были удалены.

Несвязанный canonical checkout владельца оставался на своей ветке Core remediation и не переключался, не сбрасывался и не очищался процессом G1.4.

## Назначение этапа

G1.3 зафиксировал два семейства механизмов post-transition MemoryGain и четыре заранее определённые parameterization. У G1.4 была одна ограниченная ответственность:

> Реализовать зафиксированный механизм без изменения семантики protocol, выполнить ровно зарегистрированную матрицу и оставить не более одной прошедшей parameterization в каждом семействе для последующей confirmatory работы.

Этапу запрещалось:

- изменять protocol, schema, coefficient endpoints или thresholds после просмотра результатов;
- добавлять variants, seeds, replicas, horizons, policy pairs или populations;
- выполнять adaptive search или rescue search;
- выбирать финального кандидата между двумя семействами;
- менять FSRS или scheduling behavior;
- изменять production add-on, dashboard, API, package или release surfaces;
- автоматически начинать G1.5.

## Авторитетные входные данные

Этапом управляли следующие зафиксированные источники:

- [человекочитаемый protocol G1.3](../../docs/gamification/review-xp-candidate-protocol.md);
- [machine protocol](../../research/gamification-sim/contracts/review-xp-candidate-protocol-v1.json);
- [строгая Draft 2020-12 schema](../../research/gamification-sim/schemas/review-xp-candidate-protocol-v1.schema.json);
- актуальная longitudinal configuration `configs/review-longitudinal-v0.1.json`;
- актуальный каталог matched policy pairs;
- актуальный research source и tests ветки `gamification`.

При определении day-60 boundary machine protocol имел более высокий приоритет, чем историческая fallback-формулировка.

## Научная исходная точка

После G1.2a root cause Review XP оставался локализован только частично:

```text
classification: ROOT_CAUSE_PARTIALLY_LOCALIZED
confidence: MEDIUM
largest component: memory_main
memory_main share: 0.4552230855238075
dominant timing window: post_transition
post_transition share: 0.8565121323195105
Challenge direction-consistent: false
```

Attribution был синтетическим и post-hoc. Он позволял сформулировать ограниченные prospective hypotheses, но не доказывал существование единственной правильной reward formula.

## История восстановления и интеграции

### Отсутствующий исходный worktree

При возобновлении G1.4 прежние локальные implementation worktree и branch уже отсутствовали. Сохранились:

- implementation backup;
- backup metadata worktree;
- старый baseline worktree;
- task-specific Python 3.11.9 environment.

Destructive repair, reset, clean и слепое применение patch не выполнялись.

### Целостность backup

Перед использованием recovery bundle был независимо проверен:

```text
recorded working files: 8
manifest files: 8
snapshot files: 8
missing files: 0
extra files: 0
artifact hash failures: 0
working-file hash failures: 0
patch failures: 0
result: BACKUP_INTEGRITY_PASS
```

Восстановленная реализация состояла из шести изменённых и двух новых файлов research package.

### Интеграция на актуальный `gamification`

Старая реализация была основана на более раннем состоянии репозитория и не копировалась целиком поверх актуальной ветки.

Свежий linked worktree был создан от точного `origin/gamification` SHA `54dd47cc2817b9c07fad81da29fa666a0423c4e7`. Сначала tracked patch был проверен на этой базе, затем восстановлены шесть tracked changes и два новых файла. Dirty set обязан был содержать ровно эти восемь путей.

### Доказательство совместимости `R-CURRENT`

Один восстановленный regression test содержал digest constants со старой базы и первоначально падал на актуальной базе.

Production/research implementation не изменялась ради устаревшего checkpoint. Вместо этого чистая копия актуального `HEAD` и восстановленная реализация были запущены в отдельных Python processes с одинаковыми config, seed и parameter set `R-CURRENT`.

Точно совпали:

- manifest trajectory digest;
- final-cohort digest;
- report digest;
- каждый policy trajectory digest;
- SHA-256 полного serialized payload;
- отсутствие candidate metadata.

```text
DEFAULT_R_CURRENT_PARITY_PASS
```

Только после этого constants regression test были обновлены до актуальных pre-wiring digests.

## Архитектура реализации

Опубликованный implementation commit менял только 11 research source/test paths:

```text
research/gamification-sim/src/gamification_sim/bounded_screening.py
research/gamification-sim/src/gamification_sim/cli.py
research/gamification-sim/src/gamification_sim/day_aggregation.py
research/gamification-sim/src/gamification_sim/episode_reward.py
research/gamification-sim/src/gamification_sim/longitudinal_runner.py
research/gamification-sim/src/gamification_sim/review_candidate_mechanisms.py
research/gamification-sim/tests/test_bounded_screening.py
research/gamification-sim/tests/test_day_aggregation.py
research/gamification-sim/tests/test_episode_reward.py
research/gamification-sim/tests/test_longitudinal_runner.py
research/gamification-sim/tests/test_review_candidate_mechanisms.py
```

### Зафиксированный candidate registry

`review_candidate_mechanisms.py` добавил:

- immutable typed candidate definitions;
- точные family и parameterization identities;
- зарегистрированные endpoint multipliers;
- typed simulation execution context;
- вычисление day/window multiplier;
- семантическое согласование с machine protocol.

Registry отклоняет неизвестные parameterization, недопустимые bounds, неверные mechanism classes и применение candidate с чем-либо, кроме `R-CURRENT`.

### Подключение reward path

Candidate identity и execution context проходят через episode evaluation, daily aggregation и longitudinal policy execution.

Масштабируется только MemoryGain. Не меняются:

- ordinary attempt credit;
- successful outcome credit;
- Again attempt credit;
- support и supplemental reward terms;
- completion и volume credit;
- scheduler и FSRS semantics;
- due dates и intervals;
- direct button behavior;
- response-time behavior;
- default execution `R-CURRENT`.

### Bounded screening harness

`bounded_screening.py` добавил:

- validation protocol/schema;
- validation точного registry;
- typed deterministic execution-unit identities;
- построение точного manifest из 160 units;
- выполнение matched policy pairs;
- compact unit evidence и canonical digests;
- проверки защищённых invariants;
- 16 hard gates на candidate;
- fail-closed validation результата;
- writer внешнего evidence и человекочитаемую summary.

### CLI

Research command surface получил:

```text
validate-bounded-screening
run-bounded-screening
```

Run command требует точные implementation/base SHA и записывает exact command в provenance evidence.

## Семантика day 60

Зафиксированный machine protocol определяет следующее поведение.

### STEP

```text
day < 60  → multiplier 1.0
day >= 60 → frozen endpoint
```

### TAPER

```text
day <= 60     → multiplier 1.0
60 < day < 90 → linear interpolation from 1.0 to endpoint
day >= 90     → frozen endpoint
```

Механизм активен только тогда, когда последний structural retention transition policy приходится на day `60`. Используются simulation day и retention timeline, но не wall clock и не session boundaries.

Boundary tests покрывают days `59`, `60`, `61`, `89`, `90` и `91`.

Fallback `STEP from day 61` не является авторитетной семантикой и не применяется.

## Publication barrier

Реализация была committed и pushed до просмотра любого canonical screening result.

```text
published implementation SHA:
a8857f111849e2e98744adda8e06fe1910bdf805

local/remote SHA equality:
PASS

result files present in implementation commit:
NO
```

После публикации mechanism, matrix, thresholds, seeds, replicas, horizons, population и hard-gate semantics были заморожены для run.

## Реестр проверок

### Recovery и compatibility

```text
backup integrity: PASS
restore onto current gamification base: PASS
git diff --check after restore: PASS
R-CURRENT clean-HEAD parity: PASS
single R-CURRENT regression: 1 passed
```

### Focused verification

```text
mechanism/reward/runner focused suite: 161 passed
focused suite after screening harness: 173 passed
protocol/schema semantic validation: PASS
exact manifest recomputation: 160 unique units
git diff --check: PASS
```

### Full research verification

```text
full research pytest suite after final code change: PASS
Cargo-dependent skips shown by configured suite: 2
implementation local/remote SHA equality: PASS
```

Quiet full-suite output не предоставил надёжного точного pass count, поэтому в отчёте он не выдумывается.

Источником acceptance G1.4 была локальная research verification, зафиксированная в closeout ledger. GitHub combined status checks не использовались как источник acceptance; их отсутствие не требует rerun G1.4.

### Проверка evidence

После canonical run:

- SHA-256 bundle совпал с записанным значением;
- archive содержал только ожидаемые result files;
- `evidence.json` прошёл implementation validator;
- отдельный `manifest.json` совпал с embedded manifest;
- digests всех 160 units были пересчитаны и совпали;
- provenance evidence соответствовал published implementation/base SHA;
- identities evidence и run-metadata совпали;
- repository `HEAD` и working state не изменились из-за run.

Повторная read-only проверка перед G1.5 также подтвердила:

```text
bundle SHA-256:
bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be

evidence.json SHA-256:
976e728df07fdf46c8e6037f79a5b81fd5ee3b0293d70f6ab03e4a0259483b5c

validator:
PASS

expected / actual unique:
160 / 160

missing / extra / duplicates:
0 / 0 / 0
```

## Identity screening

```text
machine protocol Git blob:
6bfec56821045b6d383f2926fab79f151157ad13

strict schema Git blob:
f211dc2099d6c1ea6fbe760b7693e66119127fa6

manifest digest:
40297310ef11318f940ddee8a6f5e1d1b20df93d914c4d7442eb4681f60da57c

evidence digest:
836b069046c6173190bf21b6f6c1e03613f9dc2fe6083327513df9d2205fe694

external evidence bundle SHA-256:
bdc2b9e25ce65937f7e01cdb96c67c1cb7444361253d0399ebb5662ba093b8be

evidence.json SHA-256:
976e728df07fdf46c8e6037f79a5b81fd5ee3b0293d70f6ab03e4a0259483b5c
```

Raw evidence имеет размер около 1 MiB и находится вне Git. Репозиторий хранит immutable identities и bounded semantic summary, а не дублирует machine payload в Markdown.

Политика external evidence:

- original raw bundle не изменяется;
- repository хранит identities, provenance и semantic summary;
- unit-level audit требует доступа к raw bundle;
- bundle не удаляется до завершения G1.5/G1.6 либо до отдельного archive decision;
- отсутствие GitHub status checks не заменяет и не отменяет локальную validation bundle.

## Учёт зафиксированной матрицы

Screening unit:

```text
(candidate_or_reference,
 policy_pair,
 control_condition,
 horizon,
 replica,
 seed,
 population_variant)
```

`candidate_or_reference` является самостоятельной осью variants.

Поле `parameterization` не является отдельной потерянной dimension. Оно детерминированно выводится при сериализации payload:

```text
R-CURRENT → parameterization: null
candidate → parameterization: <variant ID>
```

Это normalization representation, а не потеря измерения.

Размерности матрицы:

```text
candidate/reference variants: 5
policy pairs: 4
control conditions: 1
horizons: 2
replicas: 2
seeds: 2
population variants: 1

5 × 4 × 1 × 2 × 2 × 2 × 1 = 160
```

Финальный accounting:

```text
expected units: 160
actual units: 160
actual unique units: 160
missing: 0
extra: 0
duplicates: 0
```

`required_invariant_checks` корректно рассматривался как metadata, а не как дополнительная axis матрицы.

## Политика hard gates

Каждый candidate обязан был независимо пройти все 16 non-compensable gates:

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

Weighted score, Pareto compensation, least-bad choice и post-hoc threshold adjustment не разрешались.

## Результаты screening

| Family | Parameterization | Result | Gate result |
|---|---|---|---|
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-ZERO` | PASS | 16/16 PASS |
| `F-POST-TRANSITION-MG-STEP` | `P-STEP-NEUTRAL-RATIO` | REJECT | failed only `GATE-NO-CYCLING-GROWTH` |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-ZERO-30D` | PASS | 16/16 PASS |
| `F-POST-TRANSITION-MG-TAPER` | `P-TAPER-NEUTRAL-RATIO-30D` | REJECT | failed only `GATE-NO-CYCLING-GROWTH` |

### Прошедшая STEP parameterization

`P-STEP-ZERO` прошёл все gates.

```text
required cross-horizon growth range:
-0.0371046033 to -0.0004580763
```

Каждая required retention growth cell была non-positive с учётом frozen tolerance.

### Отклонённая STEP parameterization

`P-STEP-NEUTRAL-RATIO` не прошёл только cycling-growth gate.

```text
positive required growth cells: 5 / 8
maximum positive growth: +0.0175703395
```

Его baseline, suppression, fairness, backlog, unit-credit, button, session, response-validity, replay, seed, completeness и research-only gates прошли.

### Прошедшая TAPER parameterization

`P-TAPER-ZERO-30D` прошёл все gates.

```text
required cross-horizon growth range:
-0.0406010767 to -0.0024101933
```

Каждая required retention growth cell была non-positive с учётом frozen tolerance.

### Отклонённая TAPER parameterization

`P-TAPER-NEUTRAL-RATIO-30D` не прошёл только cycling-growth gate.

```text
positive required growth cells: 5 / 8
maximum positive growth: +0.0172449867
```

Остальные 15 gates прошли.

## Защищённые invariants

Все четыре candidate parameterization сохранили следующие наблюдаемые invariants:

```text
ordinary successful review: 1.00 RU
Again AttemptCredit: 0.25 RU
baseline delta vs R-CURRENT: 0
suppression events: 0
honest backlog differential vs reference: 0
intentional backlog advantage delta vs reference: 0
direct-button neutrality: PASS
session invariance: PASS
no response-time reward: PASS
response-validity proportionality: PASS
deterministic replay: PASS
secondary seed present: PASS
evidence completeness: PASS
research-only classification: PASS
```

Rejected variants не были unsafe по этим dimensions. Они были отклонены потому, что не закрыли исходный cross-horizon cycling-growth gap.

## Решение о survivors

В каждом семействе зарегистрирован ровно один survivor:

```text
F-POST-TRANSITION-MG-STEP:
P-STEP-ZERO

F-POST-TRANSITION-MG-TAPER:
P-TAPER-ZERO-30D
```

`R-CURRENT` остаётся regression/reference control и не имеет survivor eligibility.

Статус survivor означает только, что зарегистрированная parameterization прошла bounded screening gates G1.4 и может войти в отдельно разрешённый confirmatory этап G1.5.

G1.4 не утверждает, что:

- STEP лучше TAPER;
- TAPER лучше STEP;
- любой survivor является финальным кандидатом Review XP;
- любой survivor улучшает человеческое обучение или мотивацию;
- любой survivor подходит для production.

## Научная интерпретация

Поддерживается только узкий вывод:

> В рамках текущей synthetic model и frozen matrix полное удаление post-transition MemoryGain закрыло required cross-horizon growth gate как для immediate STEP, так и для 30-day TAPER, тогда как neutral-ratio endpoints этого не сделали.

Это evidence о проверенном synthetic mechanism, а не доказательство универсального causal rule.

Результат не устраняет прежнюю неопределённость partial root-cause localization. Он сужает последующую confirmatory работу до двух zero-endpoint variants, но их прохождение может быть обусловлено сочетанием MemoryGain effects и model-specific dynamics.

## Production boundary

Ни одна production surface не изменилась.

```text
add-on runtime: unchanged
dashboard: unchanged
API/payload: unchanged
Anki collection access: unchanged
local server/token behavior: unchanged
preview/sanitizer: unchanged
package contents: unchanged
release workflows: unchanged
telemetry/remote services: unchanged
```

Simulator остаётся research-only и использует deterministic synthetic inputs. Real user profile, collection, token или identifiable learning data не использовались.

## Проверки, намеренно не запускавшиеся

```text
Fast CI:
not run — research-only diff outside package/Fast CI scope

Docker / real-Anki E2E:
not run — runtime and integration surfaces unchanged

.ankiaddon build:
not run — package contents unchanged

G1.5 confirmatory matrix:
not started

adaptive/rescue sweep:
prohibited and not run

extra variants, seeds, replicas, horizons or populations:
not run

master/release/deployment:
untouched
```

## Передача в G1.5

G1.5 остаётся отдельным существующим этапом. Он может использовать только:

```text
R-CURRENT
P-STEP-ZERO
P-TAPER-ZERO-30D
```

Rejected neutral-ratio variants не возвращаются без отдельного protocol amendment.

```text
G1.4: COMPLETE
G1.5: NEXT / READY; NOT STARTED
final candidate selected: NO
production integration: PROHIBITED
```
