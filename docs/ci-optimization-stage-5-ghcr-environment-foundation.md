# CI optimization Stage 5: stable GHCR E2E environment foundation

## Status and scope

This document defines the first part of the original Stage 5 CI optimization.
It adds the producer-side foundation for a reusable E2E environment image, but
it does **not** publish an image and does not switch the current E2E consumer.

The foundation branch is based on:

```text
f2178f4c2b749bb1d52893373e060603d169a0d4
```

The producer workflow is manual-only. GitHub accepts `workflow_dispatch` only
after the workflow file exists in the default branch, so initial publication is
a separate post-integration action.

## Environment boundary

The stable boundary is:

```text
environment image
├─ pinned Playwright/browser runtime
├─ Ubuntu system libraries
├─ Anki 26.05
├─ Python runtime and anki==26.5
├─ Node.js inherited from the pinned Playwright base
├─ pnpm 9.15.9 and Playwright 1.55.1 Node packages
├─ minimal runtime tools
└─ empty runtime directories

exact checkout mount (/workspace:ro)
├─ current E2E orchestration
├─ browser/API smoke scripts
├─ validators
├─ fixtures
└─ current repository context

exact package mount (/e2e/local-input:ro)
└─ anki_study_report.ankiaddon

results mount (/e2e/artifacts)
└─ runtime evidence
```

The four concepts remain distinct:

```text
environment image
≠ test harness
≠ tested add-on
≠ E2E artifacts
```

Only `docker/anki-e2e/install-anki.sh` is copied into the environment image
because it is part of environment installation. Current orchestration scripts,
product source, dashboard manifests/lockfiles, `.ankiaddon` files, Git metadata,
profiles, logs, screenshots, caches and tokens are excluded.

## Versioned specification

The source of truth is:

```text
docker/anki-e2e/environment-image-spec.json
```

Schema v1 fixes:

```text
environment: env-v1
image: ghcr.io/aliceliddell01/anki-study-report-e2e
platform: linux/amd64
Playwright image: mcr.microsoft.com/playwright:v1.55.1-noble
Playwright base digest: sha256:2f29369043d81d6d69a815ceb80760f55e85f5020371ad06a4d996f18503ad1c
Playwright package: 1.55.1
Anki Desktop: 26.05
Anki archive SHA-256: 6223d705563f71ab40ce072a5d96a3919c546d5dde1e4c49dc27975e70067274
Python package: anki==26.5
pnpm: 9.15.9
human tag: env-v1-anki26.05-pw1.55.1
```

The Playwright digest was recovered from a successful BuildKit provenance record
for `linux/amd64`. The Dockerfile pins both tag and digest. The Node runtime is
transitively pinned by that immutable Playwright base digest; it is not coupled
to the product `.node-version` file.

The validator rejects unknown fields, non-canonical JSON, mutable or uppercase
image identity, invalid digests/platforms/versions, secret markers and local
paths. The environment revision must change before any deliberate replacement
of the deterministic human tag.

## Dockerfile and build context

The environment-only Dockerfile is separate from the current local/production
fallback:

```text
docker/anki-e2e/environment.Dockerfile
docker/anki-e2e/Dockerfile                  unchanged
```

Its dedicated ignore file defaults to excluding the complete repository and
re-includes only:

```text
docker/anki-e2e/environment.Dockerfile
docker/anki-e2e/install-anki.sh
```

Normal frontend, Python add-on, test and harness changes therefore do not enter
the build context and do not invalidate the environment layers.

The image has no project entrypoint. It uses `WORKDIR /workspace` and neutral
`CMD ["bash"]`; a future Stage 6 consumer must explicitly execute the current
harness from the read-only checkout mount.

## Producer workflow

The future producer is:

```text
.github/workflows/e2e-environment-image.yml
name: E2E Environment Image
trigger: workflow_dispatch only
runner: ubuntu-24.04
platform: linux/amd64
```

Permissions are limited to:

