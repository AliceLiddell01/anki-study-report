# CI optimization Stage 6A: opt-in GHCR consumer validation

## Status

```text
Implementation: COMPLETE ON FEATURE BRANCH
Local verification: PENDING
Cloud validation: PENDING
Default consumer: buildkit
Release consumer: buildkit
Stage 6B: NOT STARTED
```

Stage 6A adds a digest-pinned GHCR environment-image consumer to the existing
`Full Docker / Anki E2E` workflow without changing its default BuildKit path.
This document must not be changed to `COMPLETE` until the focused local checks,
canonical non-Docker gate, same-package targeted comparison and final GHCR full
gate have passed.

## Branch and base

```text
branch: chatgpt/ci-optimization-stage-6a-ghcr-consumer-validation
base master: 0584fa072eb85d3f02d3b4b3d8c15611242d20ad
PR: absent
```

No permanent cutover is part of this stage.

## Stage 5 reuse precondition

The post-portability producer reuse proof was executed manually on `master`:

```text
workflow: E2E Environment Image
run ID: 29573061110
source SHA: 0584fa072eb85d3f02d3b4b3d8c15611242d20ad
publish_required: false
environment: env-v1
human tag: env-v1-anki26.05-pw1.55.1
platform: linux/amd64
contract SHA-256: sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
image digest: sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
attestation status: existing-not-reissued
smoke status: success
created at: 2026-07-17T10:20:15Z
```

The build and attestation steps were skipped while exact digest resolution,
registry inspection, runtime smoke and environment-boundary validation passed.
The producer was not dispatched again during implementation.

## Immutable consumer identity

The versioned consumer lock is:

```text
docker/anki-e2e/environment-image-lock.json
```

Consumers derive one exact reference from `imageName + "@" + imageDigest`:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
```

The lock contains the environment revision, exact digest, `linux/amd64`, human
navigation tag, contract hash, initial publication commit/run and successful
idempotent reuse run. It does not contain tokens, paths, mutable tags or a second
independent exact-reference field.

`scripts/validate_e2e_environment_consumer.py` enforces an exact field allowlist,
canonical JSON, the current environment specification, the published identity
and the known Stage 5 evidence. Its commands are:

```powershell
python scripts/validate_e2e_environment_consumer.py validate-consumer-lock `
  --spec docker/anki-e2e/environment-image-spec.json `
  --lock docker/anki-e2e/environment-image-lock.json

python scripts/validate_e2e_environment_consumer.py render-consumer-reference `
  --spec docker/anki-e2e/environment-image-spec.json `
  --lock docker/anki-e2e/environment-image-lock.json
