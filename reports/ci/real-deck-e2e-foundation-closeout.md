# Итоговый отчёт: real-deck foundation для Docker E2E и повторное использование проверенного пакета

## Статус

```text
Дата завершения: 2026-07-23
Статус реализации: COMPLETE ON FEATURE BRANCH
Статус обязательных проверок: PASS
Pull request: #133, draft
Base branch: core
Base SHA: 5fd43d4bd5f6d93b9861f4f9dc7f7462429cdc2b
Финальный E2E harness SHA: 1a84eabaacb5c368f92ae4952e732d8610619f95
Merge: НЕ ВЫПОЛНЕН
Auto-merge: НЕ ВКЛЮЧЁН
Release/AnkiWeb publication: НЕ ВЫПОЛНЕНЫ
```

Работа заменила устаревшую синтетическую collection foundation Docker E2E на три committed рабочие колоды, расширила доказательства реального Anki runtime и разделила идентичность проверенного `.ankiaddon` от идентичности текущего E2E harness. Итоговый targeted и full cloud-контур прошёл на одном уже проверенном пакете без повторной сборки add-on после harness-only исправлений.

## Цель и границы

Основные цели:

1. Использовать в real-Anki Docker E2E полноценные рабочие `.apkg`, а не маленькую искусственную коллекцию.
2. Покрыть реальные типы заметок, поля, шаблоны, media и неоднородное содержимое.
3. Не создавать и не клонировать notes/cards/templates/media внутри harness.
4. Сохранить детерминированные сценарии Cards, Triage, Inspection Profiles, notifications и restart.
5. Сделать логи длительных стадий понятными и пригодными для диагностики.
6. Формировать публично безопасный структурированный artifact.
7. Не пересобирать `.ankiaddon` через Fast CI после каждой правки, которая затрагивает только E2E harness и не меняет package bytes.

Вне scope:

- изменения пользовательского production UI;
- изменение dashboard payload или публичных API;
- изменение Anki collection пользователя;
- release, tag, GitHub Release или публикация на AnkiWeb;
- merge PR #133;
- приватный профиль владельца как автоматический CI gate;
- performance-оптимизация без отдельной измерительной задачи.

## Итоговая collection foundation

### Committed packages

| Package | Repository path | Size | SHA-256 | Notes | Cards | Media |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| Words N1 | `docker/anki-e2e/fixtures/real-decks/words-n1.apkg` | 24 979 986 bytes | `78dfab9424fcdb1f5da4005f7e5a2789a04c13414c5477bc647069a06ad10a9b` | 718 | 718 | 2 153 |
| Grammar N5 | `docker/anki-e2e/fixtures/real-decks/grammar-n5.apkg` | 116 622 bytes | `72f0d9707604dff2c7b51fbde4ace51f104f07a5671f608eb987c2067443c19d` | 133 | 133 | 0 |
| Java | `docker/anki-e2e/fixtures/real-decks/java-core.apkg` | 74 610 bytes | `3c7ee2fe3435d57c5ac5ff8fb8eb913d9406d9461f11975114d6e6ac52b041d3` | 70 | 70 | 0 |

Финальный inventory:

```text
notes: 921
cards: 921
used note types: 3
decks: 28
media files: 2153
synthetic notes: 0
synthetic cards: 0
synthetic media: 0
content source: committed-real-apkg-only
```

### Manifest contract

Source of truth:

```text
docker/anki-e2e/fixtures/real-decks/manifest.json
```

Manifest фиксирует:

- package ID, path, size и SHA-256;
- ожидаемый inventory;
- note GUID и template ordinal для anchors;
- note-type field list и structure fingerprint;
- media capabilities;
- HTML classes для native preview proof;
- Inspection Profile mappings;
- разрешённые study-state scenarios.

Concrete identifiers не размазаны по generic scripts. Missing package, checksum mismatch, importer error, неоднозначный anchor или несовпадение fingerprint являются hard failure без fallback.

