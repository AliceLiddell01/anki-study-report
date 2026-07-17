# CI optimization Stage 6B: permanent GHCR cloud cutover

## Status

```text
Overall Stage 6B status: COMPLETE
Implementation: COMPLETE ON FEATURE BRANCH
Mandatory master precondition: PASS
Focused/static verification: PASS
Canonical local non-Docker: PASS
Exact final Fast CI: PASS
GHCR targeted settings: PASS
GHCR standard/full: PASS
Release-artifact rehearsal: PASS
PR: ABSENT
master changed: NO
```

Stage 6B removes the competing BuildKit/GHA-cache cloud consumer and makes the
existing immutable GHCR environment image the only cloud environment for
real-Anki Docker E2E. Both package-source paths are now proven:

```text
fast-ci-artifact -> exact tested commit -> exact GHCR digest -> real Anki
release-artifact -> exact SHA-256 -> exact GHCR digest -> real Anki
```

No production release, tag, draft release, attestation, deployment, GitHub
Environment request or AnkiWeb publication was created during validation.

## Repository snapshot

```text
repository: AliceLiddell01/anki-study-report
base branch: master
base SHA: b707edec3e35c266a27dd5ae384cc4213abbbf6c
feature branch: chatgpt/ci-optimization-stage-6b-ghcr-cloud-cutover
final validated implementation SHA: 2de0bc3908a4e6ca8a46ae4fc920fc0ea826b244
rehearsal branch: chatgpt/ci-optimization-stage-6b-release-rehearsal
rehearsal SHA: 5fe2c9a28f0b8ed7245d93750a6a305e13993476
PR: absent
master changed: no
```

The rehearsal branch differs from the final implementation only by the temporary
replacement of `.github/workflows/ci-fast.yml` used as an isolated manual caller.
The production workflow and runtime tested by that rehearsal come from the same
commit lineage rooted at `2de0bc3...`.

## Mandatory current-master precondition

The transitional Stage 6A interface was exercised on current `master` before the
Stage 6B implementation:

```text
master SHA: b707edec3e35c266a27dd5ae384cc4213abbbf6c
Fast CI run: 29589429944
Fast package SHA-256: a8c90798675d66b1ececde0722149de4c1e3e8a9e9e7e9ab12e4dac7e15dd4bc
GHCR E2E run: 29590681695
mode/scope: standard/settings
result: success
artifact manifest: success
```

The run used the exact Fast CI package and exact immutable GHCR image. Buildx,
BuildKit build/load, containerd image-store setup and GHA cache steps were
skipped.

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
gha-enabled current cloud evidence
```

The current sequence is:

1. validate exact package-source inputs;
2. reject source-build before registry work;
3. validate the versioned environment consumer lock;
4. expose exact image identity;
5. authenticate to GHCR with `GITHUB_TOKEN`;
6. pull the exact digest with `--platform linux/amd64`;
7. verify digest, platform and bounded OCI labels;
8. validate merged base + GHCR Compose;
9. run canonical Docker-only real-Anki E2E;
10. verify the exact package hash and export sanitized evidence;
11. collect diagnostics and clean Docker state safely, including early failures.

The final reusable-input validation no longer relies on `github.event_name`.
GitHub associates the called workflow's `github` context with the caller, so
package-source validation is performed from the validated input combination
instead.

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

The lock, digest, environment image and package visibility were not changed.

## Permissions and security boundary

The reusable workflow and release caller use only:

```yaml
permissions:
  contents: read
  actions: read
  packages: read