```

The Stage 5 producer validator and all environment-image inputs remain unchanged.

## Workflow input and allowed combinations

`ci-e2e.yml` now exposes:

```text
environment_image_source = buildkit | ghcr
default = buildkit
```

Allowed package combinations:

```text
buildkit + source-build
buildkit + fast-ci-artifact
buildkit + release-artifact
ghcr    + fast-ci-artifact
ghcr    + release-artifact
```

Rejected before GHCR login or pull:

```text
ghcr + source-build
```

Manual Stage 6A GHCR validation additionally requires `fast_ci_run_id`; release
artifact inputs are not accepted in a manual GHCR dispatch. Release-artifact
support remains a reusable-workflow contract for the later Stage 6B decision.

The concurrency identity includes the image source so matched BuildKit/GHCR
comparison runs do not cancel one another.

## Permissions and authentication

The reusable E2E workflow declares only:

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

The GHCR contour uses the same full-SHA-pinned `docker/login-action` as the
producer and authenticates with:

```text
registry: ghcr.io
username: github.actor
password: github.token
```

No PAT, repository secret, write permission, OIDC permission or attestation
permission was added. A package-access failure is fail-closed and must be fixed
through the package's Actions access settings, not through a PAT fallback or an
automatic visibility change.

The release caller remains unchanged. It does not opt into GHCR and therefore
continues to use the default BuildKit contour. Its reusable-permission startup
contract must be confirmed before cloud E2E validation is considered complete.

## BuildKit contour

When `environment_image_source=buildkit`, the existing workflow retains:

```text
containerd image store setup
Docker Buildx setup
docker/build-push-action build/load
anki-study-report-e2e:ci local alias
type=gha cache-from/cache-to and existing scope
source-build, Fast CI and release package sources
```

The base Compose file and local default commands remain unchanged.

## GHCR contour

When `environment_image_source=ghcr`, the workflow:

1. validates the consumer lock;
2. logs in to GHCR with `GITHUB_TOKEN`;
3. pulls the exact reference with `--platform linux/amd64`;
4. verifies `RepoDigests`;
5. verifies the runtime platform;
6. verifies repository source, environment version and contract OCI labels;
7. verifies the original image revision when the label is present;
8. records pull-and-validation duration and image size;
9. uses no containerd restart, Buildx, image build/load or GHA cache;
10. enters the same canonical real-Anki E2E step used by BuildKit.

There is no tag fallback and no build fallback.

## Current harness bootstrap

The stable environment image intentionally contains no current product source,
`.ankiaddon`, lockfile-driven pnpm store or E2E harness.

`docker/anki-e2e/bootstrap-current-harness.sh` stages the current harness from:

```text
/workspace/docker/anki-e2e
```

into writable:

```text
/e2e/bin
```

The checkout remains mounted read-only. The bootstrap accepts only top-level
regular `*.sh`, `*.py` and `*.mjs` files, rejects symlinks, sorts inputs,
normalizes CRLF, applies executable permissions and preserves the established
browser-smoke rename contract:

```text
smoke-browser.mjs         -> smoke-browser-core.mjs
smoke-browser-wrapper.mjs -> smoke-browser.mjs
```

It verifies the required entrypoint, run, lifecycle and browser scripts before
executing the existing entrypoint. It does not stage the package and performs no
network installation.

## Compose and wrapper

`docker/anki-e2e/docker-compose.ghcr.yml` is applied only in GHCR mode. It:

```text
uses ANKI_E2E_IMAGE as the exact reference
sets pull_policy: never
starts the checkout bootstrap through /bin/bash
keeps the base volumes and security boundary
```

It does not hardcode a second digest, add privileges, host networking, Docker
socket access or capabilities.

`scripts/run_anki_e2e_docker.ps1` keeps `ImageSource=buildkit` as its default.
GHCR mode requires `NoBuild`, an exact digest reference and a prebuilt package,
rejects `BuildOnly` and source-build, and uses one Compose-file list for config,
run and ownership restoration. The wrapper never performs a registry pull.

## Observability and provenance

Image source and package source remain independent axes.

The workflow writes a sanitized:

```text
e2e-artifacts/reports/environment-image-provenance.json
```

with bounded image, package and checkout identity. The public exporter copies
and redacts this report and adds the following fields to its summary:

```text
imageSource
imageReference
imageDigest
imagePlatform
imagePreparationDurationMs
imageSizeBytes
environmentContractSha256
environmentPublicationRunId
environmentReuseVerificationRunId
cacheState
```

BuildKit semantics:

```text
imageSource: buildkit
imageDigest: null
dockerBuildDurationMs: existing build/load duration
imagePreparationDurationMs: existing build/load duration
cacheState: gha-enabled
```

GHCR semantics:

```text
imageSource: ghcr
imageDigest: exact sha256 digest
dockerBuildDurationMs: 0
imagePreparationDurationMs: exact pull and validation duration
cacheState: ghcr-digest
```

A successful GHCR export fails closed if pull duration is supplied as Docker
build duration. The Markdown summary labels GHCR preparation separately and
does not claim a Docker build occurred.

## Tests added or updated

Focused coverage includes:

```text
consumer lock schema and identity drift
workflow inputs, permissions and concurrency
GHCR/source-build rejection order
BuildKit/GHCR conditional contours
pinned login and exact digest pull
current harness bootstrap boundary
Compose override security boundary
PowerShell wrapper fail-closed behavior
BuildKit and GHCR observability semantics
release caller remains implicit BuildKit
existing workflow regression expectations
external action full-SHA pins
```

The bootstrap `bash -n` assertion runs when Bash is available and skips on the
Windows Fast CI runner; cloud GHCR execution provides the Linux runtime proof.

## Required verification before completion

Local/static:

```powershell
python scripts/validate_e2e_environment_consumer.py validate-consumer-lock `
  --spec docker/anki-e2e/environment-image-spec.json `
  --lock docker/anki-e2e/environment-image-lock.json

python -m pytest `
  tests/test_e2e_environment_consumer.py `
  tests/test_ci_e2e_environment_observability.py `
  tests/test_ci_e2e_workflow.py `
  tests/test_ci_e2e_artifacts.py `
  tests/test_ci_e2e_handoff_hotfix.py `
  tests/test_ci_e2e_artifact_permissions.py `
  tests/test_release_workflow.py `
  tests/test_e2e_environment_image.py

.\scripts\run_full_check.ps1 -SkipDocker
```

Also required:

```text
YAML and JSON parse
Python compile
PowerShell parse
bash -n on Linux
git diff --check
action full-SHA pin scan
secret/path scan
base Compose config
GHCR merged Compose config
release reusable-workflow startup regression
```

Cloud sequence:

1. one Fast CI run on the exact branch HEAD;
2. BuildKit `standard/settings` control using that Fast CI run;
3. GHCR `standard/settings` experiment using the same Fast CI run;
4. one GHCR `standard/full` gate only after the targeted experiment passes.

No strict-APKG, Perf100, warm repeat, second full, release or producer run belongs
to Stage 6A verification.

## Acceptance boundary

Stage 6A remains incomplete until the comparison proves the same workflow SHA,
checkout SHA, Fast CI run, tested SHA and `.ankiaddon` SHA-256 across BuildKit
and GHCR, and the final GHCR full gate passes with sanitized artifacts.

No PR, merge, permanent cutover, cache removal or Stage 6B work is authorized by
this document.

## Official references

- GitHub Packages from Actions:
  <https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions>
- Package permissions:
  <https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages>
- GitHub Container Registry:
  <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
- Workflow permissions and reusable workflows:
  <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
  and
  <https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations>
- Docker digest pull:
  <https://docs.docker.com/reference/cli/docker/image/pull/>
  and <https://docs.docker.com/dhi/core-concepts/digests/>
- Compose services and merge rules:
  <https://docs.docker.com/reference/compose-file/services/>
  and <https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/>
