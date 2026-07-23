# Политика проверочных запусков

**Статус:** обязательная политика, актуализирована 2026-07-23

Полный real-Anki E2E — интеграционный gate, а не обычный цикл разработки.

## Общая последовательность

Для изменения продукта, runtime или E2E-инфраструктуры:

```text
локальные профильные тесты
→ commit и push
→ Fast CI для точного SHA — PASS
→ один целевой real-Anki scope, если его требует риск
→ standard/full только при эскалации matrix или planner
→ merge проверенного patch/tree
→ Fast CI на итоговом master
```

До успешного Fast CI для точного head SHA real-Anki E2E не запускается.

Успешный E2E для неизменного exact tree не повторяется. Новый commit требует новой оценки, потому что меняет проверяемое дерево.

## Real-deck E2E foundation

Docker collection всегда строится из трёх committed рабочих колод:

```text
docker/anki-e2e/fixtures/real-decks/words-n1.apkg
docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg
docker/anki-e2e/fixtures/real-decks/java-core.apkg
```

Отдельного `strict-apkg` mode больше нет: строгий manifest/checksum/import/anchor contract является обязательной частью каждого Docker E2E.

`perf100` разрешён только для явной performance-задачи. Он выбирает 100 distinct existing imported cards и не создаёт/клонирует notes или cards.

Изменение real-deck importer, manifest, anchors, scenario applicator, browser/API smoke, artifact manifest или Docker runner классифицируется как E2E/runtime infrastructure и требует:

```text
focused contract tests
→ Fast CI exact SHA
→ один standard/cards с restart
→ standard/full только если общий diff затрагивает общий startup/server/package/artifact contour
```

Поскольку полная замена collection foundation затрагивает startup, import, media, Cards, Profiles, browser proof, package handoff и artifact contract, финальный `standard/full` для её готового exact head обязателен после успешного целевого proof.

## Выбор целевого scope

| Изменение | Целевой gate |
| --- | --- |
| Search и Safe Actions | `standard/global` |
| Cards, native preview, media, Triage, Inspection Profiles | `standard/cards`, `verify_restart=true` |
| Statistics и FSRS | `standard/stats` |
| Decks | `standard/decks` |
| Calendar/Activity | `standard/activity` |
| Settings, privacy, telemetry | `standard/settings` |
| Notifications | `standard/notifications`, `verify_restart=true` |
| общий startup/server/package/E2E infrastructure | целевой scope по риску, затем `standard/full` |
| release path | `standard/full` с exact release artifact |

Targeted scope не ослабляет real-deck foundation: все три packages, checksum/import/inventory/anchor/scenario reports остаются обязательными.

## Exact SHA и Fast CI artifact

Готовый head PR должен иметь PASS Fast CI именно на своём SHA.

Успешный Fast CI публикует:

- диагностический artifact;
- точный `.ankiaddon` package artifact только после успешных canonical checks;
- metadata с tested SHA и package SHA-256.

Docker consumer обязан:

- получить явно указанный successful Fast CI run;
- проверить repository, branch/head identity и tested SHA;
- скачать точный package artifact;
- проверить metadata и внутренний SHA-256;
- завершиться ошибкой без fallback при несовпадении, истечении срока или неоднозначности.

После merge Fast CI на `master` обязателен. Повтор E2E требуется только если rebase/conflict resolution изменил production tree или patch относительно проверенного head.

## Stop-loss

После ошибки сначала изучаются reports, logs, screenshots и первопричина.

Разрешён максимум один повтор соответствующего gate после конкретного исправления. Вторая одинаковая ошибка прекращает слепые перезапуски.

Запрещены без отдельной задачи:

- warm-cache repeat;
- worker comparison;
- resource benchmark;
- повтор успешного exact-tree gate;
- локальный full Docker после cloud PASS;
- full после каждого небольшого исправления;
- fallback на сборку из исходников при ошибке package handoff;
- `perf100` как обычный acceptance gate.

Infrastructure failure отделяется от project failure по logs и artifact metadata. Автоматический rerun без такой классификации запрещён.

## Локальный Docker

Локальный Docker допускается, когда:

- необходимо диагностировать изменение самого Docker/runtime harness;
- cloud gate ещё не запускался для exact tree;
- владелец явно выбрал локальный proof;
- запуск не дублирует уже успешный cloud gate.

Локальный запуск не заменяет Fast CI, CodeQL или обязательный cloud exact-package proof.

## Verification planner

`scripts/plan_verification.py` принимает base/head или список paths и формирует рекомендательный план.

Planner:

- детерминирован и покрыт тестами;
- не запускает workflows;
- не хранит состояние выполненных gates;
- не может понизить изменение общего runtime, E2E, package или release;
- может быть повышен человеком или agent по фактическому риску.

## Изменения только документации

После уже успешного gate изменение только документации требует:

- `git diff --check`;
- проверки links/code fences/paths;
- Fast CI нового exact SHA, если изменение находится в PR;
- без повторного Docker, если runtime tree не изменился.

## Release

Release infrastructure, version source, changelog, publisher и AnkiWeb adapter всегда классифицируются как `full`.

Production workflow устанавливает exact final archive через `ANKI_E2E_PREBUILT_ADDON_PATH`. E2E package SHA-256 должен совпадать с release artifact. Публикация разрешена только после успешного exact release-artifact `standard/full`.

## Обязательная фиксация результата

Итоговый отчёт по gate должен содержать:

- exact commit SHA;
- Fast CI run ID и status;
- Docker mode/scope/restart policy;
- package artifact identity и SHA-256;
- PASS/FAIL пяти real-deck reports;
- artifact ID/digest;
- что не запускалось;
- причину любого пропуска или остановки;
- подтверждение отсутствия повторного exact-tree run.
