# CI optimization Stage 6A: opt-in GHCR consumer validation

## Status

```text
Stage 6A: COMPLETE
Implementation: COMPLETE ON FEATURE BRANCH
Local verification: PASS
Cloud validation: PASS
Default consumer: buildkit
Opt-in consumer: ghcr
Release consumer: buildkit
Stage 6B: NOT STARTED
```

Stage 6A adds and validates a digest-pinned GHCR environment-image consumer for
`Full Docker / Anki E2E` while preserving the existing BuildKit/GHA contour as
the default. The same exact Fast CI package was exercised through BuildKit and
GHCR, and the final standard/full real-Anki contour passed through GHCR.

## Repository snapshot

```text
branch: chatgpt/ci-optimization-stage-6a-ghcr-consumer-validation
initial Stage 5 base: 0584fa072eb85d3f02d3b4b3d8c15611242d20ad
integrated master base: a19887e551f11b95323c82038233c873b0eb9785
validated feature SHA: 5b868a3b432386c4ab1a15de63c160c8697db69b
PR: absent
master changed by Stage 6A: no
```

The branch was synchronized with the newer product/docs work on `master` before
final verification. No permanent cutover is part of this stage.

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
The published environment image was not rebuilt or changed during Stage 6A.

## Immutable consumer identity

The versioned lock is:

```text
docker/anki-e2e/environment-image-lock.json
```

