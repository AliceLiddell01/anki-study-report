# E2E-I5 — итоговый отчёт об идентичности нерелизной сборки

## Статус

```text
ЗАВЕРШЕНО
реализация принята
облачная проверка пройдена
документация синхронизирована
следующий этап E2E-I6 не начат
```

E2E-I5 завершён как самостоятельный этап Platform / CI. Реализация создаёт закрытую машиночитаемую идентичность нерелизной сборки и связывает точный пакет Fast CI, E2E harness, источник workflow, неизменяемое окружение GHCR и границу повторного использования. Идентичность конкретного запуска E2E хранится отдельно и не влияет на хэш build material.

## Исходное состояние и границы

```text
базовая ветка: core
исходный core SHA: 50c2f0473603fa5979fb4bd46b9f36198f18f85c
рабочая ветка: platform/e2e-i5-non-release-build-identity
финальный implementation SHA: 92354870970956ed5d2e9216efca5058aa8addf3
PR: #141
предыдущий завершённый этап: E2E-I4
следующий запланированный этап: E2E-I6
```

Этап не менял product/API/dashboard scope, не добавлял release provenance, retries, visual regression или performance thresholds. `core` не изменялся напрямую, force push не использовался.

## Реализованный контракт

Канонические файлы:

```text
raw:    reports/non-release-build-identity.json
public: artifacts/reports/non-release-build-identity.json
```

Верхний уровень schema v1:

```text
schemaVersion
kind
identity
identityDigest
execution
```

Основные свойства:

- `kind=non-release-build` только для пакета из точного Fast CI artifact;
- закрытая схема с запретом дополнительных полей;
- максимальный размер JSON — 32 KiB;
- `identityDigest` вычисляется только по canonical объекту `identity`;
- compact UTF-8 JSON, сортировка ключей, отсутствие BOM и завершающего перевода строки в хэшируемых байтах;
- `execution` хранит run-specific данные и не влияет на build identity.

Подробный актуальный контракт: [`../../docs/non-release-build-identity.md`](../../docs/non-release-build-identity.md).

## Состав идентичности

### Пакет Fast CI

Идентичность пакета содержит:

- точный Fast CI run/attempt;
- commit, на котором пакет был собран и проверен;
- ID и transport digest GitHub Actions artifact;
- независимо пересчитанные SHA-256 и размер внутреннего `.ankiaddon`.

Transport digest и хэш внутренних байтов не подменяют друг друга.

### E2E harness

`harness.commitSha` и фактический `harness.checkoutSha` проверяются отдельно от `package.testedCommitSha`. Это не позволяет документационному commit или trigger SHA притвориться идентичностью пакета либо harness.

### Источник workflow

Workflow source определяется через `job.workflow_repository`, `job.workflow_file_path` и `job.workflow_sha`. Checkout выполняется по `job.workflow_sha`; trigger-dependent `github.sha` хранится только в `execution.triggerSha`.

### Окружение GHCR

Проверяются:

- неизменяемая ссылка `ghcr.io/...@sha256:<digest>`;
- digest ссылки и загруженного образа;
- `RepoDigests`;
- платформа;
- SHA-256 контракта окружения;
- commit публикации образа.

Cloud source-build fallback не добавлялся.

### Граница повторного использования

В идентичность входят режим, количество изменённых файлов и SHA-256 полного списка путей. Сам список остаётся в отдельном `e2e-harness-reuse.json`. Allowlist не ослаблялся.

## Жизненный цикл артефакта

- старый identity-файл удаляется до material resolution;
- частичная identity при pre-material failure отсутствует;
- полная identity создаётся до canonical Docker E2E;
- staging-копия переживает внутренний reset каталога артефактов;
- identity восстанавливается для success и functional failure;
- cancellation сохраняет identity только после её полной материализации;
- manifest строится повторно;
- raw/public проходят проверку схемы и semantic parity;
- release-artifact path отвергает нерелизную identity.

## Опубликованные implementation commits