### Import

Disposable collection создаётся пустой. Все три packages импортируются в manifest order через публичный Anki API:

```text
Collection.import_anki_package(ImportAnkiPackageRequest)
```

Legacy importer/backend fallback отсутствует. После импорта harness не вставляет notes/cards напрямую и не клонирует content.

### Сценарии

После импорта изменяется только состояние существующих карточек:

- scheduling state;
- due, interval, factor, reps и lapses;
- revlog;
- suspended;
- buried.

Scenario report доказывает:

```text
notesCreated = 0
cardsCreated = 0
notesOrCardsCloned = 0
```

`perf100` выбирает 100 различных импортированных cards и не создаёт копии.

## Покрытие real-Anki E2E

Финальный контур проверяет:

- startup hooks и disposable profile lifecycle;
- loopback-only token-protected dashboard;
- установку exact `.ankiaddon`;
- API health/report/status;
- три native preview: Words, Grammar и Java;
- real audio, GIF и static image media;
- media traversal/absolute-path rejection;
- automatic Triage reasons и exact card recheck;
- low-success, suspended и buried states;
- Inspection Profiles для реальных Japanese и Java note types;
- notification lifecycle;
- browser routes в light/dark;
- отсутствие page errors, failed requests и неожиданного external network;
- telemetry consent/purpose isolation, bounded delivery и offline queue;
- restart persistence;
- удаление telemetry data и уничтожение credentials;
- package hash после выполнения E2E;
- redacted public artifact.

Успешный artifact обязан содержать PASS пяти базовых отчётов:

```text
real-deck-manifest-report.json
real-deck-import-report.json
collection-inventory.json
anchor-resolution-report.json
scenario-application-report.json
```

## Notification lifecycle без synthetic fixture

Оставшаяся зависимость от удалённого `fixture-summary.json` была обнаружена только в `standard/full`. Она удалена.

`seed-notification-lifecycle.py` теперь использует:

- `cards-action-recheck`;
- `cards-low-success`;
- deck ID anchor `cards-action-recheck`;
- scheduler-day timestamp из `scenario-application-report.json`.

Input reports обязаны быть schema-v1 PASS. Два card anchors обязаны быть различными. Public proof переведён на schema v2 и публикует только anchor names и `contentSource=committed-real-apkg-anchors`, без raw card/deck IDs.

## Telemetry restart lifecycle

В ходе переработки был восстановлен потерянный pre-restart lifecycle:

1. Проверяется declined consent.
2. Проверяются reliability-only и feature-only batches.
3. Fake loopback endpoint переводится в offline state.
4. Создаётся минимум 25 persistent events.
5. Anki перезапускается.
6. Строгий verifier проверяет восстановление очереди.
7. Проверяется post-restart delivery.
8. Проверяются confirmed deletion и credential destruction.

Порог и verifier не ослаблялись. В финальных успешных запусках:

```text
pending before restart: 25
delivered after restart: 29
restart persistence: PASS
confirmed deletion: true
credential destroyed: true
```

## Разделение package и E2E harness

### Проблема прежнего контура

Первоначально `fast_ci_run_id` определял не только `.ankiaddon`, но и checkout всего repository tree. Любое исправление в `docker/anki-e2e/`, browser smoke или artifact exporter требовало нового Fast CI, хотя package bytes не менялись.

Это создавало лишний цикл:

```text
harness-only fix
→ повторная полная non-Docker проверка
→ повторная сборка того же add-on
→ новый package artifact
→ только затем новый Docker run
```

### Принятое решение

Теперь разделены две идентичности:

```text
package tested commit
E2E harness/workflow commit
```

Для `harness-only` reuse workflow:

1. Оставляет текущий branch checkout как source E2E harness.
2. Получает явно указанный successful Fast CI run.
3. Проверяет diagnostics и package metadata.
4. Проверяет, что package commit является предком harness commit.
5. Получает полный `git diff --name-only` между ними.
6. Пропускает diff через fail-closed allowlist.
7. Проверяет package bytes, size и SHA-256 против исходного Fast CI.
8. Запускает текущий harness с прежним exact package.
9. Публикует обе SHA и reuse evidence.

