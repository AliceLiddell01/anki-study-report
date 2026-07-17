# CI optimization Stage 6B: permanent GHCR cloud cutover

## Status

```text
Overall Stage 6B status: PARTIAL
Implementation: COMPLETE ON FEATURE BRANCH
Mandatory master precondition: PASS
Focused/static verification: PASS
Canonical local non-Docker: PASS
Exact branch Fast CI: PASS
GHCR targeted settings: PASS
GHCR standard/full: PASS
Release-artifact rehearsal: NOT RUN — GitHub workflow_dispatch default-branch limitation
PR: ABSENT
master changed: NO
```

Stage 6B permanently removes the competing BuildKit/GHA-cache cloud consumer and
makes the existing immutable GHCR environment image the only cloud environment
for real-Anki Docker E2E. The implementation and Fast CI package path are fully
validated. The stage remains `PARTIAL`, rather than `COMPLETE`, because the
required isolated release-artifact rehearsal cannot be dispatched from a
branch-only temporary workflow without first placing that workflow on the
default branch. Modifying `master` for a rehearsal or dispatching the real
release workflow is outside the authorized scope.

## Repository snapshot

```text
repository: AliceLiddell01/anki-study-report
base branch: master
actual base SHA: b707edec3e35c266a27dd5ae384cc4213abbbf6c
feature branch: chatgpt/ci-optimization-stage-6b-ghcr-cloud-cutover
validated feature SHA: e679ef840fb8cd802e39bb3775e4a9e6c848f0fd
branch relative to base after validation fixes: ahead 15 / behind 0
PR: absent
master changed: no
```

The base is ten commits ahead of the Stage 6A merge SHA
`7cb8d1a6facc78cc70821a59de514f7497183432`. The intervening CI-relevant change
granted `packages: read` to the reusable release caller and aligned its tests.
Later product, telemetry and signals commits did not change the Docker consumer
architecture.

## Mandatory post-merge master precondition

The transitional Stage 6A interface was exercised on current `master` before any
Stage 6B implementation change:

```text
master SHA: b707edec3e35c266a27dd5ae384cc4213abbbf6c
Fast CI run: 29589429944
Fast package SHA-256: a8c90798675d66b1ececde0722149de4c1e3e8a9e9e7e9ab12e4dac7e15dd4bc
GHCR E2E run: 29590681695
mode/scope: standard/settings
result: success
artifact manifest: success
```

The run used the exact Fast CI package, exact tested commit and immutable GHCR
image. Containerd, Buildx, image build/load and GHA cache steps were skipped;
GHCR login, digest/platform/OCI-label verification, canonical E2E, package hash
verification, artifact export and cleanup passed.

## Accepted cloud architecture

`.github/workflows/ci-e2e.yml` is GHCR-only:

