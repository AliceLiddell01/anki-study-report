# CI Stage 5 — Stable GHCR E2E environment image

**Status:** Complete on producer/publication side

## Выполнено

- Versioned environment spec.
- Separate environment-only Dockerfile/build context.
- Pinned Playwright base digest, Anki 26.05, Python/Node/pnpm runtime.
- Manual producer workflow with GHCR login, provenance/SBOM, contract hash и smoke.
- Deterministic human tag и immutable digest.
- Initial publication/round-trip verification.
- Cross-platform line-ending normalization preserving published contract identity.

## Не выполнено этим этапом

- Current E2E consumer не переключён на GHCR.
- GHA BuildKit cache не удалён.
- Add-on/harness не запечены в image.

## Canonical docs/evidence

- `docs/ci-optimization-stage-5-ghcr-environment-foundation.md`
- `reports/ci/ci-optimization-stage-5-ghcr-publication-closeout.md`
