# GHCR E2E environment consumer

Снимок контракта: **2026-07-17**.

## Текущее состояние

После CI Stage 6B все cloud real-Anki E2E runs используют один environment path:
точный immutable GHCR digest из
`docker/anki-e2e/environment-image-lock.json`.

```text
Fast CI artifact
  → exact tested commit
  → exact package SHA-256
  → exact GHCR digest
  → real Anki E2E

Release artifact
  → exact package SHA-256
  → exact GHCR digest
  → real Anki E2E
```

Cloud `environment_image_source`, BuildKit build/load, containerd setup,
`docker/setup-buildx-action`, `docker/build-push-action` и `type=gha` cache
удалены. Локальная Dockerfile/Compose build path сохранена для разработки и
диагностики, но не является cloud fallback.

## Immutable identity

Source of truth: `docker/anki-e2e/environment-image-lock.json`.

Consumer принимает только exact `linux/amd64` digest и проверяет environment
contract, platform и bounded OCI labels до запуска Anki. Mutable tag, `latest`,
второй hardcoded digest, PAT fallback и автоматическое изменение package
visibility запрещены.

## Package-source contract

Cloud workflow принимает только:

```text
manual/reusable E2E  → fast-ci-artifact
release caller       → release-artifact
```

Cloud `source-build` отклоняется до registry login. Fast CI handoff проверяет
same-repository successful run, exact tested checkout, package metadata, size и
внутренний SHA-256. Release handoff проверяет exact current-run package SHA-256
до и после real-Anki execution.

## Permissions and mounts

Reusable workflow использует только:

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

GHCR login использует `GITHUB_TOKEN`. Current checkout, tested `.ankiaddon`,
environment image и E2E artifacts остаются разными identities. Workspace и
package mounts сохраняют read-only boundary; runtime artifacts пишутся отдельно.

## Current harness

Environment image не содержит текущий product checkout, `.ankiaddon` или E2E
harness. Harness staging-ится из exact read-only checkout через
`docker/anki-e2e/bootstrap-current-harness.sh` и запускает тот же canonical
real-Anki contour.

## Verification evidence

Stage 6A доказал equivalence opt-in consumer; Stage 6B завершил permanent cloud
cutover. Финальная проверка Stage 6B включала exact Fast CI, targeted GHCR E2E и
изолированный release-artifact `standard/full` rehearsal. Исторические записи:

- `../reports/ci/ci-optimization-stage-6a-ghcr-consumer-validation.md`
- `../reports/ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md`

## Дальнейшие изменения

После Stage 6B нет второго cloud consumer для сравнения или fallback. Любая
следующая оптимизация выполняется только по новым timing/flake measurements и
не должна возвращать BuildKit/GHA cache в cloud contour без отдельного
архитектурного решения.
