# CI Stage 6 — GHCR consumer validation and permanent cloud cutover

**Status:** Complete

## Stage 6A — Opt-in validation — Complete

Stage 6A добавил digest-pinned GHCR environment consumer как opt-in рядом с
существующим BuildKit path и доказал функциональную эквивалентность:

- exact `linux/amd64` digest;
- lock/spec/contract/OCI validation;
- current harness из exact read-only checkout;
- exact Fast CI package handoff;
- matched targeted BuildKit/GHCR runs;
- GHCR `standard/full` PASS;
- bounded provenance и отдельное измерение image preparation.

Historical evidence:
`../../reports/ci/ci-optimization-stage-6a-ghcr-consumer-validation.md`.

## Stage 6B — Permanent cloud cutover — Complete

Stage 6B удалил transitional selector и competing cloud BuildKit/GHA-cache path.
Cloud real-Anki E2E теперь всегда использует exact GHCR digest.

Удалено из cloud workflow:

```text
environment_image_source
containerd image-store setup
docker/setup-buildx-action
docker/build-push-action
BuildKit build/load
type=gha cache-from/cache-to
mutable local cloud image alias
```

Сохранено:

- exact Fast CI artifact handoff для manual/reusable E2E;
- exact release artifact handoff для gated release;
- fail-closed package SHA-256 validation;
- read-only checkout/package mounts;
- `GITHUB_TOKEN` с `contents: read`, `actions: read`, `packages: read`;
- local Dockerfile/Compose build path и `BuildOnly` для разработки/диагностики;
- один canonical real-Anki contour.

Финальная Stage 6B проверка включала exact Fast CI, targeted GHCR E2E и
изолированный release-artifact `standard/full` rehearsal. Production release,
tag, draft release, deployment, Environment approval и AnkiWeb publication не
создавались.

Current operational contract: `../../docs/ghcr-e2e-consumer.md`.
Historical evidence:
`../../reports/ci/ci-optimization-stage-6b-ghcr-cloud-cutover.md`.

## Result

```text
cloud E2E environment: immutable GHCR digest only
manual package source: exact Fast CI artifact
release package source: exact release artifact
local Docker build: development/diagnostic fallback
cloud BuildKit/GHA cache: removed
```

## Out of scope

- bake add-on или current harness в environment image;
- mutable tag/`latest` runtime identity;
- PAT fallback;
- automatic environment publication on every product commit;
- removal of local Docker build support;
- product or release-semantic changes outside the accepted exact-artifact gate.