```text
manual workflow_dispatch package source: fast-ci-artifact
reusable release package source: release-artifact
optional reusable package source: fast-ci-artifact
cloud source-build: rejected before registry login
cloud environment identity: exact GHCR digest only
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

The unconditional cloud sequence is:

1. validate the versioned consumer lock;
2. expose the exact immutable identity before registry work so failure cleanup
   remains deterministic;
3. authenticate to `ghcr.io` with `GITHUB_TOKEN`;
4. pull with `--platform linux/amd64` by exact digest;
5. verify `RepoDigests`, platform and bounded OCI labels;
6. validate merged base + GHCR Compose configuration;
7. run the existing canonical Docker-only real-Anki contour;
8. verify the exact package hash and export sanitized evidence.

## Exact environment identity

```text
image: ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
platform: linux/amd64
environment: env-v1
contract: sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
publication run: 29561205765
idempotent reuse run: 29573061110
image size: 3760013645 bytes
```

The lock and digest are unchanged. No image build, publication, tag mutation,
package-visibility change or PAT was introduced.

## Package identity and release caller

The existing exact-artifact handoff remains fail-closed:

- Fast CI run and artifacts are resolved through exact API identities;
- artifact transport digests are checked;
- diagnostics derive the exact tested commit;
- E2E checks out that commit before staging the package;
- metadata, size and internal SHA-256 are checked;
- release artifact SHA-256 is checked before and after real-Anki execution;
- conflicting, incomplete or invalid inputs never fall back to source-build.

The reusable workflow and release caller use only:

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

Registry authentication uses `${{ github.token }}`. No PAT, OIDC, package write
permission, repository secret fallback or automatic visibility change exists.

## Preserved local fallback

The cloud cutover does not remove or rename:

```text
docker/anki-e2e/Dockerfile
docker/anki-e2e/docker-compose.yml
scripts/run_anki_e2e_docker.ps1
scripts/run_full_check.ps1 local Docker paths
source-build local behavior
BuildOnly local behavior
```

Base Compose still contains the local image build definition and read-only
workspace/package mounts. The local wrapper may use its existing `buildkit`
path or fail-closed GHCR diagnostic mode. This is a local development and
reproduction contour, not an undocumented cloud fallback.

## Local and static verification

The final validated feature SHA passed:

```text
focused Stage 6B tests: 144 passed / 2 skipped
canonical run_full_check.ps1 -SkipDocker: PASS
full Python suite inside canonical gate: 668 passed / 4 skipped
frontend test files: 48 passed
frontend tests: 266 passed
frontend typecheck: PASS
frontend production build and bundle guard: PASS
package build and validation: PASS
YAML parse: PASS
git diff --check: PASS
consumer lock and exact identity checks: PASS
release caller permission/call-site checks: PASS
base and GHCR Compose/security-boundary checks: PASS
full-SHA Action pin checks: PASS
secret/private-path checks: PASS
```

Required no-match values are absent from current cloud workflow:

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

Artifact upload still intentionally uses `compression-level: 0`; that setting is
scoped to `actions/upload-artifact` and is not Docker BuildKit cache behavior.

## Exact branch Fast CI

```text
run: 29597756429
SHA: e679ef840fb8cd802e39bb3775e4a9e6c848f0fd
package SHA-256: 1ad9004a9492d7175e4ea9537079f3eed354bd3c9e8f8b656a58a11ee39a15fd
package size: 612878 bytes
package artifact ID: 8413815728
package artifact digest: sha256:2f19171f5ee5862af066fc95975d822d070bbf41ff92cb9e4770214259937bca
diagnostics artifact ID: 8413814951
diagnostics digest: sha256:88d31130c2aeb3557d0c1a754906e69cfb7fa3c44e8c40a2c492734daf42870f
result: success
```

## Cloud validation runs

| Purpose | Run ID | SHA | Package source | Scope | Result |
| --- | ---: | --- | --- | --- | --- |
| Fast CI package producer | `29597756429` | `e679ef840fb8cd802e39bb3775e4a9e6c848f0fd` | producer | n/a | PASS |
| GHCR targeted gate | `29598022118` | `e679ef840fb8cd802e39bb3775e4a9e6c848f0fd` | fast-ci-artifact | settings | PASS |
| GHCR final integration gate | `29598160051` | `e679ef840fb8cd802e39bb3775e4a9e6c848f0fd` | fast-ci-artifact | full | PASS |

Both E2E runs used the same exact Fast CI package and exact tested checkout.
Their jobs executed lock validation, `GITHUB_TOKEN` login, exact digest pull,
Compose validation, canonical real-Anki E2E, package hash verification, public
artifact preparation/upload and cleanup successfully. The release-artifact
steps were correctly skipped in these Fast CI package runs.

### Targeted settings evidence

```text
run: 29598022118
artifact ID: 8413869478
artifact digest: sha256:3d2fbff5b2d655381562c9d824161e4dc8893a77afaf341437c53ff05b1fac30
package source: fast-ci-artifact
screenshots: 32 (12 page / 19 state / 1 zoom)
image preparation: 39.151 s
canonical E2E: 37.935 s
workflow summary duration: 95 s
docker build duration: 0 ms
cache state: ghcr-digest
artifact manifest: success
```

### Final standard/full evidence

```text
run: 29598160051
artifact ID: 8413996722
artifact digest: sha256:36520bb57a6cd242d97b70be56969167978779dae703d41f9ec35a76fd969541
package source: fast-ci-artifact
screenshots: 124
page: 48
state: 52
cards: 12
zoom: 10
navigation: 2
image preparation: 36.392 s
canonical E2E: 220.373 s
workflow summary duration: 276 s
docker build duration: 0 ms
cache state: ghcr-digest
artifact manifest: success
```

The full artifact contains first and restart API evidence, APKG/card preview
coverage, notification restart persistence, telemetry restart proof, search and
FSRS reports, redacted runtime data and empty browser/API/security failure
surfaces required by the manifest contract.

## Performance interpretation

Stage 6A GHCR targeted reference:

```text
run: 29577800196
image preparation: 36.323 s
canonical E2E: 38.926 s
```

Stage 6B targeted:

```text
run: 29598022118
image preparation: 39.151 s
canonical E2E: 37.935 s
```

Observed difference:

```text
image preparation: +2.828 s (+7.8%)
canonical E2E: -0.991 s (-2.5%)
```

These are normal cross-run variations of the same GHCR architecture. They do
not support a new causal speed claim. The value of Stage 6B is removal of the
duplicate cloud BuildKit path and termination of GHA BuildKit cache writes.

## Release-artifact rehearsal limitation

The requested rehearsal design requires a new temporary workflow file on a
branch and a manual `workflow_dispatch` against that branch. GitHub only accepts
`workflow_dispatch` events when the workflow file exists on the default branch.
A new branch-only workflow therefore cannot be manually dispatched.

The following alternatives were deliberately rejected:

- temporarily writing the rehearsal workflow to `master`;
- replacing `release.yml` on a temporary branch to exploit an already registered
  workflow path;
- adding a push trigger instead of the required manual-only trigger;
- dispatching the real release workflow;
- creating a release, tag, attestation, deployment or AnkiWeb environment request.

No rehearsal branch or temporary workflow was created because it could not be
executed under the specified contract. Per Stage 6B acceptance rules this makes
the final result `PARTIAL`, not `COMPLETE`, and does not invalidate the proven
Fast CI package GHCR-only path.

Official platform references:

- <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch>
- <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatch>
- <https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow>

## Historical relationship to Stage 6A

Stage 6A was the opt-in validation phase: BuildKit remained the default and GHCR
proved exact-package functional equivalence. Stage 6B later removed that
transition switch and made GHCR the only cloud consumer on its feature branch.
Stage 6A timings and identities remain historical evidence and are not rewritten.

## Not performed

- no release-artifact rehearsal because its branch-only manual workflow cannot
  receive `workflow_dispatch`;
- no environment image rebuild or republish;
- no package visibility change;
- no PAT or new secret;
- no real release, tag, draft release, attestation or AnkiWeb publication;
- no GitHub Environment/deployment request;
- no PR, merge, force-push or write to `master`;
- no strict-APKG, Perf100, warm repeat or second full run;
- no next optimization stage.

## Decision

```text
GHCR-only manual E2E passed; release rehearsal remains unavailable under the
required branch-only workflow_dispatch contract. Stage 6B status is PARTIAL.
```

## Recommended next action

Prepare an integration PR only after explicitly deciding whether to accept the
static release caller proof plus the fully validated Fast CI package path, or to
add a permanent non-release rehearsal entrypoint on `master` in a separately
reviewed stage. Do not weaken release safety or run the real release merely to
obtain rehearsal evidence.