```yaml
contents: read
packages: write
id-token: write
attestations: write
```

The workflow uses `GITHUB_TOKEN` through `docker/login-action`; no PAT is
required. Every external action is pinned to a full immutable commit SHA.

The workflow will:

1. validate the versioned specification;
2. calculate a contract SHA-256 over the spec, Dockerfile, dedicated ignore file
   and Anki installer;
3. authenticate to GHCR and configure Buildx;
4. check the deterministic tag before publication;
5. publish only when the tag is absent;
6. fail closed if the tag exists with another contract SHA-256;
7. idempotently reuse the exact digest when the existing tag has the same
   contract;
8. build and push exactly `linux/amd64` without `type=gha` cache;
9. consume the build action's exact digest;
10. generate registry-backed GitHub provenance attestation using the image name
    without a tag and the exact digest;
11. pull the image back by digest and inspect platform/labels;
12. run runtime, Chromium, Anki and forbidden-content smoke checks;
13. demonstrate read-only checkout and exact-package mount boundaries;
14. write sanitized schema-versioned JSON/Markdown metadata;
15. upload the metadata artifact and job summary.

The producer enables BuildKit provenance and SBOM output. GitHub attestation
storage-record creation is explicitly disabled, so the declared permissions
remain the minimal set above; the signed container attestation is still pushed
to the registry.

## Tags and digests

The human tag is deterministic and exists only for navigation:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e:env-v1-anki26.05-pw1.55.1
```

`latest` is forbidden. A future consumer must use:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:<published-digest>
```

No published digest exists in this foundation stage and none is recorded here.
The digest will be taken only from a successful registry publication and
round-trip verification.

## Published metadata contract

`scripts/validate_e2e_environment_image.py` supports:

```text
validate-spec
contract-hash
write-published-metadata
validate-published-metadata
render-markdown
```

Published schema v1 binds repository/workflow identity, source commit, actual
image revision, run identity, image/tag/digest/platform, environment revision,
contract digest, base digest, attestation result, smoke result and an exact copy
of the validated environment specification. JSON and Markdown writes are
atomic and deterministic. Tokens, authorization data and absolute local paths
are rejected.

## Current consumer invariants

This foundation does not modify:

```text
.github/workflows/ci-e2e.yml
docker/anki-e2e/Dockerfile
docker/anki-e2e/docker-compose.yml
```

Therefore the following remain unchanged:

- source-build, Fast CI artifact and release artifact modes;
- current Buildx build/load path;
- current `type=gha` BuildKit cache;
- containerd image store setup;
- local image fallback;
- real-Anki lifecycle and canonical commands;
- package validation/handoff;
- artifact preparation, redaction and upload;
- release workflow.

Stage 6 will separately validate an opt-in digest-pinned consumer before any
permanent cutover or removal of the cloud GHA BuildKit cache.

## Publication and visibility

No GHCR package is created by this foundation branch. No package visibility or
repository setting is changed.

Public visibility is the recommended eventual setting for this public
repository, but visibility remains a separate explicit owner decision after the
first successful publication. The workflow never changes it automatically.

## Verification boundary

Static tests validate the specification, Dockerfile, ignore file, producer
workflow, metadata schema, deterministic outputs, action pinning, collision
safety and unchanged current consumer contracts.

The foundation is not runtime-complete until a networked local machine performs:

```powershell
docker buildx imagetools inspect `
  mcr.microsoft.com/playwright:v1.55.1-noble@sha256:2f29369043d81d6d69a815ceb80760f55e85f5020371ad06a4d996f18503ad1c

docker build `
  --file docker/anki-e2e/environment.Dockerfile `
  --tag anki-study-report-e2e-environment:stage5-local `
  .
```

The local image must then pass version, browser, Anki, directory, forbidden
content and read-only mount smoke checks. Full real-Anki Docker E2E is not part
of this foundation stage.

No producer workflow should be dispatched before its integration into
`master`, because `workflow_dispatch` requires the workflow file to exist in the
default branch.
