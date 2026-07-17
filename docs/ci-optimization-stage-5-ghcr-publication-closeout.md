# CI optimization Stage 5: initial GHCR publication closeout

## Status

```text
Initial publication: COMPLETE
Contract hash portability fix: IMPLEMENTED / LOCALLY VERIFIED
Stage 6: NOT STARTED
```

This document closes the initial publication portion of Stage 5 and records the
follow-up fix that makes the environment contract hash independent of working-tree
line endings. It does not switch the current Docker E2E consumer to GHCR.

## Published identity

The first successful producer run published the stable environment from:

```text
source commit: 298be46ffe84bffa612dd6322dc0421b1ff0955e
workflow: E2E Environment Image
producer run: 29561205765
run attempt: 1
producer job: Build immutable E2E environment
result: success
```

Human-readable navigation tag:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e:env-v1-anki26.05-pw1.55.1
```

Exact immutable image reference:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
```

Published registry identities:

```text
OCI index digest: sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
linux/amd64 image manifest: sha256:23fa970232a9e183fd897f2ceb1f323e6c1661e6244e760a435c3190c472d88b
attestation manifest: sha256:a8c7e60d6535c11d2e2844ee6940f892fb5e48938ba8a17e323d2b5ee1c84106
```

Published environment contract:

```text
environment: env-v1
platform: linux/amd64
contract SHA-256: sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
Playwright base digest: sha256:2f29369043d81d6d69a815ceb80760f55e85f5020371ad06a4d996f18503ad1c
smoke status: success
attestation status: created
created at: 2026-07-17T06:53:59Z
```

The human tag remains navigation-only. Any future consumer must use the exact
image digest reference.

## Publication evidence

Sanitized metadata artifact:

```text
name: e2e-environment-image-env-v1-29561205765-1
artifact ID: 8399382426
transport digest: sha256:2cb3b5e4837ad1041ebd276654f77a2cef4f3b943e5b34c74da98f049cafb821
```

Buildx record:

```text
name: AliceLiddell01~anki-study-report~1S3GK3.dockerbuild
artifact ID: 8399383053
transport digest: sha256:d9f517a8ee00ac82f6651b41247146ddfd0d1b86e586986c7ad7de0775521d0d
```

The metadata JSON, Markdown summary, registry inspection, OCI labels and BuildKit
provenance agree on the source commit, image digest and production contract
hash.

## Contract hash discrepancy

An earlier Windows completion report recorded:

```text
sha256:d16eb7b3d1d0fcda02d478c1a4a5d83872360c91bf3b620461d7e71e3b3b9a96
```

That value is superseded and is not the production environment identity. The
successful Linux producer and every published evidence surface record:

```text
sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
```

The original validator hashed raw working-tree bytes. Three contract inputs had
no explicit Git working-tree EOL policy, so the hash could vary with CRLF/LF
checkout semantics. The evidence is consistent with Windows CRLF versus Linux LF
working-tree bytes; the exact bytes from the earlier Windows checkout were not
retained, so that historical checkout is not claimed as independently proven.

The portability fix reads each contract input as strict UTF-8 text, rejects a
UTF-8 BOM, NUL bytes and invalid UTF-8, then performs only:

```text
CRLF -> LF
lone CR -> LF
```

It preserves spaces, trailing whitespace, final-newline presence, Unicode code
points, labels, input order, byte lengths after canonicalization and the existing
`anki-study-report-e2e-environment-contract-v1` framing. Meaningful text changes
continue to change the hash.

`.gitattributes` also pins `text eol=lf` for the specification, environment
Dockerfile and dedicated Docker ignore file. The installer remains covered by
the existing `docker/anki-e2e/*.sh text eol=lf` rule. No repository-wide
renormalization was performed.

## Immutable published image

This validator-only fix does not rebuild, replace or mutate the published image:

```text
ghcr.io/aliceliddell01/anki-study-report-e2e@sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
```

An OCI/Docker digest is a content identifier. The already published bytes and
digest remain unchanged when repository-side validation logic is corrected.
Package visibility and access settings are also unchanged.

## Verification

The portability regression contour proves:

- LF, CRLF, mixed LF/CRLF and lone CR variants produce the same hash;
- current canonical source files produce the published `8d3c...` golden value;
- character, instruction, version/digest, trailing-space and final-newline
  changes alter the hash;
- framing labels and input order remain significant;
- UTF-8 BOM, NUL and invalid UTF-8 fail closed;
- exact LF attributes cover all four contract inputs;
- sanitized publication identity matches run `29561205765`.

No Docker build or real-Anki E2E was required because no image input, producer
workflow, consumer workflow, Compose runtime or package handoff changed.

## Protected invariants

Unchanged:

```text
docker/anki-e2e/environment-image-spec.json
docker/anki-e2e/environment.Dockerfile
docker/anki-e2e/environment.Dockerfile.dockerignore
docker/anki-e2e/install-anki.sh
.github/workflows/e2e-environment-image.yml
.github/workflows/ci-e2e.yml
docker/anki-e2e/Dockerfile
docker/anki-e2e/docker-compose.yml
scripts/run_anki_e2e_docker.ps1
.github/workflows/release.yml
```

Therefore unchanged:

- environment revision and human tag;
- Anki, Playwright, Python and pnpm versions;
- producer action pins and permissions;
- current consumer Buildx/GHA-cache architecture;
- source-build, Fast CI artifact and release artifact modes;
- exact package handoff;
- E2E scopes and release delivery.

## Next gate

After this fix is merged, dispatch the producer once as a separate verification
action. The expected idempotent result is:

```text
same human tag
same contract hash: sha256:8d3c11ccdd9c474c751ea7fe4e845f67f21a388484cc4291c3ea2ee06cba5447
same image digest: sha256:bce7889f4db861c1b539b0747b4bbf0fcc68c38d520090a0836b1fe9a7a2b475
publish_required=false
attestationStatus=existing-not-reissued
```

Do not start Stage 6 or modify the E2E consumer until that reuse proof has been
reviewed independently.

## References

- Git attributes and EOL normalization: <https://git-scm.com/docs/gitattributes>
- Docker image digest semantics: <https://docs.docker.com/dhi/core-concepts/digests/>
- Pulling an image by digest: <https://docs.docker.com/reference/cli/docker/image/pull/>
- GHCR container registry: <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>
