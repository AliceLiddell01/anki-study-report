# Идентичность нерелизной E2E-сборки

## Статус контракта

```text
schemaVersion: 1
kind: non-release-build
область: только нерелизная сборка из точного артефакта Fast CI
```

Этот документ определяет каноническую машиночитаемую идентичность нерелизной сборки, которая проверяется в real-Anki Docker E2E. Контракт связывает пакет, E2E harness, источник workflow, неизменяемое окружение GHCR и границу повторного использования, но не смешивает идентичность сборки с конкретным запуском E2E.

## Канонические пути

```text
raw:    reports/non-release-build-identity.json
public: artifacts/reports/non-release-build-identity.json
```

Raw- и public-представления обязаны проходить одинаковую проверку схемы и быть семантически равными. Public-файл включается в `artifacts/manifest.json` и в опубликованный E2E-артефакт.

## Верхний уровень документа

Документ содержит только следующие поля:

```text
schemaVersion
kind
identity
identityDigest
execution
```

Дополнительные поля запрещены. Максимальный размер кодированного JSON — 32 KiB.

### `schemaVersion`

Текущее значение — целое число `1`.

### `kind`

Текущее значение — строка `non-release-build`. Контракт не используется для release-артефактов.

### `identity`

Канонические материальные признаки сборки. Только этот объект участвует в вычислении `identityDigest`.

### `identityDigest`

Строка вида `sha256:<64 hex>`. Хэш вычисляется по compact UTF-8 JSON объекта `identity`:

```text
ключи отсортированы
разделители не содержат лишних пробелов
BOM отсутствует
завершающий перевод строки в хэшируемые байты не входит
объект execution в хэш не входит
```

### `execution`

Идентичность конкретного запуска E2E. Она хранится рядом с идентичностью сборки, но не влияет на `identityDigest`.

## Объект `identity`

### Репозиторий

```json
{
  "repository": "AliceLiddell01/anki-study-report"
}
```

### Пакет — `identity.package`

```text
source
sourceRunId
sourceRunAttempt
testedCommitSha
artifactId
artifactDigest
innerSha256
sizeBytes
```

Правила:

- `source` для этого контракта равен `fast-ci-artifact`;
- `sourceRunId` и `sourceRunAttempt` указывают точный успешный Fast CI;
- `testedCommitSha` — commit, на котором был собран и проверен пакет;
- `artifactId` — неизменяемый ID GitHub Actions artifact;
- `artifactDigest` — транспортный SHA-256 всего artifact, возвращённый GitHub;
- `innerSha256` — независимо пересчитанный SHA-256 байтов `anki_study_report.ankiaddon`;
- `sizeBytes` — фактический размер внутреннего `.ankiaddon`.

`artifactDigest` и `innerSha256` являются разными идентичностями и не заменяют друг друга.

### E2E harness — `identity.harness`

```text
commitSha
checkoutSha
```

`commitSha` задаёт commit harness, выбранный контрактом. `checkoutSha` подтверждает фактический `HEAD` после checkout. Оба значения проверяются независимо от `package.testedCommitSha`.

### Источник workflow — `identity.workflow`

```text
repository
filePath
sourceSha
```

Источник workflow определяется через контекст `job.workflow_*`, а не через зависящий от trigger `github.sha`:

```text
repository <- job.workflow_repository
filePath   <- job.workflow_file_path
sourceSha  <- job.workflow_sha
```

`actions/checkout` получает `job.workflow_sha` напрямую. Trigger SHA сохраняется отдельно в `execution.triggerSha`.

### Окружение — `identity.environment`

```text
imageReference
imageDigest
platform
contractSha256
publishedFromCommitSha
```

Правила:

- `imageReference` обязан быть неизменяемой ссылкой `ghcr.io/...@sha256:<digest>`;
- `imageDigest` сверяется со ссылкой, `RepoDigests` загруженного образа и consumer lock;
- `platform` фиксирует фактическую платформу, например `linux/amd64`;
- `contractSha256` связывает образ с контрактом окружения;
- `publishedFromCommitSha` фиксирует commit, из которого опубликовано окружение.