Consumers derive the exact reference from `imageName + "@" + imageDigest`:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
```

`scripts/validate_e2e_environment_consumer.py` enforces the exact field
allowlist, canonical JSON, current environment specification, published digest,
`linux/amd64`, contract hash, publication identity and reuse run identity. It
rejects mutable/tag-only references, `latest`, unknown fields, invalid digests,
invalid runs, local paths and secret-like fields.

## Workflow and package-source contract

`ci-e2e.yml` exposes:

```text
environment_image_source = buildkit | ghcr
default = buildkit
```

Allowed combinations:

```text
buildkit + source-build
buildkit + fast-ci-artifact
buildkit + release-artifact
ghcr    + fast-ci-artifact
ghcr    + release-artifact
```

Rejected before registry login or pull:

```text
ghcr + source-build
```

Manual GHCR validation requires an exact successful `fast_ci_run_id`. The
concurrency identity includes image source, so matched BuildKit/GHCR runs do not
cancel each other.

## Permissions and authentication

The reusable E2E workflow declares only:

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

The GHCR contour authenticates with the full-SHA-pinned `docker/login-action`:

```text
registry: ghcr.io
username: github.actor
password: github.token
```

The exact digest pull succeeded using `GITHUB_TOKEN`; no PAT, repository secret,
write permission, OIDC permission, attestation permission, package visibility
change or token fallback was introduced. The release caller remains unchanged
and therefore remains on the default BuildKit contour.

## BuildKit contour

When `environment_image_source=buildkit`, the workflow retains:

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
2. logs in with `GITHUB_TOKEN`;
3. pulls the exact reference with `--platform linux/amd64`;
4. verifies `RepoDigests`, platform and bounded OCI labels;
5. records exact pull-and-validation telemetry;
6. skips containerd restart, Buildx, image build/load and GHA cache;
7. enters the same canonical real-Anki E2E step used by BuildKit.

There is no tag fallback and no build fallback.

## Current harness bootstrap

The stable environment image intentionally contains no current product source,
`.ankiaddon`, current E2E harness or product lockfile-driven pnpm store.

`docker/anki-e2e/bootstrap-current-harness.sh` stages the current harness from
the exact read-only checkout:

```text
/workspace/docker/anki-e2e -> /e2e/bin
```

It accepts only top-level regular `*.sh`, `*.py` and `*.mjs` files, rejects
symlinks, sorts inputs, normalizes CRLF, applies executable permissions,
preserves the browser-smoke rename contract and executes the existing
entrypoint. It does not stage the package or download scripts/dependencies.

## Compose and wrapper

`docker/anki-e2e/docker-compose.ghcr.yml` applies only in GHCR mode. It uses the
exact `ANKI_E2E_IMAGE`, sets `pull_policy: never`, starts the checkout bootstrap
through `/bin/bash` and preserves the base volumes and security boundary.

It does not add privileges, host networking, Docker socket access, capabilities
or a second hardcoded digest.

`scripts/run_anki_e2e_docker.ps1` keeps `ImageSource=buildkit` as its default.
GHCR mode requires `NoBuild`, an exact digest and a prebuilt package; it rejects
`BuildOnly` and source-build and reuses one Compose-file list for config, run
and ownership restoration. The wrapper itself never performs a registry pull.

## Observability and provenance

Image source and package source remain independent axes. The workflow exports a
sanitized `environment-image-provenance.json` and extends E2E summaries with:

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

BuildKit keeps `dockerBuildDurationMs` and `cacheState=gha-enabled`. GHCR reports
`dockerBuildDurationMs=0`, a separate pull/validation duration and
`cacheState=ghcr-digest`; the GHCR pull is never mislabeled as a Docker build.

## Local verification

The following passed on the integrated feature branch:

```text
consumer lock validation
focused Stage 6A and regression tests
notification-scope regression tests
canonical .\scripts\run_full_check.ps1 -SkipDocker
Python compile
JSON parse
YAML parse
PowerShell parse
Bash syntax on Linux/cloud
external action full-SHA pin scan
git diff --check
secret/private-path scan
base Compose config
merged GHCR Compose config
release workflow regression coverage
```

The Windows-only Bash invocation was made platform-aware; the actual Linux
bootstrap/runtime contract was then exercised successfully by both GHCR cloud
runs.

## Exact Fast CI package

```text
Fast CI run: 29576586996
tested SHA: 5b868a3b432386c4ab1a15de63c160c8697db69b
package SHA-256: a29506fa4d11e2b2a72cd574dc2499c8361847b6f74299e35000ee10d96e96d6
package size: 612920 bytes
```

The package metadata and downloaded `.ankiaddon` bytes agreed exactly.

## Cloud runs

| Purpose | Run ID | SHA | Image source | Package source | Scope | Result |
| --- | ---: | --- | --- | --- | --- | --- |
| Fast CI package producer | `29576586996` | `5b868a3b432386c4ab1a15de63c160c8697db69b` | n/a | producer | n/a | PASS |
| BuildKit targeted control | `29577257753` | `5b868a3b432386c4ab1a15de63c160c8697db69b` | buildkit | fast-ci-artifact | settings | PASS |
| GHCR targeted experiment | `29577800196` | `5b868a3b432386c4ab1a15de63c160c8697db69b` | ghcr | fast-ci-artifact | settings | PASS |
| GHCR final full gate | `29577915730` | `5b868a3b432386c4ab1a15de63c160c8697db69b` | ghcr | fast-ci-artifact | full | PASS |

## Same-package functional equivalence

The targeted runs matched on:

```text
workflow/source SHA
actual checkout SHA
Fast CI run ID
tested SHA
package SHA-256
standard mode
settings scope
three screenshot workers
manifest status
Anki 26.05
32 screenshot paths
```

Both targeted manifests contained the same 12 page, 19 state and 1 zoom
screenshots. BuildKit executed containerd/Buildx/build/cache and skipped GHCR;
GHCR skipped the entire BuildKit contour and successfully executed lock
validation, `GITHUB_TOKEN` login and exact digest pull.

The final GHCR full artifact passed with:

```text
artifact manifest: success
screenshots: 124
page: 48
state: 52
cards: 12
zoom: 10
navigation: 2
first API smoke: PASS
restart API smoke: PASS
notification restart proof: PASS
browser/API/security error arrays: empty
secret/token/private-path scan: PASS
```

The full run used the same tested SHA and exact Fast CI package and preserved the
exact environment digest, contract hash, publication run and reuse run.

## Performance observations

| Metric | BuildKit targeted | GHCR targeted | BuildKit - GHCR |
| --- | ---: | ---: | ---: |
| Image preparation | `64.744 s` | `36.323 s` | `28.421 s` |
| Observed workflow summary | `123 s` | `91 s` | `32 s` |
| Inner canonical E2E | `37.494 s` | `38.926 s` | `-1.432 s` |
| GitHub workflow elapsed | `151 s` | `109 s` | `42 s` |
| GitHub job elapsed | `143 s` | `103 s` | `40 s` |

The direct Stage 6A saving is the `28.421 s` image-preparation reduction. The
larger workflow/job differences are observational runner and artifact-finalizer
variance and are not treated as guaranteed savings. The nearly equal targeted
canonical durations support functional equivalence rather than an E2E-runtime
speed claim.

The final standard/full GHCR run reported:

```text
image preparation: 36.636 s
canonical E2E: 213.366 s
workflow summary: 266 s
GitHub workflow elapsed: 285 s
GitHub job elapsed: 280 s
```

It is a final integration gate, not an apples-to-apples comparison against the
targeted settings runs.

## Existing invariants

```text
BuildKit remains the default E2E consumer.
GHA BuildKit cache remains enabled.
Release remains on the BuildKit path.
The local Docker build fallback remains available.
Base Compose remains the default.
The environment image, digest and revision are unchanged.
Package visibility is unchanged.
No PAT or new secret was introduced.
```

## Not performed

- no permanent GHCR cutover;
- no BuildKit/containerd/Buildx/GHA-cache removal;
- no package visibility change;
- no environment image rebuild or republish;
- no release workflow dispatch;
- no PR or merge into `master`;
- no strict-APKG, Perf100, warm-repeat or second full run;
- no Stage 6B implementation.

## Decision

```text
Stage 6A passed; prepare an integration PR while keeping BuildKit as default.
```

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
- Compose merge rules:
  <https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/>
