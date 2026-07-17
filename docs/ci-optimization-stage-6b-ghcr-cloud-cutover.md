# CI optimization Stage 6B: permanent GHCR cloud cutover

## Status

```text
Stage 6B implementation: COMPLETE ON FEATURE BRANCH
Mandatory master precondition: PASS
Focused/static verification: PASS
Canonical local non-Docker: PENDING
Exact branch Fast CI: PENDING
GHCR targeted settings: PENDING
GHCR standard/full: PENDING
Release-artifact rehearsal: PENDING
PR: ABSENT
master changed: NO
```

This document records the permanent cloud architecture change after the Stage 6A
opt-in comparison. Until the pending branch and release-artifact cloud gates pass,
the stage is implementation-complete but not accepted as fully complete.

## Repository snapshot

```text
repository: AliceLiddell01/anki-study-report
base branch: master
actual base SHA: b707edec3e35c266a27dd5ae384cc4213abbbf6c
feature branch: chatgpt/ci-optimization-stage-6b-ghcr-cloud-cutover
pre-documentation implementation SHA: dc8af57b03bab2e58c692384c5cf5233cfbe55dc
```

The current base is ten commits ahead of the original Stage 6A merge SHA
`7cb8d1a6facc78cc70821a59de514f7497183432`. The only intervening change that
altered this CI contour granted `packages: read` to the reusable release caller
and aligned its test; later telemetry/signals commits did not change the Docker
consumer architecture.

## Mandatory post-merge master precondition

The final run of the transitional Stage 6A interface was executed before any
Stage 6B code change.

```text
master SHA: b707edec3e35c266a27dd5ae384cc4213abbbf6c
Fast CI run: 29589429944
Fast package SHA-256: a8c90798675d66b1ececde0722149de4c1e3e8a9e9e7e9ab12e4dac7e15dd4bc
GHCR E2E run: 29590681695
mode/scope: standard/settings
result: success
artifact manifest: success
```

Exact environment identity:

```text
image: ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
platform: linux/amd64
environment: env-v1
contract: sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
publication run: 29561205765
idempotent reuse run: 29573061110
```

The run used the exact Fast CI package and skipped containerd image-store,
Buildx, image build/load and GHA cache steps. GHCR login, exact digest pull,
platform/OCI-label checks, canonical real-Anki E2E, package hash verification,
redacted artifact export and cleanup all passed.

## Accepted architecture

### Cloud consumer

`.github/workflows/ci-e2e.yml` is GHCR-only:

```text
manual workflow_dispatch package source: fast-ci-artifact
reusable release package source: release-artifact
optional reusable package source: fast-ci-artifact
cloud source-build: rejected before registry login
cloud environment: exact GHCR digest only
```

Removed from the cloud workflow:

```text
environment_image_source
containerd image-store setup
docker/setup-buildx-action
docker/build-push-action
cache-from/cache-to type=gha
BuildKit cache scope
anki-study-report-e2e:ci mutable runtime alias
gha-enabled cloud evidence
```

The GHCR preparation sequence is unconditional:

1. validate the versioned consumer lock;
2. authenticate to `ghcr.io` with `GITHUB_TOKEN`;
3. pull the exact reference with `--platform linux/amd64`;
4. verify `RepoDigests`, platform and bounded OCI labels;
5. validate merged base + GHCR Compose configuration;
6. run the existing canonical Docker-only real-Anki contour;
7. export sanitized package/environment evidence.

### Package identity

The existing exact-artifact handoff remains authoritative:

- Fast CI run and artifacts are resolved by API and exact artifact IDs;
- transport digest validation remains fail-closed;
- diagnostics derives the exact tested commit;
- E2E checks out that commit before package staging;
- package metadata, size and inner SHA-256 are validated;
- release artifact SHA-256 is validated before and after real-Anki execution;
- partial, conflicting or invalid package inputs never fall back to source build.

### Permissions and registry access

The reusable workflow declares only:

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

The release caller grants the same read permissions to the called workflow.
Authentication uses `${{ github.token }}`; no PAT, repository secret, OIDC or
write package permission was added. Package visibility/access remains unchanged,
and a permission or pull failure is terminal.

### Observability

Every successful current cloud artifact must report:

```text
imageSource: ghcr
imageReference: exact digest reference
imageDigest: sha256:bce788...
imagePlatform: linux/amd64
imagePreparationDurationMs: pull plus validation
imageSizeBytes: inspected image size
environmentContractSha256: sha256:8d3c...
environmentPublicationRunId: 29561205765
environmentReuseVerificationRunId: 29573061110
cacheState: ghcr-digest
dockerBuildDurationMs: 0
```