```text
4d77f37c331250628f9e8e45bb47d711475e78ae  Add canonical non-release build identity
e1653de57992904424b237c03affda1d85e8f907  Bind package, harness, workflow, and environment evidence
df113081f88c2bd476c1e6f3999e2a47f47e76ed  Use exact workflow context for harness checkout
2393c1843c112c12d11757e138991bb833e18d19  Document and verify non-release build identity
92354870970956ed5d2e9216efca5058aa8addf3  Align E2E workflow tests with source identity
0a9f62bb2191301c33316ab2261f9415a751ae02  Close out non-release build identity acceptance
```

Исторические commit messages сохранены дословно как Git evidence. Человекочитаемые PR, контракт, roadmap и отчёт приведены к русскому формату.

## Локальные и профильные проверки

До облачной приёмки:

```text
компиляция изменённых Python-файлов: ПРОЙДЕНО
первичные профильные тесты: 47 ПРОЙДЕНО
разбор workflow YAML: ПРОЙДЕНО
git diff --check: ПРОЙДЕНО
```

После исправления устаревших workflow assertions:

```text
профильные тесты: 61 ПРОЙДЕНО
```

После docs-only closeout:

```text
профильные тесты: 61 ПРОЙДЕНО
проверка относительных Markdown-ссылок: ПРОЙДЕНО
git diff --check: ПРОЙДЕНО
```

## Первый Fast CI и устранение причины ошибки

Первый package-producing запуск:

```text
Fast CI run: 30149006339
результат: ОШИБКА
Python: 1020 пройдено, 6 пропущено, 2 ошибки
package artifact: не создан
```

Причина была ограничена двумя устаревшими строковыми проверками в `tests/test_ci_e2e_workflow.py`:

- ожидался trigger-dependent `github.sha` вместо `job.workflow_sha`;
- ожидался удалённый checkout tested package commit вместо точного checkout workflow/harness commit.

Production workflow не откатывался и не ослаблялся. Commit `92354870970956ed5d2e9216efca5058aa8addf3` обновил только устаревшие тестовые ожидания. Неуспешный run не переиспользовался и не перезапускался вслепую.

## Успешный Fast CI с формированием пакета

```text
Fast CI run: 30149481485 / attempt 1
результат: ПРОЙДЕНО
проверенный commit: 92354870970956ed5d2e9216efca5058aa8addf3

diagnostics artifact ID: 8617175451
diagnostics artifact digest: sha256:568456efdbc5e50aaefe1f19a7adee78d9f7258a425eb0917a3b4e41ae52f070

package artifact ID: 8617175787
package artifact digest: sha256:a3b2357e6b19486c5902d62f4d8433f54374b539e689e2cc7ad138b4caab34c1
inner package SHA-256: 4041ace490b1bba63e340ae8597613db3ce2bf8b12a1cbfb27c776b2c68e0861
inner package size: 750680 bytes
```

Package и diagnostics были скачаны и проверены до запуска E2E. Полный handoff подтвердил:

```text
reuseAllowed: true
reuseMode: exact-tree
changedFileCount: 0
changedPathsSha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Успешный полный E2E в реальном Anki

```text
E2E run: 30150971581 / attempt 1
job: Real Anki Desktop (standard / full)
результат: ПРОЙДЕНО
проверенный commit: 92354870970956ed5d2e9216efca5058aa8addf3
источник пакета: Fast CI run 30149481485

E2E artifact ID: 8617629796
имя артефакта: ci-e2e-standard-30150971581-1
E2E artifact digest: sha256:44d40f58251be7494928a26c151f8505c5a21623ec29d6f1c855314b4d703d7b
размер артефакта: 6883753 bytes
```

Успешно завершились все обязательные шаги:

- разрешение exact Fast CI package и diagnostics;
- проверка handoff;
- checkout точного workflow/harness SHA;
- проверка неизменяемого GHCR environment;
- создание canonical identity;
- Docker-only E2E;
- восстановление identity после внутреннего reset;
- повторная проверка SHA-256 пакета;
- публикация очищенных handoff/environment evidence;
- формирование public artifact;
- upload;
- Docker cleanup;
- восстановление canonical результата.

## Каноническая идентичность принятой сборки

```text
schemaVersion: 1
kind: non-release-build
identityDigest: sha256:d85608e71b0bb927fbd7f400c9b65d436395ff359f467dec6a12f0c63028cbad
repository: AliceLiddell01/anki-study-report