Проверка выполняется до запуска canonical Docker E2E. Source-build fallback в облачном контуре запрещён.

### Повторное использование — `identity.reuse`

```text
mode
changedFileCount
changedPathsSha256
```

Допустимые режимы определяются validator’ом повторного использования package/harness. Для принятого E2E-I5 использован `exact-tree`:

```text
changedFileCount: 0
changedPathsSha256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

Полный список изменённых путей не дублируется в идентичности. Он остаётся в отдельном `e2e-harness-reuse.json`; в build identity входят только режим, количество и хэш списка.

## Объект `execution`

```text
runId
runAttempt
triggerSha
ref
```

Эти поля описывают конкретный запуск E2E:

- GitHub Actions run и attempt;
- trigger SHA;
- точный Git ref.

Они намеренно исключены из `identityDigest`, поэтому повторный запуск неизменной сборки не создаёт новую идентичность build material.

## Жизненный цикл

1. До полного разрешения package, harness, workflow и environment старый identity-файл удаляется.
2. Частичная идентичность при pre-material failure не создаётся.
3. После полного разрешения material identity создаётся до canonical Docker E2E.
4. Staging-копия переживает внутренний reset каталога E2E-артефактов.
5. После success или functional failure канонический файл восстанавливается и повторно проверяется.
6. При cancellation identity сохраняется только тогда, когда она уже была полностью материализована.
7. Manifest строится повторно и включает public identity.
8. Raw/public validation и semantic parity выполняются до upload.

## Fail-closed проверки

Выполнение завершается ошибкой при любом несоответствии:

- неизвестное или дополнительное поле;
- неверный тип или формат SHA/digest;
- различие transport digest и ожидаемого artifact;
- различие внутреннего SHA-256 или размера пакета;
- несовпадение package tested SHA, harness checkout или workflow source;
- несовпадение GHCR reference/digest/platform/contract/source revision;
- запрещённый reuse boundary;
- различие raw/public;
- отсутствие identity в manifest;
- появление identity в release-artifact path;
- превышение ограничения размера.

Нельзя ослаблять validator, sanitizer или allowlist ради повторного использования старого пакета.

## Что не входит в `identityDigest`

```text
E2E run ID и attempt
trigger SHA и ref
временные метки
названия workflow, job и artifact
PR и названия веток
URL
человекочитаемые сводки
```

Эти данные либо относятся к `execution`, либо остаются во внешнем evidence.

## Граница release

Release artifact использует отдельный контракт идентичности и происхождения. Нерелизный `non-release-build-identity.json` не добавляется в release package и не подменяет release provenance.

## Безопасность публичного артефакта

Identity может содержать только публичные SHA, digest, bounded enum, размеры, счётчики и безопасные относительные пути. Запрещены:

- token и credential;
- `Authorization` header;
- token-bearing URL;
- приватные абсолютные пути;
- произвольный environment dump;
- HTML или пользовательское содержимое карточек;
- raw stack trace.

Public exporter и sanitizer остаются обязательной границей перед upload.

## Принятое доказательство E2E-I5

```text
финальный implementation SHA: 92354870970956ed5d2e9216efca5058aa8addf3
Fast CI: 30149481485 / attempt 1 — ПРОЙДЕНО
package artifact ID: 8617175787
package artifact digest: sha256:a3b2357e6b19486c5902d62f4d8433f54374b539e689e2cc7ad138b4caab34c1
inner package SHA-256: 4041ace490b1bba63e340ae8597613db3ce2bf8b12a1cbfb27c776b2c68e0861
standard/full E2E: 30150971581 / attempt 1 — ПРОЙДЕНО
E2E artifact ID: 8617629796
E2E artifact digest: sha256:44d40f58251be7494928a26c151f8505c5a21623ec29d6f1c855314b4d703d7b
identityDigest: sha256:d85608e71b0bb927fbd7f400c9b65d436395ff359f467dec6a12f0c63028cbad
browser items: 23/23
screenshots: 18/18
```

Исторический и проверочный контекст находится в [`../reports/ci/e2e-i5-non-release-build-identity-closeout.md`](../reports/ci/e2e-i5-non-release-build-identity-closeout.md).
