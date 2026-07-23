# GHCR E2E environment consumer

**Снимок контракта:** 2026-07-23.

## Текущее состояние

Все cloud real-Anki E2E runs используют exact immutable GHCR digest из:

```text
docker/anki-e2e/environment-image-lock.json
```

Manual Fast CI path:

```text
successful Fast CI package
→ exact package tested commit + package SHA-256
→ current E2E harness commit
→ ancestry + complete-diff validation
→ exact GHCR digest
→ real Anki E2E
```

Release path:

```text
exact current release artifact
→ exact package SHA-256
→ exact GHCR digest
→ real Anki standard/full
```

## Immutable environment identity

Consumer принимает только exact `linux/amd64` digest и проверяет:

- environment contract;
- platform;
- bounded OCI labels;
- expected publication/reuse metadata.

Mutable tag, `latest`, второй hardcoded digest, PAT fallback, cloud BuildKit build/load и automatic package visibility changes запрещены.

Локальная Dockerfile/Compose build path сохранена только для development/diagnostics и не является cloud fallback.

## Package sources

Cloud workflow принимает:

```text
manual/reusable E2E  → fast-ci-artifact
release caller       → release-artifact
```

Cloud `source-build` отклоняется до registry login.

### Fast CI package

Проверяются:

- same-repository successful run;
- diagnostics artifact;
- package artifact;
- package tested commit;
- package metadata;
- package size и internal SHA-256;
- artifact transport digest.

### Package/harness split

Current E2E checkout не обязан совпадать с package tested commit.

Если SHA различаются, consumer обязан:

1. проверить ancestry package commit → harness commit;
2. получить полный changed-path diff;
3. проверить каждый path через fail-closed allowlist;
4. записать `reuseMode=harness-only`;
5. сохранить обе SHA в public evidence.

При package-impacting или unrelated path run завершается до Anki. Новый Fast CI нужен только тогда, когда package действительно может измениться либо existing artifact недоступен/истёк/невалиден.

Подробности: [`e2e-package-harness-reuse.md`](e2e-package-harness-reuse.md).

### Release package

Release handoff проверяет exact current-run artifact и SHA-256 до и после real-Anki execution. Harness-only reuse старого Fast CI package не применяется к release.

## Permissions

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

GHCR login использует `GITHUB_TOKEN`. PAT, OIDC и write permission не нужны.

## Identity boundaries

Раздельные identities:

```text
workflow/harness checkout
Fast CI package
package tested commit
release artifact
environment image
runtime profile
public E2E artifact
```

Workspace и package mounts read-only. Runtime artifacts пишутся в отдельный disposable volume/path.

## Harness staging

Environment image не содержит current product checkout, `.ankiaddon` или E2E harness.

Harness staging выполняется из current validated checkout. Exact prebuilt package монтируется отдельно. Поэтому harness-only fixes могут использовать старый verified package без rebuild environment или add-on.

## Failure behavior

Fail closed при:

- invalid/expired/ambiguous Fast CI run;
- diagnostics/package metadata mismatch;
- package SHA/size mismatch;
- non-ancestor package commit;
- forbidden changed path;
- GHCR digest/platform/label mismatch;
- package hash mismatch после E2E.

Никакого cloud source-build fallback нет.

## Verification evidence

Final verified pair:

```text
Fast CI run: 30013925137
package commit: bd0355c315197cfb659cb28b32b63a4931b73458
package SHA-256: 3ae8439ba18cac82b7e8bb6b240223970cb6403130abf1f909168273ff39baf8

final full E2E run: 30022393738
harness commit: 1a84eabaacb5c368f92ae4952e732d8610619f95
reuse mode: harness-only
result: PASS
```

Исторические отчёты:

- [`../reports/ci/ci-optimization-stage-6a-ghcr-consumer-validation.md`](../reports/ci/ci-optimization-stage-6a-ghcr-consumer-validation.md)
- [`../reports/ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md`](../reports/ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md)
- [`../reports/ci/real-deck-e2e-foundation-closeout.md`](../reports/ci/real-deck-e2e-foundation-closeout.md)

## Дальнейшие изменения

Не возвращать competing cloud consumer, mutable tags, BuildKit/GHA cache или source-build fallback без отдельного архитектурного решения и новых измерений.

Не запускать новый Fast CI только из-за allowlisted harness-only изменения.