package source run: 30149481485 / attempt 1
package artifact ID: 8617175787
package artifact digest: sha256:a3b2357e6b19486c5902d62f4d8433f54374b539e689e2cc7ad138b4caab34c1
package inner SHA-256: 4041ace490b1bba63e340ae8597613db3ce2bf8b12a1cbfb27c776b2c68e0861
package size: 750680 bytes
package tested SHA: 92354870970956ed5d2e9216efca5058aa8addf3

harness commit SHA: 92354870970956ed5d2e9216efca5058aa8addf3
harness checkout SHA: 92354870970956ed5d2e9216efca5058aa8addf3
workflow source SHA: 92354870970956ed5d2e9216efca5058aa8addf3
workflow path: .github/workflows/ci-e2e.yml
reuse mode: exact-tree

environment image digest: sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
environment platform: linux/amd64
environment contract SHA-256: 8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
```

Независимый пересчёт SHA-256 compact sorted UTF-8 JSON объекта `identity` воспроизвёл сохранённый `identityDigest`.

## Проверка опубликованного артефакта

Архив был скачан через GitHub Actions artifact API и проверен вне checkout репозитория.

```text
детерминированные проверки: 33/33 ПРОЙДЕНО
опубликованные файлы: 73/73
manifest: success
identity присутствует в manifest: да
размер identity JSON: 1847 bytes
browser items: 23/23 ПРОЙДЕНО
screenshots: 18/18
console events: 0
page errors: 0
failed requests: 0
unexpected external requests: 0
preflight checks: 20/20 ПРОЙДЕНО
FSRS visual checks: 80 ПРОЙДЕНО
sanitizer: совпадений token, Authorization header, private key и token-bearing URL нет
```

Доказательства real-deck contour:

```text
committed APKG: 3
manifest packages: 3 ПРОЙДЕНО
runtime imports: 3 ПРОЙДЕНО
resolved anchors: 11/11
scenario groups: 9 ПРОЙДЕНО
API smoke: ПРОЙДЕНО
manual package extraction: false
synthetic fallback: false
```

## Безопасность и сохранённые инварианты

- dashboard token и token-bearing URL не логируются;
- public artifact проходит sanitizer;
- media validation и action allowlists не менялись;
- карточки не превращались в iframe/JavaScript execution surface;
- generated assets и runtime outputs не коммитились;
- package и harness identities остаются независимыми;
- source-build fallback не добавлен;
- исторический package reuse был отвергнут fail closed;
- release identity остаётся отдельным контрактом.

## Что намеренно не запускалось

- второй успешный E2E;
- controlled cancellation A/B;
- намеренно неуспешный облачный run;
- `perf100`;
- warm repeat;
- сравнение workers;
- visual regression;
- retries;
- повторный тяжёлый запуск после docs-only изменений.

Эти запуски не требовались после одного успешного exact-tree `standard/full` на финальном implementation SHA.

## Вне области этапа

```text
E2E-I6 — canonical final summary и history
переработка release identity/provenance
artifact attestations, SBOM, SLSA и signing
retries/quarantine
visual regression
performance thresholds
cloud source-build fallback
изменения product/API/dashboard
```

## Формат проектных материалов

Начиная с этого closeout, русский PR, closeout-отчёт, roadmap-статус и handoff используют русский язык во всём человекочитаемом тексте. Без перевода сохраняются только точные технические идентификаторы, пути, команды, поля схемы, workflow/job names, SHA/digest и устоявшиеся обозначения `Fast CI`, `E2E`, `GHCR`, `APKG`, `JSON`, `YAML`.

Это правило зафиксировано в `docs/chatgpt-work-mode.md`, `docs/codex-agent-rules.md` и текущем `docs/ai-handoff.md`.

## Решение о завершении

Все критерии E2E-I5 выполнены:

1. успешный package-producing Fast CI на финальном implementation commit;
2. успешный `standard/full` E2E с этим точным пакетом;
3. проверка identity schema/digest, manifest/public evidence, 23 browser items и 18 screenshots;
4. синхронизация актуального контракта, roadmap, handoff и подробного отчёта;
5. сохранение security, package/harness и release boundaries.

Для интеграции выбран merge commit, чтобы сохранить шесть implementation/closeout commits и явную точку слияния с `core`. Squash, rebase и auto-merge не используются. E2E-I6 остаётся отдельным следующим решением владельца.