Режимы:

```text
exact-tree   package commit == harness commit, diff пустой
harness-only package commit != harness commit, весь diff разрешён allowlist
```

При изменении production add-on, frontend, packaging, dependencies или посторонних файлов reuse блокируется и нужен новый Fast CI package.

### Evidence

Публикуются:

```text
sourceFastCiTestedSha
sourcePackageSha256
e2eCheckoutSha
packageReuseMode
packageReuseChangedFileCount
packageReuseChangedPathsSha256
artifacts/reports/e2e-harness-reuse.json
```

Summary writer независимо пересчитывает boundary и требует полного совпадения с raw handoff evidence. Нельзя подделать `harness-only`, просто передав две разные SHA.

## Artifact security

В ходе работы исправлены два класса ошибок sanitizer:

1. Частные абсолютные paths из browser console locations не редактировались полностью.
2. Слишком широкий Linux regex принимал относительный `screenshots/pages/home/...` за абсолютный `/home/...`.

Финальный контракт:

- exact workspace roots заменяются на `[WORKSPACE]`;
- произвольные абсолютные Linux/Windows private paths заменяются на `[PRIVATE_PATH]`;
- относительные route paths сохраняются;
- token-bearing URL, secrets, private keys и private paths отклоняются fail closed;
- raw readiness с token не загружается;
- artifact preparation не может изменить canonical E2E result.

Финальный artifact replay не обнаружил token-bearing URLs, GitHub/OpenAI-style secrets, private keys или private Linux/Windows paths.

## Основные обнаруженные проблемы и исправления

| Run | Результат | Подтверждённая причина | Исправление |
| ---: | --- | --- | --- |
| `29997519876` | FAIL | stale/guardrail regressions | синхронизация real-deck contract tests |
| `30001107003` | FAIL | invalid search `pageSize: 200` | exact inspect вместо недопустимого query |
| `30003630239` | FAIL | learning reasons ожидались от `search_workset` | authoritative `automatic` dataset |
| `30005443279` | FAIL | action anchor выпадал из bounded recent candidates | детерминированные свежие revlog timestamps |
| `30006724446` | FAIL | browser ждал transient heading | structural `main` + exact route/hash proof |
| `30008304682` | FAIL после functional PASS | private absolute path в browser diagnostics | полное private-path redaction |
| `30010259291` | FAIL после functional PASS | false positive на `pages/home/...` | boundary-aware Linux regex |
| `30012412207` | FAIL после functional PASS | init script читал `documentElement.dataset` до root | безопасный theme bootstrap после root creation |
| `30014258982` | FAIL после browser PASS | отсутствовала pre-restart telemetry queue | восстановлен offline telemetry lifecycle |
| `30019317103` | FAIL после functional PASS | summary требовал package SHA == harness SHA | отдельные package/harness identities и validated reuse proof |
| `30020974030` | FAIL до первого Anki start | notification seed читал удалённый synthetic fixture | real-deck anchors + scheduler-day evidence |
| `30020601292` | PASS | targeted cards acceptance | обязательный targeted gate завершён |
| `30022393738` | PASS | final full acceptance | обязательный full gate завершён |

Повторные запуски выполнялись только после конкретного исправления. Успешный unchanged gate не повторялся.

## Финальная package identity

Fast CI producer:

```text
run: 30013925137
package tested commit: bd0355c315197cfb659cb28b32b63a4931b73458
artifact: ci-package-bd0355c315197cfb659cb28b32b63a4931b73458-30013925137-1
package SHA-256: 3ae8439ba18cac82b7e8bb6b240223970cb6403130abf1f909168273ff39baf8
package size: 750415 bytes
transport digest: sha256:093b8d78bc18fb94e17dc006efd13c45ace2c7e3984fa9cf5a1f0344155d1e67
result: PASS
```

