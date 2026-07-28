# C2 — PR #130 final integration closeout

**Дата:** 2026-07-29

**Репозиторий:** `AliceLiddell01/anki-study-report`

**PR:** `#130`

**Base / integration branch:** `core`

**Рабочая ветка PR:** `c2-manual-acceptance-remediation`

**Статус:** merged; exact merged package прошёл Fast CI и real-Anki
`standard/full` с restart

## Итог

```text
PR #130: MERGED INTO CORE
Inspection Profiles: COMPLETE FOR C2 CLOSEOUT
Fast CI: PASS ON MERGED CORE
real-Anki standard/full: PASS ON MERGED CORE
Cards: ACCEPTED / COMPLETE / FROZEN
C3: NOT STARTED
release/master: NOT TOUCHED
```

Closeout завершил оставшиеся Inspection Profiles WP3–WP6, разрешил
расхождения с развившейся `core`, влил PR merge commit и проверил один exact
post-merge package. Numerical visual score и owner visual acceptance для
Inspection Profiles не присваивались: visual evidence остаётся объективным
набором screenshots, geometry, interactions, accessibility results и честным
deviation ledger.

## Исходная Git identity

```text
initial PR head:
5241e0f1068aa17998456bead90b7b72dacfc747

initial origin/core:
040d64b88a3ec20127bc79c9c607bca9f0b6ea42

merge base:
62cd4c1fc1dda6354f3e30cb3ae4aee5dfb4891f

initial branch divergence:
ahead 14 / behind 173
```

Ветка была синхронизирована обычным merge commit
`63bb45252cb4a1384bb1c3f8336a0401fce6ceba`. Rebase, force-push и
переписывание истории не применялись.

Конфликты были ограничены `AGENTS.md` и `docs/ai-handoff.md`. Разрешение
сохранило актуальные правила `core`, task-scope guard, Cards frozen boundary,
современные CI/E2E contracts и релевантную историю PR.

## Завершённые работы

### WP3 Basic correction

- Basic остаётся двухколоночным при ширине 1024 px и схлопывается только ниже
  container threshold;
- QHD использует доступную ширину editor, но form controls ограничены по
  ширине;
- aggregate и per-control validation направляют пользователя к точной Basic
  группе или control;
- правило «оставить хотя бы один template» явно связано с checkbox group;
- add/remove requirements сохраняют детерминированный keyboard focus.

### WP4 Advanced

- реализован authored strict editor для mappings, checks и templates;
- QHD показывает три упорядоченные колонки;
- редактируются stable role/check IDs и все шесть check kinds;
- смена discriminated `kind` удаляет несовместимые поля без смены check ID;
- role references обновляются при rename, а missing role/template references
  остаются видимыми и исправимыми;
- duplicate/invalid IDs, duplicate/missing roles и `minLength` вне диапазона
  блокируют сохранение на точном control.

### WP5 states, validation и accessibility

- покрыты loading, load error, unavailable store, empty, no matches, dirty
  draft, backend validation, revision conflict и tools confirmation;
- Basic/Advanced используют один draft и сохраняют изменения при переключении;
- validation summary переводит focus сначала на summary, затем на точный
  Basic/Advanced control;
- shared popup triggers публикуют `aria-controls` только пока menu существует
  в DOM;
- семь full-shell axe сценариев прошли без exclusions, violations или
  incomplete результатов.

### WP6 evidence

Внешний artifact:

```text
C:\Users\KykLa\Documents\Anki Study Report Evidence\
  pr130-inspection-profiles-final-evidence.zip

size:
14601672 bytes

SHA-256:
fd601b3f6d22f65d13a0720eb4e5ef4ce261cc00183a90acdad0e1fdd4b5f0ba

prototype archive SHA-256:
48f3ace56b11f0dd328709923a99bb7277b0747f2cbc489e00dee7821f6bf8f9
```

Artifact содержит 29 full-page captures, 56 region captures, 29 ARIA
snapshots, unmasked Basic/Advanced comparisons, page-space и viewport-space
geometry, interactions, network/console ledgers, reports и exact harness
source. Inventory: 158 payload files; `SHA256SUMS`: 159 entries; checksum
mismatches: 0; ZIP entries: 160; full-entry CRC failures: 0.

Deviation ledger не содержит OPEN blocker, major correctness, major
accessibility или methodology blocker. Он честно оставляет `PARTIAL` для
presentational differences между старым prototype frame и развившимся
production shell, а также для exact pixel parity Basic/Advanced. Это не
выдаётся за misleading `1:1`.

## Локальная проверка

| Проверка | Результат |
| --- | --- |
| focused Profiles/shared-shell/Cards Vitest | PASS — 13 files / 89 tests |
| `pnpm run test:frontend` | PASS — 75 files / 401 tests |
| `pnpm run build:addon` | PASS — 2285 modules; 21 JS chunks |
| `node scripts/run_python.mjs -m pytest` | PASS — 1124 passed / 9 skipped |
| `node scripts/run_python.mjs -m compileall -q anki_study_report` | PASS |
| `node scripts/run_python.mjs scripts/check_task_scope.py` | PASS |
| `git diff --check` | PASS |
| `.\scripts\run_full_check.ps1 -SkipDocker` | PASS |
| final Windows browser evidence harness | PASS |

Первый параллельный запуск pytest/compileall был отвергнут как
невалидный: compileall создал `__pycache__` во время hygiene test. Caches были
перемещены за пределы repository, после чего pytest, compileall и canonical
full check выполнены последовательно и прошли. Canonical full check вывел один
Windows-only warning декодирования `cp932`; test failure не было.