Historical BuildKit summaries remain parseable for old evidence, but current
cloud workflow code cannot generate `buildkit`, `gha-enabled` or `type=gha`
results. The GHCR pull duration is not represented as a Docker build duration.

## Preserved local fallback

The cutover does not remove or rename:

```text
docker/anki-e2e/Dockerfile
docker/anki-e2e/docker-compose.yml
scripts/run_anki_e2e_docker.ps1
scripts/run_full_check.ps1 local Docker paths
source-build local behavior
BuildOnly local behavior
```

The local wrapper may still select `buildkit` or fail-closed `ghcr` diagnostic
mode. Base Compose still contains the local build definition and read-only
workspace/package mounts. This is a local development/reproduction contour, not
an undocumented cloud fallback.

## Implementation commits before documentation

```text
21bc8b74708bde8060d2cbecc25e1f42c7990703
ci: make GHCR the only cloud E2E environment

92812491542e0949c3aa22944758e6a59e3cfc8e
test: lock the GHCR-only cloud E2E contract

dc8af57b03bab2e58c692384c5cf5233cfbe55dc
test: preserve exact GHCR identity and local Docker fallback
```

The implementation diff at `dc8af57...` changes only the cloud workflow and two
directly related test modules. It is three commits ahead of and zero commits
behind the recorded base.

## Focused and static verification completed

Completed before documentation commit:

```text
YAML parse of the updated workflow
Python compile of changed test modules
full-SHA external Action pin scan
consumer-lock identity review
release caller permission/call-site review
package handoff review
base and GHCR Compose/security-boundary review
no-match scan of current ci-e2e.yml
GitHub blob identity check for every written implementation file
branch/base compare: ahead 3, behind 0
```

Required no-match values absent from current `.github/workflows/ci-e2e.yml`:

```text
type=gha
cache-from
cache-to
setup-buildx-action
build-push-action
containerd-snapshotter
environment_image_source
anki-study-report-e2e:ci
gha-enabled
```

No real release, AnkiWeb deployment, environment-image publication, package
visibility change, PR, merge, force-push or master write was performed.

## Remaining acceptance gates

After the final documentation SHA is pushed:

1. run canonical `./scripts/run_full_check.ps1 -SkipDocker` locally;
2. run manual Fast CI on the exact feature-branch SHA;
3. run `standard/settings` with workers `3`, telemetry/restart disabled and the
   exact Fast CI run ID;
4. after targeted PASS, run one `standard/full` with the same package;
5. create an isolated temporary rehearsal branch from the exact implementation
   SHA, build an internal release artifact, call the local reusable E2E workflow
   with `release_artifact_name` and SHA-256, save evidence, then delete the
   temporary branch;
6. update this document with exact run/artifact identities and final status.

The real `release.yml` workflow must not be dispatched for rehearsal. Strict
APKG, Perf100, producer republish, warm repeats and a second full run are outside
this stage.

## Performance interpretation

Stage 6A GHCR targeted reference:

```text
run: 29577800196
image preparation: 36.323 s
canonical E2E: 38.926 s
```

The Stage 6B targeted run should be compared with that GHCR run for image
preparation, canonical E2E, workflow/job elapsed, artifact finalization and image
size. Removing unreachable BuildKit conditions is not assumed to create a new
causal speedup. The permanent value is a single cloud architecture and the end
of GHA BuildKit cache writes.

## Historical relationship to Stage 6A

Stage 6A was the opt-in validation phase: BuildKit remained the default and GHCR
proved exact-package functional equivalence. Stage 6B removes that transition
switch and makes the already published digest the only cloud consumer. Stage 6A
timings and run identities remain historical evidence and are not rewritten.

## Official references

- GitHub reusable workflow permissions:
  <https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations>
- GitHub workflow permissions syntax:
  <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
- GitHub Packages from Actions:
  <https://docs.github.com/en/packages/managing-github-packages-using-github-actions-workflows/publishing-and-installing-a-package-with-github-actions>
- GitHub Container Registry:
  <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
- Package permissions:
  <https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages>
- Docker pull by digest and platform:
  <https://docs.docker.com/reference/cli/docker/image/pull/>
- Docker digest semantics:
  <https://docs.docker.com/dhi/core-concepts/digests/>