```

Registry authentication uses `${{ github.token }}`. No PAT, OIDC, package write
permission, repository-secret fallback, mutable tag identity, token-bearing URL
or automatic package visibility change was introduced.

The existing read-only workspace/package mounts and local Docker fallback remain
intact. The local BuildKit path is a development/reproduction contour and is not
a cloud fallback.

## Local and static verification

The implementation and the final reusable-release fix passed:

```text
focused Stage 6B and release-workflow tests: PASS
canonical run_full_check.ps1 -SkipDocker: PASS
frontend typecheck/tests/build/bundle guard: PASS
full Python suite: PASS
package build/check: PASS
YAML parse: PASS
git diff --check: PASS
consumer-lock validation: PASS
release caller permission/call-site checks: PASS
base and GHCR Compose/security-boundary checks: PASS
full-SHA Action pin checks: PASS
secret/private-path checks: PASS
```

Generated `__pycache__`, `.pyc` and pytest cache outputs were removed or disabled
before the canonical gate and were not committed.

## Validation runs

| Purpose | Run ID | SHA | Package source | Scope | Result |
| --- | ---: | --- | --- | --- | --- |
| Current-master precondition Fast CI | `29589429944` | `b707edec3e35c266a27dd5ae384cc4213abbbf6c` | producer | n/a | PASS |
| Current-master precondition GHCR E2E | `29590681695` | `b707edec3e35c266a27dd5ae384cc4213abbbf6c` | fast-ci-artifact | settings | PASS |
| Initial Stage 6B Fast CI | `29597756429` | `e679ef840fb8cd802e39bb3775e4a9e6c848f0fd` | producer | n/a | PASS |
| Initial Stage 6B targeted | `29598022118` | `e679ef840fb8cd802e39bb3775e4a9e6c848f0fd` | fast-ci-artifact | settings | PASS |
| Initial Stage 6B full | `29598160051` | `e679ef840fb8cd802e39bb3775e4a9e6c848f0fd` | fast-ci-artifact | full | PASS |
| Release-artifact rehearsal | `29602512427` | `5fe2c9a28f0b8ed7245d93750a6a305e13993476` | release-artifact | full | PASS |
| Final exact Fast CI | `29603448342` | `2de0bc3908a4e6ca8a46ae4fc920fc0ea826b244` | producer | n/a | PASS |
| Final GHCR targeted | `29603659625` | `2de0bc3908a4e6ca8a46ae4fc920fc0ea826b244` | fast-ci-artifact | settings | PASS |

## Final exact Fast CI evidence

```text
run: 29603448342
tested SHA: 2de0bc3908a4e6ca8a46ae4fc920fc0ea826b244
package SHA-256: 9509361bb4b6575b11180c514a4aae9bd7420e609e0413128afa768bf0d7f2b1
package size: 612878 bytes
package artifact ID: 8415973844
package artifact digest: sha256:fee4e2e0d5a935d7f6ee789dfb3d563f616ccc5f2153eecc253274c1d4ae2c9e
diagnostics artifact ID: 8415973287
diagnostics artifact digest: sha256:a4696a5044a22cd2afecb14cedd4f89da26eeb43b6f19c29f4390a7b9eba117b
result: success
```

The metadata, uploaded package bytes, E2E handoff evidence and package preserved
after real-Anki execution all contain the same SHA-256 and size.

## Final targeted settings evidence

```text
run: 29603659625
SHA: 2de0bc3908a4e6ca8a46ae4fc920fc0ea826b244
Fast CI source run: 29603448342
package SHA-256: 9509361bb4b6575b11180c514a4aae9bd7420e609e0413128afa768bf0d7f2b1
artifact ID: 8416021691
artifact digest: sha256:2511274b98d4ea05e8e9ed3fdb901822a11aba09419a3af986a2ef0828ccc96d
package source: fast-ci-artifact
image source: ghcr
image preparation: 48.367 s
canonical E2E: 33.471 s
workflow summary duration: 96 s
docker build duration: 0 ms
cache state: ghcr-digest
artifact manifest: success
```

The artifact contains 32 settings screenshots and clean first-start API/browser
evidence. The release-artifact steps were skipped, while exact Fast CI
resolution, diagnostics validation, exact checkout, package validation, GHCR
pull and package hash verification all passed.

## Release-artifact rehearsal evidence

```text
run: 29602512427
rehearsal SHA: 5fe2c9a28f0b8ed7245d93750a6a305e13993476
base implementation SHA: 2de0bc3908a4e6ca8a46ae4fc920fc0ea826b244
release version/channel: 1.1.0 / stable
release package SHA-256: 64f604e7dc47994878b0710fb07b0cce893d42b24f710b071560b01d7b243060
release package size: 612878 bytes
release bundle artifact ID: 8415609847
release bundle digest: sha256:a690faee9ed929ce59a1b7384460de0a65195141372854cf056b0b4dcbd4e219
E2E artifact ID: 8415728329
E2E artifact digest: sha256:d67f7ed7f18c80d8019228f0d2b3220cd902e9420355c66fb637ab75202713bd
package source: release-artifact
scope: full
image preparation: 46.438 s
canonical E2E: 207.401 s
workflow summary duration: 280 s
docker build duration: 0 ms
cache state: ghcr-digest
artifact manifest: success
```

The exact release package SHA-256 was checked before real-Anki execution and
again against the package emitted by the E2E artifact. The values matched
exactly. Fast CI resolution/download steps were correctly skipped.

The full artifact contains 124 screenshots, first/restart API evidence,
APKG/problematic-card coverage, card preview evidence, notification restart
persistence, telemetry restart proof, search and FSRS reports, redacted runtime
evidence and clean browser/API/security failure surfaces.

## Performance interpretation

The final targeted run reported:

```text
GHCR exact pull/validation: 48.367 s
canonical settings E2E: 33.471 s
workflow summary: 96 s
```

Stage 6A and earlier Stage 6B targeted timings remain historical reference
points. Cross-run runner and registry variance is not treated as a causal
performance claim. The permanent Stage 6B value is the single cloud
architecture and elimination of GHA BuildKit cache writes.

## Not performed

- no environment image rebuild or republish;
- no package visibility change;
- no PAT or new secret;
- no real release, tag, draft GitHub Release or attestation;
- no GitHub Environment/deployment request;
- no AnkiWeb publication;
- no PR or merge;
- no write to `master`;
- no strict-APKG, Perf100, warm repeat or unnecessary second full run;
- no next optimization stage.

## Decision

```text
Stage 6B COMPLETE.

The GHCR-only cloud cutover passed the exact Fast CI package path, the isolated
release-artifact full rehearsal, exact package/hash handoff, immutable
environment validation, canonical real-Anki E2E and sanitized evidence export.
```

## Next action

Delete the temporary rehearsal branch locally and remotely, then prepare the
Stage 6B integration PR as a separate explicit action. Do not merge or change
`master` until that PR is reviewed.