## Merge identity

```text
final PR head:
2724e14f01d8569778d7331154d78b89730b4b30

merge commit / merged core SHA:
57eeca039247ab0522555b1292fc1f25c66976fd

merged core tree:
5a0a36d328287b98dd3f169806d83f35cf905666
```

PR был переведён из draft только после clean/mergeable проверки и отсутствия
open review threads. Использован merge commit с exact-head guard; squash,
rebase, admin bypass и force не применялись.

## Post-merge Fast CI

```text
run:
30408497011

URL:
https://github.com/AliceLiddell01/anki-study-report/actions/runs/30408497011

event/ref/result:
workflow_dispatch / refs/heads/core / success

testedCommitSha/sourceHeadSha:
57eeca039247ab0522555b1292fc1f25c66976fd
```

Artifacts:

```text
diagnostics:
ID 8707548201
ci-fast-30408497011-1
sha256:685f3ec16045cb149971659f30fb83c3302745590e73e853b0ca5aad8f42d0ec

package:
ID 8707548784
ci-package-57eeca039247ab0522555b1292fc1f25c66976fd-30408497011-1
sha256:69cec3a3e05ba9f69d08ae4dc6b992c45bf40a8175faf1002671b9b80ee4925e
```

Exact package:

```text
anki_study_report.ankiaddon
size: 774826 bytes
SHA-256: 02dd9a7aca3a8f1f1bf9a3cd1ba77b00f5a6ca7fb6b9f38e29286e52ded151a7
ZIP entries: 97
full-entry CRC failures: 0
```

Verification plan потребовал E2E, `mode=standard` и `fullRequired=true`.

## Post-merge real-Anki E2E

```text
run:
30408746188

URL:
https://github.com/AliceLiddell01/anki-study-report/actions/runs/30408746188

mode/scope/restart/purpose:
standard / full / true / acceptance

fast_ci_run_id:
30408497011

result:
success
```

Artifacts:

```text
main:
ID 8707632702
ci-e2e-standard-30408746188-1
sha256:f7d0fe06d8657cd5bc4e97aadfda5921fccc0816c9b1caae91bb4c4c644a1bcc

history:
ID 8707634660
ci-e2e-history-30408746188-1
sha256:6867792082edccf181f0335b52506167489e64c3d908addf7e7cd329d3e2e4e1
```

Обязательные проверки:

| Evidence | Результат |
| --- | --- |
| `real-deck-manifest-report.json` | PASS — 3 committed APKG / 11 anchors |
| `real-deck-import-report.json` | PASS — 921 notes / 921 cards / 2153 media |
| `collection-inventory.json` | PASS — 3 note types / 28 decks |
| `anchor-resolution-report.json` | PASS |
| `scenario-application-report.json` | PASS |
| `run-events.jsonl` | PASS — 89 valid events / terminal `run/pass` |
| first/restart API smoke | PASS |
| restart | PASS / executed |
| browser plan | PASS — 23/23 items / 18 screenshots |
| console/page/request/external request errors | 0 / 0 / 0 / 0 |
| package source | exact Fast CI artifact |
| package SHA before/after | equal / PASS |
| workflow/harness/checkout SHA | merged core SHA |
| public/source artifact validation | PASS / PASS |
| artifact manifest/final cleanup | PASS / PASS |
| token/private path scan | 0 matches |

Run использовал только:

```text
words-n1.apkg
grammar-n5.apkg
java-core.apkg
```

`syntheticFallback=false`; source-build fallback не применялся.

## Security и contracts

- frontend не получил прямого доступа к Anki collection;
- loopback/token boundary не расширена;
- sanitizer, media validation и action allowlists не ослаблены;
- preview не стал iframe или JavaScript surface;
- backend/API/schema и payload contracts в remaining WP3–WP6 pass не
  менялись;
- package format не менялся;
- evidence, logs, screenshots, runtime profile data и `.ankiaddon` не
  коммитились.

Актуальные contracts:

- [Inspection Profiles UI](../../docs/inspection-profiles-ui.md)
- [Guided Inspection Profiles](../../docs/guided-inspection-profiles.md)
- [Cards v2 product contract](../../docs/cards-v2-product-contract.md)
- [Verification run policy](../../docs/verification-run-policy.md)
- [Fast CI package / E2E reuse](../../docs/e2e-package-harness-reuse.md)

## Не запускалось

- отдельный exact Cards AV/media gate: не было новой Cards regression;
- `strict-apkg`, `perf100`, warm repeat и worker comparison;
- duplicate successful Fast CI или E2E;
- local full Docker после cloud full PASS;
- C3;
- release, deployment, publication и merge в `master`;
- проверки на приватной collection владельца.

После successful production gates изменяется только этот documentation
closeout и три docs/index файла. Docs-only merge не изменяет package bytes и
не требует повторного Fast CI или Docker E2E.

## Финальная классификация

```text
C2 PR #130 integration: COMPLETE
Inspection Profiles WP3 correction: COMPLETE
Inspection Profiles WP4 Advanced: COMPLETE
Inspection Profiles WP5 closeout: COMPLETE
Inspection Profiles WP6 evidence: COMPLETE
Fast CI exact merged package: PASS
real-Anki standard/full + restart: PASS
post-merge product fixes: NONE
Cards: ACCEPTED / COMPLETE / FROZEN
C3: NOT STARTED
master/release: UNTOUCHED
```