## Targeted proof

```text
run: 30020601292
mode/scope: standard/cards
restart: true
package commit: bd0355c315197cfb659cb28b32b63a4931b73458
harness commit: 04444a72fe4316102087958652257fc80c972842
reuse mode: harness-only
artifact: ci-e2e-standard-30020601292-1
artifact digest: sha256:ac84605da481a00bf178b9f85c80906d4cb8b0d837cec8003319429718935694
result: PASS
```

Подтверждены real-deck import, Cards/Triage/Profiles, browser, 18 screenshots, telemetry restart, sanitizer, upload и final restore.

## Final full proof

```text
run: 30022393738
mode/scope: standard/full
restart: true
package commit: bd0355c315197cfb659cb28b32b63a4931b73458
harness commit: 1a84eabaacb5c368f92ae4952e732d8610619f95
reuse mode: harness-only
changed file count: 10
changed paths SHA-256: 6218706412a4f672bbbc45271a1f97adaa82ded1122677f7da2401e0592da403
artifact: ci-e2e-standard-30022393738-1
artifact digest: sha256:4437e3ca749bd528ad8b66f473f15db37b667014f7d51a0560b3ae84cb2b4fcf
artifact size: 6799725 bytes
artifact result: success
manifest status: success
workflow result: PASS
```

Full proof подтвердил notification lifecycle, API/browser, media, Inspection Profiles, exact recheck, telemetry restart/deletion, exact package hash, sanitizer, upload, cleanup и final canonical restore.

## Изменённые слои

PR включает изменения в следующих группах:

### Real decks и import

- committed APKG и manifest;
- `real_deck_contract.py`;
- import/preparation scripts;
- empty collection bootstrap;
- scenario applicator;
- inventory/anchor/failure reports.

### Runtime/browser proof

- API smoke;
- Playwright browser smoke;
- real preview/media screenshots;
- restart orchestration;
- notification lifecycle;
- telemetry pre-restart lifecycle.

### Artifact и CI handoff

- artifact manifest;
- private-path/token sanitizer;
- Fast CI handoff validator;
- package/harness reuse validator;
- separate summary identities;
- package hash verification.

### Tests и documentation

- focused real-deck contract tests;
- action/recheck и exact inspect tests;
- screenshot/artifact/security tests;
- notification/telemetry/reuse tests;
- Docker E2E, fixtures, verification и CI documentation.

Полный список файлов хранится в PR #133.

## Что не проверялось

- PowerShell-specific local execution на Windows отдельно не запускался в финальной последовательности.
- Приватный рабочий профиль Anki владельца не использовался как CI gate.
- `perf100`, warm-cache repeats и worker comparison не запускались.
- Release artifact path не переигрывался в этой задаче: он уже имеет отдельный контракт и не должен использовать harness-only reuse старого release package.
- Merge, release и AnkiWeb publication не выполнялись.

## Итоговое решение по запускам

После этой работы действует правило:

```text
изменён add-on/package input
→ нужен новый Fast CI package

изменён только разрешённый E2E harness/orchestration/test
→ новый Fast CI не нужен
→ используется существующий successful package
→ boundary проверяется fail closed

изменена только документация после успешных gates
→ Docker/Fast CI не повторяются без отдельной причины
```

Новый canonical contract описан в [`../../docs/e2e-package-harness-reuse.md`](../../docs/e2e-package-harness-reuse.md).

## Заключение

Обязательные gates завершены:

1. package-producing Fast CI — PASS;
2. targeted `standard/cards` с restart — PASS;
3. final `standard/full` с notifications, telemetry и restart — PASS;
4. artifact inspection и sanitizer replay — PASS.

Real-Anki E2E теперь основан на committed рабочих колодах, не подменяет их synthetic content, публикует воспроизводимое безопасное evidence и не требует бессмысленной повторной сборки неизменённого add-on после каждой harness-only правки.
